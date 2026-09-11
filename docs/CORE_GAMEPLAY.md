# Core gameplay menus and messages

Completed 2026-09-10. Open
[torneko3-core-gameplay-english.gba](../build/core-gameplay/torneko3-core-gameplay-english.gba)
in mGBA. This build retains all earlier enemy/item translations, dungeon
interface work and seven-character Adventure Log names, and adds **259 new
translated entries**. The 262-entry catalog also records three existing settings
rows whose allocations are reused explicitly.

| Covered family | Entries | Validation |
|---|---:|---|
| Item handling, ordinary combat, hunger, status and item-use messages | 205 | Native message engine, normal and maximum-width substitutions |
| Main command rows | 11 | Four fixed variants plus ground/trap/stair/back and world commands |
| Statistics rows | 4 | Native printf, field boundaries, large numeric fixtures |
| Settings labels | 33 | All original label callbacks, including two arena variants |
| Stair and trap choices | 4 | Three fixed stair records plus the trap activation row |
| Container/prompt labels | 3 | Native literal display fixtures |
| Conditional actor labels | 2 | Someone / Fake Torneko; existing 30-byte copy budget retained |

These are the selected core gameplay families, not the entire coarse
“dungeon messages” extraction category. Tutorial/help bodies, further status
explanations, ally orders/dialogue, shop services, story dialogue and other
message blocks remain to translate. Four source candidates without verified
readers remain untouched. The world menu's village name belongs to a separate
proper-name family and remains Japanese.

[core-gameplay.json](../translations/core-gameplay.json) is the editable catalog.
The [terminology review](../translations/core-gameplay-terminology-review.tsv)
covers every entry; the [glossary](../translations/glossary.json) records shared
terms. Mimic, Cannibox, Zoom, Torneko and Tipper reuse the previously reviewed
Japanese identities and references. New sentences are independently translated
from the original Japanese, with no fan-patch English or font assets.

“Tactics” retains the series word used in the
[official Dragon Quest VII manual](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/nintendo_3ds_2/dragonquest7/ElectronicManual_Nintendo3DS_DragonQuest7_EN.pdf).
Its application to Torneko's broader command/settings menu is a project UI
choice. Fullness, leaky belly, wakefulness, whiffing and darkness remain explicit
project status wording. This does not import another game's effects.

The main command window grows from 72 to **80 pixels**, ending at x96 with an
eight-pixel gap before the status header. “Tactics” fits in full. “Abilities”
uses the separately recorded **Skills** display label in two transformed-character
variants; the full term remains in the catalog and glossary. Settings retain
native selection controls, styles and the original submenu arrow glyph.

Message wrapping reserves **144 pixels per item name**, **120 per actor name**,
and the width of a signed 32-bit number. English uses explicit measured breaks
within a 208-pixel, three-line message window. Japanese `$/NNN` commands only
choose conditional line breaks; they are replaced with English layout while
all actor/item/number substitutions are retained. Pauses and complex concatenated
battle fragments outside this scope have not been guessed at.

## Ownership and storage

The [memory map](MEMORY_MAP.md) records the source pools, pointer owners, fixed
records, window fields and fixture buffers. A native check exposed the command
variants' **four 30-byte records**; the whole table is relocated with its stride
and padding intact. Stair choices similarly retain their three 32-byte records.
The shared ledger rejected duplicate ownership of Reset settings, Text speed
and Display; these three rows now validate and reuse the earlier allocations.

Every component is rebuilt together from the pinned Japanese original. Source
text and discovered padding remain protected. No new permanent RAM reservation,
font insertion or save-layout change was needed.

| Current English build | Value |
|---|---:|
| ROM size | 32 MiB |
| Appended bytes used, including alignment | 63,084 |
| Additional bytes since dungeon interface | 6,889 |
| Appended capacity remaining | 16,714,132 |
| Allocations / checked original patch ranges | 1,845 / 2,066 |

The occupied appended interval is `[01000000,0100F66C)`. These are this build's
results, not offsets to reuse manually. Exact assets and original patches are
in [english-build.json](../build/core-gameplay/english-build.json).

English SHA-256:
`d0289146a232f3231217044d609cd1a4843bf5e0537d6879f356057296c13e10`.
Japanese control SHA-256:
`567349d96eb15fd5d205407d2318665014f039321812a3d24b7812786fa25a4e`.
The control leaves earlier components English and isolates only this component's
new Japanese relocation; the three shared curated rows stay English too.

## Automated acceptance

[acceptance.json](../build/core-gameplay/acceptance.json) ties the results to the
ROM and catalog hashes:

- **108 unit tests**, including source/argument contracts, record strides,
  measured column limits, shared ownership and preservation of earlier assets.
- **483 English screenshots**: 410 message cases, 24 direct row cases, 37
  settings callbacks, four computed command variants and eight navigation steps.
- **278 Japanese control screenshots**, each pixel-identical to the previous
  build using the same fixture inputs.
- **Nine native stair-choice reader calls**, covering all three record offsets
  in English, Japanese control and baseline.
- **400 guarded enemy copies**, both fixed protagonist copies, 14 secondary
  action menus, both natural ground-search routes, 14 inventory/information
  screenshots and four protagonist-detail screenshots on the new ROM.
- `Torneko` creation, save, cold-load and world entry; save remains **64 KiB**.
- **9,318 master source records** reconstruct the pinned original exactly.
  Re-extraction preserves existing English and notes. Five newly discovered
  computed command/choice sources are now indexed and searchable.

Message fixtures run the original formatter and message renderer, suppress the
per-glyph delay, and stop before the input wait. They check actual substitutions,
font, positions and output guards. Maximum-width names are synthetic stress
inputs; ordinary cases use established English names. Direct row fixtures and
static pointer ownership do not establish every natural gameplay caller.
Settings left/right navigation changes and restores the actual option value.
Command-row checks use actual nontransparent glyph pixels because the original
second row begins at y13 in a 24-pixel-high panel.

Example captures: [main commands](../build/core-gameplay/verification/english/route-commands.png),
[settings](../build/core-gameplay/verification/english/route-game-settings.png),
[combat message](../build/core-gameplay/verification/english/gameplay.001b4df1-normal.png).

Natural hunger progression, curses, consumable effects, monster reveal labels,
transformation and dungeon transition choices remain in the
[playtest backlog](PLAYTEST_BACKLOG.md). Personal playtesting can wait.

## Reproduce

From the project root, using the installed environment:

```bash
.venv/bin/python -m tools.build_core_gameplay
.venv/bin/python -m tools.verify_core_gameplay_all
```

The verifier rebuilds, runs the unit/native/regression checks, refreshes the
extraction browser and writes acceptance. To audit existing artifacts without
replaying all emulator fixtures:

```bash
.venv/bin/python -m tools.verify_core_gameplay_all --summarize-only
```

Edit only `english`, optional `display`, and `notes` in the gameplay catalog.
Typed `{hex:...}` controls, `{arrow}`, printf argument types and dollar
substitutions are validated against the source. Message line breaks are derived
from the measured budgets; manually supplied breaks remain paragraph boundaries.
Changes to the three shared settings rows must agree with the original curated
catalog, rather than introducing a second patch owner.
