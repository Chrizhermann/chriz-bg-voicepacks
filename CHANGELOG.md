# Changelog

## 1.1.0

- Added Ajantis 2.0.0 (26 assigned slots): his original BG1 companion voice
  only, decoded bit-exact from the unmodified BG:EE recordings.
- Added Viconia (BG1) 1.0.0 (27 slots) and Viconia (BG2) 1.0.0 (39 slots):
  her original BG1 and BG2/Throne of Bhaal companion voices, each line in
  its own event slot. Unrecorded events stay empty.
- Added Garithos 1.1.0 (23 slots): IAIWE's Lord Garithos soundset, with
  recordings from Warcraft III: The Frozen Throne, as an EE installer. All
  WAVs are byte-identical to IAIWE's files; IAIWE's two portraits are
  included as extras and are not installed.
- The fourteen 1.0.1 packs are unchanged. The release carries the same
  1.0.1 files and checksums.
- The release manifest records each pack's own version.
- Added builders and verifiers for the new packs, and a release assembly
  script that requires the rebuilt 1.0.1 archives to match the published
  bytes.

## 1.0.1

- All fourteen installers support BG:EE, BG:EE with Siege of Dragonspear,
  BG2:EE, and EET using the EE 2.6 soundset layout.
- Removed the BG2:EE/EET-only restriction from Amelyssan and Gromnir.
- Added a consistent game/table check and selected-game-language sound folder.
- Preserved all 556 audio files, subtitles, and curated assignments.
- Added a repeatable build recipe and installer verification for both slot orders.
- Documented BG:EE 2.6's inactive rare action slots and other optional-slot limits.

## 1.0.0

Initial public archive of fourteen curated player voicepacks, documented for
BG2:EE and EET.
