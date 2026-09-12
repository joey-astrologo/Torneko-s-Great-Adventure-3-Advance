# Adventure results and high scores

This component has **passed its controlled native checks**. The
[acceptance report](../build/completion/results/component-checkpoint.json)
records the exact ROM, catalogs, harnesses, screenshots and save evidence.

The [result catalog](../translations/adventure-results.json) independently
translates 185 resources through 284 original pointer words. Of these, 181
belong to the current master inventory. Three scoped empty relation copies and
one short actor-relation format were reviewed outside that inventory. Full
wording remains alongside measured display forms. Original result lookup keys,
cause numbers, special marker, optional-note priority and three list modes are
preserved. Exact source/table/code ownership is in [MEMORY_MAP.md](MEMORY_MAP.md)
and the [source report](../build/completion/results/source-owners.json).

The same 97 unique cause tails serve the high-score list (`0800177C`), score
detail (`080860B0`) and dungeon-ending screen (`0805BEFC`). English moves the
Japanese relation particles from a shared actor-name prefix table into each
result phrase. Unknown-actor relation copies explicitly supply `something`.
The normal list still uses its original ellipsis logic.

The original detail window has a 208px text area. The new private descriptor
uses 216px while retaining the original height, font and record layout. A
232px prototype was rejected after the native constructor cleared beyond the
existing tile buffer and damaged font state. Its images, ledger and failure
evidence are preserved under
[rejected-width232](../build/completion/results/research/rejected-width232/rejection.json).
The revised native probe checks both displayed glyphs and unchanged font-table
pointers. Text insertion alone is not treated as runtime acceptance.

The longest combined actor/item result needs eight display abbreviations.
These apply through a private copy of the 370-entry item-name table, selected
only by the three result readers. Original inventory names, full glossary terms,
item IDs and their existing pointer ownership stay intact.

| Item | Result display |
| --- | --- |
| Double-edged staff | Double-edged stf. |
| Safe Passage scroll | Safe Passage scr. |
| Spoiled blank scroll | Spoiled blank scr. |
| Monster haste scroll | Monster haste scr |
| Trap trigger scroll | Trap trigger scr. |
| Throw effect statue | Throw effect st. |
| Trap growth statue | Trap growth st. |
| Trap breaker statue | Trap breaker st. |

The full glossary remains the terminology authority. The Japanese result
`異縮小のたね` contains a spelling error; its item identity and neighboring
belly-seed results establish the existing Small belly seed entry. `Spiked floor`
is descriptive project wording. The [terminology review](../build/completion/results/terminology-review.json)
records reused identities and their existing evidence quality.

High scores use 48-byte records in eight categories of twenty entries. Their
protagonist bit selects the built-in Torneko/Tipper name; these readers do not
read the editable Adventure Log name. The original record writer `080011F0`
stores numeric statistics, cause/actor/item IDs, equipment and protagonist bits,
then shifts whole 48-byte rows. The [native profile save proof](../build/completion/results/verification/profile-saves/verification.json)
now passes: creation and row shifting in all eight categories, native checksum
and FLASH writes, identical profile bytes in a fresh core, unchanged Adventure
Log sectors, and both seven-character Torneko names cold-loaded successfully.
The input save had an erased score/history region, so the fixture used the same
native profile initializer as the frontend. The separate profile is 8,108 bytes
inside the final two FLASH sectors. These records require no name-field or
save-size expansion; the save remains 65,536 bytes. Natural dungeon-end save
timing is still separate from this controlled persistence proof.

The completed checks cover 1,558 English result/list/detail cases and 236
ending/category cases, with 1,128 Japanese relocation pixel comparisons. They
include every cause key and protagonist, all three list modes, optional notes,
unknown actors, all dungeon labels and every species/item against its widest
partner. The category menu now has 208px of space; its occupied, empty and
invalid-profile branches pass. Campaign has separate label coverage, without
claiming a selectable path. These controlled checks do not establish natural
dungeon-ending transitions or every achievement condition.

Both full ROM images reconstruct exactly from their allocation/patch ledgers.
Earlier patches and appended data remain byte-identical, and protected original
Japanese sources remain intact. The combined English ROM is
[torneko3-adventure-results-english.gba](../build/completion/results/torneko3-adventure-results-english.gba),
SHA256 `6db4a44bb2f06ff976cae82bedb18224c35b6bc8c302d2257169240a6cb2bbff`.

Rebuild: `.venv/bin/python -m tools.build_adventure_results build`.
Native checks: `.venv/bin/python -m tools.verify_adventure_results english`
(also `japanese` and `baseline`), then `tools.verify_result_ending` for the
same three variants, `tools.verify_result_saves`, and
`tools.summarize_adventure_results`. Run the save verifier before the ending
verifier if regenerating from scratch; the category fixtures use its native
profile save.
