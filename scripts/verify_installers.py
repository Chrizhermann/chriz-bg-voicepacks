"""Exercise the actual released WeiDU installers in disposable small game fixtures."""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

from build_release import PACKS, ROOT, VERSION, original_files, sha256

# Row IDs verified against EE 2.6 tables and the EE Soundset Tool author's
# explanation of the BGEE/BG2EE ordering difference. Do not derive from the helper
# under test: a broken helper must be able to fail this independent expectation.
COMMON_ROWS = {
    "morale_break1": 1, "happy": 2, "unhappy_1": 3, "unhappy_2": 4,
    "breaking_pt": 5, "leader1": 6, "tired1": 7, "bored1": 8,
    "battlecry1": 9, "battlecry2": 10, "battlecry3": 11, "battlecry4": 12,
    "battlecry5": 13, "attack1": 14, "attack2": 15, "attack3": 16, "attack4": 17,
    "damage1": 18, "dying1": 19, "hurt1": 20, "forest": 21, "city": 22,
    "dungeon": 23, "day": 24, "night": 25,
    "common1": 26, "common2": 27, "common3": 28, "common4": 29,
    "common5": 30, "common6": 31, "action1": 32, "action2": 33, "action3": 34,
    "gen_death1": 53, "action_rare1": 63, "action_rare2": 64,
    "criticalhit": 65, "criticalmiss": 66, "immune": 67, "inventory": 68,
    "pickpocket": 69, "shadows": 70, "disrupted": 71, "trap": 72,
    "morale_break2": 83, "leader2": 84, "tired2": 85, "bored2": 86,
    "hurt2": 87, "common7": 88, "dying2": 91, "gen_death2": 92,
}
SLOT_CALL = re.compile(r"^\s*cd_(\w+)\s*=\s*RESOLVE_STR_REF\(@(\d+)\)", re.M)
TRA_ENTRY = re.compile(r"^\s*@(\d+)\s*=\s*~([^~]*)~(?:\s*\[([^\]]+)\])?", re.M)


def slot_rows(game: str) -> dict[str, int]:
    rows = dict(COMMON_ROWS)
    bg1 = game in ("bgee", "sod")
    rows.update({f"action{i}": (79 if bg1 else 35) + i - 4 for i in range(4, 8)})
    rows.update({f"select_rare{i}": (35 if bg1 else 75) + i - 1 for i in range(1, 5)})
    return rows


def tlk_entries(data: bytes) -> list[tuple[str, str]]:
    assert data[:8] == b"TLK V1  "
    count, text_start = struct.unpack_from("<II", data, 10)
    entries = []
    for index in range(count):
        offset = 18 + 26 * index
        sound = data[offset + 2:offset + 10].split(b"\0", 1)[0].decode("ascii").upper()
        start, size = struct.unpack_from("<II", data, offset + 18)
        text = data[text_start + start:text_start + start + size].decode("utf-8")
        entries.append((text, sound))
    return entries


def make_tlk() -> bytes:
    # Preserve a real original entry as well as the empty sentinel through install/uninstall.
    text = b"Original voice"
    return (b"TLK V1  " + struct.pack("<HII", 0, 2, 18 + 52)
            + bytes(26) + struct.pack("<H8sIIII", 1, b"", 0, 0, 0, len(text)) + text)


def table(data: bytes) -> tuple[list[str], dict[int, list[str]]]:
    lines = [line.split() for line in data.decode("ascii").splitlines() if line.strip()]
    header = lines[2]
    rows = {int(line[0]): line[1:] for line in lines[3:]}
    assert all(len(row) == len(header) for row in rows.values())
    return header, rows


