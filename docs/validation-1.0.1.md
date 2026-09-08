# Version 1.0.1 installer validation

The local acceptance run used the actual bundled WeiDU executables, with
CHARSND.2DA/SNDSLOT.IDS read-only captures from BG:EE and BG2:EE 2.6.6.0's
DEFAULT.BIF. All installation targets were disposable fixtures.

| Fixture | Game language | Pack installs | Verified assignments |
| --- | --- | ---: | ---: |
| BG:EE | English | 14 | 556 |
| BG:EE + SoD marker | English | 14 | 556 |
| BG2:EE | English | 14 | 556 |
| EET markers | English | 14 | 556 |
| BG:EE | German | 14 | 556 |
| BG2:EE | German | 14 | 556 |

All 84 pack installations passed. Every fixture also passed a reinstall check
and reverse uninstall of the full stack. Existing table columns, Lua menu
registrations, original TLK entries, and game resource files were preserved;
installed WAVs were removed on uninstall. No live game installation was modified.

All fourteen packs rejected each of three invalid targets without adding
voicepack audio or strings: classic BG1, an old 30-row soundset table, and a
missing soundset table (42 negative checks).

The new ZIPs have exactly the same files as their pinned 1.0.0 sources. Only
each TP2 and the prerequisite messages in each TRA changed. All 556 WAVs,
subtitle/audio pairs, soundset helper files, and WeiDU executable bytes match
their original values. Two builds produced identical bytes for all 16 artifacts
(fourteen ZIPs, checksum file, manifest). Windows Defender reported no threats.

CI repeats the installer tests with minimal 99-row fixtures. The source recipe
documents the captured table hashes and how to rerun with those captures.

This evidence proves installer behavior and event registration. It does not
prove live character creation, playback, event frequency, or save/reload behavior.
Those listening checks remain for the BG:EE playtest, including the documented
engine limits on rare action slots and common selection 7.
