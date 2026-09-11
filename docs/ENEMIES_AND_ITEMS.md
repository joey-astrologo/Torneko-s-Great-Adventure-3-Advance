# Combined enemy and item milestone

Completed 2026-09-10; all automated acceptance checks passed. The newer
[dungeon-interface build](DUNGEON_INTERFACE.md) includes this entire milestone
and adds 120 entries. This page preserves the enemy/item acceptance snapshot.
The earlier small-batch documents are
historical checkpoints. Authorized 2026-09-10: complete both families together,
integrate them into one playable ROM, and validate automatically. Personal
playtesting remains deferred.

## Build and scope

Open **[torneko3-enemies-items-english.gba](../build/enemy-items/torneko3-enemies-items-english.gba)**
in mGBA. This 32 MiB ROM includes the earlier menus and seven-character name
entry, defaulting to `Torneko`, plus:

| Family | Completed catalog strings | Table rows |
|---|---:|---:|
| Character/monster names | 200 | 200 |
| Monster traits | 200 | 200 |
| Identified item names | 369 | 370 |
| Item descriptions | 350 | 370 |
| Unidentified disguises | 246 | 246 |
| Synthesis descriptions | 98 | 100 |
| Total | **1,463** | **1,486** |

Counts include character, object, reserved and debug rows, not just ordinary
monsters and obtainable items. Aliased pointers retain their shared identity.
Story/NPC/ally dialogue, recruited monsters' nicknames, dungeon/trap labels and
the rest of the interface are later work. Character names in these tables do
not automatically translate the same characters' names in dialogue or saves.

The Japanese original is the sole text/build source. No partial-patch English
or font assets were used. Original ROM bytes remain unchanged except the owned,
checked pointer/code patches in the shared ledger.

## Names and wording

All 200 names and 200 traits are authored. The final 72 name decisions and their
reference games/URLs are in [enemy-name-review.tsv](../translations/enemy-name-review.tsv).
Earlier reviewed enemy names remain intact. Exact Japanese identity takes
precedence over literal meanings: for example, the DQ II ghost しにがみ uses
**Mean spirit**, while the separate skeleton design must not supply its name.
Full **Justice's elder brother** measures 110 pixels; all enemy names fit the
120-pixel checked details layout and original 29-byte payload limit.

