# Dungeon names, interactions and item actions

Completed 2026-09-10. This milestone's retained ROM is
[torneko3-dungeon-interface-english.gba](../build/dungeon-interface/torneko3-dungeon-interface-english.gba).
It includes the complete earlier [enemy/item milestone](ENEMIES_AND_ITEMS.md),
27 early menus, seven-character Adventure Log name entry, and **120 additional
catalog entries**. No personal playtest is required before further work.

The newer [core-gameplay build](CORE_GAMEPLAY.md) includes all of this work and
259 more translated entries. It is the current playable build; the counts and
coverage below describe this earlier checkpoint.

| New family | Catalog entries | Physical coverage |
|---|---:|---|
| Dungeon names | 36 | All 64 pointers, including alternate-mode aliases |
| Traps, stairs and teleportal | 23 | All 23 pointers |
| Search messages | 14 | All 21 object-table pointers plus two ground-search event pointers |
| Action labels | 41 | Complete 41-record table, including reserved/placeholder commands |
| Action overrides | 4 | Three Discard sources and the separate concealed-object placeholder |
| Built-in protagonist names | 2 | Torneko / Tipper pair, seven shared base references |

These counts describe source records, not 120 distinct objects or all game UI.
At this checkpoint, general menus, shop services, dialogue, ally nicknames and
most dungeon messages remained later work. The subsequent core-gameplay pass
translates the world Search command and the other main command rows.

## Language and display choices

[dungeon-interface.json](../translations/dungeon-interface.json) is the editable
insertion catalog. [interface-terminology-review.tsv](../translations/interface-terminology-review.tsv)
records every Japanese source, full English choice, displayed form and evidence.
The [glossary](../translations/glossary.json) records the scoped terms and current
review. English is independently authored from the Japanese original; no partial
fan-patch prose or fonts were used.

