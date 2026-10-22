"""Verify strict companion Viconia (BG1/BG2) provenance and real WeiDU in disposable games.

Never targets a supplied game for installation: --source is read-only, and every
installer target is a freshly created child of --work-dir. No engine is launched.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

from build_ajantis import GameResources
import verify_installers as common


VERSION = "1.0.0"
HELPER_SHA256 = "a581fae61b165c0c8af8a6ad7136b7b1b825e14d379c528bfb89453a06f843c5"
# Independent expectations: original companion CRE tables, not the builder's slot map.
VARIANTS = {
    "bg1": {
        "mod": "cd_vicbg1", "prefix": "VICOB1", "menu": "Viconia (BG1)",
        "creatures": ("VICONI", "VICONI4", "VICONI6"), "source_rows": "bgee",
        # BGEE native rows 35-38 are rare selection, NOT action acknowledgements 4-7,
        # and are not duplicated into rare action rows 63/64. No city line exists.
        "expected": {
            1: ("morale_break1", "VICON02"), 2: ("happy", "VICON04"),
            3: ("unhappy_1", "VICON05"), 4: ("unhappy_2", "VICON06"),
            5: ("breaking_pt", "VICON07"), 6: ("leader1", "VICON08"),
            7: ("tired1", "VICON09"), 8: ("bored1", "VICON10"),
            9: ("battlecry1", "VICON03"), 18: ("damage1", "VICON38"),
            19: ("dying1", "VICON39"), 20: ("hurt1", "VICON11"),
            21: ("forest", "VICON12"), 23: ("dungeon", "VICON14"),
            24: ("day", "VICON15"), 25: ("night", "VICON16"),
            26: ("common1", "VICON17"), 27: ("common2", "VICON18"),
            28: ("common3", "VICON19"), 32: ("action1", "VICON20"),
            33: ("action2", "VICON21"), 34: ("action3", "VICON22"),
            35: ("select_rare1", "VICON23"), 36: ("select_rare2", "VICON24"),
            37: ("select_rare3", "VICON25"), 38: ("select_rare4", "VICON26"),
            53: ("gen_death1", "VICON40"),
        },
        # The September build also registered select_rare2/4 as action_rare1/2.
        "retired_legacy_audio": {"lang/en_us/sounds/vicob1x.wav", "lang/en_us/sounds/vicob1y.wav"},
    },
    "bg2": {
        "mod": "cd_vicbg2", "prefix": "VICOB2", "menu": "Viconia (BG2)",
        "creatures": ("VICONI16", "VICONI6", "VICONI8", "VICONI9", "VICONI11", "VICONI13"),
        "source_rows": "bg2ee",
        # BG2 native rows 35-38 are action acknowledgements 4-7.
        "expected": {
            1: ("morale_break1", "VICONI02"), 2: ("happy", "VICONI03"),
            3: ("unhappy_1", "VICONI04"), 4: ("unhappy_2", "VICONI05"),
            5: ("breaking_pt", "VICONI06"), 6: ("leader1", "VICONI07"),
            7: ("tired1", "VICONI08"), 8: ("bored1", "VICONI09"),
            9: ("battlecry1", "VICONI10"), 10: ("battlecry2", "VICONI11"),
            11: ("battlecry3", "VICONI12"), 18: ("damage1", "VICONI13"),
            19: ("dying1", "VICONI14"), 20: ("hurt1", "VICONI15"),
            21: ("forest", "VICONI16"), 22: ("city", "VICONI17"),
            23: ("dungeon", "VICONI18"), 24: ("day", "VICONI19"),
            25: ("night", "VICONI20"), 26: ("common1", "VICONI21"),
            27: ("common2", "VICONI22"), 28: ("common3", "VICONI23"),
            29: ("common4", "VICONI24"), 30: ("common5", "VICONI25"),
            31: ("common6", "VICONI26"), 32: ("action1", "VICONI27"),
            33: ("action2", "VICONI28"), 34: ("action3", "VICONI29"),
            35: ("action4", "VICONI30"), 36: ("action5", "VICONI31"),
            37: ("action6", "VICONI32"), 38: ("action7", "VICONI33"),
            63: ("action_rare1", "VICONI34"), 64: ("action_rare2", "VICONI35"),
            65: ("criticalhit", "VICONI36"), 66: ("criticalmiss", "VICONI37"),
            67: ("immune", "VICONI38"), 68: ("inventory", "VICONI39"),
            71: ("disrupted", "VICONI42"),
        },
        "retired_legacy_audio": set(),
    },
}
GAMES = ("bgee", "sod", "bg2ee", "eet")
LANGUAGES = ("en_us", "de_de")

# Set by configure() from --variant before any check runs.
MOD = PREFIX = MENU = ""
SPEC: dict = {}
EXPECTED: dict[int, tuple[str, str]] = {}


def configure(variant: str) -> None:
    global MOD, PREFIX, MENU, SPEC, EXPECTED
    SPEC = VARIANTS[variant]
    MOD, PREFIX, MENU, EXPECTED = SPEC["mod"], SPEC["prefix"], SPEC["menu"], SPEC["expected"]
    native = common.slot_rows(SPEC["source_rows"])
    # The independent table must agree with the independent event-to-row map.
    assert all(native[key] == row for row, (key, _) in EXPECTED.items()), "Expectation table inconsistent"


def normalize_subtitle(text: str) -> str:
    return re.sub(r"^\[VICONIA \d+\]\s*", "", text).strip()


def read_package(root: Path, *, legacy: bool = False) -> dict[str, bytes]:
    """Read only this standalone pack, never sibling packages or old backups."""
    mod_root = root / MOD
    assert mod_root.is_dir(), f"Missing package: {mod_root}"
    files = {}
    for path in mod_root.rglob("*"):
        if not path.is_file() or "backup" in path.relative_to(mod_root).parts:
            continue
        relative = path.relative_to(root).as_posix()
        if legacy and (path.suffix.lower() in (".debug", ".log") or path.name.endswith(".transcript")):
            continue
        assert path.resolve().is_relative_to(root.resolve()), ("Package escapes root", path)
        files[relative] = path.read_bytes()
    executables = [p for p in root.iterdir() if p.is_file() and p.name.lower() == f"setup-{MOD}.exe"]
    assert len(executables) == 1, f"Expected one setup-{MOD}.exe in {root}"
    files[f"setup-{MOD}.exe"] = executables[0].read_bytes()
    for required in (f"{MOD}/{MOD}.tp2", f"{MOD}/english/setup.tra", f"{MOD}/tph/cd_add_soundset.tph"):
        assert required in files, f"Missing {required}"
    return files


def copy_package(files: dict[str, bytes], root: Path) -> None:
    for name, data in files.items():
        path = (root / name).resolve()
        assert path.is_relative_to(root.resolve())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def decode_source(data: bytes, ffmpeg: str) -> tuple[int, bytes]:
    """Independent decoder invocation; do not reuse the builder's audio function."""
    executable = Path(ffmpeg)
    probe = executable.with_name("ffprobe" + executable.suffix)
    probe_result = subprocess.run(
        [str(probe), "-v", "error", "-select_streams", "a:0", "-show_entries",
         "stream=sample_rate,channels", "-of", "json", "-i", "pipe:0"],
        input=data, capture_output=True, timeout=30, check=True,
    )
    streams = json.loads(probe_result.stdout)["streams"]
    assert len(streams) == 1 and streams[0]["channels"] == 1, streams
    rate = int(streams[0]["sample_rate"])
    decoded = subprocess.run(
        [str(executable), "-v", "error", "-i", "pipe:0", "-map", "0:a:0",
         "-ac", "1", "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1"],
        input=data, capture_output=True, timeout=30, check=True,
    ).stdout
    assert decoded and len(decoded) % 2 == 0
    return rate, decoded


