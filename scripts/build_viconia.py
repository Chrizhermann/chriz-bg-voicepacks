"""Reconstruct Viconia (BG1 or BG2) only from her companion's recorded sound slots.

The game directories are read-only sources. Outputs must be outside every game.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import wave
from pathlib import Path

from build_ajantis import GameResources, sha256
from build_release import HELPER_SHA256, PREFLIGHT, write_zip

VERSION = "1.0.0"

# Original BGEE VICONI.CRE slot -> helper name, TRA id, resource suffix.
# BGEE's 35-38 are rare selection despite their legacy SELECT_ACTION names.
# The helper translates these to 75-78 on BG2EE/EET, never to movement 35-38.
# They are not duplicated into the rare action slots 63/64. She has no city line.
BG1_SLOTS = {
    1: ("morale_break1", 52, "u_"), 2: ("happy", 45, "r_"),
    3: ("unhappy_1", 68, "5_"), 4: ("unhappy_2", 69, "6_"),
    5: ("breaking_pt", 23, "j_"), 6: ("leader1", 50, "b"),
    7: ("tired1", 65, "c"), 8: ("bored1", 21, "d"),
    9: ("battlecry1", 16, "a"), 18: ("damage1", 34, "l"),
    19: ("dying1", 40, "m"), 20: ("hurt1", 46, "e"),
    21: ("forest", 42, "n"), 23: ("dungeon", 39, "p"),
    24: ("day", 37, "q"), 25: ("night", 54, "r"),
    26: ("common1", 25, "f"), 27: ("common2", 26, "g"),
    28: ("common3", 27, "h"), 32: ("action1", 1, "i"),
    33: ("action2", 2, "j"), 34: ("action3", 3, "k"),
    35: ("select_rare1", 56, "w_"), 36: ("select_rare2", 57, "x_"),
    37: ("select_rare3", 58, "y_"), 38: ("select_rare4", 59, "z_"),
    53: ("gen_death1", 43, "w"),
}

# Original BG2EE VICONI16.CRE slot -> helper name, TRA id, resource suffix.
# BG2's 35-38 are action acknowledgements 4-7; the helper moves them to 79-82 on BGEE.
BG2_SLOTS = {
    1: ("morale_break1", 52, "u_"), 2: ("happy", 45, "r_"),
    3: ("unhappy_1", 68, "5_"), 4: ("unhappy_2", 69, "6_"),
    5: ("breaking_pt", 23, "j_"), 6: ("leader1", 50, "b"),
    7: ("tired1", 65, "c"), 8: ("bored1", 21, "d"),
    9: ("battlecry1", 16, "a"), 10: ("battlecry2", 17, "8"),
    11: ("battlecry3", 18, "9"), 18: ("damage1", 34, "l"),
    19: ("dying1", 40, "m"), 20: ("hurt1", 46, "e"),
    21: ("forest", 42, "n"), 22: ("city", 24, "o"),
    23: ("dungeon", 39, "p"), 24: ("day", 37, "q"),
    25: ("night", 54, "r"), 26: ("common1", 25, "f"),
    27: ("common2", 26, "g"), 28: ("common3", 27, "h"),
    29: ("common4", 28, "0"), 30: ("common5", 29, "k_"),
    31: ("common6", 30, "l_"), 32: ("action1", 1, "i"),
    33: ("action2", 2, "j"), 34: ("action3", 3, "k"),
    35: ("action4", 4, "s"), 36: ("action5", 5, "t"),
    37: ("action6", 6, "u"), 38: ("action7", 7, "v"),
    63: ("action_rare1", 8, "x"), 64: ("action_rare2", 9, "y"),
    65: ("criticalhit", 32, "z"), 66: ("criticalmiss", 33, "1"),
    67: ("immune", 48, "2"), 68: ("inventory", 49, "3"),
    71: ("disrupted", 38, "6"),
}

VARIANTS = {
    "bg1": {
        "mod": "cd_vicbg1", "prefix": "VICOB1", "menu": "Viconia (BG1)", "label": "Chriz-Viconia-BG1-Companion-Soundset",
        "creatures": ("VICONI", "VICONI4", "VICONI6"), "slots": BG1_SLOTS,
        "source_game": "Unmodified BGEE English", "source_name": "BGEE", "era": "BG1",
        "title": "Viconia (BG1): original BG1 companion soundset",
        "translation": "BGEE rare selection 35-38 -> BG2EE/EET rare selection 75-78; all other assigned rows unchanged.",
        "rows": ("BGEE row", "BG2EE/EET row"), "moved": lambda slot: slot + 40 if 35 <= slot <= 38 else slot,
    },
    "bg2": {
        "mod": "cd_vicbg2", "prefix": "VICOB2", "menu": "Viconia (BG2)", "label": "Chriz-Viconia-BG2-Companion-Soundset",
        "creatures": ("VICONI16", "VICONI6", "VICONI8", "VICONI9", "VICONI11", "VICONI13"), "slots": BG2_SLOTS,
        "source_game": "Unmodified BG2EE English", "source_name": "BG2EE", "era": "BG2/ToB",
        "title": "Viconia (BG2): original BG2/ToB companion soundset",
        "translation": "BG2EE/EET action acknowledgements 4-7 (rows 35-38) -> BGEE rows 79-82; all other assigned rows unchanged.",
        "rows": ("BG2EE/EET row", "BGEE row"), "moved": lambda slot: slot + 44 if 35 <= slot <= 38 else slot,
    },
}
# CRE rows that can feed a player event in either era; the remainder are NPC-only.
PLAYER_SOURCE_SLOTS = set(range(1, 39)) | {53} | set(range(63, 74)) | set(range(75, 100))

DUPLICATE_GUARD = r"""
// Fail closed on an orphan/duplicate column; normal WeiDU reinstall removes it first.
COPY_EXISTING ~charsnd.2da~ ~override~
  COUNT_2DA_COLS {var}_cols
  READ_2DA_ENTRIES_NOW {var}_header ({var}_cols - 1)
  FOR ({var}_col = 0; {var}_col < {var}_cols - 1; ++{var}_col) BEGIN
    READ_2DA_ENTRY_FORMER {var}_header 0 {var}_col {var}_header_name
    PATCH_IF (~%{var}_header_name%~ STRING_EQUAL_CASE ~{prefix}~) BEGIN
      PATCH_FAIL @73
    END
  END
  BUT_ONLY

