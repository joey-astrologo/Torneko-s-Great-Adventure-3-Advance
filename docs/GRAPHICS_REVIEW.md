# Remaining scene graphics review

Step 1 of the agreed follow-up is complete (2026-09-13): **102 scene-table
backgrounds, 73 distinct graphics sets and all 194 tile-animation frames**
are exported and checked against the original game's native loader.
No additional confidently readable Japanese lettering or separate town-name
card was identified in this family. This is bounded coverage, not proof that
every graphic in the ROM has been found.

The final **END** artwork is already English in the Japanese original, as are
the **INN** signs examined here. Six small details are preserved separately:
the cake plaque, a gold wall panel, hanging paper, an inn sign, an outside sign
and a room notice. Some contain lettering-like marks that cannot be reliably
transcribed at GBA resolution. They are review leads, not six established
missing translations and not additions to the 74 unresolved text candidates.

## Review images

- [Open the full graphics gallery](../build/graphics-review/index.html)
- [Ending backgrounds and END artwork](../build/graphics-review/ending-backgrounds.png)
- [Small signs and lettering-like details, 6×](../build/graphics-review/small-details.png)
- Scene overview pages: [000–023](../build/graphics-review/scenes-page-1.png),
  [024–047](../build/graphics-review/scenes-page-2.png),
  [048–071](../build/graphics-review/scenes-page-3.png),
  [072–095](../build/graphics-review/scenes-page-4.png),
  [096–101](../build/graphics-review/scenes-page-5.png).
- Animated metatile frames: [1](../build/graphics-review/animations-page-1.png),
  [2](../build/graphics-review/animations-page-2.png),
  [3](../build/graphics-review/animations-page-3.png),
  [4](../build/graphics-review/animations-page-4.png),
  [5](../build/graphics-review/animations-page-5.png),
  [6](../build/graphics-review/animations-page-6.png),
  [7](../build/graphics-review/animations-page-7.png).

Individual PNGs preserve source pixels at native size. Overview sheets reduce
large maps to fit; the detail sheet uses nearest-neighbour enlargement. These
are decoded background layers, including offscreen layouts, rather than
screenshots of every scene. Actors, object overlays, camera placement and
runtime colour/fade effects are separate. Static composites use base palettes
and the first tile-animation frame; the animation sheets separately cover
every frame's changing metatiles.

## Ending associations

The existing credit text export covered only its 31 text cards. The surrounding
script explicitly loads these five background scene IDs through opcode `03`:

| Command ROM offset | Scene | Visible background |
| --- | --- | --- |
| `0091D628` | 9 | Castle throne-room interior |
| `0091D7C0` | 56 | Room with bookshelves and a purple table covering |
| `0091D9A8` | 83 | Tower exterior |
| `0091DD08` | 31 | Town streets and buildings |
| `0091DD78` | 101 | Separate English END artwork |

These descriptions identify the pictures, not newly chosen localized place
names. Script association follows the original eight-byte commands and native
dispatcher `08065152`, which calls scene loader `08066FE4` at `080651A8`.
This pass does not play the complete ending, verify its timing or compose
all its actors and overlays. That remains the separately proposed step 2.

## Source and validation

Source is the pinned Japanese ROM `35bfff00…4d02`. No fan-patch art or English
was used. The accepted [arrival-card ROM](ARRIVAL_INSERTION.md), SHA256
`08239b255025e6e2627ec0184eb829cb453dc30b0aa7a518e7e8714fc678f2c6`,
is unchanged. All recorded background-resource bytes also match that build.
The main Japanese title-screen logo remains intentionally retained.

The [scene manifest](../build/graphics-review/scene-manifest.json) records
all selectors, headers, dimensions, palettes, tile and metatile spans, exact
compressed-stream ends, animation records, frame sources and PNG hashes.
The [range and detail report](../build/graphics-review/resource-ranges.json)
consolidates **1,104 existing source-range records** and records each detail
crop's contributing tile offsets, map words, palette banks and layer placement.
The [memory map](MEMORY_MAP.md#complete-scene-background-review-2026-09-13)
indexes these occupied resources. None is approved for reuse or patching.

[Native verification](../build/graphics-review/native-verification.json) restores
a disposable fixture for each scene and executes original game instructions.
All 102 cases match both complete RLE/XOR map planes, all metatile definitions
and padding, the complete static VRAM tile region, and native palette staging.
All 194 tile-animation frames match native frame selection, metatile-attribute
updates and tile uploads, with adjacent VRAM intact. The surrounding buffers,
profile and save checks pass. Animation timer pacing and palette cycling are
outside these bounded fixtures.

The visual review inspected five scene overview sheets, seven animation sheets
and selected full-size details. It found no additional readable Japanese
phrases; tiny decorative marks remain explicitly untranscribed. A complete
sprite/object-art inventory, other graphics loaders and natural first-visit
town/ending coverage remain open. Earlier shrine/inn routes and this table
review do not prove universal absence of town arrival cards.

The [acceptance report](../build/graphics-review/acceptance.json) pins the
reports and review artifacts. This step neither changes the ROM nor performs
the separately proposed full-credits or current-build regression passes.

```sh
.venv/bin/python -m tools.extract_scene_review
.venv/bin/python -m tools.verify_scene_review
.venv/bin/python -m tools.summarize_graphics_review
```
