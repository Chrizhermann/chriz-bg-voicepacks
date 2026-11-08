Every voicepack installer now writes its own registration through existing
soundset state. An old 30-row `CHARSND.2DA` is extended to the 99-row EE layout;
an existing column or `M_cdsnd.lua` menu entry for the pack is rewritten rather
than causing an install refusal or a duplicate registration.

- The fourteen generated packs are **1.0.2**.
- **Ajantis 2.0.1** retains 26 original BG1 companion slots.
- **Viconia (BG1) 1.0.1** retains 27 original BG1 companion slots and
  **Viconia (BG2) 1.0.1** retains 39 original BG2/Throne of Bhaal companion
  slots.
- **Garithos 1.1.1** retains IAIWE's 23 supplied Lord Garithos soundset clips
  and the two non-installed portrait extras.

Audio files, assigned event slots, and English subtitles are unchanged. Every
pack still supports BG:EE, BG:EE with Siege of Dragonspear, BG2:EE, and EET.
Download the ZIP for the voice you want, extract it into the game directory,
and run its setup executable. To replace an earlier build of the same pack,
close the game and choose Reinstall in WeiDU; WeiDU may also reinstall mods
installed after that pack.

Installer verification uses disposable fixtures for BG:EE, SoD, BG2:EE, and
EET, including ordinary 99-row tables, old 30-row tables, changed layouts, and
existing registrations. It does not replace live character-creation or
gameplay-listening playtests.

[Voicepack catalogue](https://bg.chrizfader.org/voicepacks) ·
[Compatibility recipe](https://github.com/Chrizhermann/chriz-bg-voicepacks/blob/v1.2.0/docs/compatibility-recipe.md)
