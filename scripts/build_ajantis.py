"""Reconstruct Ajantis only from the BGEE companion's recorded sound slots.

The game directories are read-only sources. Outputs must be outside every game.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
import wave
from pathlib import Path

from build_release import HELPER_SHA256, PREFLIGHT, write_zip

VERSION = "2.0.0"
MOD = "cd_ajanti"
PREFIX = "AJANTI"
MENU_NAME = "Ajantis (BG1 companion)"

# Original BGEE CRE slot -> helper name, TRA id, resource suffix.
# BGEE's 35-38 are rare selection despite their legacy SELECT_ACTION names.
# The helper translates these to 75-78 on BG2EE/EET, never to movement 35-38.
NATIVE_SLOTS = {
    1: ("morale_break1", 52, "u_"), 2: ("happy", 45, "r_"),
    3: ("unhappy_1", 68, "5_"), 4: ("unhappy_2", 69, "6_"),
    5: ("breaking_pt", 23, "j_"), 6: ("leader1", 50, "b"),
    7: ("tired1", 65, "c"), 8: ("bored1", 21, "d"),
    9: ("battlecry1", 16, "a"), 18: ("damage1", 34, "l"),
    19: ("dying1", 40, "m"), 20: ("hurt1", 46, "e"),
    21: ("forest", 42, "n"), 22: ("city", 24, "o"),
    23: ("dungeon", 39, "p"), 26: ("common1", 25, "f"),
    27: ("common2", 26, "g"), 28: ("common3", 27, "h"),
    32: ("action1", 1, "i"), 33: ("action2", 2, "j"),
    34: ("action3", 3, "k"), 35: ("select_rare1", 56, "w_"),
    36: ("select_rare2", 57, "x_"), 37: ("select_rare3", 58, "y_"),
    38: ("select_rare4", 59, "z_"), 53: ("gen_death1", 43, "w"),
}
PLAYER_SOURCE_SLOTS = set(range(1, 39)) | {53} | set(range(63, 74)) | set(range(75, 100))

DUPLICATE_GUARD = r"""
// Fail closed on an orphan/duplicate column; normal WeiDU reinstall removes it first.
COPY_EXISTING ~charsnd.2da~ ~override~
  COUNT_2DA_COLS ajantis_cols
  READ_2DA_ENTRIES_NOW ajantis_header (ajantis_cols - 1)
  FOR (ajantis_col = 0; ajantis_col < ajantis_cols - 1; ++ajantis_col) BEGIN
    READ_2DA_ENTRY_FORMER ajantis_header 0 ajantis_col ajantis_header_name
    PATCH_IF (~%ajantis_header_name%~ STRING_EQUAL_CASE ~AJANTI~) BEGIN
      PATCH_FAIL @73
    END
  END
  BUT_ONLY

