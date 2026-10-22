# Viconia (BG2) — original BG2/ToB companion voice

Version 1.0.0. A standalone player voicepack for BG:EE, BG:EE + Siege of
Dragonspear, BG2:EE and EET using the EE 2.6-style soundset table.
This does not support the original/classic BG1 or BG2 engines.

## What is included

Exactly 39 recorded player-voice slots from the unmodified English BG2EE
Viconia companion (`VICONI16.CRE`, cross-checked against `VICONI6.CRE`,
`VICONI8.CRE`, `VICONI9.CRE`, `VICONI11.CRE` and `VICONI13.CRE`, which carry
the same sound table). The shipped audio is decoded directly from those
original recordings to mono 16-bit PCM without trimming, resampling,
normalization, voice effects, synthesis or added lines. Spoken subtitles
retain the game's English wording. Original damage/death grunts deliberately
have no subtitle text.

Every line keeps its BG2 slot meaning. Her action acknowledgements 4–7 use
BG2EE/EET rows 35–38 and BGEE rows 79–82; her two rare action responses,
critical hit, critical miss, weapon-immune, full-inventory and spell-disrupted
lines keep their own rows. The EE Soundset Tool authors documented that the
two rare action slots do not trigger in BG:EE 2.6; the lines remain
registered and are not moved to other events.

Her BG2 companion has no rare-selection, party-death, pickpocket, hide-in-
shadows or trap lines; those slots stay empty. No filler, greeting reuse,
interaction/banter reuse, BG1-era recordings or TTS. See `SLOT_MAP.md` for
every assignment and `provenance.json` for its source and audio checksums.

## Install

1. Save and fully quit the game and InfinityLoader. Keep both closed until the
   installer has completely finished; otherwise the game's text file may be
   locked even after audio files have been copied.
2. Extract the archive into the intended game directory (the directory with
   `chitin.key` and `Baldur.exe`). Keep `cd_vicbg2` and `setup-cd_vicbg2.exe`
   next to one another.
3. Run `setup-cd_vicbg2.exe` and install its single Viconia (BG2) component.
   Choose the language used by your game; the voice and subtitles themselves
   are English. No other voicepack is installed.
4. Require a completed successful install with no final `FATAL ERROR`,
   especially no `dialog.tlk: Permission denied` message.
5. In the game's voice selection choose **Viconia (BG2)**. On an existing
   character, reselect this voice through Customize → Sounds so the character
   picks up the replacement sound references.

### Replacing an earlier Viconia (BG2) pack

This retains the `cd_vicbg2` mod identity and `VICOB2` soundset prefix so
WeiDU can uninstall an earlier build before applying this one. Keep the
existing `cd_vicbg2/backup` directory; never delete or replace it with another
game's backups. The archive contains no installation backups. The new
installer copies only its explicit 39-file list, so stray WAVs left in the
mod's source folder by archive extraction are not installed.

Use WeiDU's **Re-install** option. Merely copying WAVs, or an install command
that treats an already-installed component as satisfied, is insufficient.
If other mods were installed after this pack, do not start a blind reinstall:
WeiDU may need to reinstall those later components. A duplicate/orphan
`VICOB2` table column is rejected rather than silently adding another.

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
