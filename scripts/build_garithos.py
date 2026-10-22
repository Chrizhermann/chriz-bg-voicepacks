"""Package the user's preassigned legacy Garithos set, without changing audio."""
from __future__ import annotations

import argparse
import io
import json
import re
import wave
from pathlib import Path

from build_release import HELPER_SHA256, PREFLIGHT, ROOT, sha256, write_zip

MOD = "cd_garith"
PREFIX = "CGARIT"
VERSION = "1.1.0"
WEIDU_SHA256 = "0d17e26e3f3ef5b36796eb0ee8ae73cb851d8b62c9702c2e224da2945caafb75"

# The supplied filenames already follow the documented legacy BG2 convention.
# Do not recurate, invent missing lines, or treat action 4-7 as rare selection.
SLOTS = {
    "a": ("battlecry1", "Battle cry 1", 9, 9),
    "8": ("battlecry2", "Battle cry 2", 10, 10),
    "9": ("battlecry3", "Battle cry 3", 11, 11),
    "b": ("leader1", "Becoming leader", 6, 6),
    "d": ("bored1", "Bored", 8, 8),
    "f": ("common1", "Selected 1", 26, 26),
    "g": ("common2", "Selected 2", 27, 27),
    "h": ("common3", "Selected 3", 28, 28),
    "0": ("common4", "Selected 4", 29, 29),
    "i": ("action1", "Action acknowledgement 1", 32, 32),
    "j": ("action2", "Action acknowledgement 2", 33, 33),
    "k": ("action3", "Action acknowledgement 3", 34, 34),
    "s": ("action4", "Action acknowledgement 4", 79, 35),
    "t": ("action5", "Action acknowledgement 5", 80, 36),
    "u": ("action6", "Action acknowledgement 6", 81, 37),
    "v": ("action7", "Action acknowledgement 7", 82, 38),
    "l": ("damage1", "Taking damage", 18, 18),
    "m": ("dying1", "Dying", 19, 19),
    "n": ("forest", "Forest", 21, 21),
    "o": ("city", "City", 22, 22),
    "p": ("dungeon", "Dungeon", 23, 23),
    "z": ("criticalhit", "Critical hit", 65, 65),
    "1": ("criticalmiss", "Critical miss", 66, 66),
}

DUPLICATE_GUARD = r"""
// Normal WeiDU reinstall removes this pack first. Reject orphan registrations.
COPY_EXISTING ~charsnd.2da~ ~override~
  COUNT_2DA_COLS garith_cols
  READ_2DA_ENTRIES_NOW garith_header (garith_cols - 1)
  FOR (garith_col = 0; garith_col < garith_cols - 1; ++garith_col) BEGIN
    READ_2DA_ENTRY_FORMER garith_header 0 garith_col garith_header_name
    PATCH_IF (~%garith_header_name%~ STRING_EQUAL_CASE ~CGARIT~) BEGIN
      PATCH_FAIL @73
    END
  END
  BUT_ONLY

ACTION_IF FILE_EXISTS_IN_GAME ~M_cdsnd.lua~ BEGIN
  COPY_EXISTING ~M_cdsnd.lua~ ~override~
    COUNT_REGEXP_INSTANCES ~^[ %TAB%]*filenames_stringrefs[ %TAB%]*\[[ %TAB%]*['"]CGARIT['"][ %TAB%]*\][ %TAB%]*=~ garith_menu_count
    PATCH_IF (garith_menu_count > 0) BEGIN PATCH_FAIL @73 END
    BUT_ONLY
END
"""