Dungeon names and most trap/command wording are explicitly **project choices**,
not claims of official English names. `Baleina` is a provisional romanization
to keep consistent when the island and settlements are translated.
**Teleportal** follows modern series usage: the
[Square Enix Tact event page](https://www.square-enix-games.com/en_US/home/dragon-quest-iv-event-dragon-quest-tact)
supplies primary English evidence, and the
[DQ Wiki entry](https://dragon-quest.org/wiki/Teleportal) supplies secondary
evidence for the exact Japanese identity 旅の扉. Its XI section is a stub;
this is not presented as a verified XI game-text capture. Torneko and Tipper
retain the character decisions already reviewed in the glossary.

The native dungeon status header is only **120 pixels wide**. Full names remain
in `english`; seven separate `display` overrides fit the header and its optional
numbered-puzzle suffix:

| Full name | Display |
|---|---|
| Coral temple - Corridors | Coral corridors |
| Seabed mountain - Foothills | Seabed foothills |
| Sea Dragon Isle ruins | Sea Dragon ruins |
| Great Ruins cavern - South | Ruins cavern - S |
| Great Ruins cavern - North | Ruins cavern - N |
| Jungle Island dig site | Jungle dig site |
| Seabed mountain - Summit | Seabed summit |

The puzzle header retains both format arguments and uses `name #number`.
This number denotes a **puzzle**, not a dungeon floor. All names are checked
with `#99` as a width stress case; that does not imply every dungeon naturally
has numbered puzzles.

The action table has 12-byte records: three style bytes and at most eight text
bytes plus NUL. Its complete relocated copy preserves that stride. **Info**,
**Pour**, and **Fill** are separate display forms of Information, Pour water,
and Fill with water. All other action labels fit without a display override.
The original 32-pixel popup is widened to 48 pixels and moved to x184, retaining
an eight-pixel gap after the inventory and ending at x232. Warehouse labels
start at x4, giving a common 44-pixel text budget. Enabled/disabled styles and
the caller-supplied Discard label remain native game behavior.

The `$t` story substitution uses a separate two-record protagonist table;
it does **not** use the entered Adventure Log name. Its fixed ten-byte stride
is retained while replacing the built-in labels with Torneko and Tipper.
No Adventure Log field or save layout changes were needed.

## Ownership and storage

[MEMORY_MAP.md](MEMORY_MAP.md) records every discovered table, source pool,
descriptor, format pointer and temporary fixture field. The new component
rebuilds alongside the earlier components through one `RomBuild` ledger.
Original strings, table padding and descriptor blocks stay protected; newly
relocated text never makes the old source space available for reuse.

- English SHA-256: `d9aebbd3d0753bbd16e2e95680a058dc6440c4df10e867ec7f9f5426a6d2131c`
- Japanese-control SHA-256: `1a82ec1e4f79dcdf13409af727d22420ed9e9166f5b77e3b7b5cb5e83c78b909`
- English uses **56,195 appended bytes**, only **2,147 more** than the previous
  milestone. **16,721,021 appended bytes remain** in the 32 MiB ROM.
- [English ledger](../build/dungeon-interface/english-build.json): 1,590
  allocations and 1,672 checked original-ROM patch ranges. Complete image
  reconstruction succeeds. Earlier components' allocated bytes and patches
  are preserved exactly by an integration test.
- The Japanese control retains the completed earlier English milestone while
  relocating only this new component in Japanese, with original geometry.
  This isolates relocation changes from translation/layout changes.
- Cartridge saves remain **65,536 bytes**. Fixtures use disposable saves and
  restored emulator states; ordinary play saves and both supplied ROMs remain
  unchanged.

The computed action table exposed **40 previously missed strings**. Together
with its separate concealed-object placeholder, the master inventory grows
from 9,272 to **9,313 entries**, all reconstructed exactly from source tokens.
The browser overlays the new catalog without overwriting existing drafts or
notes. This remains an inventory, not proof that all text in the game is found.

## Automated acceptance and limits

[acceptance.json](../build/dungeon-interface/acceptance.json) pins the delivered
ROM and current catalogs. The checks include:

- **156 English interface screens**, covering all action records, dungeon
  pointers, trap pointers and all search strings for both protagonists.
- **156 identical Japanese/baseline pixel comparisons**, plus identical
  Japanese trap-copy output.
- All 23 trap-copy helpers per variant with guarded 30-byte destinations;
  400 existing enemy-copy cases, both fixed protagonist copies, and the
  concealed-trap header.
- Fourteen secondary action-menu fixtures across seven item categories;
  seven normal inventory/information routes (14 screens); four protagonist
  detail screens. These check the widened menus alongside existing text.
- Both protagonists' ordinary ground-search event routes, with actual event
  pointer reads and complete displayed messages, without redirecting text.
- Adventure Log creation with default Torneko, saving, cold loading and entry
  into the opening world; 100 unit tests pass.

Dungeon-header and trap-panel tests execute original native functions in a
disposable world state. The action-table cases force IDs to cover reserved
rows. Search-message cases feed all object-table strings through the native
story formatter/renderer; this does not execute every object's opened/unopened
branch. Secondary menu fixtures supply valid caller labels; they do not perform
warehouse transactions or container effects. Headers can appear over the
opening-world background in these controlled screenshots. The real dungeon
transition, object branches, shops, rankings and save-record questions remain
in [PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).

## Rebuild and verify

Run from the project root:

```bash
.venv/bin/python -m tools.build_dungeon_interface
.venv/bin/python -m tools.extract_master_text
```

To reproduce the complete milestone checks, including rebuilding, unit tests,
native fixtures, regression routes, saving and extraction:

```bash
.venv/bin/python -m tools.verify_dungeon_interface_all
```

To check existing reports against a fresh ledger rebuild and current catalog
hashes without replaying the emulator fixtures:

```bash
.venv/bin/python -m tools.verify_dungeon_interface_all --summarize-only
```

The next substantial translation scope is the remaining gameplay/system menus
and dungeon messages. Story and ally dialogue remain separate later families.
