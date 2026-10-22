# Version 1.1.0 validation

All installation targets were disposable fixtures; no live game installation
was modified. The fixtures use CHARSND.2DA/SNDSLOT.IDS extracted read-only from
unmodified Steam BG:EE and BG2:EE 2.7.3.0. Those tables are byte-identical to
the 2.6.6.0 captures used for 1.0.1.

## The fourteen 1.0.1 packs

`build_release.py` rebuilt all fourteen archives from the pinned 1.0.0 sources.
`assemble_release.py` confirmed that each rebuilt archive is byte-identical to
the published 1.0.1 asset, and it rejected a copy with one changed byte.
`verify_installers.py` passed again: 14 installs with 556 checked assignments
in each of six fixtures (BG:EE, BG:EE + SoD, BG2:EE and EET in English; BG:EE
and BG2:EE in German), reinstall, uninstall restoration, and 42 invalid-target
checks. CI repeats the rebuild, the byte comparison and the installer tests.

## The four new packs

| Pack | Assigned slots | Audio check | Fixtures passed | Invalid targets rejected |
| --- | ---: | --- | ---: | ---: |
| Ajantis 2.0.0 | 26 | 26/26 decode exactly to the BG:EE recordings | 8 | 6 |
| Viconia (BG1) 1.0.0 | 27 | 27/27 decode exactly to the BG:EE recordings | 8 | 6 |
| Viconia (BG2) 1.0.0 | 39 | 39/39 decode exactly to the BG2:EE recordings | 8 | 6 |
| Garithos 1.1.0 | 23 | all WAVs byte-identical to IAIWE's files | 8 | 6 |

The eight fixtures are BG:EE, BG:EE + SoD, BG2:EE and EET, each with an English
and a German game language. Each run checked every subtitle/audio pair in the
male and female TLK files, the target game's row order, reinstall, and
byte-exact restoration after uninstall. The rejected targets are the classic
engine, an old 30-row table, a malformed table, a missing table, a duplicate
soundset column, and a duplicate or orphan menu entry. None of them changed a
game resource or TLK file.

The Ajantis and Viconia builders refuse to run unless every listed creature
variant carries the same recorded player slots: AJANTI, AJANTI4 and AJANTI6;
VICONI, VICONI4 and VICONI6 (BG:EE); VICONI16, VICONI6, VICONI8, VICONI9,
VICONI11 and VICONI13 (BG2:EE). The verifiers read the slot tables from the
game independently of the builders. An earlier, unreleased Viconia (BG1) build
also registered two rare selection lines a second time as rare action
responses; 1.0.0 removes that duplication. Upgrading from copies of the earlier
Viconia builds was tested once, including a simulated failed TLK write.

Rebuilding each new pack produced byte-identical archives. Windows Defender
reported no threats in the assembled release.

## Limits

This evidence proves installer behavior and event registration. It does not
prove live character creation, playback, event frequency, or save/reload
behavior; listening remains a playtest step. CI cannot rebuild Ajantis, Viconia
or Garithos, because their builds need an unmodified game or IAIWE's soundset
folder. CI compiles their builders and verifiers; the release manifest and the
table below record their archive checksums.

## Release assets

| Archive | SHA-256 |
| --- | --- |
| ajantis-player-voicepack-v2.0.0.zip | `7d2150ba920205e68258b9fc74a35594c1368d8b09e4e66ca9f1569a1baed77b` |
| viconia-bg1-player-voicepack-v1.0.0.zip | `bd56af0ef69e84986061ee53fad36611291fb2038c2dbfd059542eb6d6a0d5f5` |
| viconia-bg2-player-voicepack-v1.0.0.zip | `dde9cfca2692de0b75e1bd9a6bc8dabba85db79608b87da18f49ae685d31420a` |
| garithos-player-voicepack-v1.1.0.zip | `24abfd30cd8c9e5bedc77b2f8c9ab8b1444cc5c4189f5857d2b70def805525c5` |

The fourteen 1.0.1 archives keep their published checksums; `SHA256SUMS` in the
release lists all eighteen.
