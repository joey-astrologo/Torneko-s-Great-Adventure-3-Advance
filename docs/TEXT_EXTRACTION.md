# Broad Japanese text extraction

The [2026-09-11 coverage audit](TEXT_COVERAGE.md) expands discovery checks to all
pointer alignments/cartridge windows and unaligned NUL-boundary starts. It
records 14 omitted UI resources separately and verifies the observed ROM text
on three opening-game routes against the master. Its 2,414 candidate leads are
not promoted into the inventory; no complete-game extraction claim is made.

The follow-up [story/event provenance audit](STORY_PROVENANCE.md) traces 36
opening-story sources through their event operands, formatter and reused RAM
buffer to native reads. All 36 are already in this inventory. It separately
records 134 original English credit strings and one punctuation-only dialogue
line omitted by the language filter, with native reader checks and protected
ranges in the memory map. That audit did not change the inventory count.

Current inventory: **9,318 entries / 413,712 source bytes**, with **4,828
translated/inserted (51.81%)** and **4,490 remaining**. The
[early-journey pass](EARLY_JOURNEY.md) overlays 194 new story, advice, place
and Zoom UI translations through 322 reviewed pointer words. All have
controlled native checks; the natural opening/first-chief route is a regression
of earlier scenes. Original master drafts, notes and source bytes remain
unchanged. The
[first-village pass](FIRST_VILLAGE.md) overlays 281 new translations with 367
reviewed event operands. All have native display coverage, and ten village
messages extend the natural opening route through the first chief meeting.
Existing master source bytes, English drafts and notes remain unchanged. The
[opening-story pass](OPENING_STORY.md) overlays 46 entries, adding 45 new
translations while reusing the existing first narration. Both dream responses
have natural emulator coverage through the first bedroom; later rest/return
messages have controlled display checks. The
[default-nickname pass](ALLY_NICKNAMES.md) adds an overlay for all 200 table rows
covering 198 distinct existing sources. Original master English, notes and
source bytes remain intact. The
[companion-dialogue pass](COMPANION_DIALOGUE.md) overlays 1,227 further translated
entries: the remaining 1,224 main-table responses and three conditional Rosa
alternatives already present in the inventory. Together with the earlier
[400-entry ally-dialogue pass](ALLY_DIALOGUE.md), all 1,624 non-null main-table
sources are translated and inserted, preserving master source/English/notes.
This is not a claim of complete story/event extraction or translation. The
198 distinct default nicknames now have their own completed insertion catalog. The
[tutorial/gameplay pass](TUTORIAL_GAMEPLAY.md) overlays 285 further entries,
including nine tutorials and 98 equipment-effect labels, without changing
existing master English/notes or source bytes. The
[ally/service pass](ALLY_SERVICES.md) overlays 138 further translated entries
without changing the source inventory or earlier English/notes. The
[gameplay-help pass](GAMEPLAY_HELP.md) overlays 191 new help, order, status and
message translations. These sources were already present in the master;
the inventory count and existing English/notes are unchanged. The
[core-gameplay pass](CORE_GAMEPLAY.md) adds five computed command/choice
sources and overlays all 262 gameplay catalog rows in the browser. Fixed
records are seeded by their documented strides, without treating their padding
as free space. Existing English and notes are preserved.

The preceding
[dungeon-interface pass](DUNGEON_INTERFACE.md) adds 40 previously missed action
records and a separate concealed-object placeholder. All 41 fixed action records
are now explicitly seeded by their documented stride; their English and the
other new interface translations appear in the browser overlay. Existing
English/notes remain intact. The figures below describe the original broad pass.

Discovered table/source ranges and their insertion status are indexed in the
[memory map](MEMORY_MAP.md). Update that map with further range discoveries;
extraction candidates and gaps never constitute allocation permission.

The first broad extraction pass is complete. It produces **9,272 source entries
and candidates**, covering **413,278 non-overlapping ROM bytes** including
terminators. **3,507 entries use indexed glyphs** that the earlier CP932-only
inventory could not correctly decode. The Japanese original is the only ROM
input; no English or font assets come from the partial fan translation.

Start with the [searchable catalog](../build/text-extraction/index.html). It opens
locally without a server and searches Japanese, existing English, source IDs,
addresses, and table rows such as `monster_names:3`. The category and evidence
filters separate the major text families. The page is a read-only snapshot.