def check_package(files: dict[str, bytes], source: Path, ffmpeg: str) -> dict:
    provenance = json.loads(files[f"{MOD}/provenance.json"])
    assert provenance["version"] == VERSION and provenance["menu_name"] == MENU
    helper_hash = common.sha256(files[f"{MOD}/tph/cd_add_soundset.tph"])
    assert helper_hash == provenance["helper_sha256"] == HELPER_SHA256
    records = provenance["slots"]
    assert len(records) == len(EXPECTED)
    by_slot = {entry["source_slot"]: entry for entry in records}
    assert len(by_slot) == len(records) and set(by_slot) == set(EXPECTED)
    tp = files[f"{MOD}/{MOD}.tp2"].decode("utf-8-sig")
    tra = files[f"{MOD}/english/setup.tra"].decode("utf-8-sig")
    assert re.search(rf'cd_name\s*=\s*"{PREFIX}"', tp)
    assert re.search(rf"VERSION\s+~{re.escape(VERSION)}~", tp)
    calls_list = common.SLOT_CALL.findall(tp)
    calls = {key: int(ref) for key, ref in calls_list}
    assert len(calls) == len(calls_list), "Duplicate slot assignments"
    assert set(calls) == {key for key, _ in EXPECTED.values()} | {"select_name"}
    entries_list = common.TRA_ENTRY.findall(tra)
    entries = {int(ref): (text, sound.upper()) for ref, text, sound in entries_list}
    assert len(entries) == len(entries_list), "Duplicate TRA numbers"
    assert entries[calls["select_name"]] == (MENU, "")
    game = GameResources(source)
    assert provenance["source_key_sha256"] == common.sha256(game.key)
    assert provenance["source_tlk_sha256"] == common.sha256(game.tlk)
    native_rows = set(common.slot_rows(SPEC["source_rows"]).values())
    source_creatures = {}
    for name in SPEC["creatures"]:
        cre, origin = game.get(name, 1009, "CRE", base=True)
        assert cre[:8] == b"CRE V1.0"
        refs = struct.unpack_from("<100i", cre, 0xA4)
        playable = {}
        for row in native_rows:
            if refs[row] < 0:
                continue
            text, sound = game.string(refs[row])
            if sound:
                try:
                    game.get(sound, 4, "WAV", base=True)
                except KeyError:
                    continue
                playable[row] = (normalize_subtitle(text), sound)
        assert set(playable) == set(EXPECTED), (name, "Changed native recorded player rows", playable)
        for row, (_, sound) in EXPECTED.items():
            assert playable[row][1] == sound, (name, row, playable[row])
        source_creatures[name] = {"origin": origin, "sha256": common.sha256(cre)}
        if name == SPEC["creatures"][0]:
            source_entries = playable
        else:
            assert playable == source_entries, (name, "Companion variant differs")
    assert {record["cre"]: {"origin": record["origin"], "sha256": record["sha256"]}
            for record in provenance["source_variants"]} == source_creatures
    expected_audio = set()
    for row, (key, source_resref) in EXPECTED.items():
        entry = by_slot[row]
        assert entry["slot_key"] == key and entry["source_resref"].upper() == source_resref
        target = entry["target_resref"]
        assert re.fullmatch(rf"{PREFIX}[A-Za-z0-9_]{{1,2}}", target), target
        assert calls[key] == entry["tra"]
        assert entry["subtitle"] == source_entries[row][0]
        assert entries[entry["tra"]] == (entry["subtitle"], target.upper())
        folder = entry["folder"]
        assert folder in ("sounds", "wav")
        assert folder == ("sounds" if len(target) == 7 else "wav")
        matches = [name for name in files if name.lower() == f"{MOD}/{folder}/{target}.wav".lower()]
        assert len(matches) == 1, (target, matches)
        path = matches[0]
        assert path not in expected_audio, ("Reused target audio", target)
        expected_audio.add(path)
        original, _ = game.get(source_resref, 4, "WAV", base=True)
        assert common.sha256(original) == entry["source_sha256"]
        rate, decoded = decode_source(original, ffmpeg)
        with wave.open(io.BytesIO(files[path]), "rb") as wav:
            assert wav.getnchannels() == 1 and wav.getsampwidth() == 2 and wav.getcomptype() == "NONE"
            assert wav.getframerate() == rate == entry["sample_rate"]
            assert wav.getnframes() == entry["frames"] == len(decoded) // 2
            pcm = wav.readframes(wav.getnframes())
        assert pcm == decoded, (source_resref, "PCM was altered or recut")
        assert common.sha256(pcm) == entry["pcm_sha256"]
        assert common.sha256(files[path]) == entry["wav_sha256"]
    # The same source recording must never feed two events (no rare-line duplication).
    assert len({entry["source_resref"].upper() for entry in records}) == len(records), "Recording reused"
    actual_audio = {name for name in files if name.lower().endswith(".wav")}
    assert actual_audio == expected_audio, ("Extra/missing audio", actual_audio ^ expected_audio)
    return {"source": str(source), "sourceKeySha256": common.sha256(game.key),
            "sourceTlkSha256": common.sha256(game.tlk), "creatures": source_creatures,
            "assignedSlots": len(EXPECTED), "nativeRateUncutPcm": "passed", "slots": records}


