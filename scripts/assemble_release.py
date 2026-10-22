"""Assemble one release from the unchanged 1.0.1 packs and separately built packs (stdlib only).

The fourteen 1.0.1 archives come from build_release.py and must be byte-identical
to the published 1.0.1 assets. Ajantis, Viconia and Garithos are built from a
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

RELEASE = "1.1.0"
# The bundled setup executable of every 1.0.x pack.
WEIDU_SHA256 = "0d17e26e3f3ef5b36796eb0ee8ae73cb851d8b62c9702c2e224da2945caafb75"
PUBLISHED = {
    "neera": "f2adbfd775f86f9cfbcae37ca1b4aaa1ca9e57876b8952603a56b632aba50fbc",
    "safana-bg1": "e5b3e7fa69461c333530d61979bf713dfddc693614e95f6cea854e45ae8a541d",
    "safana-sod": "edd486e85c9521905dd8cba2a5f3fddb846f3ae33b3f36e0308bab89c0432602",
    "jaheira-bg1": "d8a3bd683fc1c044eceec662414ff8279ea4992053b6c931486097436ad03806",
    "jaheira-bg2": "5efe01db15944ad675eaf115ba0ca6bbcf76656ffa6c0408096e4c82be5ccf07",
    "yeslick": "c3c1213cc4ec89002b750788c58cd533d5c765d839c9c6b7c463c9db9ec3f22b",
    "edwin-bg1": "6c02995b38edc5a021a54afbf544ae3e3ec3fa8f7cf5750aad22eb853a5e5411",
    "edwin-bg2": "d32e6f5577b95ae73b2113cb2ec83de2952a8c83383b4863d7df5fdcbc6aebc9",
    "aerie": "04ce446df621ad6def59f5ca922c44a4d9a147ca86a236afdb22df1390ba6775",
    "imoen-bg1": "cda87d6b56a15437025c536e2ea50194330565adf8a5e55f1cbdbbcaf8de79bb",
    "imoen-bg2": "043d6216b4cf347a8a28f0d464af4286f01624587e55c14e324d0d21f628be60",
    "sarevok": "e105f9b296d06677d9d0ba67ffdc3583c90ac13a97ea4dd7d45117f721af7937",
    "amelyssan": "f67c4e4b87ccafc9272539d212c0211d53e45f8cd76d1a06aabd86239f4b6809",
    "gromnir-il-khan": "7aaad0379a6cbba87c5b2aa772ad3b53b777ae1d1821194567cfa8288811c9f5",
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
