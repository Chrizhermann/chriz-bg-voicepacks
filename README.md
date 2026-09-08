# ChrizFader's Baldur's Gate voicepacks

Curated companion player soundsets for **Baldur's Gate: Enhanced Edition**, **Siege of Dragonspear**, **Baldur's Gate II: Enhanced Edition**, and **Enhanced Edition Trilogy**. Use the EE 2.6 soundset format or a compatible later version. Each release ZIP works in all these games and contains one WeiDU setup executable beside its matching `cd_*` mod folder.

Download the current [1.0.1 release](https://github.com/Chrizhermann/chriz-bg-voicepacks/releases/tag/v1.0.1). The 1998 original BG1 and pre-2.6 Enhanced Editions are not supported by these installers.

## Voicepacks in release 1.0.1

| Voicepack | Assigned slots | Notes |
| --- | ---: | --- |
| Neera | 53 | BG:EE, BG2:EE, and Siege of Dragonspear recordings |
| Safana (BG1) | 58 | BG1-first set with BG2 bonus-voice vocalizations and limited SoD filler |
| Safana (SoD) | 48 | Consistent Siege of Dragonspear voice |
| Jaheira (BG1) | 53 | Original BG1 voice with same-actress BG2 filler |
| Jaheira (BG2) | 40 | BG2/Throne of Bhaal voice with the BG1 death reaction |
| Yeslick | 38 | All surviving original BG1 companion lines |
| Edwin (BG1) | 55 | BG1 voice with same-actor BG2 filler |
| Edwin (BG2) | 45 | BG2/Throne of Bhaal voice with BG1 death reactions |
| Aerie | 38 | Genuine BG2/Throne of Bhaal companion recordings only |
| Imoen (BG1) | 26 | Era-pure original BG1 voice |
| Imoen (BG2) | 39 | Mature BG2/Throne of Bhaal voice |
| Sarevok | 36 | Redeemed Chaotic-Good Throne of Bhaal companion variant |
| Amelyssan | 17 | Deliberately sparse; 44 slots intentionally vacant; no TTS |
| Gromnir Il-Khan | 10 | Deliberately sparse; 51 slots intentionally vacant; no TTS |

## Install

1. Close the game and EEex.
2. Extract one ZIP into the BG:EE, BG:EE + SoD, BG2:EE, or EET game root. The setup executable must sit beside its `cd_*` folder.
3. Run the included WeiDU setup executable. If prompted for the game's language, choose the language you play in. The voice and subtitles are English; the selectable sounds are installed into the chosen language's sound folder.
4. Start the game and select the voice in the character sound menu.

The release includes a `SHA256SUMS` file and a machine-readable manifest. The public catalogue, full descriptions, and separately credited upstream recommendations are at [bg.chrizfader.org/voicepacks](https://bg.chrizfader.org/voicepacks).

## Compatibility and updates

Version 1.0.0 explicitly blocked BG:EE in the Amelyssan and Gromnir installers. The other twelve already included a BG:EE mapping, but the release had only documented BG2:EE/EET support. Version 1.0.1 applies a consistent game/layout check to all fourteen and uses the game's selected language folder. Every audio file, subtitle, and curated slot assignment is preserved.

The included EE Soundset Tool helper automatically selects the game's row order. BG:EE uses rows 35-38 for rare selection responses and 79-82 for action acknowledgements 4-7. BG2:EE/EET uses rows 35-38 for those actions and 75-78 for rare selection responses. You do not need separate downloads or renamed audio.

Assigned slots count registrations, not guaranteed audible events. The EE Soundset Tool authors documented that the two rare action slots do not trigger in BG:EE 2.6, and common selection 7 does not trigger in the 2.6 games. The lines remain registered; no curated clips are moved to different events. The two problematic extra damage slots remain unused. See the [author's compatibility findings](https://www.gibberlings3.net/forums/topic/34560-adding-soundsets-to-the-ees-using-the-ee-soundset-tool/#comment-310690).

Already installed on BG2:EE/EET in English? This update adds compatibility and does not change the voice content. To update an existing installation, close the game, extract the new ZIP over that pack's source folder, and choose **Reinstall** in WeiDU. Reinstalling a pack below other mods can cause WeiDU to reinstall those later mods too. A BG:EE installation that previously skipped Amelyssan/Gromnir can simply install the new version.

Validation uses the actual included WeiDU executables in disposable game fixtures, including tables extracted from unmodified BG:EE/BG2:EE 2.6.6.0 resources. It checks every registered subtitle/audio pair, both row orders, language directories, reinstall, and uninstall restoration. This is installer verification; live character creation and gameplay listening remain a user playtest step.

## Rebuild and verify all packs

The shared [compatibility recipe](docs/compatibility-recipe.md) applies to all fourteen packs. Python 3.11+ and the standard library are sufficient; the build fetches and verifies the immutable 1.0.0 source ZIPs. Audio and installer executables stay in release assets, outside the source repository.

```powershell
python scripts/build_release.py
python scripts/verify_installers.py
```

The verifier runs the bundled Windows WeiDU executables and therefore needs Windows. The builder is portable. The output directory must be empty; use `--out-dir` for a separate build. Release archives, the manifest, and checksums are written to `dist/`.

## Audio and rights

These are curated player soundsets assembled from original Baldur's Gate game recordings. The underlying audio, characters, and voice performances belong to their respective rights holders. Christopher Hermann / ChrizFader did not perform or acquire ownership of the voice acting. This repository is not an open-content license or a claim of ownership over those recordings.

External voicepacks by other pack authors are linked and credited on the website rather than mirrored in this repository.

Soundset registration uses the [EE Soundset Tool](https://github.com/Gibberlings3/EE_soundset_tool) by CamDawg and Graion Dilach. The original helper and its credit header are preserved byte for byte.
