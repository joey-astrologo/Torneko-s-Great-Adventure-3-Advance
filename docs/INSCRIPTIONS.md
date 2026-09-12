# Blank-scroll inscriptions

The English keyboard now works with blank scrolls. Each of the 49 supported
scroll identities has an English spelling of at most seven characters. The
existing learned-scroll list displays that spelling. Matching ignores English
letter case and still requires the game to have marked the scroll as learned.
Unknown and unlearned spellings follow the original spoiled-scroll behavior.

The full item names remain unchanged. Short inputs such as `MthSeal`, `IreLyre`
and `TrapAct` are field abbreviations, not alternate official item names.
[translations/inscriptions.json](../translations/inscriptions.json) links each
spelling to the existing glossary identity and both original kana sources.
The table below is generated from that catalog.

Both original kana spellings, including mixed hiragana/katakana, still work.
The original dictionary and its source strings remain byte-identical. English
matching runs before the original matcher and resumes its existing eligibility,
result flags and accounting paths. The seven-position editor commits the
original eight-byte item field; no permanent RAM or save-layout expansion is
needed. [MEMORY_MAP.md](MEMORY_MAP.md) records all ownership and fixture ranges.

The [component checkpoint](../build/completion/inscriptions/component-checkpoint.json)
verifies 549 English matcher cases, 255 legacy regressions, 294 English versus
Japanese item-result comparisons, 51 learned-list selection cases, all 49
native list rows and seven unchanged Japanese screenshot pairs. Four real
joypad cases enter Bang, MthSeal, IreLyre and TrapAct through the complete
original item-name caller and verify conversion/terminators/record boundaries.
These fixtures do not establish natural effect consumption or save persistence.

```sh
.venv/bin/python -m tools.build_inscriptions build
.venv/bin/python -m tools.verify_inscriptions english
.venv/bin/python -m tools.verify_inscriptions japanese
.venv/bin/python -m tools.verify_inscriptions baseline
.venv/bin/python -m tools.verify_inscription_input
.venv/bin/python -m tools.summarize_inscriptions
```

English ROM: [torneko3-inscriptions-english.gba](../build/completion/inscriptions/torneko3-inscriptions-english.gba),
SHA256 `577f519029f96c714ba1f1a53c68bdee0007d15e9bd67ca65f88217e455848f1`.
Japanese control SHA256:
`b9494f267d14a56dd82318c87602d3b6e2a00c09fe43a7ba6ae40b29cce4d7f7`.

| Full item name | English input |
|---|---|
| Bang scroll | `Bang` |
| Prayer scroll | `Prayer` |
| Peep scroll | `Peep` |
| Look-back scroll | `LookBck` |
| Blaze scroll | `Blaze` |
| Gale scroll | `Gale` |
| Great room scroll | `GrtRoom` |
| Binding scroll | `Binding` |
| Lyre of Ire scroll | `IreLyre` |
| Mouthseal scroll | `MthSeal` |
| Zing scroll | `Zing` |
| Time bomb scroll | `TimeBmb` |
| Foe sight scroll | `FoeSght` |
| Sheen scroll | `Sheen` |
| Buff scroll | `Buff` |
| Reckless scroll | `Recklss` |
| Sand pillar scroll | `SandPlr` |
| Sanctuary scroll | `Sanctry` |
| Holy castle scroll | `HolyCst` |
| Item sight scroll | `ItemSgt` |
| Big blast scroll | `BigBlst` |
| Chicken scroll | `Chicken` |
| Medium room scroll | `MedRoom` |
| Pot fortify scroll | `PotFort` |
| Safe Passage scroll | `SafePas` |
| Poof scroll | `Poof` |
| Oomphle scroll | `Oomphle` |
| Deep sleep scroll | `DeepSlp` |
| Rooting scroll | `Rooting` |
| Power-up scroll | `PowerUp` |
| Bread scroll | `Bread` |
| Pulling scroll | `Pulling` |
| Freeze scroll | `Freeze` |
| No-pickup scroll | `NoPick` |
| Dud scroll | `Dud` |
| Multiheal scroll | `MultiHl` |
| Transform scroll | `Transfm` |
| Monster haste scroll | `MonHast` |
| Monster bind scroll | `MonBind` |
| Drought scroll | `Drought` |
| Fuddle scroll | `Fuddle` |
| Plating scroll | `Plating` |
| Monster scroll | `Monster` |
| Evac scroll | `Evac` |
| Kasap scroll | `Kasap` |
| Glow scroll | `Glow` |
| Trap scroll | `Trap` |
| Trap erase scroll | `TrapClr` |
| Trap trigger scroll | `TrapAct` |