The [combined milestone](ENEMIES_AND_ITEMS.md) now has 200 name drafts and
200 trait drafts in the master, plus complete insertion catalogs for these and
all 1,063 item/context strings. The browser overlays current insertion English
with its catalog/entry ID while retaining master drafts and notes. Re-extraction
preserves those drafts; it does not replace them with shortened display prose.

## What was recovered

| Family | Physical table slots | Distinct source addresses |
|---|---:|---:|
| Item names | 370 | 369 |
| Unidentified-item names | 246 | 246 |
| Character/monster names | 200 | 200 |
| Ally dialogue | 1,624 non-null fields in 200 records | 1,624 |
| Ally nicknames | 200 | 198 |
| Monster traits/descriptions | 200 | 200 |
| Item descriptions | 370 | 350 |
| Synthesis-effect descriptions | 100 | 98 |
| Dungeon names | 64 | 36 |
| Trap names | 23 | 23 |
| Object-interaction messages | 21 | 12 |
| Candidate name-filter terms | 165 | 165 |

These roles are based on table structure and decoded content. The character
table includes Torneko and Popolo as well as monsters. Placeholders, reserved
entries, and repeated pointers are retained; row counts are not counts of unique
player-visible objects. The ally dialogue table has a stride of 80 bytes, with
20 potential pointer fields per record. All 4,000 fields, including nulls, are
recorded without assigning unverified meanings to individual fields.

The catalog also includes **3,329 event/dialogue candidates**, **1,018 dungeon
message/UI candidates**, **722 other message/UI candidates**, **588 menu/help
candidates**, and **94 debug/auxiliary candidates**. Those categories use source
regions, not a complete call graph. Some entries are filenames, internal labels,
debug text, or short data matches and should not automatically be translated.

All 27 previously curated sources remain linked to their existing IDs and
verified pointer owners. Their English remains in
[catalog.json](../translations/catalog.json), the existing builder's input.
The name-entry proof and its default `Torneko` name are unaffected.

## The additional encoding

The shared character decoder at `0x0808C72C` reads two bytes for leads
`80..9F` and `E0..FE`. Glyph lookup at `0x0808C66C` supports more than ordinary
CP932:

1. A single byte goes through the 256-entry mapping at ROM offset `0x00CA2674`.
   For example, byte `C4`, normally displayed as halfwidth `ﾄ` by CP932, selects
   the game's **と** glyph. The new catalog shows the game's mapped characters.
2. Ordinary two-byte codes look up a matching font descriptor.
3. Indexed codes select a descriptor directly:
   `index = (lead - 0xF8) * 224 + trail - 0x20`.

For the extraction's **font-0 view**, the 1,345 descriptors start at ROM offset
`0x00C93B4C`, each 12 bytes long, with the glyph code at `+4`. The decoder checks
the index bounds and uses that descriptor's CP932 code as the readable label.
For example, `F9 61 F9 84 F9 66 F9 4C 00` at `0x00191C14` decodes as `トルネコ`.
The existing assembly evidence is in
`build/research/title-font-disassembly.txt`, function `0808c66c`, especially
instructions `0808c686..0808c6a4`.

Indexed glyphs depend on the active font. The catalog explicitly records
`decoding_font: 0` and flags indexed entries; it does not claim that every
runtime font context has been observed. No glyph images or labels are taken
from the fan patch. This encoding uses glyph indexes, not a dictionary of
translated words or an external compression format.

## Source and reference preservation

[game_text.py](../tools/game_text.py) preserves text, line controls, binary
controls, dollar commands, printf templates, and the final NUL as tokens. Their
`raw_hex` fields reconstruct the exact bytes. Unicode is a reading aid and is
never re-encoded to perform the Japanese round trip.

The shared formatter's dollar arguments have fixed byte lengths: `$i0`, `$m0`,
`$d0`, `$j0`, `$p1`, and `$C1` consume one argument; `$v05` consumes two; `$/084`
consumes three. An adjacent number is ordinary text after that fixed length.
`$c` retains its established story-centering role. Other command meanings and
substitution limits still require context-specific checks.

Known `03` controls retain opaque arguments, including zero and Japanese lead
bytes. Source templates such as `03 05 %c` are kept together and flagged because
printf may supply the eventual control argument. A repeated `03 03 08 xx`
sequence in statistics labels retains the first `03` as an opaque prefix, in
accordance with the formatter's default copying branch; its display behavior
is not newly verified. Other unknown binary controls fail closed.