def write_key_bif(game_root: Path, resources: list[tuple[str, int, bytes]]) -> None:
    name = b"data/fixture.bif\0"
    data_offset = 20 + 16 * len(resources)
    entries, contents = bytearray(), bytearray()
    for ordinal, (_, kind, data) in enumerate(resources):
        entries += struct.pack("<IIIHH", ordinal, data_offset + len(contents), len(data), kind, 0)
        contents += data
    bif = b"BIFFV1  " + struct.pack("<III", len(resources), 0, 20) + entries + contents
    key = bytearray(b"KEY V1  " + struct.pack("<IIII", 1, len(resources), 24, 36 + len(name)))
    key += struct.pack("<IIHH", len(bif), 36, len(name), 1) + name
    for ordinal, (resref, kind, _) in enumerate(resources):
        key += struct.pack("<8sHI", resref.encode("ascii"), kind, ordinal)
    (game_root / "data").mkdir()
    (game_root / "data/fixture.bif").write_bytes(bif)
    (game_root / "chitin.key").write_bytes(key)


def fixture(root: Path, game: str, language: str, fixture_dir: Path | None,
            row_count: int = 99, missing_table: bool = False) -> bytes:
    root.mkdir()
    (root / "override").mkdir()
    for lang in {"en_us", language}:
        (root / f"lang/{lang}/sounds").mkdir(parents=True)
        (root / f"lang/{lang}/dialog.tlk").write_bytes(make_tlk())
    (root / "override/M_cdsnd.lua").write_bytes(b"filenames_stringrefs['ORIGINAL'] = {1, 2}\n")
    # Keep data rows wider than the two-token 2DA signature/header. WeiDU's
    # COUNT_2DA_ROWS filters by token count; real CHARSND tables have many voices.
    base_table = ("2DA V1.0\n-1\nORIGINAL CONTROL\n" + "".join(f"{i} 1 -1\n" for i in range(1, row_count + 1))).encode("ascii")
    ids = b"IDS V1.0\n79 BGEE_ACTION4\n82 BGEE_ACTION7\n92 IWDEE_REACT_TO_DIE_GENERAL2\n"
    if fixture_dir and row_count == 99:
        kind = "bgee" if game in ("bgee", "sod") else "bg2ee"
        base_table = (fixture_dir / kind / "CHARSND.2DA").read_bytes()
        ids = (fixture_dir / kind / "SNDSLOT.IDS").read_bytes()
    resources = [("SNDSLOT", 1008, ids)]
    if not missing_table:
        resources.append(("CHARSND", 1012, base_table))
    markers = {
        "bgee": ["OH1000"], "sod": ["OH1000", "BD0100"],
        "bg2ee": ["OH6000"], "eet": ["OH1000", "OH6000"],
        "classic": ["AR0125"],
    }
    resources.extend((marker, 1010, b"AREAV1.0") for marker in markers[game])
    if game == "eet":
        (root / "override/eet.flag").write_bytes(b"EET")
    write_key_bif(root, resources)
    return base_table


def tree(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)).replace("\\", "/").lower(): sha256(path.read_bytes())
            for path in root.rglob("*") if path.is_file()}