The [item terminology review](../translations/item-terminology-review.tsv)
records every identified name, the full English choice, reference game, sources
and evidence status. XI is the baseline; examples of documented fallbacks are
**Steel broadsword** (IX's matching weapon), **Giant mallet** (VII/VIII), and
**Astraea's abacus** (HD-2D remakes). Weapon おおきづち is Giant mallet; the
identically written monster is Hammerhood. These are separate identities.
**Seed of growth** uses paired Dark Prince references with its identity match
explicitly labelled inferred. Torneko-specific names remain project choices;
absence of a reference is not proof that no official equivalent exists.

[Series terms](../translations/series-term-review.tsv) include XI **Oomphle** for
バイキルト, **Deceleratle**, **Fuddle**, **Cock-a-doodle-doo** and **Kamikazee**.
Compound labels such as a spell's staff/scroll are project compounds using the
verified spell name, not claims that the entire item has an official translation.
The [glossary](../translations/glossary.json) preserves these distinctions and
labels fan-maintained references as secondary evidence.

Descriptions were written independently from Torneko 3's Japanese. Five-line
item descriptions and two-line synthesis effects preserve their own targets,
conditions and exceptions. Synthesis effects are not copied from ordinary item
descriptions: for example, the hunger-prevention ring's synthesis source says
hunger is greatly slowed, and a Plain ring's synthesis source adds slime damage.
Old phonetic reading headers are omitted because the item name is already shown.

The complete earlier 16 item drafts and 10 context drafts, including their notes,
remain unchanged. Enemy trait 72's full draft changes `wand effects` to
`staff effects` for category consistency; its effect is unchanged. Twenty-two
traits have separately condensed display prose while retaining full drafts.

## Layout and storage

Original Japanese font 0 supplies every Latin glyph. No new font is required.
Enemy details use a two-line encounter header; ally details retain the full
species name alongside a compact `Max HP` label. Three trait lines fit the
112-pixel-high native window. All original format arguments are retained.
[MEMORY_MAP.md](MEMORY_MAP.md) records the three format-pointer changes and two
local layout halfwords; the shared row-position table is unchanged.

Full canonical names are retained in review TSVs and the glossary. Five measured
[item display overrides](../translations/item-display-overrides.json) reserve
space for native decorations:

| Full name | Display name | Full raw width |
|---|---|---:|
| Monster identification staff | Monster ID staff | 136 px |
| Cock-a-doodle-doo ring | Wake-up ring | 114 px |
| Manchurian ash staff | Manch. ash staff | 104 px |
| Mandarin garnet ring | Mandarin ring | 101 px |
| Steller sea lion scroll | Steller scroll | 105 px |

The raw item-name budget is 100 pixels; the formatted information header allows
144. The 708 identified-name formatter fixtures, including signed decorations,
reach at most 120 pixels. All 246 disguise labels remain distinct. Kaede/Momiji/
Maple, Agate/Menou and Brown/Kasshoku retain distinct Japanese labels instead of
inventing different species or gems. `Regan` (レーガン) and `Claw andrea` remain
explicitly provisional romanizations. ドール is the animal **Dhole**, not Doll.

The complete English build uses **54,048 appended bytes**, including alignment,
menus, keyboard, all six tables and layout formats. **16,723,168 appended bytes
remain**. The 65,536-byte save format receives no additional changes in this
milestone. Original source strings and FF/zero candidates are not free space.

- English SHA-256: `1177c9ef9fef184f2d92d4b62b68b1b63b136dd1eba6324dbb64262fcbd8a852`
- Japanese-relocation SHA-256: `eacf6c802586f435f05ed0e4765786f213640a2612792675b3f53697ea438ace`
- [English ledger](../build/enemy-items/english-build.json): 1,507 allocations,
  1,543 checked original-ROM patch ranges.
- [Japanese ledger](../build/enemy-items/japanese-build.json): 1,504 allocations,
  1,538 patches, 48,192 appended bytes. Menus/name entry remain English in this
  control ROM; the six newly relocated families use their exact Japanese bytes.

These are rebuild-dependent snapshots. Never stack older proof ROMs or hard-code
the end of a previous component as a new allocation address.

## Verification

The acceptance report is [verification/report.json](../build/enemy-items/verification/report.json).
Checks are tied to the ROM/catalog hashes in each report:

- Both native enemy detail layouts for all 200 rows: 400 English screens.
- Inventory and information screens for all 370 item IDs: 740 screens,
  matching full English glyph sequences, raw pointers and measured placement.
- All 246 disguise rows, 100 synthesis rows, plus the synthesis high-bit case:
  347 screens. The 101 synthesis wrapper calls preserve their 1,024-byte buffer
  neighbors and exact source/control bytes.
- 708 identified and 258 unidentified/identified/custom-name calls per variant,
  with 100-byte destination guards. Two enemy-copy helpers cover 400 calls with
  30-byte guarded outputs. Eleven revealed-Cannibox item cases exercise a shared
  enemy-name reader through multiple item categories.
- Japanese relocation comparisons check pixels and formatter output against
  the baseline: **1,487 pixel pairs are identical**, and all 1,377 guarded
  formatter results per variant retain identical Japanese output.
- Combined creation, default-name rendering, saving, cold loading and entry into
  the opening world pass with `Torneko`; save size remains 65,536 bytes.
- 95 unit tests cover source identity, complete coverage, aliases, collision
  rejection, byte/line/ink limits, controls, draft preservation and reconstruction
  of the complete delivered image from its ledger.

Item 127 is a reserved bundle record: byte `+15` (hex) selects a different
item-name row. Its own `Reserved 127` name has static relocation coverage;
its description and selected-name formatting have native coverage. Do not
claim every placeholder name appears in normal gameplay.

The debugger occasionally observes the identical glyph placement twice. One
synthesis case also reports the same draw entry twice, with glyphs only on the
second observation. Tests retain the raw evidence, count these observations,
and coalesce only exact adjacent duplicates before checking complete sequences
and coordinates. The cause is not assumed. Differing text/geometry, missing
following glyphs and actual doubled letters at different positions still fail.

These are controlled emulator fixtures, not natural dungeon playthroughs.
Normal identification, actual synthesis, multi-effect navigation, shops, item
state persistence, recruitment, other live-actor/reveal states and ranking/save
records remain in [PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).

## Rebuild and edit

Run from the project root; mGBA and the existing Python environment are sufficient:

```bash
.venv/bin/python -m tools.build_enemy_items
.venv/bin/python -m unittest discover -s tests
.venv/bin/python -m tools.extract_master_text
```

Edit `english`/`notes` in [items.json](../translations/items.json) and
[item-contexts.json](../translations/item-contexts.json). Enemy full drafts and
optional display prose live in [enemies.json](../translations/enemies.json).
Keep the glossary, canonical review and display overrides consistent with name
changes. The TSV reviews are provenance/full-prose records; they do not silently
replace later manual catalog edits. `prepare_item_catalogs` validates imports
and preserves existing drafts. `initialize_catalog` likewise never rewrites
existing enemy prose or display text.

The searchable [extraction review](../build/text-extraction/index.html) now
shows current insertion text alongside retained master drafts. Re-extraction
preserves English/notes and still reconstructs all 9,272 source entries exactly.
It does not independently authorize candidate pointers for insertion.

Reproduce all native checks with:

```bash
.venv/bin/python -m tools.verify_enemy_items_all
```

The runner uses temporary emulator cartridges and disposable saves. Reports,
traces and screenshots go under `build/enemy-items/verification/`. Ordinary
play saves are not modified. Record newly discovered locations in MEMORY_MAP.md
before changing any ownership or layout.
