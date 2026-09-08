"""Build every voicepack from the hash-pinned original release (stdlib only)."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://github.com/Chrizhermann/chriz-bg-voicepacks/releases/download/v1.0.0"
VERSION = "1.0.1"
HELPER_SHA256 = "a581fae61b165c0c8af8a6ad7136b7b1b825e14d379c528bfb89453a06f843c5"
PACKS = [
    ("neera", "cd_neera", 53, "23fb004e15ce4590e4747e2a4b93a527cf91b2d1d1c771cd5944f1f12b40aa65"),
    ("safana-bg1", "cd_safana", 58, "c97eab282fa95414b6ea0b78ea98f9892633f10993ac1caa54f38c9434028a6a"),
    ("safana-sod", "cd_safsod", 48, "a550ffabbce3d654738068e3a609ebeaa7ffc48f6f735fa6490609d9d9414b71"),
    ("jaheira-bg1", "cd_jahebg1", 53, "725e8360f93ea139c3c67970824b235db2fd795188ca2fd7c8cf24b7c3e6f485"),
    ("jaheira-bg2", "cd_jahebg2", 40, "b46153f0a619f6fc01d112d5e1fc75accd8c85a1a5b189bcaba00de31b5f21a0"),
    ("yeslick", "cd_yeslick", 38, "fa6a68d6776b580ad81c8068cf95cc178cd6d31198b68e5e3cf09a81fd09ee0c"),
    ("edwin-bg1", "cd_edwnbg1", 55, "c6b259cf735c02474d8aa86137d89e230f6b690dddc3470bd1d3361c4ff80cf0"),
    ("edwin-bg2", "cd_edwnbg2", 45, "021e30200d341a0c17391634d2935e4761f89f8e4fc4b5a09ed03483bdb7d901"),
    ("aerie", "cd_aerie", 38, "79d8b51f11d54501ed55ca966026291706529bb410507c246e14132b4ce45021"),
    ("imoen-bg1", "cd_imobg1", 26, "144ae4507fd752c3803c9534af4f14612b02e227f6d6db167ef0e8657ff17163"),
    ("imoen-bg2", "cd_imobg2", 39, "0f414924416e14aa666e51434e435c4d10a782eef3ed393e588ba9485a0762a1"),
    ("sarevok", "cd_sarevok", 36, "dca523182a2a1fa208e32d905a77a8d68524863a72f619426b0c11c0f8ea838e"),
    ("amelyssan", "cd_amely", 17, "294969335105d7092f17be746cfb18765296f2df17347f51f7e069bfa23f1636"),
    ("gromnir-il-khan", "cd_gromn", 10, "844f2e211d58bd6cdd60e4159302ef520f18dcfc88a5000a2109af5fb1d43ac9"),
]

PREFLIGHT = """REQUIRE_PREDICATE (GAME_IS ~bgee bg2ee eet~) @71
REQUIRE_PREDICATE (FILE_EXISTS_IN_GAME ~charsnd.2da~) @72