def run_weidu(root: Path, mod: str, language: str, uninstall: bool = False) -> str:
    action = "--force-uninstall-list" if uninstall else "--force-install-list"
    args = [str(root / f"setup-{mod}.exe"), f"{mod}/{mod}.tp2", "--no-auto-tp2",
            "--noautoupdate", "--game", str(root), "--language", "0", "--use-lang", language,
            action, "0", "--no-exit-pause", "--log", f"{mod}-{'uninstall' if uninstall else 'install'}.debug"]
    result = subprocess.run(args, cwd=root, stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
    output = (result.stdout + result.stderr).decode("utf-8", "replace")
    (root / f"{mod}-{'uninstall' if uninstall else 'install'}.transcript").write_text(output, encoding="utf-8")
    if result.returncode or re.search(r"ERROR|FATAL", output):
        raise AssertionError(f"WeiDU failed ({result.returncode}) in {root}:\n{output[-7000:]}")
    return output


def unpack_release(release_dir: Path, root: Path, pack: tuple) -> dict[str, bytes]:
    ident, _, _, _ = pack
    with zipfile.ZipFile(release_dir / f"{ident}-player-voicepack-v{VERSION}.zip") as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
        # Build step has validated every path; repeat the boundary check here.
        for name, data in files.items():
            target = (root / name).resolve()
            assert target.is_relative_to(root.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return files


def check_registration(root: Path, files: dict[str, bytes], mod: str, game: str,
                       language: str, previous: bytes, slots: int) -> bytes:
    tp = files[f"{mod}/{mod}.tp2"].decode("utf-8")
    tra = files[f"{mod}/english/setup.tra"].decode("utf-8")
    prefix = re.search(r'cd_name\s*=\s*"([^"]+)"', tp)[1].upper()
    calls = {key: int(ref) for key, ref in SLOT_CALL.findall(tp)}
    strings = {int(ref): (text, sound.upper()) for ref, text, sound in TRA_ENTRY.findall(tra)}
    before_header, before_rows = table(previous)
    after_data = (root / "override/charsnd.2da").read_bytes()
    header, rows = table(after_data)
    assert header == before_header + [prefix], (game, mod, header)
    assert set(rows) == set(before_rows)
    assert all(rows[row][:-1] == before_rows[row] for row in rows), (game, mod, "changed original column")
    tlk = tlk_entries((root / f"lang/{language}/dialog.tlk").read_bytes())
    expected = {slot_rows(game)[key]: strings[ref] for key, ref in calls.items() if key != "select_name"}
    assert len(expected) == slots
    for row, values in rows.items():
        ref = int(values[-1])
        if row in expected:
            assert tlk[ref] == expected[row], (game, mod, row, tlk[ref], expected[row])
        else:
            assert ref == -1, (game, mod, row, "unexpected occupied slot")
    lua = (root / "override/M_cdsnd.lua").read_text(encoding="utf-8")
    assert "filenames_stringrefs['ORIGINAL'] = {1, 2}" in lua
    registrations = re.findall(rf"filenames_stringrefs\['{prefix}'\] = \{{(\d+), 2\}}", lua)
    assert len(registrations) == 1
    assert tlk[int(registrations[0])] == strings[calls["select_name"]]
    for name, data in files.items():
        if "/sounds/" in name:
            installed = root / f"lang/{language}/sounds/{Path(name).name}"
        elif "/wav/" in name:
            installed = root / f"override/{Path(name).name}"
        else:
            continue
        assert installed.read_bytes() == data
    return after_data


def positive_matrix(work: Path, release_dir: Path, cache: Path, fixture_dir: Path | None) -> list[dict]:
    results = []
    for game, language in [(g, "en_us") for g in ("bgee", "sod", "bg2ee", "eet")] + [("bgee", "de_de"), ("bg2ee", "de_de")]:
        root = work / f"{game}-{language}"
        current = fixture(root, game, language, fixture_dir)
        original_override = tree(root / "override")
        original_tlk = tlk_entries((root / f"lang/{language}/dialog.tlk").read_bytes())
        untouched = {str(p): sha256(p.read_bytes()) for p in (root / "chitin.key", root / "data/fixture.bif")}
        installed = []
        for pack in PACKS:
            ident, mod, slots, _ = pack
            files = unpack_release(release_dir, root, pack)
            source = original_files(cache, pack)
            assert set(files) == set(source)
            for name, data in source.items():
                if not name.endswith((".tp2", ".tra")):
                    assert files[name] == data, (ident, name, "payload changed")
            # Every original subtitle and sound association is retained verbatim.
            old_entries = {int(n): (t, s) for n, t, s in TRA_ENTRY.findall(source[f"{mod}/english/setup.tra"].decode("utf-8"))}
            new_entries = {int(n): (t, s) for n, t, s in TRA_ENTRY.findall(files[f"{mod}/english/setup.tra"].decode("utf-8"))}
            assert all(new_entries[n] == value for n, value in old_entries.items() if n != 71)
            before = current
            output = run_weidu(root, mod, language)
            assert "SUCCESSFULLY INSTALLED" in output and "SKIPPING:" not in output
            current = check_registration(root, files, mod, game, language, before, slots)
            installed.append((mod, before))
        # Reinstall the final pack using its normal two-step uninstall/install path.
        last_mod, last_before = installed[-1]
        run_weidu(root, last_mod, language, uninstall=True)
        run_weidu(root, last_mod, language)
        files = {str(p.relative_to(root)).replace("\\", "/"): p.read_bytes()
                 for p in (root / last_mod).rglob("*") if p.is_file() and "backup" not in p.parts}
        check_registration(root, files, last_mod, game, language, last_before, PACKS[-1][2])
        for mod, before in reversed(installed):
            run_weidu(root, mod, language, uninstall=True)
            if (root / "override/charsnd.2da").exists():
                assert table((root / "override/charsnd.2da").read_bytes()) == table(before)
        assert tree(root / "override") == original_override
        for lang in {"en_us", language}:
            assert not tree(root / f"lang/{lang}/sounds")
        after_tlk = tlk_entries((root / f"lang/{language}/dialog.tlk").read_bytes())
        assert after_tlk[:len(original_tlk)] == original_tlk
        assert all(sha256(Path(p).read_bytes()) == digest for p, digest in untouched.items())
        results.append({"game": game, "language": language, "packsInstalledAndUninstalled": len(PACKS), "assignmentsVerified": sum(p[2] for p in PACKS), "reinstall": "passed"})
        print(f"PASS {game}/{language}: all 14 installs, 556 mappings, reinstall, uninstall", flush=True)
    return results


def rejection_matrix(work: Path, release_dir: Path) -> list[dict]:
    results = []
    cases = [("classic", 99, False), ("bgee", 30, False), ("bgee", 99, True)]
    for index, (game, count, missing) in enumerate(cases):
        root = work / f"rejected-{index}"
        fixture(root, game, "en_us", None, row_count=count, missing_table=missing)
        before = tree(root / "override")
        tlk = (root / "lang/en_us/dialog.tlk").read_bytes()
        for pack in PACKS:
            unpack_release(release_dir, root, pack)
            mod = pack[1]
            try:
                output = run_weidu(root, mod, "en_us")
            except AssertionError as error:
                # An old table fails in the controlled preflight patch before audio.
                output = str(error)
                assert count != 99 and "older or incompatible soundset layout" in output
            assert "SUCCESSFULLY INSTALLED" not in output
            assert "SKIPPING:" in output or "older or incompatible soundset layout" in output
            assert tree(root / "override") == before
            assert (root / "lang/en_us/dialog.tlk").read_bytes() == tlk
            assert not tree(root / "lang/en_us/sounds")
        results.append({"game": game, "rows": count, "missingTable": missing, "packsRejectedWithoutChanges": 14})
        print(f"PASS rejection {game}/{count} rows/missing={missing}: all 14", flush=True)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--source-dir", type=Path, default=ROOT / "_cache/v1.0.0")
    parser.add_argument("--fixture-dir", type=Path, help="Optional read-only captures: bgee/ and bg2ee/ each containing CHARSND.2DA and SNDSLOT.IDS")
    args = parser.parse_args()
    (ROOT / "_work").mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="installer-tests-", dir=ROOT / "_work"))
    report = {"version": VERSION, "scope": "Actual WeiDU in disposable fixtures; no game engine launched", "work": str(work)}
    report["positive"] = positive_matrix(work, args.release_dir, args.source_dir, args.fixture_dir)
    report["negative"] = rejection_matrix(work, args.release_dir)
    if args.fixture_dir:
        report["capturedResourceHashes"] = {str(p.relative_to(args.fixture_dir)): sha256(p.read_bytes())
                                             for p in args.fixture_dir.rglob("*") if p.suffix.lower() in (".ids", ".2da")}
    (work / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"All checks passed. Report: {work / 'report.json'}")