def tlk_records(data: bytes) -> list[tuple[str, str, int, int, int]]:
    entries = common.tlk_entries(data)
    records = []
    for index, (text, sound) in enumerate(entries):
        offset = 18 + 26 * index
        flags = struct.unpack_from("<H", data, offset)[0]
        volume, pitch = struct.unpack_from("<II", data, offset + 10)
        records.append((text, sound, flags, volume, pitch))
    return records


def female_tlk() -> bytes:
    text = b"Original female voice"
    return (b"TLK V1  " + struct.pack("<HII", 0, 2, 70) + bytes(26)
            + struct.pack("<H8sIIII", 1, b"", 0, 0, 0, len(text)) + text)


def setup_fixture(root: Path, game: str, language: str, fixtures: Path,
                  *, row_count: int = 99, missing_table: bool = False) -> bytes:
    previous = common.fixture(root, game, language, fixtures if row_count == 99 else None,
                              row_count=row_count, missing_table=missing_table)
    for lang in {"en_us", language}:
        (root / f"lang/{lang}/dialogF.tlk").write_bytes(female_tlk())
        (root / f"lang/{lang}/sounds/CONTROL.wav").write_bytes(b"Existing unrelated sound\n")
    (root / "override/CONTROL.bin").write_bytes(b"Existing unrelated override resource\n")
    return previous


