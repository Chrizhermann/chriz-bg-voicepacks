"""Verify Garithos using real WeiDU in new disposable game fixtures only."""
from __future__ import annotations

import argparse
import io
import json
import re
import struct
import subprocess
import tempfile
import wave
import zipfile
from pathlib import Path

import verify_installers as common

MOD, PREFIX = "cd_garith", "CGARIT"
# Independent expected legacy suffix -> (BGEE/SoD row, BG2EE/EET row).
EXPECTED = {
    "a": (9, 9), "b": (6, 6), "d": (8, 8),
    "f": (26, 26), "g": (27, 27), "h": (28, 28), "0": (29, 29),
    "i": (32, 32), "j": (33, 33), "k": (34, 34),
    "s": (79, 35), "t": (80, 36), "u": (81, 37), "v": (82, 38),
    "l": (18, 18), "m": (19, 19), "n": (21, 21), "o": (22, 22),
    "p": (23, 23), "z": (65, 65), "1": (66, 66), "8": (10, 10), "9": (11, 11),
}


def records(data: bytes) -> list[tuple]:
    entries = common.tlk_entries(data)
    result = []
    for i, entry in enumerate(entries):
        offset = 18 + 26 * i
        flags = struct.unpack_from("<H", data, offset)[0]
        volume, pitch = struct.unpack_from("<II", data, offset + 10)
        result.append((*entry, flags, volume, pitch))
    return result


def tlks(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix().lower(): p.read_bytes()
            for p in (root / "lang").rglob("*.tlk")}


def resources(root: Path) -> dict[str, str]:
    result = {"chitin.key": common.sha256((root / "chitin.key").read_bytes())}
    for folder in ("override", "lang", "data"):
        result.update({f"{folder}/{name}": value for name, value in common.tree(root / folder).items()})
    return result


def setup(root: Path, files: dict[str, bytes], game: str, language: str, fixtures: Path,
          count: int = 99, missing: bool = False) -> bytes:
    previous = common.fixture(root, game, language, fixtures if count == 99 else None,
                              row_count=count, missing_table=missing)
    for lang in {"en_us", language}:
        text = b"Original female voice"
        data = (b"TLK V1  " + struct.pack("<HII", 0, 2, 70) + bytes(26)
                + struct.pack("<H8sIIII", 1, b"", 0, 0, 0, len(text)) + text)
        (root / f"lang/{lang}/dialogF.tlk").write_bytes(data)
        (root / f"lang/{lang}/sounds/CONTROL.wav").write_bytes(b"Unrelated sound")
    (root / "override/CONTROL.bin").write_bytes(b"Unrelated resource")
    for name, data in files.items():
        target = (root / name).resolve()
        assert target.is_relative_to(root.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    # An overlaid extra source file must not become an accidental filler slot.
    (root / f"{MOD}/sounds/CGARITc.wav").write_bytes(b"Do not install")
    return previous


def verify_package(files: dict[str, bytes], source: Path, manifest: dict) -> dict:
    assert len(files) == 32, (len(files), sorted(files))
    provenance = json.loads(files[f"{MOD}/provenance.json"])
    assert provenance["menu_name"] == "Garithos" and provenance["version"] == "1.1.0"
    assert common.sha256(files[f"{MOD}/tph/cd_add_soundset.tph"]) == "a581fae61b165c0c8af8a6ad7136b7b1b825e14d379c528bfb89453a06f843c5"
    assert common.sha256(files[f"setup-{MOD}.exe"]) == "0d17e26e3f3ef5b36796eb0ee8ae73cb851d8b62c9702c2e224da2945caafb75"
    clips = {x["source_file"]: x for x in manifest["clips"]}
    assert set(clips) == {f"garitho{s}.wav" for s in EXPECTED}
    assert len(provenance["slots"]) == len(EXPECTED) == 23
    by_source = {x["source_file"]: x for x in provenance["slots"]}
    tp = files[f"{MOD}/{MOD}.tp2"].decode("ascii")
    calls_list = common.SLOT_CALL.findall(tp)
    calls = {key: int(ref) for key, ref in calls_list}
    assert len(calls) == len(calls_list) == 24
    translations_list = common.TRA_ENTRY.findall(files[f"{MOD}/english/setup.tra"].decode("ascii"))
    translations = {int(n): (text, sound.upper()) for n, text, sound in translations_list}
    assert len(translations) == len(translations_list)
    assert translations[calls["select_name"]] == ("Garithos", "")
    expected_audio = set()
    for suffix, (bg1, bg2) in EXPECTED.items():
        filename = f"garitho{suffix}.wav"
        original = (source / filename).read_bytes()
        target = f"{MOD}/sounds/{PREFIX}{suffix}.wav"
        expected_audio.add(target)
        assert files[target] == original, (filename, "Audio changed")
        clip = clips[filename]
        assert common.sha256(original) == clip["sha256"]
        r = by_source[filename]
        assert (r["bgee_sod_row"], r["bg2ee_eet_row"]) == (bg1, bg2)
        assert (common.slot_rows("bgee")[r["slot_key"]], common.slot_rows("bg2ee")[r["slot_key"]]) == (bg1, bg2)
        assert translations[calls[r["slot_key"]]] == (clip["subtitle"], (PREFIX + suffix).upper())
        assert r["subtitle"] == clip["subtitle"]
        with wave.open(io.BytesIO(original), "rb") as wav:
            assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) == (1, 2, 22050, "NONE")
            assert wav.getnframes() == r["frames"]
            assert common.sha256(wav.readframes(wav.getnframes())) == r["pcm_sha256"]
    assert {name for name in files if name.lower().endswith(".wav")} == expected_audio
    assert sum(bool(x["subtitle"]) for x in clips.values()) == 22
    assert clips["garithom.wav"]["subtitle"] == "Is the nightmare finally over?"
    assert clips["garithoz.wav"]["subtitle"] == "Humanity will rise again."
    assert "picnic" in clips["garithod.wav"]["subtitle"]
    assert provenance["source_archive_sha256"] == "677f93c93484d323cfc47b77bb82306eb83186be9baf096a9a8bcd9a36d778d3"
    for portrait in manifest["portraits"]:
        data = (source / portrait["source_file"]).read_bytes()
        assert files[f"Extras/Portraits/{portrait['source_file']}"] == data
        assert common.sha256(data) == portrait["sha256"]
    assert ".bmp" not in tp, "Do not install portraits as part of the voice update"
    return {"assignedSlots": 23, "spokenSubtitles": 22, "nonverbalClips": 1,
            "audioByteIdentical": True, "preservedLegacyAssignments": True}


