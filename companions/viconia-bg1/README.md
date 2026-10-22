# Viconia (BG1) — original BG1 companion voice

Version 1.0.0. A standalone player voicepack for BG:EE, BG:EE + Siege of
Dragonspear, BG2:EE and EET using the EE 2.6-style soundset table.
This does not support the original/classic BG1 or BG2 engines.

## What is included

Exactly 27 recorded player-voice slots from the unmodified English BGEE
Viconia companion (`VICONI.CRE`, cross-checked against `VICONI4.CRE` and
`VICONI6.CRE`). The shipped audio is decoded directly from those original
recordings to mono 16-bit PCM without trimming, resampling, normalization,
voice effects, synthesis or added lines. Spoken subtitles retain the game's
English wording; the internal `[VICONIA nn]` labels are removed. Original
damage/death grunts deliberately have no subtitle text.

Her four repeated-click lines remain rare-selection lines. BGEE places these
at rows 35–38; BG2EE/EET use rows 75–78. They are not added as movement
acknowledgements, and they are not registered a second time as rare action
responses. The general party-death response uses `VICON40`, not the
Kivan-specific `VICON41` response. She has no city line, so the city slot
stays empty; her day and night lines are kept.

No filler battle cries, critical-hit lines, greeting reuse, interaction/banter
reuse, cross-era recordings or TTS. Unrecorded slots stay empty. See
`SLOT_MAP.md` for every assignment and `provenance.json` for its source and
audio checksums.

## Install

1. Save and fully quit the game and InfinityLoader. Keep both closed until the
   installer has completely finished; otherwise the game's text file may be
   locked even after audio files have been copied.
2. Extract the archive into the intended game directory (the directory with
   `chitin.key` and `Baldur.exe`). Keep `cd_vicbg1` and `setup-cd_vicbg1.exe`
   next to one another.
3. Run `setup-cd_vicbg1.exe` and install its single Viconia (BG1) component.
   Choose the language used by your game; the voice and subtitles themselves
   are English. No other voicepack is installed.
4. Require a completed successful install with no final `FATAL ERROR`,
   especially no `dialog.tlk: Permission denied` message.
5. In the game's voice selection choose **Viconia (BG1)**. On an existing
   character, reselect this voice through Customize → Sounds so the character
   picks up the replacement sound references.

### Replacing an earlier Viconia (BG1) pack

This retains the `cd_vicbg1` mod identity and `VICOB1` soundset prefix so
WeiDU can uninstall an earlier build before applying this one. That earlier
build also registered two rare-selection lines a second time as rare action
responses (`VICOB1x`, `VICOB1y`); this version no longer does. Keep the
existing `cd_vicbg1/backup` directory; never delete or replace it with another
game's backups. The archive contains no installation backups. The new
installer copies only its explicit 27-file list, so obsolete WAVs left in the
mod's source folder by archive extraction are not reinstalled. WeiDU's
old-component uninstall removes the old installed audio first.

Use WeiDU's **Re-install** option. Merely copying WAVs, or an install command
that treats an already-installed component as satisfied, is insufficient.
If other mods were installed after this pack, do not start a blind reinstall:
WeiDU may need to reinstall those later components. A duplicate/orphan
`VICOB1` table column is rejected rather than silently adding another.

To remove this pack, run the same installer and choose **Uninstall**.

## Credits and compatibility basis

- Original Viconia performance and game text: the Baldur's Gate game assets.
  This is a fan conversion; no ownership of the original audio is claimed.
- Companion-faithful assembly and source/slot audit: ChrizFader.
- Registration helper: CamDawg / Graion Dilach's
  [EE Soundset Tool](https://github.com/Gibberlings3/EE_soundset_tool).
- Installer: [WeiDU](https://github.com/WeiDUorg/weidu).
- Format reference: [IESDP CHARSND](https://gibberlings3.github.io/iesdp/files/2da/2da_bgee/charsnd.htm).

The installer uses the target game's selected language folder and writes both
sound/text references and the voice-menu name. It requires a compatible
99-row `charsnd.2da` table and rejects unsupported layouts before copying
audio. Separate installer tests exercise BGEE, SoD, BG2EE and EET identities;
these are not a substitute for in-game playback testing.
