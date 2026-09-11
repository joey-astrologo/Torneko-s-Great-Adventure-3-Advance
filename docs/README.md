# Torneko 3 Advance documentation

Current build: [early dungeon journey and place names](EARLY_JOURNEY.md), adding 194 entries across the rest stops, complete dungeon advice, place table and Zoom picker. All new sources have native checks, including six-topic menus and bounded destination copies. The build preserves earlier translations and both Adventure Logs, with an opening/first-chief-meeting regression. Start there for the playable ROM, terminology, storage and acceptance report.

Latest research: [story/event provenance](STORY_PROVENANCE.md), extended by the opening translation and ten further naturally reached village sources. A separate resource report records 134 original English credits and one punctuation-only line omitted by the language filter. This extends the [extraction coverage audit](TEXT_COVERAGE.md) and its 14 short UI resources. The inventory remains 9,318 entries with 4,828 translated/inserted (51.81%) after 194 new journey/place/UI translations; complete-game discovery is still unproven.

- [Memory map and insertion ownership](MEMORY_MAP.md): central range index, protected source data, current allocations, RAM/save reservations and collision-prevention rule.
- [Tooling decisions](TOOLING.md): selected tools, responsibilities, and the emulator acceptance criteria.
- [ROM roles](TOOLING.md#rom-roles-and-translation-source): Japanese source/build base and the fan translation's technical-reference role.
- [Translation terminology](TERMINOLOGY.md): modern official Dragon Quest naming, sourced glossary, Torneko-specific fallbacks and the existing-English review.
- [Enemy-name research](ENEMY_NAMES.md): historical naming batches; all 200 table rows are now in the combined build.
- [Enemy-trait research](ENEMY_TRAITS.md): historical effect reviews; all 200 rows now have measured native displays.
- [Deferred gameplay checks](PLAYTEST_BACKLOG.md): coverage to revisit while translation work continues.
- [Installation on macOS](INSTALL.md): local prerequisites and installation/build instructions.
- [First working label](FIRST_LABEL.md): reproduce the Begin proof patch, inspect the rendering trace, and run its tests.
- [ROM storage and expansion](STORAGE.md): storage budget, 32 MiB relocation proof, and real save/load checks.
- [Text systems and inventory](TEXT_SYSTEMS.md): candidate extraction, verified readers, controls, RAM limits, and three additional relocation checks.
- [Latin font review](FONTS.md): existing glyphs, pixel widths, native menu/dialogue comparisons, and the interactive review page.
- [Translation catalog and builds](TRANSLATION_PIPELINE.md): edit English, rebuild Japanese/English, and check layout, storage, and native rendering.
- [Early menus and adventure creation](EARLY_MENUS.md): the expanded 27-entry batch, default choices, automatically sized menus, and both save slots.
- [Seven-character name entry](NAME_ENTRY.md): working Latin keyboard, full `Torneko` name, both-slot saves, and compatibility with Japanese saves.
- [Broad Japanese extraction](TEXT_EXTRACTION.md): 9,318 catalog entries, indexed-glyph decoding, computed action/command records, searchable review page and coverage gaps.
- [Item text insertion](ITEM_TEXT.md): complete name/description tables in the combined build, eight English examples, native reader checks and shared collision enforcement.
- [Unidentified names and synthesis descriptions](ITEM_CONTEXTS.md): 344 further strings, complete reader coverage, preserved category fields and six-pixel synthesis spacing.

## Earlier milestones

The tooling choices were agreed on 2026-09-09. The selected tools are installed;
mGBA automation, Ghidra's GBA import/disassembly, and armips have passed setup checks.
The first independent label patch also passes its build and emulator checks.
The 32 MiB expansion proof passes the recorded menu, adventure-log creation,
and cold-load route; broader gameplay compatibility remains to be tested.
As of 2026-09-10, the reusable catalog builds 27 independently translated entries
with font 0. Japanese extraction/reinsertion is byte-identical; all 52 unit tests
and 39 paired emulator screenshots pass. Both save slots pass creation and cold
loading, with identical Japanese/English save data. The batch uses 785 appended
bytes. See the [pipeline workflow](TRANSLATION_PIPELINE.md) and
[early-menu results](EARLY_MENUS.md) for the build, screenshots, and remaining work.

A separate [name-entry proof](NAME_ENTRY.md) now supports seven-character names
with font 0, without increasing the 64 KB save file. Its complete build occupies
2,528 appended ROM bytes and defaults new logs to `Torneko`. Both slots, existing
Japanese saves, all 62 new letter/digit IDs, and editing limits pass native checks.

The first [broad extraction pass](TEXT_EXTRACTION.md) now contains 9,272 source
entries and candidates covering 413,278 bytes. It decodes the font indexes used
by 3,507 entries, including monster names, ally dialogue and descriptions. All
sources reconstruct exactly. Use the [searchable review page](../build/text-extraction/index.html)
to explore the catalog; completeness and new-family insertion still need checks.

The [combined item build](ITEM_TEXT.md) now relocates 719 unique item strings
through all 740 table pointers, alongside the existing menus and name entry.
Eight items have English names/descriptions; the remaining item text stays
Japanese. All 87 current unit tests pass, with 16 identical Japanese relocation screen
pairs, native coverage of every English item draft, 380 guarded formatter calls
per variant and a combined `Torneko` save/cold-load check. The complete shared
ledger rejects collisions and records 27,951 appended bytes for this draft.

The subsequent [item-context build](ITEM_CONTEXTS.md) adds all unidentified-name
and synthesis-description rows to that shared ledger. Ten new English entries
pass native layout checks; all 346 new pointer fields have reader coverage.
The complete build uses 36,826 appended bytes. Its 87 unit tests, 107 identical
Japanese relocation screen pairs, guarded formatters and combined save/cold-load
check pass. These use controlled item fixtures; natural dungeon item behavior
still needs playthrough coverage.

The [terminology review](TERMINOLOGY.md) covers all 53 existing English entries
and the embedded name-entry copy. Six entries were corrected, including repeated
item names in synthesis headings. The [glossary](../translations/glossary.json)
records modern series references and provisional Torneko-specific choices.
Both combined builds pass their native checks and save/cold-load routes after
the corrections; the latest context ROM uses four more bytes than its first
draft. There are now [128 enemy-name drafts](ENEMY_NAMES.md) following the same
naming policy, plus [80 enemy-trait drafts](ENEMY_TRAITS.md) translated from
Torneko 3's Japanese. They are searchable in the review page; their ROM insertion
and runtime checks remain pending. Translation work can continue while the user
defers personal playtesting.