ACTION_IF FILE_EXISTS_IN_GAME ~M_cdsnd.lua~ BEGIN
  COPY_EXISTING ~M_cdsnd.lua~ ~override~
    COUNT_REGEXP_INSTANCES ~^[ %TAB%]*filenames_stringrefs[ %TAB%]*\[[ %TAB%]*['"]{prefix}['"][ %TAB%]*\][ %TAB%]*=~ {var}_menu_count
    PATCH_IF ({var}_menu_count > 0) BEGIN PATCH_FAIL @73 END
    BUT_ONLY
END
"""


def subtitle(text: str) -> str:
    cleaned = re.sub(r"^\[VICONIA \d+\]\s*", "", text).strip()
    if "~" in cleaned or "\n" in cleaned or "\r" in cleaned:
        raise ValueError("Unexpected subtitle delimiter or multiline content")
    return cleaned


def build(variant: str, source: Path, output: Path, helper: Path, weidu: Path, ffmpeg: str) -> Path:
    spec = VARIANTS[variant]
    mod, prefix, slots = spec["mod"], spec["prefix"], spec["slots"]
    output = output.resolve()
    if any((parent / "chitin.key").exists() for parent in (output, *output.parents)):
        raise ValueError("Never build inside a game installation")
    if output.exists():
        raise ValueError("Build output must be a new directory; existing work is preserved")
    resrefs = [(prefix + suffix).upper() for _, _, suffix in slots.values()]
    if len(set(resrefs)) != len(resrefs) or len({tra for _, tra, _ in slots.values()}) != len(slots):
        raise ValueError("Slot map reuses a target resource or TRA id")
    helper_bytes = helper.read_bytes()
    if sha256(helper_bytes) != HELPER_SHA256:
        raise ValueError("Unreviewed soundset helper")
    game = GameResources(source)
    companions = [game.companion(name) for name in spec["creatures"]]
    native = {r["slot"]: r for r in companions[0]["slots"]}
    for creature in companions:
        rows = {r["slot"]: r for r in creature["slots"]}
        if creature["origin"].lower().startswith("override"):
            raise ValueError(f"Use an unmodified {spec['source_name']} companion source")
        recorded = {i for i, r in rows.items() if i in PLAYER_SOURCE_SLOTS and r["sound"]}
        if recorded != set(slots):
            raise ValueError(f"{creature['cre']} sound table differs from the reviewed original: {sorted(recorded)}")
        for index in slots:
            if (rows[index]["sound"], rows[index]["text"]) != (native[index]["sound"], native[index]["text"]):
                raise ValueError(f"Companion variants disagree at slot {index}")

    package = output / "package"
    mod_root = package / mod
    for folder in ("english", "sounds", "wav", "tph"):
        (mod_root / folder).mkdir(parents=True, exist_ok=True)
    originals = output / "source_audio"
    originals.mkdir()
    (mod_root / "tph/cd_add_soundset.tph").write_bytes(helper_bytes)
    (package / f"setup-{mod}.exe").write_bytes(weidu.read_bytes())
    readme = Path(__file__).resolve().parents[1] / f"companions/viconia-{variant}/README.md"
    (mod_root / "README.md").write_bytes(readme.read_bytes())

    records = []
    for index, (slot_key, tra, suffix) in slots.items():
        row = native[index]
        if row.get("missing_audio"):
            raise ValueError(f"Slot {index} names missing audio {row['sound']}")
        original, origin = game.get(row["sound"], 4, "WAV")
        if origin.lower().startswith("override"):
            raise ValueError("Expected an original recorded companion resource")
        raw_path = originals / (row["sound"] + ".wav")
        raw_path.write_bytes(original)
        folder = "wav" if suffix.endswith("_") else "sounds"
        resref = prefix + suffix
        target = mod_root / folder / (resref + ".wav")
        # Decode only: no trim, normalization, resampling, voice effects or synthesis.
        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-i", str(raw_path),
                        "-map_metadata", "-1", "-ac", "1", "-c:a", "pcm_s16le", "-bitexact", str(target)], check=True)
        raw_pcm = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(raw_path),
                                  "-ac", "1", "-f", "s16le", "-c:a", "pcm_s16le", "pipe:1"],
                                 check=True, capture_output=True).stdout
        with wave.open(str(target), "rb") as wav:
            rate, frames = wav.getframerate(), wav.getnframes()
            if wav.getnchannels() != 1 or wav.getsampwidth() != 2 or rate not in (22050, 44100):
                raise ValueError("Unsupported output WAV format")
            pcm = wav.readframes(frames)
        if pcm != raw_pcm or not pcm:
            raise ValueError("Decoded audio was changed or lost")
        records.append({"source_slot": index, "slot_key": slot_key, "source_resref": row["sound"],
                        "source_strref": row["strref"], "source_origin": origin,
                        "target_resref": resref, "tra": tra, "subtitle": subtitle(row["text"]),
                        "source_sha256": sha256(original), "pcm_sha256": sha256(pcm),
                        "wav_sha256": sha256(target.read_bytes()), "sample_rate": rate,
                        "frames": frames, "folder": folder})

    primary = spec["creatures"][0]
    tra_lines = [f"@0 = ~{spec['title']}~", ""]
    for row in sorted(records, key=lambda r: r["tra"]):
        tra_lines += [f"// {spec['source_name']} {primary}.CRE slot {row['source_slot']} -> {row['slot_key']}; {row['source_resref']}",
                      f"@{row['tra']} = ~{row['subtitle']}~ [{row['target_resref']}]"]
    tra_lines += ["", f"@70 = ~{spec['menu']}~",
                  "@71 = ~This voicepack requires BG:EE (with or without SoD), BG2:EE, or EET.~",
                  "@72 = ~This voicepack requires the EE 2.6 soundset table (charsnd.2da rows 1-99). Your game has an older or incompatible soundset layout.~",
                  f"@73 = ~{spec['menu']} is already registered. Uninstall the old {spec['menu']} component before installing this replacement.~"]
    (mod_root / "english/setup.tra").write_text("\n".join(tra_lines) + "\n", encoding="utf-8")
    guard = DUPLICATE_GUARD.format(var=prefix.lower(), prefix=prefix)
    tp2 = f"""BACKUP ~{mod}/backup~
SUPPORT ~https://github.com/Chrizhermann/chriz-bg-voicepacks~
VERSION ~{VERSION}~

LANGUAGE ~English~ ~english~ ~%MOD_FOLDER%/english/setup.tra~

BEGIN @0
DESIGNATED 0
LABEL ~{spec['label']}~

{PREFLIGHT}
{guard}
INCLUDE ~%MOD_FOLDER%/tph/cd_add_soundset.tph~

// Explicit allowlist: an archive overlay may leave retired WAVs in the source
// folder. Never copy those files back; empty slots must remain truly silent.
"""
    for r in records:
        destination = "override" if r["folder"] == "wav" else "lang/%EE_LANGUAGE%/sounds"
        tp2 += f"COPY ~%MOD_FOLDER%/{r['folder']}/{r['target_resref']}.wav~ ~{destination}/{r['target_resref']}.wav~\n"
    tp2 += "\nLAF cd_add_soundset\n  INT_VAR\n"
    tp2 += "".join(f"    cd_{r['slot_key']:<17} = RESOLVE_STR_REF(@{r['tra']})\n" for r in sorted(records, key=lambda r: r["slot_key"]))
    tp2 += f'    cd_select_name       = RESOLVE_STR_REF(@70)\n  STR_VAR cd_name = "{prefix}"\nEND\n'
    (mod_root / f"{mod}.tp2").write_text(tp2, encoding="utf-8")
    manifest = {"version": VERSION, "menu_name": spec["menu"], "source_game": spec["source_game"],
                "source_key_sha256": sha256(game.key), "source_tlk_sha256": sha256(game.tlk),
                "source_variants": [{k: c[k] for k in ("cre", "origin", "sha256")} for c in companions],
                "policy": "Original companion event slots only. No fillers, dialogue repurposing, cross-era mixing or TTS.",
                "slot_translation": spec["translation"],
                "helper_sha256": sha256(helper_bytes), "slots": records,
                "excluded_recordings": [{"slot": r["slot"], "sound": r["sound"], "reason": "NPC-only event; not repurposed for a player slot"}
                                        for r in native.values() if r["sound"] and r["slot"] not in slots]}
    (mod_root / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    source_column, other_column = spec["rows"]
    table = [f"# {spec['menu']} companion slot map", "",
             f"All {len(records)} assignments come directly from the original {spec['era']} companion. Blank text below means an original non-verbal grunt.", "",
             f"| Event | {source_column} | {other_column} | Original audio | Subtitle |", "|---|---:|---:|---|---|"]
    for r in records:
        table.append(f"| {r['slot_key']} | {r['source_slot']} | {spec['moved'](r['source_slot'])} | {r['source_resref']} | {r['subtitle']} |")
    table += ["", "All other player slots remain empty. NPC-only greetings, conversations, insults, compliments and specific-death reactions are deliberately not reassigned."]
    (mod_root / "SLOT_MAP.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    files = {p.relative_to(package).as_posix(): p.read_bytes() for p in package.rglob("*") if p.is_file()}
    archive = output / f"viconia-{variant}-player-voicepack-v{VERSION}.zip"
    write_zip(archive, files)
    (output / "SHA256SUMS").write_text(f"{sha256(archive.read_bytes())}  {archive.name}\n", encoding="ascii")
    print(json.dumps({"package": str(package), "archive": str(archive), "assigned_slots": len(records),
                      "original_audio_frame_fidelity": f"{len(records)}/{len(records)} exact",
                      "installed_into_any_game": False}, indent=2))
    return package


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", required=True, choices=sorted(VARIANTS))
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--helper", type=Path)
    parser.add_argument("--weidu", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    if args.out:
        if not args.helper or not args.weidu:
            parser.error("--out requires --helper and --weidu")
        build(args.variant, args.source, args.out, args.helper, args.weidu, args.ffmpeg)
        return
    game = GameResources(args.source)
    print(json.dumps({"source": str(game.root), "creatures": [game.companion(name) for name in VARIANTS[args.variant]["creatures"]]}, indent=2))


if __name__ == "__main__":
    main()
