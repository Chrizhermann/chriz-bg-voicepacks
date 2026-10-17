"""Exercise the non-cascading Garithos update in disposable games only."""
from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from pathlib import Path

import verify_garithos as pack
import verify_installers as common

MOD = "cd_garup"
OWNED_ROWS = {7, 8, 19, 65}


def read_zip(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def copy_files(files: dict[str, bytes], root: Path) -> None:
    for name, data in files.items():
        path = (root / name).resolve()
        assert path.is_relative_to(root.resolve())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def initialize(root: Path, old: dict[str, bytes], update: dict[str, bytes], game: str,
               language: str, fixtures: Path) -> None:
    pack.setup(root, old, game, language, fixtures)
    # Restore the real old tired clip over setup's deliberate stray-source sentinel.
    copy_files(old, root)
    common.run_weidu(root, "cd_garith", language)
    copy_files(update, root)
    # A real later mod catches accidental cascade/uninstall, including menu damage.
    later = {
        "setup-later_guard.exe": old["setup-cd_garith.exe"],
        "later_guard/later_guard.tp2": b'BACKUP ~later_guard/backup~\nAUTHOR ~Fixture~\nBEGIN ~Later mod preservation fixture~\nCOPY ~later_guard/payload.bin~ ~override/LATER.bin~\nAPPEND ~M_cdsnd.lua~ ~-- later mod: preserve this comment~\n',
        "later_guard/payload.bin": b"Later mod payload - not Garithos\n",
    }
    copy_files(later, root)
    common.run_weidu(root, "later_guard", language)


def variant(root: Path) -> None:
    path = root / "override/charsnd.2da"
    header, rows = common.table(path.read_bytes())
    index = header.index("CGARIT")
    header = ["OTHER_NEW", "CGARIT", *header[:index], *header[index + 1:]]
    # Move the owned column, reorder rows, add an unrelated row and distinct values.
    order = list(reversed(rows))
    data = "2DA V1.0\n-1\n" + "\t".join(header) + "\n"
    for row in order:
        values = rows[row]
        values = [str(1000 + row), values[index], *values[:index], *values[index + 1:]]
        data += str(row) + "\t" + "\t".join(values) + "\n"
    data += "107 " + " ".join(["42", "-1", *("-1" for _ in header[2:])]) + "\n"
    path.write_text(data, encoding="ascii")
    # A different menu order/format and spelling of unrelated display entries
    # must not matter: the updater does not rewrite the menu at all.
    lua = root / "override/M_cdsnd.lua"
    lua.write_bytes(b'-- unrelated UI customization\nfilenames_stringrefs["EXTRA"] = {1, 2}\n' + lua.read_bytes())


def assert_updated(root: Path, language: str, game: str, before_table: bytes,
                   before_resources: dict, before_tlks: dict, full: dict, manifest: dict) -> None:
    bh, br = common.table(before_table)
    ah, ar = common.table((root / "override/charsnd.2da").read_bytes())
    assert bh == ah and list(br) == list(ar), "Table shape/order changed"
    column = ah.index("CGARIT")
    for row, values in br.items():
        for index, value in enumerate(values):
            if index != column or row not in OWNED_ROWS:
                assert ar[row][index] == value, ("Unrelated cell changed", row, index)
    clips = {x["source_file"]: x for x in manifest["clips"]}
    for path, old_data in before_tlks.items():
        data = (root / path).read_bytes()
        old_records, records = pack.records(old_data), pack.records(data)
        assert records[:len(old_records)] == old_records, ("Original TLK record changed", path)
        if not path.startswith(f"lang/{language}/"):
            assert data == old_data
            continue
        for suffix, row_pair in pack.EXPECTED.items():
            row = row_pair[0 if game in ("bgee", "sod") else 1]
            ref = int(ar[row][column])
            text = clips[f"garitho{suffix}.wav"]["subtitle"]
            assert records[ref][:2] == (text, ("CGARIT" + suffix).upper()), (path, row, records[ref])
            assert records[ref][2] & 2
            if text:
                assert records[ref][2] & 1
        assert ar[7][column] == "-1"
    for name, data in full.items():
        if "/sounds/" in name:
            target = root / f"lang/{language}/sounds/{Path(name).name}"
            assert target.read_bytes() == data
    assert not (root / f"lang/{language}/sounds/CGARITc.wav").exists()
    after = pack.resources(root)
    modified = {p for p in before_resources.keys() | after.keys() if before_resources.get(p) != after.get(p)}
    allowed = {"override/charsnd.2da", f"lang/{language}/dialog.tlk", f"lang/{language}/dialogf.tlk"}
    allowed |= {f"lang/{language}/sounds/cgarit{s}.wav" for s in "cdmz"}
    assert modified <= allowed, ("Unexpected modified resources", modified - allowed)
    # In the first run all intended files change; in repeat application TLK may be identical.
    assert {f"lang/{language}/sounds/cgarit{s}.wav" for s in "cdmz"} <= modified


def positives(work: Path, old: dict, update: dict, full: dict, manifest: dict, fixtures: Path) -> list[dict]:
    results = []
    cases = [(g, lang, False) for g in ("bgee", "sod", "bg2ee", "eet") for lang in ("en_us", "de_de")]
    cases += [(g, "de_de", True) for g in ("bgee", "eet")]
    for game, language, varied in cases:
        name = f"{game}-{language}" + ("-varied" if varied else "")
        root = work / name
        initialize(root, old, update, game, language, fixtures)
        if varied:
            variant(root)
        before = pack.resources(root)
        old_tlks = pack.tlks(root)
        table = (root / "override/charsnd.2da").read_bytes()
        log_before = (root / "WeiDU.log").read_text(encoding="utf-8")
        for cycle in range(2):
            output = common.run_weidu(root, MOD, language)
            assert "SUCCESSFULLY INSTALLED" in output
            assert "Uninstalling" not in output and "Later mod preservation fixture" not in output
            assert_updated(root, language, game, table, before, old_tlks, full, manifest)
            # A satisfied force-install must be a true no-op, not a duplicate column.
            snapshot = pack.resources(root)
            common.run_weidu(root, MOD, language)
            assert pack.resources(root) == snapshot
            active = [line for line in (root / "WeiDU.log").read_text(encoding="utf-8").splitlines() if line.startswith("~")]
            original_active = [line for line in log_before.splitlines() if line.startswith("~")]
            assert active[:-1] == original_active and "CD_GARUP" in active[-1].upper()
            common.run_weidu(root, MOD, language, uninstall=True)
            after = pack.resources(root)
            assert {p: h for p, h in after.items() if not p.endswith(".tlk")} == {p: h for p, h in before.items() if not p.endswith(".tlk")}
            for path, data in old_tlks.items():
                assert pack.records((root / path).read_bytes())[:len(pack.records(data))] == pack.records(data)
        results.append({"case": name, "upgradeCycles": 2, "all23MappingsAndBothTlk": "passed",
                        "otherModsAndMenuPreserved": "passed", "repeatNoOpAndUninstall": "passed",
                        "reorderedColumnsRowsAndExtraRow": varied})
        print(f"PASS update {name}: corrected slots/subtitles, no cascade, exact resource undo", flush=True)
    return results


def negatives(work: Path, old: dict, update: dict, fixtures: Path) -> list[dict]:
    results = []
    for case in ("missing-column", "duplicate-column", "missing-row", "duplicate-row", "missing-base"):
        root = work / case
        initialize(root, old, update, "eet", "en_us", fixtures)
        path = root / "override/charsnd.2da"
        header, rows = common.table(path.read_bytes())
        if case == "missing-base":
            common.run_weidu(root, "later_guard", "en_us", uninstall=True)
            common.run_weidu(root, "cd_garith", "en_us", uninstall=True)
        else:
            index = header.index("CGARIT")
            if case == "missing-column":
                header[index] = "UNRELATED"
            if case == "duplicate-column":
                header.append("CGARIT")
                for values in rows.values():
                    values.append("-1")
            if case == "missing-row":
                del rows[65]
            data = "2DA V1.0\n-1\n" + " ".join(header) + "\n"
            data += "".join(f"{row} {' '.join(values)}\n" for row, values in rows.items())
            if case == "duplicate-row":
                data += "65 " + " ".join(rows[65]) + "\n"
            path.write_text(data, encoding="ascii")
        before = pack.resources(root)
        try:
            output = common.run_weidu(root, MOD, "en_us")
        except AssertionError as exc:
            output = str(exc)
        expected = ("exactly one CGARIT" if "column" in case else
                    "missing or duplicated" if "row" in case else "full Garithos voicepack first")
        assert expected in output and "SUCCESSFULLY INSTALLED" not in output, output[-3000:]
        assert pack.resources(root) == before
        results.append({"case": case, "rejectedWithoutChanges": True})
        print(f"PASS update rejection {case}", flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-archive", type=Path, required=True)
    parser.add_argument("--full-archive", type=Path, required=True)
    parser.add_argument("--update-archive", type=Path, required=True)
    args = parser.parse_args()
    work = Path(tempfile.mkdtemp(prefix="garithos-update-tests-", dir=common.ROOT / "_work"))
    old, full, update = map(read_zip, (args.old_archive, args.full_archive, args.update_archive))
    manifest = json.loads((common.ROOT / "custom/garithos/voicepack.json").read_text(encoding="utf-8"))
    report = {"version": "1.1.0", "updateArchiveSha256": common.sha256(args.update_archive.read_bytes()),
              "scope": "Actual WeiDU in disposable games only; no live install or engine playtest",
              "compatibility": "Owns four Garithos rows and four WAV paths; tolerates reordered/extra table data; preserves other mods. SR/non-SR spell and effect variations are inapplicable: no SPL/EFF/script/EEex dependency is read or changed."}
    report["positive"] = positives(work, old, update, full, manifest, common.ROOT / "_work/fixtures")
    report["negative"] = negatives(work, old, update, common.ROOT / "_work/fixtures")
    report_path = work / "verification-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"All checks passed. Report: {report_path}")