ACTION_IF FILE_EXISTS_IN_GAME ~M_cdsnd.lua~ BEGIN
  COPY_EXISTING ~M_cdsnd.lua~ ~override~
    COUNT_REGEXP_INSTANCES ~^[ %TAB%]*filenames_stringrefs[ %TAB%]*\[[ %TAB%]*['"]AJANTI['"][ %TAB%]*\][ %TAB%]*=~ ajantis_menu_count
    PATCH_IF (ajantis_menu_count > 0) BEGIN PATCH_FAIL @73 END
    BUT_ONLY
END
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class GameResources:
    """Read ordinary KEY/BIFF resources, honoring override without changing it."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.key = (self.root / "chitin.key").read_bytes()
        if self.key[:8] != b"KEY V1  ":
            raise ValueError("Unsupported KEY header")
        nbif, nres, bifoff, resoff = struct.unpack_from("<IIII", self.key, 8)
        self.bifs = []
        for i in range(nbif):
            _, off, size, _ = struct.unpack_from("<IIHH", self.key, bifoff + i * 12)
            name = self.key[off:off + size].rstrip(b"\0").decode("ascii").replace("\\", "/")
            self.bifs.append(name)
        self.resources = {}
        for i in range(nres):
            name, kind, locator = struct.unpack_from("<8sHI", self.key, resoff + i * 14)
            self.resources[name.rstrip(b"\0").decode("ascii").upper(), kind] = locator
        self.overrides = {p.name.upper(): p for p in (self.root / "override").glob("*") if p.is_file()}
        self.tlk = (self.root / "lang/en_us/dialog.tlk").read_bytes()
        if self.tlk[:8] != b"TLK V1  ":
            raise ValueError("Unsupported TLK header")
        self.string_count, self.string_start = struct.unpack_from("<II", self.tlk, 10)

    def get(self, name: str, kind: int, extension: str, *, base: bool = False) -> tuple[bytes, str]:
        filename = f"{name}.{extension}".upper()
        if not base and filename in self.overrides:
            path = self.overrides[filename]
            return path.read_bytes(), str(path.relative_to(self.root))
        locator = self.resources[name.upper(), kind]
        bif_name = self.bifs[locator >> 20]
        with (self.root / bif_name).open("rb") as stream:
            header = stream.read(20)
            if header[:8] != b"BIFFV1  ":
                raise ValueError(f"Unsupported BIF compression in {bif_name}")
            count, _, table = struct.unpack_from("<III", header, 8)
            ordinal = locator & 0xFFFFF
            if ordinal >= count:
                raise ValueError("Resource ordinal exceeds BIFF table")
            stream.seek(table + ordinal * 16)
            _, offset, size, actual_kind, _ = struct.unpack("<IIIHH", stream.read(16))
            if actual_kind != kind:
                raise ValueError("Resource type does not match KEY")
            stream.seek(offset)
            data = stream.read(size)
            if len(data) != size:
                raise ValueError("Truncated resource")
        return data, bif_name

    def string(self, ref: int) -> tuple[str, str]:
        if not 0 <= ref < self.string_count:
            raise ValueError(f"Invalid TLK reference {ref}")
        entry = 18 + 26 * ref
        sound = self.tlk[entry + 2:entry + 10].rstrip(b"\0").decode("ascii").upper()
        start, length = struct.unpack_from("<II", self.tlk, entry + 18)
        text = self.tlk[self.string_start + start:self.string_start + start + length].decode("utf-8")
        return text, sound

    def companion(self, name: str) -> dict:
        cre, location = self.get(name, 1009, "CRE")
        if cre[:8] != b"CRE V1.0":
            raise ValueError(f"Unsupported companion format: {name}")
        slots = []
        for index, ref in enumerate(struct.unpack_from("<100i", cre, 0xA4)):
            if ref < 0:
                continue
            text, sound = self.string(ref)
            record = {"slot": index, "strref": ref, "text": text, "sound": sound}
            if sound:
                try:
                    wav, origin = self.get(sound, 4, "WAV")
                    record.update(audio_origin=origin, source_sha256=sha256(wav), audio_bytes=len(wav), header=repr(wav[:12]))
                except KeyError:
                    record["missing_audio"] = True
            slots.append(record)
        return {"cre": name, "origin": location, "sha256": sha256(cre), "slots": slots}


def subtitle(text: str) -> str:
    cleaned = re.sub(r"^\[AJANTIS (?:\d+|POST)\]\s*", "", text).strip()
    if "~" in cleaned or "\n" in cleaned or "\r" in cleaned:
        raise ValueError("Unexpected subtitle delimiter or multiline content")
    return cleaned


def build(source: Path, output: Path, helper: Path, weidu: Path, ffmpeg: str) -> Path:
    output = output.resolve()
    if any((parent / "chitin.key").exists() for parent in (output, *output.parents)):
        raise ValueError("Never build inside a game installation")
    if output.exists():
        raise ValueError("Build output must be a new directory; existing work is preserved")
    helper_bytes = helper.read_bytes()
    if sha256(helper_bytes) != HELPER_SHA256:
        raise ValueError("Unreviewed soundset helper")
    game = GameResources(source)
    companions = [game.companion(name) for name in ("AJANTI", "AJANTI4", "AJANTI6")]
    native = {r["slot"]: r for r in companions[0]["slots"]}
    recorded = {i for i, r in native.items() if i in PLAYER_SOURCE_SLOTS and r["sound"]}
    if recorded != set(NATIVE_SLOTS):
        raise ValueError(f"Companion sound table differs from the reviewed original: {recorded}")
    for creature in companions:
        rows = {r["slot"]: r for r in creature["slots"]}
        if creature["origin"].lower().startswith("override"):
            raise ValueError("Use an unmodified BGEE companion source")
        for index in NATIVE_SLOTS:
            if (rows[index]["sound"], rows[index]["text"]) != (native[index]["sound"], native[index]["text"]):
                raise ValueError(f"Companion variants disagree at slot {index}")

    package = output / "package"
    mod_root = package / MOD
    for folder in ("english", "sounds", "wav", "tph"):
        (mod_root / folder).mkdir(parents=True, exist_ok=True)
    originals = output / "source_audio"
    originals.mkdir()
    (mod_root / "tph/cd_add_soundset.tph").write_bytes(helper_bytes)
    (package / f"setup-{MOD}.exe").write_bytes(weidu.read_bytes())
    (mod_root / "README.md").write_bytes((Path(__file__).resolve().parents[1] / "companions/ajantis/README.md").read_bytes())

    records = []
    for index, (slot_key, tra, suffix) in NATIVE_SLOTS.items():
        row = native[index]
        original, origin = game.get(row["sound"], 4, "WAV")
        if origin.lower().startswith("override") or row.get("missing_audio"):
            raise ValueError("Expected an original recorded companion resource")
        raw_path = originals / (row["sound"] + ".wav")
        raw_path.write_bytes(original)
        folder = "wav" if suffix.endswith("_") else "sounds"
        resref = PREFIX + suffix
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

    tra_lines = [f"@0 = ~Ajantis: original BG1 companion soundset~", ""]
    for row in sorted(records, key=lambda r: r["tra"]):
        tra_lines += [f"// BGEE AJANTI.CRE slot {row['source_slot']} -> {row['slot_key']}; {row['source_resref']}",
                      f"@{row['tra']} = ~{row['subtitle']}~ [{row['target_resref']}]"]
    tra_lines += ["", f"@70 = ~{MENU_NAME}~",
                  "@71 = ~This voicepack requires BG:EE (with or without SoD), BG2:EE, or EET.~",
                  "@72 = ~This voicepack requires the EE 2.6 soundset table (charsnd.2da rows 1-99). Your game has an older or incompatible soundset layout.~",
                  "@73 = ~Ajantis is already registered. Uninstall the old Ajantis component before installing this replacement.~"]
    (mod_root / "english/setup.tra").write_text("\n".join(tra_lines) + "\n", encoding="utf-8")
    tp2 = f"""BACKUP ~{MOD}/backup~
SUPPORT ~https://github.com/Chrizhermann/chriz-bg-voicepacks~
VERSION ~{VERSION}~

LANGUAGE ~English~ ~english~ ~%MOD_FOLDER%/english/setup.tra~

BEGIN @0
DESIGNATED 0
LABEL ~Chriz-Ajantis-Companion-Soundset~

{PREFLIGHT}
{DUPLICATE_GUARD}
INCLUDE ~%MOD_FOLDER%/tph/cd_add_soundset.tph~

// Explicit allowlist: an archive overlay may leave retired WAVs in the source
// folder. Never copy those files back; empty slots must remain truly silent.
"""
    for r in records:
        destination = "override" if r["folder"] == "wav" else "lang/%EE_LANGUAGE%/sounds"
        tp2 += f"COPY ~%MOD_FOLDER%/{r['folder']}/{r['target_resref']}.wav~ ~{destination}/{r['target_resref']}.wav~\n"
    tp2 += "\nLAF cd_add_soundset\n  INT_VAR\n"
    tp2 += "".join(f"    cd_{r['slot_key']:<17} = RESOLVE_STR_REF(@{r['tra']})\n" for r in sorted(records, key=lambda r: r["slot_key"]))
    tp2 += f'    cd_select_name       = RESOLVE_STR_REF(@70)\n  STR_VAR cd_name = "{PREFIX}"\nEND\n'
    (mod_root / f"{MOD}.tp2").write_text(tp2, encoding="utf-8")
    manifest = {"version": VERSION, "menu_name": MENU_NAME, "source_game": "Unmodified BGEE English",
                "source_key_sha256": sha256(game.key), "source_tlk_sha256": sha256(game.tlk),
                "source_variants": [{k: c[k] for k in ("cre", "origin", "sha256")} for c in companions],
                "policy": "Original companion event slots only. No fillers, dialogue repurposing, cross-era mixing or TTS.",
                "slot_translation": "BGEE rare selection 35-38 -> BG2EE/EET rare selection 75-78; all other assigned rows unchanged.",
                "helper_sha256": sha256(helper_bytes), "slots": records,
                "excluded_recordings": [{"slot": r["slot"], "sound": r["sound"], "reason": "NPC-only event; not repurposed for a player slot"}
                                        for r in native.values() if r["sound"] and r["slot"] not in NATIVE_SLOTS]}
    (mod_root / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    table = ["# Ajantis companion slot map", "", "All 26 assignments come directly from the original companion. Blank text below means an original non-verbal grunt.", "",
             "| Event | BGEE row | BG2EE/EET row | Original audio | Subtitle |", "|---|---:|---:|---|---|"]
    for r in records:
        destination = r["source_slot"] + 40 if 35 <= r["source_slot"] <= 38 else r["source_slot"]
        table.append(f"| {r['slot_key']} | {r['source_slot']} | {destination} | {r['source_resref']} | {r['subtitle']} |")
    table += ["", "All other player slots remain empty. NPC-only greetings, conversations, insults, compliments and specific-death reactions are deliberately not reassigned."]
    (mod_root / "SLOT_MAP.md").write_text("\n".join(table) + "\n", encoding="utf-8")
    files = {p.relative_to(package).as_posix(): p.read_bytes() for p in package.rglob("*") if p.is_file()}
    archive = output / f"ajantis-player-voicepack-v{VERSION}.zip"
    write_zip(archive, files)
    (output / "SHA256SUMS").write_text(f"{sha256(archive.read_bytes())}  {archive.name}\n", encoding="ascii")
    print(json.dumps({"package": str(package), "archive": str(archive), "assigned_slots": len(records),
                      "original_audio_frame_fidelity": "26/26 exact", "installed_into_any_game": False}, indent=2))
    return package


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--helper", type=Path)
    parser.add_argument("--weidu", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    if args.out:
        if not args.helper or not args.weidu:
            parser.error("--out requires --helper and --weidu")
        build(args.source, args.out, args.helper, args.weidu, args.ffmpeg)
        return
    game = GameResources(args.source)
    print(json.dumps({"source": str(game.root), "creatures": [game.companion(name) for name in ("AJANTI", "AJANTI4", "AJANTI6")]}, indent=2))


if __name__ == "__main__":
    main()