def game_tree(root: Path) -> dict[str, str]:
    result = {"chitin.key": common.sha256((root / "chitin.key").read_bytes())}
    for folder in ("override", "lang", "data"):
        result.update({f"{folder}/{path}": digest for path, digest in common.tree(root / folder).items()})
    return result


def tlk_snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix().lower(): p.read_bytes()
            for p in (root / "lang").rglob("*") if p.is_file() and p.suffix.lower() == ".tlk"}


def audio_targets(files: dict[str, bytes], language: str) -> dict[str, str]:
    paths = {}
    for name, data in files.items():
        if "/sounds/" in name and name.lower().endswith(".wav"):
            target = f"lang/{language}/sounds/{Path(name).name}"
        elif "/wav/" in name and name.lower().endswith(".wav"):
            target = f"override/{Path(name).name}"
        else:
            continue
        paths[target.lower()] = common.sha256(data)
    return paths


def assert_tlk_preserved(before: dict[str, bytes], root: Path, language: str) -> None:
    after = tlk_snapshot(root)
    assert set(after) == set(before)
    for name, original in before.items():
        if name.startswith(f"lang/{language}/"):
            original_entries = tlk_records(original)
            assert tlk_records(after[name])[:len(original_entries)] == original_entries, name
        else:
            assert after[name] == original, ("Unselected language changed", name)


def assert_installed_files(root: Path, baseline: dict[str, str], files: dict[str, bytes], language: str) -> None:
    after = game_tree(root)
    audio = audio_targets(files, language)
    permitted = set(audio) | {"override/charsnd.2da", "override/m_cdsnd.lua",
                             f"lang/{language}/dialog.tlk", f"lang/{language}/dialogf.tlk"}
    assert set(after) - set(baseline) <= permitted, ("Unexpected game file", set(after) - set(baseline) - permitted)
    assert not set(baseline) - set(after), "Deleted original game file"
    for name, digest in baseline.items():
        if name not in permitted:
            assert after[name] == digest, ("Changed unrelated game file", name)
    assert all(after.get(name) == digest for name, digest in audio.items())


def assert_install_write_allowlist(root: Path, before: dict[str, str], files: dict[str, bytes], language: str) -> None:
    """Include setup/mod sources and root files, not just the engine resource tree."""
    after = common.tree(root)
    engine = set(audio_targets(files, language)) | {
        "override/charsnd.2da", "override/m_cdsnd.lua",
        f"lang/{language}/dialog.tlk", f"lang/{language}/dialogf.tlk",
    }
    installer_files = {"weidu.log", "weidu.conf"} | {
        f"{MOD}-{action}.{extension}"
        for action in ("install", "uninstall") for extension in ("debug", "transcript")
    }
    for name in set(before) | set(after):
        if before.get(name) == after.get(name):
            continue
        assert (name in engine or name in installer_files
                or name.startswith((f"{MOD}/backup/", "inlined/", "diagnostics/"))), (
            "Installer wrote outside its allowlist", name)