def positive(work: Path, files: dict[str, bytes], fixtures: Path, manifest: dict) -> list[dict]:
    results = []
    clips = {c["source_file"]: c for c in manifest["clips"]}
    for game in ("bgee", "sod", "bg2ee", "eet"):
        for language in ("en_us", "de_de"):
            root = work / f"{game}-{language}"
            previous = setup(root, files, game, language, fixtures)
            before = resources(root)
            old_tlks = tlks(root)
            for cycle in range(2):
                output = common.run_weidu(root, MOD, language)
                assert "SUCCESSFULLY INSTALLED" in output and "SKIPPING:" not in output
                after_table = common.check_registration(root, files, MOD, game, language, previous, 23)
                _, rows = common.table(after_table)
                for path, original in old_tlks.items():
                    current = (root / path).read_bytes()
                    if not path.startswith(f"lang/{language}/"):
                        assert current == original, (game, "Other language altered", path)
                        continue
                    entries = records(current)
                    assert entries[:len(records(original))] == records(original)
                    for suffix, row_pair in EXPECTED.items():
                        row = row_pair[0 if game in ("bgee", "sod") else 1]
                        ref = int(rows[row][-1])
                        text = clips[f"garitho{suffix}.wav"]["subtitle"]
                        actual = entries[ref]
                        assert actual[:2] == (text, (PREFIX + suffix).upper()), (game, path, row, actual)
                        assert actual[2] & 2, ("Sound flag missing", path, row)
                        if text:
                            assert actual[2] & 1, ("Subtitle flag missing", path, row)
                expected_targets = {f"lang/{language}/sounds/{PREFIX.lower()}{s}.wav" for s in EXPECTED}
                changed = {p for p, value in resources(root).items() if before.get(p) != value}
                assert changed == expected_targets | {"override/charsnd.2da", "override/m_cdsnd.lua", f"lang/{language}/dialog.tlk", f"lang/{language}/dialogf.tlk"}, changed
                assert not (root / f"lang/{language}/sounds/CGARITc.wav").exists()
                common.run_weidu(root, MOD, language, uninstall=True)
                # WeiDU may retain appended unused strings; originals must stay intact.
                current_resources = resources(root)
                assert {k: v for k, v in current_resources.items() if not k.endswith(".tlk")} == {k: v for k, v in before.items() if not k.endswith(".tlk")}
                for path, original in old_tlks.items():
                    current = (root / path).read_bytes()
                    assert records(current)[:len(records(original))] == records(original)
                    if not path.startswith(f"lang/{language}/"):
                        assert current == original
            results.append({"game": game, "language": language, "installUninstallCycles": 2,
                            "all23MappingsAndSubtitles": "passed", "maleAndFemaleTlk": "passed",
                            "originalResourcesRestored": "passed", "extraWavIgnored": "passed"})
            print(f"PASS {game}/{language}: 23 mappings, subtitles, both TLKs, reinstall and restoration", flush=True)
    return results


