"""Assemble one release from the generated 1.0.2 packs and separately built packs (stdlib only).

The fourteen 1.0.2 archives come from build_release.py and must be byte-identical
to the pinned 1.2.0 generated assets. Ajantis, Viconia and Garithos are built from a
local game or a supplied soundset by their own scripts; their archives are
inspected here and listed with the version recorded in their provenance.json.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from pathlib import Path

from build_release import HELPER_SHA256, PACKS, ROOT, VERSION, sha256

RELEASE = "1.2.0"
# The bundled setup executable of every 1.0.x pack.
WEIDU_SHA256 = "0d17e26e3f3ef5b36796eb0ee8ae73cb851d8b62c9702c2e224da2945caafb75"
PUBLISHED = {
    "neera": "b7d029f839062b5e7763de61f541a4922e2cb73d82b6e6c035d8fcdcff3eac94",
    "safana-bg1": "daf45b3d58901509a05f570269e417ad137dcd920cc4cbfc14fbeafe6272f276",
    "safana-sod": "eacccb9187a1abaa28d8d8e6171e3437459f1280b04bec9c9c4199e7f33a2be2",
    "jaheira-bg1": "7167f278446bc9d63485aebf54cefe281d52d6659a496a2c070417fc734322e8",
    "jaheira-bg2": "1c629463c66b0cc377e35356e560e1d26868eab61124fa704c26d61843df8bcf",
    "yeslick": "b4118fecf98786bd092056f9039ee6d8591d5419aa09cdb5b8807ba85bd2c7d6",
    "edwin-bg1": "478b58972a4f247e00c046e02ab6c2c87f3fb520d3b10f037b730ba855061a5b",
    "edwin-bg2": "131d4db31326c377ddfde2f73009d1bc18e8d62ff0f053d66389d6be684b8e3d",
    "aerie": "a6c0d61b87803df550dd97cdd9e56e443ee268a06e5751e9b6b4cb2cbba93f18",
    "imoen-bg1": "7bac3a24dbd5ecdc70afb2b82210c2e6e39061fcb4f2b7803aeb9c911452d098",
    "imoen-bg2": "98125ee8e3159ec7c968649e769fa1de0073c0d9dc8c41675c62247586ebe3d7",
    "sarevok": "29589c43eb14191124155b246979270c137af2f1303a70e8df245173d1c31882",
    "amelyssan": "d16ed2b2b773b5e6caf1b67597eab4c1717ea0014ddbf90e969cc1d808b2693a",
    "gromnir-il-khan": "ce709ab49aea5db3e6ac1419995301d66c64c9bf13e79f55be1968926a363e0b",
}
BUILT = re.compile(r"(?P<ident>[a-z0-9]+(?:-[a-z0-9]+)*)-player-voicepack-v(?P<version>\d+\.\d+\.\d+)\.zip")


def entry(path: Path, ident: str, version: str, slots: int, files: int) -> dict:
    data = path.read_bytes()
    return {
        "id": ident, "version": version, "filename": path.name, "assignedSlots": slots,
        "fileCount": files, "archiveBytes": len(data), "sha256": sha256(data),
        "supportedGames": ["bgee", "bg2ee", "eet"], "soundsetLayout": "EE 2.6 (99 rows)",
    }


def published_pack(packs_dir: Path, pack: tuple) -> tuple[Path, dict]:
    ident, _, slots, _ = pack
    path = packs_dir / f"{ident}-player-voicepack-v{VERSION}.zip"
    if sha256(path.read_bytes()) != PUBLISHED[ident]:
        raise ValueError(f"Rebuilt archive differs from the published {VERSION} asset: {path.name}")
    with zipfile.ZipFile(path) as archive:
        files = len(archive.namelist())
    return path, entry(path, ident, VERSION, slots, files)


def built_pack(path: Path) -> tuple[Path, dict]:
    match = BUILT.fullmatch(path.name)
    if not match:
        raise ValueError(f"Expected <id>-player-voicepack-v<version>.zip: {path.name}")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        mods = {name.split("/", 1)[0] for name in names if re.fullmatch(r"cd_[a-z0-9_]+/provenance\.json", name)}
        if len(mods) != 1:
            raise ValueError(f"Expected one cd_* mod with provenance.json: {path.name}")
        mod = mods.pop()
        provenance = json.loads(archive.read(f"{mod}/provenance.json"))
        if provenance.get("version") != match["version"]:
            raise ValueError(f"Archive name and provenance version differ: {path.name}")
        if provenance.get("helper_sha256") != HELPER_SHA256 or sha256(archive.read(f"{mod}/tph/cd_add_soundset.tph")) != HELPER_SHA256:
            raise ValueError(f"Unreviewed soundset helper: {path.name}")
        if sha256(archive.read(f"setup-{mod}.exe")) != WEIDU_SHA256:
            raise ValueError(f"Unexpected setup executable: {path.name}")
        slots = provenance["slots"]
        wavs = {name.rsplit("/", 1)[1].lower() for name in names if name.startswith(f"{mod}/") and name.lower().endswith(".wav")}
        if {f"{slot['target_resref'].lower()}.wav" for slot in slots} != wavs:
            raise ValueError(f"Provenance slots and archived audio differ: {path.name}")
    return path, entry(path, match["ident"], match["version"], len(slots), len(names))


def assemble(packs_dir: Path, built: list[Path], output: Path) -> list[dict]:
    output.mkdir(parents=True, exist_ok=True)
    if list(output.iterdir()):
        raise ValueError(f"Output directory must be empty: {output}")
    selected = [published_pack(packs_dir, pack) for pack in PACKS] + [built_pack(path) for path in built]
    ids = [item["id"] for _, item in selected]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Duplicate pack id: {ids}")
    manifest = []
    for path, item in selected:
        shutil.copyfile(path, output / path.name)
        if sha256((output / path.name).read_bytes()) != item["sha256"]:
            raise ValueError(f"Copy changed {path.name}")
        manifest.append(item)
        print(f"Added {path.name}: {item['assignedSlots']} assignments, sha256 {item['sha256']}", flush=True)
    (output / "voicepacks-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "SHA256SUMS").write_text("".join(f"{p['sha256']}  {p['filename']}\n" for p in manifest), encoding="ascii")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packs-dir", type=Path, default=ROOT / "dist", help="build_release.py output")
    parser.add_argument("--built", type=Path, action="append", default=[], help="An archive from build_ajantis.py, build_viconia.py or build_garithos.py")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "release" / RELEASE)
    args = parser.parse_args()
    assemble(args.packs_dir, args.built, args.out_dir)