def assert_restored(root: Path, baseline: dict[str, str], before_tlk: dict[str, bytes], language: str) -> None:
    after = game_tree(root)
    selected_tlks = {f"lang/{language}/dialog.tlk", f"lang/{language}/dialogf.tlk"}
    assert {k: v for k, v in after.items() if k not in selected_tlks} == {
        k: v for k, v in baseline.items() if k not in selected_tlks
    }, "Uninstall did not byte-exactly restore override/sounds/resources"
    assert_tlk_preserved(before_tlk, root, language)
    assert not active_log(root), f"{MENU} still recorded as installed"


def active_log(root: Path) -> list[str]:
    path = root / "WeiDU.log"
    if not path.exists():
        return []
    lines = [line for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
             if line.lstrip().startswith("~")]
    mod = re.escape(MOD.upper())
    assert all(re.match(rf"~(?:{mod}[/\\])?(?:SETUP-)?{mod}\.TP2~\s+#0\s+#0(?:\s|$)", line, re.I)
               for line in lines), ("Unrelated component recorded", lines)
    return lines


def run_step(root: Path, language: str, label: str, *, uninstall: bool = False) -> str:
    kind = "uninstall" if uninstall else "install"
    try:
        return common.run_weidu(root, MOD, language, uninstall=uninstall)
    finally:
        diagnostics = root / "diagnostics"
        diagnostics.mkdir(exist_ok=True)
        for extension in ("debug", "transcript"):
            path = root / f"{MOD}-{kind}.{extension}"
            if path.exists():
                shutil.copyfile(path, diagnostics / f"{label}.{extension}")


def inspect_registration(root: Path, files: dict[str, bytes], game: str, language: str,
                         previous: bytes, baseline: dict[str, str], original_tlks: dict[str, bytes]) -> None:
    common.check_registration(root, files, MOD, game, language, previous, len(EXPECTED))
    assert len(active_log(root)) == 1
    _, rows = common.table((root / "override/charsnd.2da").read_bytes())
    occupied = {row: int(values[-1]) for row, values in rows.items() if int(values[-1]) != -1}
    expected_rows = {common.slot_rows(game)[key] for key, _ in EXPECTED.values()}
    assert set(occupied) == expected_rows and len(occupied) == len(EXPECTED)
    lua = (root / "override/M_cdsnd.lua").read_text(encoding="utf-8")
    menu_ref = int(re.findall(rf"filenames_stringrefs\['{PREFIX}'\] = \{{(\d+), 2\}}", lua)[0])
    male = tlk_records((root / f"lang/{language}/dialog.tlk").read_bytes())
    for filename in ("dialog.tlk", "dialogF.tlk"):
        entries = tlk_records((root / f"lang/{language}/{filename}").read_bytes())
        for row, ref in occupied.items():
            assert 0 <= ref < len(entries), (filename, row, "Dangling strref", ref)
            text, sound, flags, _, _ = entries[ref]
            assert (text, sound) == male[ref][:2], (filename, row, "Male/female text or sound mismatch")
            assert flags & 2 and (not text or flags & 1), (filename, row, "Bad TLK text/sound flags", flags)
        assert 0 <= menu_ref < len(entries)
        assert entries[menu_ref][:2] == (MENU, "")
        # WeiDU normally sets flags 7 even when the sound resref is empty.
        # Require visible text; the empty resref above proves there is no menu audio.
        assert entries[menu_ref][2] & 1, (filename, "Menu text flag")
    assert_installed_files(root, baseline, files, language)
    assert_tlk_preserved(original_tlks, root, language)


