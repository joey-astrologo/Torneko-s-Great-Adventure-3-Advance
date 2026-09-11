# Gameplay help, ally orders and status summaries

Completed 2026-09-10. Open
[torneko3-gameplay-help-english.gba](../build/gameplay-help/torneko3-gameplay-help-english.gba)
in mGBA. This combined build adds **191 translated entries**, preserving all
earlier item/enemy text, interfaces, core gameplay and seven-character Log names.

| New family | Entries | Native coverage |
|---|---:|---|
| How-to-play pages | 10 | Original help reader, both protagonist substitutions, actual world-menu navigation |
| Ally orders | 7 | Original seven-row order menu, existing 30-byte copy limit |
| Status summaries | 68 | All 64 table rows plus four conditional/fallback literals; bounded formatting and original row renderer |
| Further combat/item effects and order feedback | 106 | Original message engine, normal and maximum-width substitutions |

Edit [gameplay-help.json](../translations/gameplay-help.json), keeping source
metadata intact. Only `english`, optional `display`, and `notes` are editable.
The [review sheet](../translations/gameplay-help-terminology-review.tsv) covers
every entry. All English is independently written from the original Japanese;
the partial patch supplies no text or font assets.

Fight Wisely and Focus on Healing use modern series names. Their Japanese
identities are documented by the secondary Japanese DQ dictionary, with English
spellings corroborated by the [official DQ VII manual](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/nintendo_3ds_2/dragonquest7/ElectronicManual_Nintendo3DS_DragonQuest7_EN.pdf).
The other five commands are project translations. No Abilities refers to
`とくぎ`; it is not the no-magic tactic. Existing spell/species compounds retain
Bazoom, Snooze, Heal, Fullheal, Fizzle, Kaclang, Lump mage staff and Lump wizard
staff. Putrid bread and Wearproof wording match the item catalog. References,
evidence quality and eight new terminology records are in the
[982-term glossary](../translations/glossary.json).

## Layout and ownership

All discoveries are indexed in [MEMORY_MAP.md](MEMORY_MAP.md). New insertions
use the shared allocator after rebuilding every previous component. Original
text is protected; only checked pointer words change in the source ROM. There
are no new fonts, permanent RAM reservations or save-format changes.

- Help keeps its **512-byte buffer and 208x136px window**, with at most ten
  measured lines. English layout replaces Japanese indentation. Text-entry
  help describes the existing Latin case toggle; the legacy kana-voicing
  START operation is explicitly identified as kana-only.
- Status rows keep their **64-byte records**, including a terminator, and fit
  the **200 pixels available after x8**. The long shop-bill prefix has a recorded
  display override; held-item and used-item amounts remain separately labelled.
- Orders retain their seven IDs and original **128px window**, drawing at x4.
  Each name stays within 120px and the existing 30-byte actor substitution slot.
- Messages retain **three lines at 208px**. Wrapping reserves 144px for item
  names, 120px for actor/order names and signed 32-bit numeric widths.

The original status table repeats “double speed, two attacks” in two adjacent
rows. This source quirk is preserved and recorded; the help page separately
explains the one-attack and two-attack rules. Four table rows are skipped by the
normal selector, including a Reserved entry. Forced-row tests cover their data
without claiming that they appear naturally. These are not gameplay fixes.

| Combined English build | Value |
|---|---:|
| ROM size | 32 MiB |
| Appended bytes including alignment | 70,192 |
| Added since core gameplay | 7,108 |
| Appended capacity remaining | 16,707,024 |
| Allocations / checked original patch ranges | 2,036 / 2,325 |

The appended interval is `[01000000,01011230)`. Exact assets and original
patches are in [english-build.json](../build/gameplay-help/english-build.json).
English SHA-256:
`42c41d0c8592aebe135b9076dfe67089b1c2f1b154fae105fd542b4a69b987e5`.
Japanese-control SHA-256:
`6935c9d1915d95173673ea7995e0c62b29e89f5307410945e55a883a7b128db9`.
The control keeps earlier components English and relocates this component's
unchanged Japanese, isolating its new pointer changes.

## Verification

[acceptance.json](../build/gameplay-help/acceptance.json) pins the output ROMs,
catalog, terminology review, preservation checks and results:

- **115 unit tests**, including fixed-buffer terminators, immutable source and
  pointer ownership, semantic substitutions, width/height limits and retention
  of every earlier allocation and patch.
- **381 English screenshots**: 212 message cases, 136 status cases, 20 help
  cases, one seven-order screen and 12 ordinary navigation steps.
- **197 Japanese/baseline pixel-identical pairs**, including those navigation
  steps. The previous core-gameplay ROM is the baseline.
- **400 guarded enemy copies**, both protagonist copies, 14 secondary action
  menus, both natural ground-search protagonists, 14 item inventory/info
  screens and four protagonist detail screens on the new combined ROM.
- `Torneko` creation, save, cold-load and world entry; save remains **64 KiB**.
- **9,318 Japanese master entries / 413,712 source bytes**, reconstructing the
  original exactly. Earlier English and notes survive extraction, and the
  browser includes the 191 new insertion overlays.

The status fixture forces one table row at a time, then runs the original
indexing, formatter, active-list write and row renderer. Guards distinguish
buffer overruns from the legitimate active-list pointer immediately after the
last record. Four conditional status literals use direct formatting/rendering;
their shop predicates are not exercised. Order fixtures supply level 99 to the
original unlock helper and draw all seven rows without issuing commands.
Message fixtures suppress the per-glyph delay and stop before the input wait.

Example captures: [help](../build/gameplay-help/verification/english/help.000ea884-normal.png),
[all orders](../build/gameplay-help/verification/english/orders.png),
[speed rules](../build/gameplay-help/verification/english/help.000eaa84-normal.png),
[status](../build/gameplay-help/verification/english/help.001b7c90-normal.png),
[natural help navigation](../build/gameplay-help/verification/natural/english/route-06.png).

Natural dungeon effects, recruiting and commanding allies, shop conditions,
and the original speed-summary discrepancy remain in the
[playtest backlog](PLAYTEST_BACKLOG.md). Personal playtesting can wait.
The subsequent [ally/service milestone](ALLY_SERVICES.md) adds 138 entries
for ally management and shared warehouse/shop/bank/token services. Tutorial
popups, further message blocks, narrative and ally dialogue remain.

## Reproduce

```bash
.venv/bin/python -m tools.build_gameplay_help
.venv/bin/python -m tools.verify_gameplay_help_all
```

The second command rebuilds, runs unit/native/regression checks, refreshes the
extraction browser and writes acceptance. To audit existing artifacts:

```bash
.venv/bin/python -m tools.verify_gameplay_help_all --summarize-only
```
