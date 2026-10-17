"""Build a reversible tail update for an already-installed Garithos 1.0 pack.

Owns only CGARIT rows 7/8/19/65, WAVs d/m/z and removal of the retired c WAV.
Other voices, other Garithos slots, existing menu registrations, TLK records,
portraits, saves, and later mods are preserved. No cascade reinstall is needed.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from build_release import ROOT, sha256, write_zip

MOD = "cd_garup"
VERSION = "1.1.0"
OLD_ZIP_SHA256 = "3b1cd7b778e64459e64cd09e0552a10847b06c4b73bc7da55985f236203557b9"


def build(full_archive: Path, old_archive: Path, output: Path) -> Path:
    assert sha256(old_archive.read_bytes()) == OLD_ZIP_SHA256, "Unexpected prior release"
    with zipfile.ZipFile(old_archive) as archive:
        old = json.loads(archive.read("cd_garith/provenance.json"))
    with zipfile.ZipFile(full_archive) as archive:
        new_files = {name: archive.read(name) for name in archive.namelist()}
    new = json.loads(new_files["cd_garith/provenance.json"])
    old_by_target = {r["target_resref"]: r for r in old["slots"]}
    new_by_target = {r["target_resref"]: r for r in new["slots"]}
    changed = {name for name, r in new_by_target.items()
               if name not in old_by_target or r["wav_sha256"] != old_by_target[name]["wav_sha256"]
               or r["subtitle"] != old_by_target[name]["subtitle"]}
    assert changed == {"CGARITD", "CGARITM", "CGARITZ"}
    assert old_by_target.keys() - new_by_target.keys() == {"CGARITC"}
    assert new["version"] == VERSION
    # These four event IDs are identical in BGEE, SoD, BG2EE and EET.
    assert {new_by_target[n]["bg2ee_eet_row"] for n in changed} == {8, 19, 65}
    files = {f"setup-{MOD}.exe": new_files["setup-cd_garith.exe"]}
    copy_lines, translations, refs = [], [], []
    for number, target in enumerate(sorted(changed), 1):
        r = new_by_target[target]
        candidates = [name for name in new_files if name.lower() == f"cd_garith/sounds/{target}.wav".lower()]
        assert len(candidates) == 1
        files[f"{MOD}/sounds/{target}.wav"] = new_files[candidates[0]]
        translations.append(f"@{number} = ~{r['subtitle']}~ [{target}]")
        copy_lines.append(f"COPY ~%MOD_FOLDER%/sounds/{target}.wav~ ~lang/%EE_LANGUAGE%/sounds/{target}.wav~")
        refs.append((r["bg2ee_eet_row"], number))
    assignments = "\n".join(f"    PATCH_IF (~%garup_label%~ STRING_EQUAL ~{row}~) BEGIN SET garup_value = RESOLVE_STR_REF(@{number}) END" for row, number in refs)
    tp = rf'''BACKUP ~{MOD}/backup~
SUPPORT ~https://github.com/Chrizhermann/chriz-bg-voicepacks~
VERSION ~{VERSION}~
LANGUAGE ~English~ ~english~ ~%MOD_FOLDER%/english/setup.tra~

BEGIN @0
DESIGNATED 0
LABEL ~Chriz-Garithos-V2-Update~
REQUIRE_PREDICATE (GAME_IS ~bgee bg2ee eet~) @71
REQUIRE_COMPONENT ~cd_garith/cd_garith.tp2~ 0 @74
REQUIRE_PREDICATE (FILE_EXISTS_IN_GAME ~charsnd.2da~) @72

// Resolve the owned column and event labels. Other columns, old values,
// row order and extra rows are not fingerprints or prerequisites.
COPY_EXISTING ~charsnd.2da~ ~override~
  COUNT_2DA_COLS garup_cols
  COUNT_2DA_ROWS garup_cols garup_rows
  PATCH_IF (garup_cols < 2 OR garup_rows < 1) BEGIN PATCH_FAIL @72 END
  READ_2DA_ENTRIES_NOW garup_header (garup_cols - 1)
  SET garup_matches = 0
  FOR (garup_col = 0; garup_col < garup_cols - 1; ++garup_col) BEGIN
    READ_2DA_ENTRY_FORMER garup_header 0 garup_col garup_name
    PATCH_IF (~%garup_name%~ STRING_EQUAL_CASE ~CGARIT~) BEGIN
      SET garup_matches += 1
      SET garup_target_col = garup_col + 1
    END
  END
  PATCH_IF (garup_matches != 1) BEGIN PATCH_FAIL @75 END
  PATCH_FOR_EACH garup_required IN 7 8 19 65 BEGIN
    SET garup_matches = 0
    FOR (garup_row = 0; garup_row < garup_rows; ++garup_row) BEGIN
      READ_2DA_ENTRY garup_row 0 garup_cols garup_label
      PATCH_IF (~%garup_label%~ STRING_EQUAL ~%garup_required%~) BEGIN
        SET garup_matches += 1
      END
    END
    PATCH_IF (garup_matches != 1) BEGIN PATCH_FAIL @76 END
  END
  // All validation precedes publication. Do not rewrite shared TLK strings.
  FOR (garup_row = 0; garup_row < garup_rows; ++garup_row) BEGIN
    READ_2DA_ENTRY garup_row 0 garup_cols garup_label
    SET garup_value = (0 - 2)
    PATCH_IF (~%garup_label%~ STRING_EQUAL ~7~) BEGIN SET garup_value = (0 - 1) END
{assignments}
    PATCH_IF (garup_value != (0 - 2)) BEGIN
      SET_2DA_ENTRY garup_row garup_target_col garup_cols ~%garup_value%~
    END
  END
  BUT_ONLY

{chr(10).join(copy_lines)}
// Retire only the old pack's tired file. WeiDU backs it up for uninstall.
ACTION_IF FILE_EXISTS ~lang/%EE_LANGUAGE%/sounds/CGARITc.wav~ BEGIN
  DELETE ~lang/%EE_LANGUAGE%/sounds/CGARITc.wav~
END
'''
    tra = "\n".join([
        "@0 = ~Garithos: corrected v2 sounds and subtitles (update existing pack)~",
        *translations,
        "@71 = ~This update requires BG:EE, BG2:EE, or EET.~",
        "@72 = ~Cannot update Garithos: CHARSND.2DA is missing or malformed.~",
        "@74 = ~Install the full Garithos voicepack first. This component only updates an existing registered pack.~",
        "@75 = ~Cannot update Garithos: CHARSND.2DA must contain exactly one CGARIT voice column.~",
        "@76 = ~Cannot update Garithos: one of event rows 7, 8, 19 or 65 is missing or duplicated.~", "",
    ])
    files[f"{MOD}/{MOD}.tp2"] = tp.encode("ascii")
    files[f"{MOD}/english/setup.tra"] = tra.encode("ascii")
    files[f"{MOD}/provenance.json"] = (json.dumps({
        "version": VERSION, "full_archive_sha256": sha256(full_archive.read_bytes()),
        "prior_archive_sha256": OLD_ZIP_SHA256, "owned_rows": [7, 8, 19, 65],
        "replaced_sounds": sorted(changed), "retired_sound": "CGARITC",
        "menu_and_other_slots": "unchanged", "uninstall": "Restores the state before this update.",
    }, indent=2) + "\n").encode("utf-8")
    files["README-Garithos-Update.txt"] = f'''Garithos v{VERSION}: update an existing voicepack

This small WeiDU component updates only the corrected Garithos v2 files and
their soundset rows. It does not uninstall/reinstall mods later than Garithos.
It does not edit existing TLK strings, menu names, other voices, portraits or saves.

Close the game, InfinityLoader and EEKeeper. Extract setup-{MOD}.exe and the
{MOD} folder into the actual game directory, then run setup-{MOD}.exe and
install component 0. The full cd_garith component 0 must already be installed.
Keep both mods' backup folders. Uninstall this update to restore the old lines.

After updating an existing character, reselect Garithos in Customize -> Sounds
so its stored sound-slot references match the new subtitles and empty tired slot.

The full garithos-voicepack-v{VERSION}.zip is for new installations. This smaller
update is for an existing pack, especially one buried beneath newer mods.
No installation is performed by creating this archive.
'''.encode("ascii")
    output = output.resolve()
    assert not any((p / "chitin.key").exists() for p in [output, *output.parents])
    output.mkdir(parents=True, exist_ok=True)
    assert not any(output.iterdir()), "Use an empty output folder"
    package = output / "Garithos Update"
    for name, data in files.items():
        target = package / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    archive = output / f"garithos-update-v{VERSION}.zip"
    write_zip(archive, files)
    print(f"Built {archive}: three replacement/new WAVs, four owned slots, reversible tail update")
    return archive


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full-archive", type=Path, required=True)
    parser.add_argument("--old-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.full_archive, args.old_archive, args.output)
