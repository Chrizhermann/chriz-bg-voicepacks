# One installer for BG:EE, SoD, BG2:EE, and EET

The recipe is implemented once in `scripts/build_release.py` and applied to all
fourteen hash-pinned 1.0.0 release ZIPs. It does not extract fresh game recordings,
recut audio, or change the source approach used to curate a pack.

## What changes

1. Add `VERSION ~1.0.1~` to each TP2.
2. Accept `GAME_IS ~bgee bg2ee eet~`. WeiDU treats BG:EE with SoD as `bgee`;
   `sod` is not a `GAME_IS` keyword. Remove the old BG2/EET-only guard from
   Amelyssan and Gromnir.
3. Before copying audio, require the EE 2.6 `charsnd.2da` layout: 99 data rows,
   labeled 1 through 99 in order. Use `COUNT_2DA_COLS` when reading the table
   so its column header is not mistaken for a data row. Reject missing, old,
   or incompatible layouts with a useful message.
4. Copy the ordinary sound files to `lang/%EE_LANGUAGE%/sounds`, using the
   game language selected in WeiDU. Extended files still go to `override`.
5. Keep `cd_add_soundset.tph` unchanged. It already switches the row mapping
   between BG:EE and BG2:EE/EET. Keep all WAVs, slot assignments, menu names,
   subtitle/audio pairs, and bundled WeiDU executable bytes unchanged.
6. Update only the prerequisite messages in the TRA files, then build new
   versioned ZIPs with fixed metadata and new SHA-256 checksums.

The engine row mapping is independent of the characters' story origins: Aerie,
Sarevok, Amelyssan, and Gromnir can be player voices in BG:EE, just as a BG1-era
voice can be used in BG2:EE.

## Rows that differ

| Event | BG:EE / SoD | BG2:EE / EET |
| --- | --- | --- |
| Action acknowledgements 4-7 | 79-82 | 35-38 |
| Rare selection responses 1-4 | 35-38 | 75-78 |
| Rare action acknowledgements 1-2 | 63-64, registered but do not trigger in 2.6 | 63-64 |

`SNDSLOT.IDS` labels alone do not reveal this engine difference: the BG:EE and
BG2:EE 2.6.6.0 files are byte-identical. Use the engine-specific behavior described
by the tool authors and the helper's two branches. Common selection 7 is also
documented as inactive in 2.6. Damage 2/3 are deliberately left unused. Do not
promise that every assigned slot will fire in every game.

Primary sources:

- [CamDawg's EE Soundset Tool guide and compatibility investigation](https://www.gibberlings3.net/forums/topic/34560-adding-soundsets-to-the-ees-using-the-ee-soundset-tool/)
- [EE Soundset Tool registration helper](https://github.com/Gibberlings3/EE_soundset_tool/blob/master/cd_soundsets/tph/cd_add_soundset.tph)
- [WeiDU 249 GAME_IS implementation](https://github.com/WeiDUorg/weidu/blob/v249.00/src/tppe.ml)
- [WeiDU 249 selected EE language variable](https://github.com/WeiDUorg/weidu/blob/v249.00/src/var.ml)

## Repeatable build

```powershell
python scripts/build_release.py --out-dir dist
python scripts/verify_installers.py --release-dir dist
```

The builder downloads only the listed release ZIPs when the source cache is
missing, validates each archive's pinned hash and path allowlist, applies the
recipe, and round-trip checks the generated ZIP. It refuses nonempty output
directories. `--source-dir` can point to an existing set of the same 1.0.0 ZIPs;
the exact hashes are still required. When making another release, update the
shared `VERSION` constant and the documentation together.

The verifier runs the real installers across BG:EE, BG:EE with the SoD marker,
BG2:EE, and EET fixtures, plus BG:EE/BG2:EE with German game-language folders.
It validates the 556 assignments against an independent event-to-row map,
checks that previously installed voices remain intact, exercises reinstall,
and uninstalls every pack in reverse order. It also confirms all packs reject
classic BG1, a pre-2.6 table, and a missing table before adding audio or strings.
WeiDU can retain unused appended TLK strings after uninstall; the verifier
requires original TLK entries and all original override/sound files to survive.

For the 1.0.1 acceptance run, the positive fixtures used the actual CHARSND.2DA
and SNDSLOT.IDS extracted read-only from the games' DEFAULT.BIF files:

| Resource | SHA-256 |
| --- | --- |
| BG:EE 2.6.6.0 CHARSND.2DA | `c96dd7b77550a19456e4728fe0873997c067ee9ff6a9abb49d156601e02db268` |
| BG2:EE 2.6.6.0 CHARSND.2DA | `ae3e599fed3ec60b23aaf4aab7e0caeacf90411365d8e761e7cdda3946771955` |
| Both SNDSLOT.IDS files | `22eea9b69626ece0d6dd2834dd0696b8536453081db8e7f1553f258e1517efab` |

Pass their containing directory with `--fixture-dir`: it must contain `bgee/`
and `bg2ee/`, each with `CHARSND.2DA` and `SNDSLOT.IDS`. Without that argument,
the verifier generates minimal 99-row fixtures. Real game folders are never
installation targets for this verifier. Every run keeps its diagnostics under
the ignored `_work/` directory.

Live BG:EE character creation, ordinary selection/action playback, combat, and
save/reload listening still need a playtest. Do not equate installer assertions
with proof that a particular optional engine event fires.
