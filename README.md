# ChrizFader's Baldur's Gate voicepacks

Curated player soundsets, mostly from Baldur's Gate companions, for **Baldur's Gate: Enhanced Edition**, **Siege of Dragonspear**, **Baldur's Gate II: Enhanced Edition**, and **Enhanced Edition Trilogy**. Use the EE 2.6 soundset format or a compatible later version. Each release ZIP works in all these games and contains one WeiDU setup executable beside its matching `cd_*` mod folder.

Download the current [1.1.0 release](https://github.com/Chrizhermann/chriz-bg-voicepacks/releases/tag/v1.1.0). The 1998 original BG1 and pre-2.6 Enhanced Editions are not supported by these installers.

## Voicepacks in release 1.1.0

Release 1.1.0 adds Ajantis, Viconia (BG1), Viconia (BG2), and Garithos. The fourteen 1.0.1 packs are unchanged: the release carries the same 1.0.1 files with the same checksums, so existing installations need no update. Each pack keeps its own version number.

| Voicepack | Version | Assigned slots | Notes |
| --- | --- | ---: | --- |
| Neera | 1.0.1 | 53 | BG:EE, BG2:EE, and Siege of Dragonspear recordings |
| Safana (BG1) | 1.0.1 | 58 | BG1-first set with BG2 bonus-voice vocalizations and limited SoD filler |
| Safana (SoD) | 1.0.1 | 48 | Consistent Siege of Dragonspear voice |
| Jaheira (BG1) | 1.0.1 | 53 | Original BG1 voice with same-actress BG2 filler |
| Jaheira (BG2) | 1.0.1 | 40 | BG2/Throne of Bhaal voice with the BG1 death reaction |
| Yeslick | 1.0.1 | 38 | All surviving original BG1 companion lines |
| Edwin (BG1) | 1.0.1 | 55 | BG1 voice with same-actor BG2 filler |
| Edwin (BG2) | 1.0.1 | 45 | BG2/Throne of Bhaal voice with BG1 death reactions |
| Aerie | 1.0.1 | 38 | Genuine BG2/Throne of Bhaal companion recordings only |
| Imoen (BG1) | 1.0.1 | 26 | Era-pure original BG1 voice |
| Imoen (BG2) | 1.0.1 | 39 | Mature BG2/Throne of Bhaal voice |
| Sarevok | 1.0.1 | 36 | Redeemed Chaotic-Good Throne of Bhaal companion variant |
| Amelyssan | 1.0.1 | 17 | Deliberately sparse; 44 slots intentionally vacant; no TTS |
| Gromnir Il-Khan | 1.0.1 | 10 | Deliberately sparse; 51 slots intentionally vacant; no TTS |
| Ajantis | 2.0.0 | 26 | Original BG1 companion voice only; unrecorded slots stay empty |
| Viconia (BG1) | 1.0.0 | 27 | Original BG1 companion voice only |
| Viconia (BG2) | 1.0.0 | 39 | Original BG2/Throne of Bhaal companion voice only |
| Garithos | 1.1.0 | 23 | IAIWE's Lord Garithos soundset, with IAIWE's two portraits as extras |

Ajantis, Viconia, and Garithos replace earlier builds that were not part of a public release. Their installers keep the same mod names, so WeiDU can replace such a build with **Reinstall**; each pack's own readme explains this.

## Install

1. Close the game and EEex.
2. Extract one ZIP into the BG:EE, BG:EE + SoD, BG2:EE, or EET game root. The setup executable must sit beside its `cd_*` folder.
3. Run the included WeiDU setup executable. If prompted for the game's language, choose the language you play in. The voice and subtitles are English; the selectable sounds are installed into the chosen language's sound folder.
4. Start the game and select the voice in the character sound menu.

The release includes a `SHA256SUMS` file and a machine-readable manifest. The public catalogue, full descriptions, and separately credited upstream recommendations are at [bg.chrizfader.org/voicepacks](https://bg.chrizfader.org/voicepacks).

## Compatibility and updates

Every installer checks the game and the soundset table before copying audio and uses the game's selected language folder. Version 1.0.1 brought this consistent check to the original fourteen packs: version 1.0.0 had blocked BG:EE in the Amelyssan and Gromnir installers and documented only BG2:EE/EET support. The new packs use the same check.

The included EE Soundset Tool helper automatically selects the game's row order. BG:EE uses rows 35-38 for rare selection responses and 79-82 for action acknowledgements 4-7. BG2:EE/EET uses rows 35-38 for those actions and 75-78 for rare selection responses. You do not need separate downloads or renamed audio. Each line keeps its original meaning: a BG1 voice's rare selection lines stay rare selection lines in BG2:EE, and a BG2 voice's action acknowledgements stay action acknowledgements in BG:EE.

Assigned slots count registrations, not guaranteed audible events. The EE Soundset Tool authors documented that the two rare action slots do not trigger in BG:EE 2.6, and common selection 7 does not trigger in the 2.6 games. The lines remain registered; no curated clips are moved to different events. The two problematic extra damage slots remain unused. See the [author's compatibility findings](https://www.gibberlings3.net/forums/topic/34560-adding-soundsets-to-the-ees-using-the-ee-soundset-tool/#comment-310690).

To update an existing installation, close the game, extract the new ZIP over that pack's source folder, and choose **Reinstall** in WeiDU. Reinstalling a pack below other mods can cause WeiDU to reinstall those later mods too.

Validation uses the actual included WeiDU executables in disposable game fixtures, including tables extracted from unmodified BG:EE/BG2:EE 2.7.3.0 resources (byte-identical to 2.6.6.0). It checks every registered subtitle/audio pair, both row orders, language directories, reinstall, and uninstall restoration. For Ajantis and Viconia it also proves that every WAV decodes to exactly the original game recording; Garithos's WAVs are byte-identical to IAIWE's files. This is installer verification; live character creation and gameplay listening remain a user playtest step.

## Rebuild and verify all packs

Python 3.11+ and the standard library are sufficient for the builders. Audio and installer executables stay in release assets, outside the source repository. The verifiers run the bundled Windows WeiDU executables and therefore need Windows. Every output directory must be new or empty.

**The fourteen 1.0.1 packs.** The shared [compatibility recipe](docs/compatibility-recipe.md) applies to all fourteen. The build fetches and verifies the immutable 1.0.0 source ZIPs and writes the archives, manifest, and checksums to `dist/`:

```powershell
python scripts/build_release.py
python scripts/verify_installers.py
```

**Ajantis and Viconia** are rebuilt from an unmodified English game used as a read-only source: BG:EE for Ajantis and Viconia (BG1), BG2:EE for Viconia (BG2). They need `ffmpeg` and `ffprobe`, plus `cd_add_soundset.tph` and the setup executable from any 1.0.1 pack (`--helper`, `--weidu`). The verifiers also need CHARSND.2DA/SNDSLOT.IDS captures in `bgee/` and `bg2ee/` folders (`--fixtures`):

```powershell
python scripts/build_ajantis.py --source <BG:EE> --out <new dir> --helper <tph> --weidu <exe>
python scripts/verify_ajantis.py --package-dir <new dir>/package --source <BG:EE> --fixtures <captures> --work-dir <dir>
python scripts/build_viconia.py --variant bg1 --source <BG:EE> --out <new dir> --helper <tph> --weidu <exe>
python scripts/build_viconia.py --variant bg2 --source <BG2:EE> --out <new dir> --helper <tph> --weidu <exe>
python scripts/verify_viconia.py --variant bg1 --package-dir <new dir>/package --source <BG:EE> --fixtures <captures> --work-dir <dir>
```

**Garithos** is packaged from IAIWE's `GARITHOS` folder (from `Lord Garithos v2.zip`, SHA-256 `677f93c93484d323cfc47b77bb82306eb83186be9baf096a9a8bcd9a36d778d3`). [custom/garithos/voicepack.json](custom/garithos/voicepack.json) pins every input file and subtitle:

```powershell
python scripts/build_garithos.py --source <GARITHOS> --helper <tph> --weidu <exe> --output <new dir>
python scripts/verify_garithos.py --archive <new dir>/garithos-player-voicepack-v1.1.0.zip --source <GARITHOS> --fixtures <captures>
```

**The release.** `assemble_release.py` requires the fourteen rebuilt archives to match the published 1.0.1 bytes, checks the other archives' helper, setup executable, and provenance, and writes the combined manifest and checksums:

```powershell
python scripts/assemble_release.py --packs-dir dist --built <ajantis zip> --built <viconia-bg1 zip> --built <viconia-bg2 zip> --built <garithos zip>
```

## Audio and rights

These are curated player soundsets assembled from original Baldur's Gate game recordings, except Garithos: that pack converts IAIWE's Lord Garithos soundset, whose recordings come from Warcraft III: The Frozen Throne (Blizzard Entertainment). The underlying audio, characters, and voice performances belong to their respective rights holders. Christopher Hermann / ChrizFader did not perform or acquire ownership of the voice acting. This repository is not an open-content license or a claim of ownership over those recordings.

The Garithos soundset and its two portraits are IAIWE's work; this project only converted them into an EE installer. Other authors' voicepacks are linked and credited on the website rather than mirrored in this repository.

Soundset registration uses the [EE Soundset Tool](https://github.com/Gibberlings3/EE_soundset_tool) by CamDawg and Graion Dilach. The original helper and its credit header are preserved byte for byte.
