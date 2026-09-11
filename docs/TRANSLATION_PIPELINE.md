# Translation catalog and build workflow

Current full-build workflow: [COMPANION_DIALOGUE.md](COMPANION_DIALOGUE.md).
This page describes the original curated menu/message component; `catalog.json`
remains its authority. The current combined builder also consumes `items.json`,
`item-contexts.json`, `enemies.json`, `dungeon-interface.json` and
`core-gameplay.json`, `gameplay-help.json`, `ally-services.json` and
`tutorial-gameplay.json`, `ally-dialogue.json` and `companion-dialogue.json` through the same ownership
ledger. All 311 earlier core/help message templates now obey the 59-byte history
payload limit, including 16 whitespace-only reflows owned by their original
components. Live queue capacity alone is insufficient. Historical builders keep
their previous default layouts; the current builder composes the reflow callback.

Before adding or revising English, follow the [terminology policy](TERMINOLOGY.md)
and [sourced glossary](../translations/glossary.json). Match Japanese identities,
keep Torneko 3's effects, and check repeated names across all family catalogs.

Status, 2026-09-10: the expanded 27-entry English batch builds and passes its native
mGBA checks using **the original Japanese ROM's font 0**. The Japanese round trip
is byte-for-byte identical to the source ROM. English was drafted independently
from the extracted Japanese; the partial fan translation supplies no text or
font assets to this build.

The [early-menu milestone](EARLY_MENUS.md) records the 21 added entries, menu
default markers, automatically sized windows, and verification of both save slots.

## Edit and build

Edit only `english` values in [translations/catalog.json](../translations/catalog.json).
Each entry includes its Japanese text and context. Use `null` to leave an entry
untranslated. Retain the other source fields: the builder compares them with
fresh extraction from the pinned Japanese ROM.

Run from the project root with the installed Python environment:

```bash
# Extract the currently verified anchors into a separate inspection file.
.venv/bin/python -m tools.translation_pipeline extract

# Reconstruct Japanese from the catalog's original byte tokens.
.venv/bin/python -m tools.translation_pipeline build --language japanese

# Build English, validating every translated entry before writing output.
.venv/bin/python -m tools.translation_pipeline build

# Run source, allocator, encoding, and layout tests, then native emulator routes.
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tools.verify_translation
```

Extraction writes `build/translation/extracted-ja.json`; it does not overwrite
the editable catalog. The commands accept an explicit ROM path and `--output`.
Build and verification also accept `--catalog` and `--anchors`. When using a
different output directory, pass it to both builds and verification.

| Output under `build/translation/` | Purpose |
|---|---|
| `torneko3-english.gba` | Playable 32 MiB build containing the 27 translated entries |
| `torneko3-japanese-roundtrip.gba` | Reconstructed 16 MiB Japanese ROM, identical to the original |
| `english-build.json`, `japanese-build.json` | Input/output hashes, allocations, pointer changes, and bounds checks |
| `verification.json` | Emulator acceptance results tied to the ROM, catalog, and anchor hashes |
| `early-menus.png` | Six native-resolution screenshots of the current build |
| `first-batch.png` | Retained four-screen review of the original six-entry milestone |
| `verification/{original,english}/` | Six route directories: `settings`, `creation`, `story`, `slot-two`, `creation-two`, `story-two`; screenshots, traces, schedules, and creation saves |
| `verification/cross-load-original/` | Original-ROM loading check using the English build's save |

Open `torneko3-english.gba` in mGBA to try the batch. Generated ROMs and saves are
local artifacts under ignored `build/`. The older proof ROMs and their patches
are independent experiments; build this catalog directly against the Japanese
original rather than applying those proofs together.

## Current batch and bounds