def positive_case(work: Path, files: dict[str, bytes], fixtures: Path, game: str, language: str) -> dict:
    root = work / f"positive-{game}-{language}"
    previous = setup_fixture(root, game, language, fixtures)
    baseline, original_tlks = game_tree(root), tlk_snapshot(root)
    copy_package(files, root)
    root_before = common.tree(root)
    for number in (1, 2):
        output = run_step(root, language, f"install-{number}")
        assert "SUCCESSFULLY INSTALLED" in output and "SKIPPING:" not in output
        inspect_registration(root, files, game, language, previous, baseline, original_tlks)
        assert_install_write_allowlist(root, root_before, files, language)
        output = run_step(root, language, f"uninstall-{number}", uninstall=True)
        assert "SUCCESSFULLY REMOVED" in output
        assert_restored(root, baseline, original_tlks, language)
        assert_install_write_allowlist(root, root_before, files, language)
    print(f"PASS {game}/{language}: {len(EXPECTED)} exact companion assignments, male/female TLKs, reinstall/uninstall", flush=True)
    return {"game": game, "language": language, "assignments": len(EXPECTED), "installations": 2,
            "maleAndFemaleTlk": "passed", "unselectedLanguageUnchanged": "passed",
            "reinstall": "passed", "byteExactResourceRestoration": "passed"}


def negative_case(work: Path, files: dict[str, bytes], fixtures: Path, case: str) -> dict:
    root = work / f"negative-{case}"
    game = "classic" if case == "classic" else "bgee"
    previous = setup_fixture(root, game, "en_us", fixtures,
                             row_count=30 if case == "old-table" else 99,
                             missing_table=case == "missing-table")
    if case in ("malformed-table", "duplicate-column"):
        header, rows = common.table(previous)
        if case == "malformed-table":
            # Preserve row count/width but break the exact ordered 1-99 labels.
            content = "2DA V1.0\n-1\n" + " ".join(header) + "\n"
            content += "".join(f"{100 if row == 50 else row} {' '.join(values)}\n" for row, values in rows.items())
        else:
            content = "2DA V1.0\n-1\n" + " ".join(header + [PREFIX]) + "\n"
            content += "".join(f"{row} {' '.join(values)} -1\n" for row, values in rows.items())
        (root / "override/charsnd.2da").write_text(content, encoding="ascii")
    if case == "duplicate-menu":
        with (root / "override/M_cdsnd.lua").open("ab") as stream:
            stream.write(f"filenames_stringrefs['{PREFIX}'] = {{1, 2}}\n".encode("ascii"))
    baseline, original_tlks = game_tree(root), tlk_snapshot(root)
    copy_package(files, root)
    try:
        output = run_step(root, "en_us", "rejected-install")
    except AssertionError as error:
        output = str(error)
    assert "SUCCESSFULLY INSTALLED" not in output, (case, output)
    assert any(marker in output for marker in ("SKIPPING:", "NOT INSTALLED DUE TO ERRORS")), (case, output)
    if case in ("old-table", "malformed-table", "missing-table"):
        assert "older or incompatible soundset layout" in output, (case, output)
    if case.startswith("duplicate-"):
        assert f"{MENU} is already registered" in output, (case, output)
    assert game_tree(root) == baseline, (case, "Failed preflight changed game resources")
    assert tlk_snapshot(root) == original_tlks, (case, "Failed preflight changed strings")
    assert not active_log(root)
    print(f"PASS rejection {case}: no game-resource or TLK changes", flush=True)
    return {"case": case, "rejectedWithoutGameChanges": True}