def negatives(work: Path, files: dict[str, bytes], fixtures: Path) -> list[dict]:
    results = []
    for case in ("classic", "old-table", "missing-table", "malformed-table", "duplicate-column", "orphan-menu"):
        root = work / case
        previous = setup(root, files, "classic" if case == "classic" else "bgee", "en_us", fixtures,
                         count=30 if case == "old-table" else 99, missing=case == "missing-table")
        if case == "malformed-table":
            lines = previous.decode("ascii").splitlines()
            # Replace one valid ordered label with an out-of-order row.
            for i, line in enumerate(lines):
                if line.split() and line.split()[0] == "50":
                    lines[i] = re.sub(r"^\s*50\b", "98", line)
                    break
            else:
                raise AssertionError("Fixture has no row 50")
            (root / "override/charsnd.2da").write_text("\n".join(lines) + "\n", encoding="ascii")
        if case == "duplicate-column":
            header, rows = common.table(previous)
            data = "2DA V1.0\n-1\n" + " ".join(header + [PREFIX]) + "\n"
            data += "".join(f"{row} {' '.join(values)} -1\n" for row, values in rows.items())
            (root / "override/charsnd.2da").write_text(data, encoding="ascii")
        if case == "orphan-menu":
            with (root / "override/M_cdsnd.lua").open("ab") as stream:
                stream.write(b'  filenames_stringrefs [ "CGARIT" ] = {1, 2}\n')
        before = resources(root)
        try:
            output = common.run_weidu(root, MOD, "en_us")
        except AssertionError as exc:
            output = str(exc)
        expected = ("requires Baldur's Gate" if case == "classic" else
                    "registration already exists" if case in ("duplicate-column", "orphan-menu") else
                    "older or incompatible soundset layout")
        assert expected in output and "SUCCESSFULLY INSTALLED" not in output, (case, output[-2500:])
        assert resources(root) == before, (case, "Rejected install changed game resources")
        results.append({"case": case, "rejectedWithoutResourceChanges": True})
        print(f"PASS rejection: {case}", flush=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=common.ROOT / "custom/garithos/voicepack.json")
    parser.add_argument("--fixtures", type=Path, default=common.ROOT / "_work/fixtures")
    args = parser.parse_args()
    source_before = common.tree(args.source)
    with zipfile.ZipFile(args.archive) as archive:
        assert len(set(archive.namelist())) == len(archive.namelist())
        files = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    work = Path(tempfile.mkdtemp(prefix="garithos-tests-", dir=common.ROOT / "_work"))
    report = {"version": "1.1.0", "archiveSha256": common.sha256(args.archive.read_bytes()),
              "scope": "Real WeiDU in disposable fixtures; no live game installation or engine playtest",
              "package": verify_package(files, args.source, manifest)}
    report["positive"] = positive(work, files, args.fixtures, manifest)
    report["negative"] = negatives(work, files, args.fixtures)
    assert common.tree(args.source) == source_before
    report["userSourceUnchanged"] = True
    report["capturedFixtureHashes"] = common.tree(args.fixtures)
    path = work / "verification-report.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"All checks passed. Report: {path}")


if __name__ == "__main__":
    main()