The original six entries below remain in the build. See [EARLY_MENUS.md](EARLY_MENUS.md#added-sources)
for the 21 additions and their pointer owners.

| Entry ID | English / context | ROM bytes, including NUL | Checked layout |
|---|---|---:|---|
| `title.new_game` | New game | 9 | 46 px advance within 76 px available from x=4 |
| `title.continue` | Continue | 9 | 39 px within the same title window |
| `title.settings` | Settings | 9 | 39 px within the same title window |
| `settings.message_speed` | Text speed; Slow / Norm / Fast | 41 | Fixed x=64/96/128 columns in a 152 px window |
| `save.new_log_explanation` | Start a new adventure; name the selected Adventure Log | 75 | Three lines, longest 136 px including slot ２, within 208 px |
| `story.opening_01` | Torneko's past adventure with the heroes | 98 | Three centered lines, advances 162/139/142 px, within 208 px |

Font 0's existing advances and visible glyph bounds determine fit. No font data
or renderer code is patched. These profiles were observed with zero extra
spacing and font 0; their limits are not global limits for every screen.

The settings checker reserves **at least four pixels between a segment's end
and the next fixed column**. This is our readability allowance, not an engine
requirement. `Normal` advances exactly 32 pixels and technically fits between
x=96 and x=128, but leaves the options visually crowded. The draft uses `Norm`
(23 px) to leave separation. The original position and selection controls stay
in their original order. Native captures also exercise Slow, Norm, and Fast
selection with left/right input, then return to the title menu.

Formatted payload limits are 256 bytes for the settings formatter, 999 for the
new-log message, and 1,023 for this story reader. The terminating NUL is allowed
at the payload-end address. The current English payloads use 40, 73, and 97
bytes respectively. Settings text also passes through a second buffer with
style controls; the verifier checks its wrapped contents on the recorded route.
These are observed reader limits, not a guarantee that every future caller or
wrapper can accept that much text.

## Text and control syntax

English uses printable ASCII plus line breaks. In JSON, write a line break as
`\n`. Accents, typographic punctuation, raw dollar/backtick commands, NULs,
unrecognized controls, and unmatched braces are rejected. There is no automatic
word wrapping: choose line breaks explicitly and let the builder check them.

| Catalog token | Game bytes / meaning |
|---|---|
| `{slot}` | `$j0`; inserts the selected Adventure Log number |
| `{center}` | `$c`; centers one story line |
| `{default}` | Leading `*`; initially selects a generic-menu option, with no visible glyph |
| `{x:64}`, `{x:96}`, `{x:128}` | `03 08 xx`; fixed horizontal positions |
| `{choice:1}`, `{choice:2}`, `{choice:3}` | `03 14 xx`; original option drawing attributes |

Every translated entry must retain the Japanese source's ordered sequence of
command tokens. Wording and line breaks may change within the profile's bounds.
Each story line must begin with `{center}`. The checker expands `{slot}` to both
original fullwidth digits, `１` and `２`, and checks both glyph widths and RAM
payloads. Both substitutions were also exercised through normal controller
input in mGBA. The digit glyphs remain Japanese-ROM assets.
`{default}` is permitted only at the beginning of a menu label with that marker
in its Japanese source. Moving, removing, or adding an initial selection is
rejected. Menu profiles also check fit against the actual native window width
when the game contracts a panel around shorter English labels.

For example, the current save prompt is:

```text
Start a new adventure.
Name Adventure Log {slot} using
up to four characters.
```

`source_tokens` retain original byte encodings. The Japanese round trip uses
those bytes rather than Unicode re-encoding, which could change CP932 aliases.

## Allocation and source ownership

[translations/anchors.json](../translations/anchors.json) is the technical map:
stable IDs, original file offsets, verified pointer locations, and layout
profiles. It is maintained when adding verified sources, separately from
editing English. The builder rejects incorrect pointer values, duplicate
owners, overlapping source strings, changed source fields, and a different base
ROM. It does not search for arbitrary pointer-like integers and rewrite them.

All English payloads share one four-byte-aligned, append-only allocator in file
offsets `0x01000000..0x01FFFFFF`. Allocation order follows sorted entry IDs, so
reordering catalog entries cannot change the ROM. Changed translations may
move subsequent allocations; the builder rewrites their owned pointers and
records every allocation, alignment gap, and pointer change in the report.

The current batch contains **741 payload bytes plus 44 bytes of alignment**:
785 bytes used and **16,776,431 bytes remaining** in the appended 16 MiB region.
This budget is shared by future translation data and any future additions to
the same build; it is not a full-game size forecast. Overflow beyond 32 MiB is
an error. Original-ROM padding is not used. An all-null catalog leaves the ROM
at its original 16 MiB size.

Inside the original 16 MiB region, only the 27 declared pointer words change.
The original text, font bitmaps, and all other bytes are preserved and checked.
The builder validates first, then replaces generated output files atomically;
it refuses to overwrite the ROM or JSON inputs through its output paths.

## Verification and remaining work

The current milestone passed **52 unit tests** and **39 paired native screenshots**
across settings, creation/loading in both slots, and the second empty-slot prompt.
Pixels outside translated text and automatically sized menu panels match the
Japanese runs. Native traces verify all 27 relocated sources, their pointer reads, glyph sequences,
positions, widths, natural font-0 selection, and formatter results. The complete
English story screenshot is also reproduced from the original font bitmaps.
The six-screen review image and the display-option captures were visually inspected.

Both builds create identical 65,536-byte cartridge saves for each slot, persist
them to disk, and cold-load successfully. The slot-1 English save also loads in the Japanese ROM
and reaches the pinned original story fixture. Advancing from the translated
first story page reaches an unchanged second page that matches the original.
The verifier uses the installed mGBA 0.10.5 bindings and built-in BIOS, with no
game-memory or font-selection overrides.

English ROM SHA-256 for this draft:

```text
0b066b5d0e61e2014ed5d47fb828bff3949a9e371620a675acf9440c77a84561
```

This is a small working batch, not a complete text extraction or translation.
The verifier requires coverage of every translated entry and both supported
slot-number substitutions; adding sources outside the recorded routes requires
new route coverage. Both builder and verifier support null entries. A 26-entry
partial catalog with Japanese narration also passed native checks. At least
one entry must be translated for English verification. Other menus, names, descriptions, dynamic
substitutions, compressed text, and later events still need confirmed sources,
pointer owners, controls, and window measurements. Font-1 contexts need their
own treatment. Full gameplay and physical hardware have not been tested.

The subsequent [seven-character name proof](NAME_ENTRY.md) completes the bounded
Latin name-entry pass, including `$i0`, both-slot saves, and legacy-save loads.
Its separate builder uses this catalog and allocator, then appends the name code
and tables with an explicit patch ledger. It overrides the length explanation
in memory; this editable catalog and the ordinary 27-entry build remain unchanged.

The first [broad Japanese extraction](TEXT_EXTRACTION.md) is now available in
`translations/master.json`: 9,272 source entries and candidates, with exact
bytes, table rows, controls and reference evidence. Its 27 curated links retain
this catalog as their English authority. New master drafts do not automatically
enter this builder; a new family needs verified owners, encoding, substitution
rules and layout profiles first.

That integration is now complete in the [item-text build](ITEM_TEXT.md).
`tools.build_items` supplies one `RomBuild` to the menu, name and item components,
with a complete allocation/patch ledger and collision rejection. Its item catalog
owns both full item tables and preserves untranslated Japanese. The commands on
this page still reproduce the earlier menu-only milestone; use the item workflow
for the combined ROM with seven-character naming and item text.

The latest [item-context workflow](ITEM_CONTEXTS.md) builds those components
together with the complete unidentified-name and synthesis-description tables.
Use `tools.build_item_contexts` for that combined ROM; each earlier workflow
continues to reproduce its documented milestone.
