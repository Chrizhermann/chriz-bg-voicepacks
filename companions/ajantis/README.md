# Ajantis — original BG1 companion voice

Version 2.0.0. A standalone player voicepack for BG:EE, BG:EE + Siege of
Dragonspear, BG2:EE and EET using the EE 2.6-style soundset table.
This does not support the original/classic BG1 or BG2 engines.

## What is included

Exactly 26 recorded player-voice slots from the unmodified English BGEE
Ajantis companion (`AJANTI.CRE`, cross-checked against `AJANTI4.CRE` and
`AJANTI6.CRE`). The shipped audio is decoded directly from those original
recordings to mono 16-bit PCM without trimming, resampling, normalization,
voice effects, synthesis or added lines. Spoken subtitles retain the game's
English wording; the internal `[AJANTIS nn]` labels are removed. Original
damage/death grunts deliberately have no subtitle text.

His four repeated-click lines remain rare-selection lines. BGEE places these
at rows 35–38; BG2EE/EET use rows 75–78. They are not added as movement
acknowledgements. The general party-death response uses `AJANT40`, not the
NPC-specific `AJANT41` response.

No filler battle cries, critical-hit lines, greeting reuse, interaction/banter
reuse, cross-era recordings or TTS. Unrecorded slots stay empty. This follows
the original BG1 companion, not EET's additional redistribution of some rare
lines into battle cries and action responses. See `SLOT_MAP.md` for every
assignment and `provenance.json` for its source and audio checksums.

## Install

1. Save and fully quit the game and InfinityLoader. Keep both closed until the
   installer has completely finished; otherwise the game's text file may be
   locked even after audio files have been copied.
2. Extract the archive into the intended game directory (the directory with
   `chitin.key` and `Baldur.exe`). Keep `cd_ajanti` and `setup-cd_ajanti.exe`
   next to one another.
3. Run `setup-cd_ajanti.exe` and install its single Ajantis component. Choose
   the language used by your game; the voice and subtitles themselves are
   English. No other voicepack is installed.
4. Require a completed successful install with no final `FATAL ERROR`,
   especially no `dialog.tlk: Permission denied` message.
5. In the game's voice selection choose **Ajantis (BG1 companion)**. On an
   existing character, reselect this voice through Customize → Sounds so the
   character picks up the replacement sound references.

### Replacing the old Ajantis pack

This intentionally retains the `cd_ajanti` mod identity and `AJANTI` soundset
prefix so WeiDU can uninstall the old component before applying the rebuild.
Keep the existing `cd_ajanti/backup` directory; never delete or replace it with
another game's backups. The archive contains no installation backups.
The new installer copies only its explicit 26-file list, so obsolete WAVs
left in the mod's source folder by archive extraction are not reinstalled.
WeiDU's old-component uninstall removes the old installed audio first.

Use WeiDU's **Re-install** option. Merely copying WAVs, or an install command
that treats an already-installed component as satisfied, is insufficient.
If other mods were installed after Ajantis, do not start a blind reinstall:
WeiDU may need to reinstall those later components. A duplicate/orphan
`AJANTI` table column is rejected rather than silently adding another.

To remove this pack, run the same installer and choose **Uninstall**.

## Credits and compatibility basis

- Original Ajantis performance and game text: the Baldur's Gate game assets.
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
