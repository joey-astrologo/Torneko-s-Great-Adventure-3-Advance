# Torneko 3 Advance documentation

Current build: [continuous completion](COMPLETION.md), through the ordinary story,
pet/password scenes, shared narration, arena services, adventure history/results, church services, remaining frontend text, composed item labels, direct dungeon events and remaining
battle feedback, world merchants, the shared keyboard, scroll inscriptions, remaining world messages, system labels, encounter menus, arena outcome text and indexed arena graphics, sound-test help and the live-floor summary. It contains
8,422 English-authored source entries from the 9,318-entry inventory (90.38%). Each
new component has passed its documented controlled native checks, including
all 2,875 ordinary story cases and eight menus. The latest ROM and exact
coverage are linked there; translation and discovery work continue.

The [extraction coverage audit](TEXT_COVERAGE.md) still tracks resources outside
the initial language filter, including original English credits and short UI
formats. Processing the current inventory does not prove full-game discovery.
Natural later-story, battle and ranking coverage remains separately recorded
in the playtest backlog.

- [Memory map and insertion ownership](MEMORY_MAP.md): central range index, protected source data, current allocations, RAM/save reservations and collision-prevention rule.
- [Tooling decisions](TOOLING.md): selected tools, responsibilities, and the emulator acceptance criteria.
- [ROM roles](TOOLING.md#rom-roles-and-translation-source): Japanese source/build base and the fan translation's technical-reference role.
- [Translation terminology](TERMINOLOGY.md): modern official Dragon Quest naming, sourced glossary, Torneko-specific fallbacks and the existing-English review.
- [Enemy-name research](ENEMY_NAMES.md): historical naming batches; all 200 table rows are now in the combined build.
- [Enemy-trait research](ENEMY_TRAITS.md): historical effect reviews; all 200 rows now have measured native displays.
- [Deferred gameplay checks](PLAYTEST_BACKLOG.md): coverage to revisit while translation work continues.
- [Natural first-cave regression](NATURAL_CAVE.md): normal village/rest, equipment, combat and stairs route to floor two on the current combined ROM.
- [Gameplay wording corrections](TEXT_POLISH.md): latest combined ROM, Recovery pot tutorial/menu consistency and normal pot-use verification.
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

- [Adventure results and high scores](ADVENTURE_RESULTS.md): cause composition, measured display forms, native ranking records and FLASH persistence.
- [Church and save-service dialogue](CHURCH_SERVICES.md): five service voices, complete pages and native table selection.
- [Remaining frontend text](FRONTEND_COMPLETION.md): complete mode help, save warnings and native Adventure Log summaries.

- [Composed item labels](ITEM_DISPLAY.md): quantities, categories, custom names, tracks/graves and prices.

- [Direct dungeon dialogue and tutorials](DUNGEON_EVENTS.md): boss/rescue scenes, companion help and arena pause prompts.

- [Remaining battle feedback and services](BATTLE_COMPLETION.md): 298 sources, guarded history, original item symbols and paged companion/shop prompts.

- [World merchant dialogue](MERCHANTS.md): shops, Medal King, player shops, forging and synthesis; native world pages and separate printf buffer checks.

- [Shared keyboard completion](KEYBOARD_COMPLETION.md): conditional History, English labels and original kana grid font, verified with native layouts and joypad input.

- [Blank-scroll inscriptions](INSCRIPTIONS.md): 49 English input spellings, original kana compatibility and learned-only native matching.
- [Retained resources](RETAINED_RESOURCES.md): reader-confirmed program data and language-neutral formatting, tracked separately from authored English.

- [Remaining world messages](WORLD_COMPLETION.md): Zoom restrictions, item observations and inline initialized warehouse messages.

- [Remaining system labels](SYSTEM_LABELS.md): Adventure Log titles, mode/party menus, object and equipment labels, growth types and bounded ally contexts.

- [Encounter menus and themed houses](ENCOUNTER_UI.md): category names, native house announcements and companion spell availability.

- [Arena outcome text](ARENA_RESULTS_TEXT.md): winner rows, odds, no-winner and additional-winner labels; separate graphic-heading lead.

- [Indexed arena graphics](ARENA_GRAPHICS.md): six phrases outside the ordinary text inventory, using the original Latin font and native tile renderer.

- [Scene program-data audit](SCENE_RESOURCE_AUDIT.md): native ownership of event command prefixes mistakenly found as short strings.

- [Retained program resources](RETAINED_RESOURCES.md): 816 inventory entries
  with positive reader evidence, leaving 80 open candidates.
- [Scene command audit](SCENE_RESOURCE_AUDIT.md) and [background graphics audit](SCENE_GRAPHICS_AUDIT.md):
  native classification of apparent strings inside command and graphics data.

- [Auxiliary and neutral resource audit](AUXILIARY_RESOURCES.md): typed numeric
  fields, input assets, original English diagnostics and unchanged formats.

- [Remaining sound-test help and floor summary](REMAINING_DISPLAY.md): four
  native help selectors and complete dungeon-name/floor-byte boundary checks.

- [Drafts awaiting reader context](UNOWNED_TEXT_REVIEW.md): 30 independent
  drafts outside the build catalogs, plus one unresolved original-star phrase.

The [cold-boot graphics audit](BOOT_GRAPHICS.md) now covers the first 600
frames with native copies and nine Japanese/English pixel pairs. It confirms
a Japanese illustrated title logo outside the ordinary text inventory. The user chose to preserve the original Japanese title artwork; it is an
intentional retained graphic, not an unfinished English title insertion.