def legacy_case(work: Path, files: dict[str, bytes], legacy: dict[str, bytes], fixtures: Path,
                *, lost_tlk_flush: bool) -> dict:
    label = "lost-tlk-flush" if lost_tlk_flush else "valid-install"
    root = work / f"legacy-{label}"
    previous = setup_fixture(root, "eet", "en_us", fixtures)
    baseline, original_tlks = game_tree(root), tlk_snapshot(root)
    copy_package(legacy, root)
    output = run_step(root, "en_us", "legacy-install")
    assert "SUCCESSFULLY INSTALLED" in output and len(active_log(root)) == 1
    legacy_targets = audio_targets(legacy, "en_us")
    assert all(game_tree(root).get(name) == digest for name, digest in legacy_targets.items())
    if lost_tlk_flush:
        # Disposable-only reconstruction of the failed final TLK write: registrations
        # and WeiDU backup state exist, but both TLKs still contain their old bytes.
        for name, data in original_tlks.items():
            (root / name).write_bytes(data)
        _, rows = common.table((root / "override/charsnd.2da").read_bytes())
        assert any(int(values[-1]) >= len(common.tlk_entries(original_tlks["lang/en_us/dialog.tlk"]))
                   for values in rows.values() if int(values[-1]) >= 0)
    output = run_step(root, "en_us", "legacy-uninstall", uninstall=True)
    assert "SUCCESSFULLY REMOVED" in output
    assert_restored(root, baseline, original_tlks, "en_us")
    # Overlay normally, deliberately retaining legacy WAVs and WeiDU backup files.
    # The new installer's explicit copy allowlist must NOT republish retired clips.
    copy_package(files, root)
    assert all((root / name).exists() for name in legacy if name.lower().endswith(".wav"))
    root_before = common.tree(root)
    output = run_step(root, "en_us", "replacement-install")
    assert "SUCCESSFULLY INSTALLED" in output and "SKIPPING:" not in output
    inspect_registration(root, files, "eet", "en_us", previous, baseline, original_tlks)
    assert_install_write_allowlist(root, root_before, files, "en_us")
    obsolete = set(legacy_targets) - set(audio_targets(files, "en_us"))
    # Exactly the known retired duplicates, if any; none for an identical file set.
    assert obsolete == SPEC["retired_legacy_audio"], ("Unexpected legacy/new audio difference", obsolete)
    assert not obsolete.intersection(game_tree(root)), ("Obsolete legacy audio survived", obsolete)
    output = run_step(root, "en_us", "replacement-uninstall", uninstall=True)
    assert "SUCCESSFULLY REMOVED" in output
    assert_restored(root, baseline, original_tlks, "en_us")
    assert_install_write_allowlist(root, root_before, files, "en_us")
    print(f"PASS legacy upgrade {label}: standard WeiDU replacement, obsolete audio absent: {sorted(obsolete)}", flush=True)
    return {"case": label, "replacement": "passed", "obsoleteAudioRemoved": sorted(obsolete),
            "duplicateRegistrations": 0, "danglingReplacementStrrefs": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True, choices=sorted(VARIANTS))
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True, help="Read-only clean BGEE (bg1) or BG2EE (bg2) game")
    parser.add_argument("--fixtures", type=Path, required=True, help="Read-only bgee/bg2ee CHARSND and SNDSLOT captures")
    parser.add_argument("--work-dir", type=Path, required=True, help="Parent of a NEW disposable run directory")
    parser.add_argument("--legacy-dir", type=Path, help="Optional read-only old standalone package root")
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"), help="ffmpeg executable; ffprobe must be beside it")
    args = parser.parse_args()
    assert args.ffmpeg, "ffmpeg is not on PATH; supply --ffmpeg"
    configure(args.variant)
    args.package_dir, args.source, args.fixtures, args.work_dir = (
        path.resolve() for path in (args.package_dir, args.source, args.fixtures, args.work_dir)
    )
    inputs = [args.package_dir, args.source, args.fixtures]
    if args.legacy_dir:
        args.legacy_dir = args.legacy_dir.resolve()
        inputs.append(args.legacy_dir)
    for path in inputs:
        assert not args.work_dir.is_relative_to(path), ("Work directory is inside a read-only input", path)
    # Reject a work directory inside ANY existing game tree, even an unspecified one.
    for path in (args.work_dir, *args.work_dir.parents):
        assert not (path / "chitin.key").exists(), f"Work directory is inside game: {path}"
    files = read_package(args.package_dir)
    provenance = check_package(files, args.source, args.ffmpeg)
    legacy = read_package(args.legacy_dir, legacy=True) if args.legacy_dir else None
    args.work_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"viconia-{args.variant}-installer-tests-", dir=args.work_dir))
    report = {"version": VERSION, "variant": args.variant,
              "scope": "Actual WeiDU in disposable fixtures; source games read-only; no engine launched",
              "work": str(work), "provenance": provenance, "positive": [], "negative": [], "legacy": []}
    try:
        for game in GAMES:
            for language in LANGUAGES:
                report["positive"].append(positive_case(work, files, args.fixtures, game, language))
        for case in ("classic", "old-table", "malformed-table", "missing-table", "duplicate-column", "duplicate-menu"):
            report["negative"].append(negative_case(work, files, args.fixtures, case))
        if legacy:
            for lost_tlk_flush in (False, True):
                report["legacy"].append(legacy_case(work, files, legacy, args.fixtures, lost_tlk_flush=lost_tlk_flush))
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["failure"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        (work / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Report: {work / 'report.json'}", flush=True)


if __name__ == "__main__":
    main()
