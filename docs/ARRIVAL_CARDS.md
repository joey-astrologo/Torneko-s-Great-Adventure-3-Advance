# Arrival-card review sheets

The original dungeon arrival table has **64 selectors pointing to 36 distinct
Japanese graphics**. All 36 are exported for review, including the four
alternate trial titles. [An English lettering audition](ARRIVAL_AUDITION.md)
now includes a reusable reconstructed Shiren face and interactive comparisons.
The user subsequently approved Credits adapted; the
[English insertion](ARRIVAL_INSERTION.md) now covers all 36 cards and their
matching floor lettering. This page retains the original Japanese source review.

- [All 36 cards, 2× PNG](../build/arrival-cards/arrival-cards-japanese.png)
- Larger pages: [1](../build/arrival-cards/arrival-cards-japanese-page-1.png),
  [2](../build/arrival-cards/arrival-cards-japanese-page-2.png),
  [3](../build/arrival-cards/arrival-cards-japanese-page-3.png)
- [Native-scale overview](../build/arrival-cards/arrival-cards-japanese-1x.png)
- [Separate floor artwork: 0–9, F and Q](../build/arrival-cards/floor-glyphs-japanese.png)
- [Individual 240×160 cards and name-only PNGs](../build/arrival-cards/japanese/)

Each card retains its native screen placement and colours. A black review
background replaces the changing, darkened gameplay scene. Sample floor
numbers are 1F, or Q1 for the two puzzle dungeons; the arena card has no floor
line. These samples are reconstructed from the original tilemap and tiles,
not screenshots of 36 naturally visited locations.

The IDs below each card are stable selector references. English captions are
the existing ordinary-text dungeon names from
`translations/dungeon-interface.json`, placed outside the game screen to help
identify the Japanese graphics. They are not English artwork or a font
decision. Shared selectors use the same source asset and appear once on the
sheet; the manifest preserves all aliases. Both original and English reference
names are retained there. The Japanese name reference is catalog text, not a
new OCR transcription of the artwork.

## Town coverage

The 64-entry table contains dungeon names, including the arena and puzzle
caves; it does not contain the village/shrine place names. The normal
[Shrine of the Gods entry](../build/arrival-cards/verification/shrine/transition-sheet.png)
and [inn exit into Barinabo Village](../build/arrival-cards/verification/village/transition-sheet.png)
were captured at ten-frame intervals. These transitions show scene fades/pans
without a separate arrival title, and neither reads the dungeon-card table.

**No separate town arrival-card family is confirmed yet.** These two routes
do not establish that all towns, first-visit events or later story transitions
lack such cards. Any further town artwork discovered during gameplay should
be added to the manifest and memory map before audition/insertion. Ending and
credit graphics remain outside this extraction; the original Japanese title
logo remains intentionally preserved.

The subsequent [scene-background sweep](GRAPHICS_REVIEW.md) exports all 102
scene-table backgrounds and their tile-animation frames. It confirms no
additional town-name card in that family, while preserving small sign/detail
PNGs for review. This narrows the search but leaves sprite/object overlays,
other loaders and natural first-visit coverage separate.

## Source and validation

Source: pinned Japanese ROM, SHA256
`35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02`.
The fan translation supplied no text, graphics or font assets.

The [manifest](../build/arrival-cards/manifest.json) records all 64 selector
mappings, 36 unique source spans, tile counts, source hashes, ordinary-name
references and PNGs. The [range ledger](../build/arrival-cards/resource-ranges.json)
and [memory map](MEMORY_MAP.md#original-dungeon-arrival-cards-2026-09-12)
protect the original cards, palette, atlas, tables and native readers.
All asset ends join exactly across the identified envelope.

Native constructor `0800518C` selects `dungeon_id + 32 * bank`. It copies a
29×9-tile name region from a 32×32 source map, then draws the independent
floor glyphs. Classifier `08004B6C` selects puzzle formatting for IDs 25/27;
ID 26 omits the floor line. Puzzle number 100 or a separate suppression flag
skips the whole card. These are native conditions, not PNG guesses.

The [verification report](../build/arrival-cards/verification.json) records a
normal-button Mysterious cave floor-one-to-two transition on the unchanged
English ROM `8757bf5c…e960`. All **3,649 nontransparent artwork pixels** match
the exported reconstruction exactly. Original title tiles and the entire
floor atlas also match native VRAM byte-for-byte, and watchpoints observe the
original pointer/palette readers. All 41 recorded source-resource ranges are
unchanged in that English ROM. This confirms the extraction method on one
natural card; it does not claim natural visitation of every selector.

## Reproduce and audition next

```sh
.venv/bin/python -m tools.extract_arrival_cards
.venv/bin/python -m tools.verify_arrival_cards
```

Extraction needs the pinned original, Pillow and the existing dungeon-name
catalog. The native verification additionally uses mGBA, the accepted English
ROM and recorded cave-clear checkpoints. Review captions use macOS Menlo;
that host font is not a proposed game font.

The reference workflow is GB2's `tools/arrival_card_audition.py` and
`tools/arrival_cards.py`, with GB1's `tools/floorcardgen.py` as the other
example. For Torneko 3, start the English audition from these indexed originals:
compare font/size/outline samples on the 240×160 canvas, then review the whole
name set before allocating and inserting replacement assets. ROM storage and
tile-budget changes must use the shared allocator and collision checks.

## Shiren lettering reference (2026-09-12)

The user nominated `../Shiren/shiren-revamp-fixes` as a possible source for
the rough, Papyrus-like arrival lettering under discussion. Its
`gfx/fonts/area_title_font.2bpp` contains the actual English title artwork.
[The decoded reference PNG](../build/arrival-cards/references/shiren-area-titles.png)
shows all 28 nonblank titles from its thirty title records.

Despite the filename, this asset is arranged as **pieces of rendered names**,
not a directly usable alphabet. `data/demos/demos.asm` supplies 194 chunk
pointers; `code/bank_05.asm` assembles the chunks into names. Each source chunk
is nine 8×8 SNES 2bpp tiles forming a 24×24 cell. The reference sheet preserves
those pixels, showing each name left aligned in white on black, enlarged 2×
without filtering. It does not reproduce the SNES screen placement or floor
number; Shiren loads its floor digits through the separate Kointai path.

No reusable TTF/OTF source or explicit Papyrus attribution was found in that
checkout. The visual resemblance is useful evidence for the desired style,
but does not identify the original typeface or its modifications. The
[subsequent reconstruction](ARRIVAL_AUDITION.md) recovers 43 source characters
and explicitly marks missing-character supplements and new spacing for review.

[The source manifest](../build/arrival-cards/references/shiren-source.json)
records the external files, hashes and all used bitmap spans. No Shiren file
or Torneko ROM changed, and no font choice or insertion was finalized.
Reproduce with:

```sh
.venv/bin/python -m tools.extract_shiren_arrival_reference
```