[extract_master_text.py](../tools/extract_master_text.py) combines pinned table
layouts, aligned absolute-pointer candidates, aligned NUL-boundary searches,
and adjacent packed/aligned string pools. Discovery scans the entire ROM;
promotion to the main catalog uses the mapped text banks listed in
`coverage.json`. Readable matches outside those banks remain in the review queue.

The catalog retains **153 sources without a discovered absolute pointer**.
Whole source strings absorb overlapping parses: **291 interior target addresses**
are attached to their containing entries, of which **102 land inside a character
or control**. Even an interior target on a character boundary is only a possible
suffix reference, not an approved pointer owner. Identical strings at different
addresses retain separate IDs and ownership: there are **8,381 distinct byte
payloads** across the 9,272 entries.

Only the existing curated `verified_pointer_owners` have approval from the
earlier runtime/relocation checks. Neither table membership nor a pointer-shaped
word authorizes the builder to rewrite it.

## Files, editing, and reproduction

| File | Purpose |
|---|---|
| [translations/master.json](../translations/master.json) | Stable offset IDs, Japanese view, exact tokens/bytes, references, table membership, English drafts and notes |
| [build/text-extraction/index.html](../build/text-extraction/index.html) | Searchable local review page |
| [master.tsv](../build/text-extraction/master.tsv) | Spreadsheet-friendly review export |
| [coverage.json](../build/text-extraction/coverage.json) | Counts, table summaries, controls, byte budget and limitations |
| [tables.json](../build/text-extraction/tables.json) | Every row/field, including nulls and aliases |
| [review-queue.json](../build/text-extraction/review-queue.json) | Rejected or deferred matches, source addresses and reasons |

Edit only `english` and `notes` in the master. Re-extraction preserves those
fields and refuses changed source bytes, disappearing IDs, duplicate IDs, or a
different base ROM. Curated entries link to the existing English authority in
`translations/catalog.json`; edit their working translations there. Enemy and item insertion uses `enemies.json`, `items.json` and
`item-contexts.json`; edit the actual insertion catalog as well as any retained
full draft. The TSV and browser are generated
views, so edits to those files do not flow back into the master.

```bash
.venv/bin/python -m tools.extract_master_text
.venv/bin/python -m unittest discover -s tests -v
open build/text-extraction/index.html
```

The extractor accepts an optional Japanese ROM path, `--master` JSON path, and
`--output` directory. It verifies the pinned original hash before extraction,
checks all 3,583 non-null table fields, and reconstructs every catalog source
from its tokens. Reinserting those original bytes produces the identical full
ROM SHA-256:

```text
35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02
```

Validation passed **65 unit tests**. Repeating extraction left all six generated
catalog/report artifacts byte-identical. The review page's JavaScript passed
search, category/evidence filtering, pagination and empty-result checks in
JavaScriptCore with a mock DOM; this was not a visual browser test. Hash checks
also confirmed that both supplied ROMs and the existing English/name-entry
proof ROMs were unchanged. New gameplay routes were not exercised in this pass.

## Storage and remaining coverage

The measured source total is about **404 KiB**. As planning scenarios, storing
each catalog entry separately with up to three alignment bytes would require:

| Payload assumption | Bytes including conservative alignment | Remaining from appended 16 MiB |
|---|---:|---:|
| Same byte count as extracted source | 441,094 | 16,336,122 |
| Twice the source byte count | 854,372 | 15,922,844 |
| Four times the source byte count | 1,680,928 | 15,096,288 |

Even the four-times scenario occupies about **1.60 MiB**, leaving **14.40 MiB**.
This is strong planning headroom for the extracted text, not a measurement of
finished English or a guarantee of complete coverage. These scenarios exclude
other code/assets and do not reserve the existing proof builds' allocations.
They also do not establish screen-width, name-field, substitution, or RAM-buffer
limits. Those remain separate insertion constraints.

The review queue contains **11,839 matches**, mostly pointer-shaped non-text
data; it is not 11,839 missing Japanese strings. It records failure reasons and,
where available, a readable prefix before failure. Unknown encodings/controls,
relative or computed references, unaligned or mirrored pointer words, compressed
resources, and text baked into graphics can still be absent. Unused text and
false positives can still occur inside the main catalog's candidate entries.
No full-game playthrough or new runtime validation of the broad catalog is
claimed by this extraction pass.

The broad catalog is now available for translation planning. The next insertion
work can cover a complete text family, starting with item names/descriptions,
using table rows for context and confirming its readers, pointer ownership,
font choice, and output budgets before extending the existing builder.
Ranking-name save-layout work remains deferred.