// EE 2.6 uses rows 1-99. Reject old or incompatible layouts before adding audio.
COPY_EXISTING ~charsnd.2da~ ~override~
  COUNT_2DA_COLS chriz_sound_cols
  COUNT_2DA_ROWS chriz_sound_cols chriz_sound_rows
  PATCH_IF (chriz_sound_rows != 99) BEGIN PATCH_FAIL @72 END
  FOR (chriz_row = 0; chriz_row < 99; ++chriz_row) BEGIN
    READ_2DA_ENTRY chriz_row 0 chriz_sound_cols chriz_label
    PATCH_IF (chriz_label != chriz_row + 1) BEGIN PATCH_FAIL @72 END
  END
  BUT_ONLY
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def original_files(cache: Path, pack: tuple) -> dict[str, bytes]:
    ident, mod, slots, digest = pack
    filename = f"{ident}-player-voicepack-v1.0.0.zip"
    path = cache / filename
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(f"{BASE_URL}/{filename}", headers={"User-Agent": "chriz-bg-voicepacks-builder"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        if sha256(data) != digest:
            raise ValueError(f"Source checksum mismatch: {filename}")
        path.write_bytes(data)
    data = path.read_bytes()
    if sha256(data) != digest:
        raise ValueError(f"Source checksum mismatch: {path}")
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            name = entry.filename
            if "\\" in name or PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts:
                raise ValueError(f"Unsafe source path: {name}")
            if name.lower() in {key.lower() for key in files}:
                raise ValueError(f"Duplicate source path: {name}")
            allowed = name in {
                f"setup-{mod}.exe", f"{mod}/{mod}.tp2",
                f"{mod}/english/setup.tra", f"{mod}/tph/cd_add_soundset.tph",
            } or re.fullmatch(rf"{mod}/(?:sounds|wav)/[A-Za-z0-9_]{{1,8}}\.wav", name)
            if not allowed:
                raise ValueError(f"Unexpected source file: {name}")
            files[name] = archive.read(entry)
    if len(files) != slots + 4 or sum(name.endswith(".wav") for name in files) != slots:
        raise ValueError(f"Unexpected source file count: {ident}")
    if sha256(files[f"{mod}/tph/cd_add_soundset.tph"]) != HELPER_SHA256:
        raise ValueError(f"Unreviewed soundset helper: {ident}")
    return files


def update_installer(files: dict[str, bytes], mod: str, version: str) -> dict[str, bytes]:
    updated = dict(files)
    tp_path = f"{mod}/{mod}.tp2"
    tra_path = f"{mod}/english/setup.tra"
    tp = files[tp_path].decode("utf-8-sig").replace("\r\n", "\n")
    tra = files[tra_path].decode("utf-8-sig").replace("\r\n", "\n")
    if "VERSION " in tp or "@72" in tra:
        raise ValueError(f"Unexpected baseline metadata: {mod}")
    tp = re.sub(r"(?m)^REQUIRE_PREDICATE \(GAME_IS ~bg2ee eet~\) @71\n\n?", "", tp)
    if "REQUIRE_PREDICATE" in tp or tp.count("BEGIN @0") != 1:
        raise ValueError(f"Unexpected installer shape: {mod}")
    tp = tp.replace("\nLANGUAGE ", f"\nVERSION ~{version}~\n\nLANGUAGE ", 1)
    tp = tp.replace("BEGIN @0\n", f"BEGIN @0\n\n{PREFLIGHT}", 1)
    if tp.count("~lang/en_us/sounds~") != 1:
        raise ValueError(f"Unexpected sounds destination: {mod}")
    tp = tp.replace("~lang/en_us/sounds~", "~lang/%EE_LANGUAGE%/sounds~")
    tra = re.sub(r"(?m)^// Unsupported-game prerequisite error\n", "", tra)
    tra = re.sub(r"(?m)^@71\s*=\s*~[^~]*~\s*$", "", tra)
    tra = tra.rstrip() + "\n\n// Installation prerequisites\n"
    tra += "@71 = ~This voicepack requires Baldur's Gate: Enhanced Edition (with or without Siege of Dragonspear), Baldur's Gate II: Enhanced Edition, or Enhanced Edition Trilogy (EET).~\n"
    tra += "@72 = ~This voicepack requires the EE 2.6 soundset table (charsnd.2da rows 1-99). Your game has an older or incompatible soundset layout.~\n"
    updated[tp_path] = tp.encode("utf-8")
    updated[tra_path] = tra.encode("utf-8")
    return updated


def write_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 8, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    with zipfile.ZipFile(path) as archive:
        if {name: archive.read(name) for name in archive.namelist()} != files:
            raise ValueError(f"ZIP round-trip failed: {path}")


def build(cache: Path, output: Path, version: str = VERSION) -> list[dict]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version) or version == "1.0.0":
        raise ValueError("Choose a new numeric release version")
    output.mkdir(parents=True, exist_ok=True)
    if list(output.iterdir()):
        raise ValueError(f"Output directory must be empty: {output}")
    manifest = []
    for pack in PACKS:
        ident, mod, slots, _ = pack
        source = original_files(cache, pack)
        files = update_installer(source, mod, version)
        filename = f"{ident}-player-voicepack-v{version}.zip"
        path = output / filename
        write_zip(path, files)
        archive_data = path.read_bytes()
        manifest.append({
            "id": ident, "filename": filename, "assignedSlots": slots,
            "fileCount": len(files), "archiveBytes": len(archive_data),
            "sha256": sha256(archive_data),
            "supportedGames": ["bgee", "bg2ee", "eet"],
            "soundsetLayout": "EE 2.6 (99 rows)",
        })
        print(f"Built {filename}: {slots} assignments, audio unchanged", flush=True)
    (output / "voicepacks-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "SHA256SUMS").write_text("".join(f"{p['sha256']}  {p['filename']}\n" for p in manifest), encoding="ascii")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "_cache" / "v1.0.0")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--version", default=VERSION)
    args = parser.parse_args()
    build(args.source_dir, args.out_dir, args.version)