def build(source: Path, manifest_path: Path, helper: Path, weidu: Path,
          output: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == VERSION and manifest["menu_name"] == "Garithos"
    source = source.resolve()
    output = output.resolve()
    assert not output.is_relative_to(source), "Never write into the user's source"
    assert not output.exists() or not any(output.iterdir()), "Use an empty output folder"
    assert not any((p / "chitin.key").exists() for p in [output, *output.parents]), "Output must not be inside a game"
    expected = {f"garitho{suffix}.wav" for suffix in SLOTS}
    portraits = {record["source_file"].lower(): record for record in manifest.get("portraits", [])}
    actual = {p.name.lower() for p in source.iterdir() if p.is_file()}
    assert actual == expected | portraits.keys(), ("Unexpected or missing source files", actual ^ (expected | portraits.keys()))
    clips = {record["source_file"]: record for record in manifest["clips"]}
    assert len(clips) == len(manifest["clips"]) == len(SLOTS) and set(clips) == expected
    helper_bytes, weidu_bytes = helper.read_bytes(), weidu.read_bytes()
    assert sha256(helper_bytes) == HELPER_SHA256, "Unreviewed helper"
    assert sha256(weidu_bytes) == WEIDU_SHA256, "Unreviewed WeiDU binary"

    files = {
        f"setup-{MOD}.exe": weidu_bytes,
        f"{MOD}/tph/cd_add_soundset.tph": helper_bytes,
    }
    for name, record in portraits.items():
        assert re.fullmatch(r"[a-z0-9]+\.bmp", name)
        data = (source / record["source_file"]).read_bytes()
        assert sha256(data) == record["sha256"]
        files[f"Extras/Portraits/{record['source_file']}"] = data
    records, copy_lines, calls, translations = [], [], [], []
    for number, (suffix, (key, label, bg1_row, bg2_row)) in enumerate(SLOTS.items(), 1):
        original = f"garitho{suffix}.wav"
        clip = clips[original]
        data = (source / original).read_bytes()
        assert sha256(data) == clip["sha256"], (original, "Source changed")
        subtitle = clip["subtitle"]
        assert isinstance(subtitle, str) and not any(c in subtitle for c in "~\r\n[]")
        subtitle.encode("ascii")  # English punctuation is portable across game encodings.
        with wave.open(io.BytesIO(data), "rb") as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) == (1, 2, 22050, "NONE")
            frames = wav.getnframes()
            pcm = wav.readframes(frames)
            assert len(pcm) == frames * 2 and frames > 0
        target = PREFIX + suffix
        assert re.fullmatch(r"[A-Za-z0-9]{7}", target)
        files[f"{MOD}/sounds/{target}.wav"] = data
        copy_lines.append(f"COPY ~%MOD_FOLDER%/sounds/{target}.wav~ ~lang/%EE_LANGUAGE%/sounds/{target}.wav~")
        calls.append(f"    cd_{key:<19} = RESOLVE_STR_REF(@{number})")
        translations.append(f"@{number} = ~{subtitle}~ [{target.upper()}]")
        records.append({
            "source_file": original, "slot_key": key, "slot_label": label,
            "bgee_sod_row": bg1_row, "bg2ee_eet_row": bg2_row,
            "target_resref": target.upper(), "tra": number, "subtitle": subtitle,
            "nonverbal": not bool(subtitle), "sample_rate": 22050, "channels": 1,
            "bits_per_sample": 16, "frames": frames, "duration_seconds": round(frames / 22050, 6),
            "source_sha256": clip["sha256"], "wav_sha256": sha256(data),
            "pcm_sha256": sha256(pcm),
        })

    tp = f"""BACKUP ~{MOD}/backup~
SUPPORT ~https://github.com/Chrizhermann/chriz-bg-voicepacks~
VERSION ~{VERSION}~

LANGUAGE ~English~ ~english~ ~%MOD_FOLDER%/english/setup.tra~

BEGIN @0
DESIGNATED 0
LABEL ~Chriz-Garithos-Soundset~

{PREFLIGHT}
{DUPLICATE_GUARD}
INCLUDE ~%MOD_FOLDER%/tph/cd_add_soundset.tph~

// Explicit allowlist; unrelated or retired WAVs must not fill absent slots.
{chr(10).join(copy_lines)}

LAF cd_add_soundset
  INT_VAR
{chr(10).join(calls)}
    cd_select_name       = RESOLVE_STR_REF(@70)
  STR_VAR cd_name = "{PREFIX}"
END
"""
    tra = "\n".join([
        "// English subtitles, transcribed from the supplied audio. No invented grunts.",
        "@0 = ~Garithos - player voicepack~", *translations,
        "@70 = ~Garithos~",
        "@71 = ~This voicepack requires Baldur's Gate: Enhanced Edition (with or without Siege of Dragonspear), Baldur's Gate II: Enhanced Edition, or Enhanced Edition Trilogy (EET).~",
        "@72 = ~This voicepack requires the EE 2.6 soundset table (charsnd.2da rows 1-99). Your game has an older or incompatible soundset layout.~",
        "@73 = ~A Garithos (CGARIT) soundset registration already exists. Uninstall its original installer before adding this package; no duplicate registration was added.~", "",
    ])
    files[f"{MOD}/{MOD}.tp2"] = tp.encode("ascii")
    files[f"{MOD}/english/setup.tra"] = tra.encode("ascii")
    provenance = {
        "version": VERSION, "menu_name": "Garithos", "mod": MOD, "prefix": PREFIX,
        "source_archetype": "User-supplied legacy BG2 player soundset",
        "source_collection": manifest["source_archive"] + "/GARITHOS",
        "source_archive_sha256": manifest["source_archive_sha256"],
        "source_compiler": "IAIWE (original Lord Garithos soundset and portraits)",
        "recordings": "Lord Garithos, Warcraft III: The Frozen Throne (Blizzard Entertainment)",
        "mapping_method": "Preserve legacy filename suffixes; translate action 4-7 rows for BGEE/SoD with the pinned EE Soundset Tool helper.",
        "audio_processing": "None. Every WAV is byte-identical to the corresponding supplied file.",
        "subtitle_method": manifest["subtitle_method"],
        "helper_sha256": HELPER_SHA256, "weidu_sha256": WEIDU_SHA256,
        "portraits": list(portraits.values()),
        "slots": records,
    }
    files[f"{MOD}/provenance.json"] = (json.dumps(provenance, indent=2) + "\n").encode("utf-8")
    slot_map = [
        "# Garithos: supplied soundset assignments", "",
        "These are the existing source assignments, not new clip selections. All 23 files are preserved, including the longer clips. No TTS, trimming, duplication, or filler was added.", "",
        "| Slot | Original file | Installed sound | BGEE/SoD row | BG2EE/EET row | Subtitle |",
        "|---|---|---|---:|---:|---|",
    ]
    for r in records:
        text = r["subtitle"] or "(Nonverbal; intentionally no subtitle)"
        slot_map.append(f"| {r['slot_label']} | {r['source_file']} | {r['target_resref']} | {r['bgee_sod_row']} | {r['bg2ee_eet_row']} | {text} |")
    slot_map += [
        "", "## Intentionally unfilled", "",
        "No source clip was supplied for these events: morale break/panic; happy/unhappy/breaking point; tired; badly hurt; day/night; companion death; rare selection/rare action; ineffective attack; inventory full; pickpocketing; stealth; spell interrupted; setting a trap. Additional variation slots beyond the ones above are also empty. NPC-only dialogue/interaction rows and unused table rows are not filled.", "",
        "An empty assignment is -1, not a random substitute or reused clip. The exact registered rows and file hashes are in provenance.json.", "",
    ]
    files[f"{MOD}/SLOT_MAP.md"] = "\n".join(slot_map).encode("utf-8")
    readme = f"""Garithos player voicepack v{VERSION}

23 original clips, 22 English spoken subtitles, and one nonverbal damage sound.
The character voice menu shows exactly: Garithos

CHANGES FROM 1.0.0 (the supplied Lord Garithos v2.zip)
- Bored: added "Can't you idiots follow simple orders? ... having a picnic!"
- Dying: "Is the nightmare finally over?"
- Critical hit: "Humanity will rise again."
- Tired: now empty; the old clip has moved to Dying.
- The former "elf witch" critical-hit clip is no longer in the supplied set.
- Two supplied portraits are preserved unchanged in Extras/Portraits.
  The voice installer does not install or change any portrait.

SUPPORTED GAMES
Baldur's Gate: Enhanced Edition, with or without Siege of Dragonspear;
Baldur's Gate II: Enhanced Edition; Enhanced Edition Trilogy (EET).
Requires the Enhanced Edition 2.6-style 99-row soundset table.
Not an installer for the original non-Enhanced BG1/BG2 games or Icewind Dale.
English audio and subtitles are installed into the language you select.

INSTALL (Windows)
1. Close the game, InfinityLoader, and save editors such as EEKeeper.
2. Extract setup-{MOD}.exe and the {MOD} folder into the actual game
   folder containing chitin.key and Baldur.exe. Keep the folder structure.
3. Run setup-{MOD}.exe. Choose your game's language when asked, then install
   the Garithos component. Do not just copy the sound files on their own.
4. Choose Garithos in character creation or Record -> Customize -> Sounds.
   Spoken text appears when the game's character-sound subtitles are enabled.

UNINSTALL / REINSTALL
Close the game and editors. Run the same installer and select Uninstall or
Reinstall. Keep the {MOD}/backup folder after installing so WeiDU can restore
the previous state. No save-file editing is needed. On an existing character,
reselect Garithos under Customize -> Sounds to refresh its stored slot references.
If other mods were installed after Garithos, normal WeiDU reinstallation can
reinstall that later mod stack; do not interrupt it.

WHAT WAS PRESERVED
IAIWE's GARITHOS folder was already a classic BG2-style soundset. Its
23 filename-based assignments are retained. Every WAV is unchanged: mono,
16-bit PCM, 22050 Hz. Longer clips are not cut. Missing slots stay empty.
The resource prefix changes from GARITHO to CGARIT; the menu name is Garithos.
Action acknowledgements 4-7 are mapped to the correct rows in each EE game.
See {MOD}/SLOT_MAP.md for the complete file, text, and slot list.

SUBTITLES
Subtitles follow the v2 audio and filenames, not the former slot text. Existing
subtitles were retained only for byte-identical recordings. The new bored line
was transcribed locally with Whisper large-v3 and cross-checked with base.en;
large-v3 recognizes "picnic", where base.en misrecognizes "pet neck". Punctuation
was reviewed. The nonverbal clip has no invented text. No manual audition claimed.

CREDITS / PROVENANCE
Original soundset: IAIWE (Lord Garithos v2, GARITHOS folder), including the
two portraits in Extras/Portraits.
Recordings: Lord Garithos from Warcraft III: The Frozen Throne
(Blizzard Entertainment).
This package is a conversion, not a claim of authorship of the recordings
or of IAIWE's soundset.
EE Soundset Tool helper: CamDawg / Graion Dilach and contributors.
https://github.com/Gibberlings3/EE_soundset_tool
Installer: WeiDU 25100, https://github.com/WeiDUorg/weidu
Conversion project: https://github.com/Chrizhermann/chriz-bg-voicepacks

No game installation is performed when this archive is created. The accompanying
verification report records disposable installer tests, not an in-game playtest.
"""
    files["README-Garithos.txt"] = readme.encode("utf-8")
    output.mkdir(parents=True, exist_ok=True)
    package = output / "Garithos Voicepack"
    package.mkdir()
    for name, data in files.items():
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archive = output / f"garithos-player-voicepack-v{VERSION}.zip"
    write_zip(archive, files)
    (output / "SHA256SUMS").write_text(f"{sha256(archive.read_bytes())}  {archive.name}\n", encoding="ascii")
    print(f"Built {archive}: {len(records)} preserved assignments, byte-identical WAVs.")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--weidu", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "custom/garithos/voicepack.json")
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    build(options.source, options.manifest, options.helper, options.weidu, options.output)
