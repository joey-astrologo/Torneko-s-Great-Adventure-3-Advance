# Original Latin font review

Verified and selected by the owner on 2026-09-09. **Font 0, the original small
12-row variant, is the chosen baseline for English text.** It has variable widths, intact
descenders, and works in the tested menu, message, and story renderers.
Use its existing glyphs and advances for translation builds and width checks.

Open the interactive comparison in a browser:

```bash
open build/font-review/index.html
```

The page includes native 240 × 160 game screenshots, optional 2×/3× integer
scaling, all printable ASCII glyphs, and a live line-width preview. It embeds
its images and glyph data and works offline. The assets come from the Japanese
original. The fan translation is not a source for any text, glyph, or build here.

## The three identified variants

| Font | Rows drawn | Printable ASCII advances | Assessment |
|---|---:|---:|---|
| 0: small | 12 | 3–7 px | Selected English baseline |
| 1: small | 10 | 3–7 px | Same Latin bitmaps and widths as font 0, with the bottom two rows omitted |
| 2: decorative | 12 | 3–13 px | Wider, stylized lettering; many glyphs contain palette indices rather than a monochrome mask |

All three tables contain entries for ASCII `20..7E`: 95 characters including
space. That does not mean all 95 bytes can be inserted literally into every
text path: `$` and the backtick have reader-specific meanings.

**Font 1 does not save horizontal space.** Its entire 72-byte stored bitmap for
each printable ASCII character matches font 0. The renderer's shorter row count
removes pixels from 21 characters, including `g`, `j`, `p`, `q`, `y`, the comma,
underscore, and several punctuation marks. The native screenshots show this
loss. It is not a separate, shorter Latin design with redrawn descenders.

Font 2 is forced into the existing text windows for comparison. Its colored
glyphs use those windows' palette, producing the multicolored output shown in
the captures. Its intended palette and normal usage have not been established.
These images demonstrate its behavior as a substitution in these windows, not
a reconstruction of its intended appearance. Using it for body text would
require palette and layout work as well as an aesthetic decision.

## Measured advances

Values below are cursor advances with the observed additional letter spacing
of zero. They include spaces.

| Sample | Font 0 | Font 1 | Font 2 |
|---|---:|---:|---:|
| `New game` | 46 px | 46 px | 66 px |
| `Settings` | 39 px | 39 px | 57 px |
| `Start adventure` | 78 px | 78 px | 110 px |
| `Game settings` | 67 px | 67 px | 97 px |
| `Adventure log` | 64 px | 64 px | 99 px |
| `The quick brown fox jumps` | 129 px | 129 px | 192 px |
| `Torneko was a merchant.` | 123 px | 123 px | 176 px |

Examples in font 0: `i` and `l` advance 3 pixels, digits advance 5, `A` and `B`
advance 6, `m` and `w` advance 7, and a space advances 5. Widths should be
measured in pixels, not approximated with a single character-count limit.

[font_metrics.py](../tools/font_metrics.py) records both cursor advance and
the visible right edge. Those values can differ; trailing spaces advance the
cursor without drawing, and glyphs can have overhang. Its plain-ASCII measuring
helper rejects control-sensitive characters and unsupported text rather than
pretending to interpret the game's formatting language.

## Widths of the captured windows

These measurements come from the live window descriptors and glyph positions,
not from estimating the border in a screenshot.

| Context | Window origin on screen | Window width | Observed text placement |
|---|---|---:|---|
| Review title menu | `(24, 16)` | 80 px | Labels start at local x=4, leaving 76 px to the right edge |
| New-save message window | `(16, 120)` | 208 px | Lines start at local x=0 |
| Opening story | `(16, 64)` | 208 px | `$c` centers each line according to its measured advance |

These are bounds for these specific layouts. Other menus, alignment modes,
icons, and margins need their own measurements. The earlier title proof's
86-pixel assertion was a coarse test bound, not a measured general layout
budget. The review page uses the window measurements above.

For the story, the observed starting x coordinate is
`floor((208 - line_advance) / 2)`. The same 129-pixel sample begins at x=39
with font 0, while its 192-pixel decorative equivalent begins at x=8.
The message and story examples use three lines spaced 12 pixels apart.
All review samples fit the measured window bounds.

## Extraction and native verification

| Font | GBA descriptor-table address | Entries | Rows |
|---|---|---:|---:|
| 0 | `0x08C93B4C` | 1,345 | 12 |
| 1 | `0x08C9E5CC` | 382 | 10 |
| 2 | `0x08CA1300` | 97 | 12 |

The booted game supplies these tables at RAM `0x020398EC`, counts at
`0x02039900`, and row counts at `0x02039910`. The active font is at
`0x020398F8`; additional signed letter spacing is at `0x020398DC`.
The review checks those metadata values against the original ROM.

The relevant 12-byte glyph descriptor fields are the bitmap pointer at `+0`,
character code at `+4`, signed advance at `+6`, and the precolored-bitmap flag
at `+10`. Each stored bitmap uses 72 bytes: twelve rows of six bytes, with
twelve 4-bit pixels per row, low nibble first. The renderer reads only the
active font's row count. Other descriptor fields remain uninterpreted here.

[review_fonts.py](../tools/review_fonts.py) creates a separate expanded ROM
containing independently written review labels and a pangram. It changes four
text pointers, preserves their original strings, and leaves every original
font byte intact. The menu reads appended strings; the message and story paths
format their appended sources into RAM as established in [TEXT_SYSTEMS.md](TEXT_SYSTEMS.md).

For each of the three variants, the verifier captures a menu, a message window,
and a story page. During the target scene, a debugger callback selects the
requested existing font at glyph lookup, including story width calculations.
It checks the actual glyph sequence, descriptor addresses, advances, per-letter
cursor movement, zero extra spacing, line bounds, and story centering.

The native story captures are also reconstructed from extracted glyph pixels,
recorded positions, and background palette bank 15. **All three reconstructed
frames match their mGBA screenshots pixel for pixel.** This checks bitmap
orientation, palette conversion, draw height, and the previews' pixel source.

Nine scene captures passed their runtime checks. All **27 unit tests passed**,
including five new tests for spaces, overhang, extra spacing, empty lines, and
control-sensitive input. The review page's width, overflow, unsupported-input,
and integer-scale logic passed checks in JavaScriptCore. A headless Chrome
launch aborted in this environment, so browser layout and interactions were
not verified through browser automation. Native screenshots were visually reviewed.

## Reproduce and inspect

The story route uses the pinned save created during the previous milestone.
If it is missing, recreate it first:

```bash
.venv/bin/python -m tools.verify_text_relocation
```

Then generate the review:

```bash
.venv/bin/python -m tools.review_fonts
.venv/bin/python -m unittest discover -s tests -v
open build/font-review/index.html
```

The generator accepts an explicit Japanese ROM path as its first argument and
an `--output` directory. It requires the verified Japanese original hash.

| Artifact in `build/font-review/` | Contents |
|---|---|
| `index.html` | Offline interactive review page |
| `metrics.json` | Glyph pixels, metrics, metadata, comparisons, and build allocations |
| `advances.tsv` | All 95 ASCII advances for all three fonts |
| `font-0-atlas.png`, `font-1-atlas.png`, `font-2-atlas.png` | Glyph sheets; labels are hex code:advance |
| `font-N/{menu,message,story}/` | Native screenshots and detailed capture reports |
| `torneko3-font-review.gba` | English review text using the game's normal font selection |

The ROM alone does not reproduce the forced font-1/font-2 comparisons; those
are emulator experiments generated by the Python tool. It is a review build,
not a translation patch, and its allocation addresses are independent of the
other proof builds. Both supplied ROMs remain untouched.

Review-ROM SHA-256:

```text
0259f3ee17bcfc24a94451987489ed2433d9fc9920f998cb3fc0b8454a84b0f6
```

## Selected font and next work

The owner approved font 0 after reviewing the comparison. Keep its existing
bitmaps and advances as the English baseline. The subsequent
[catalog and reinsertion milestone](TRANSLATION_PIPELINE.md) now verifies 27
translated menu, settings, message, and story entries with shared allocation
and font-0 width checks. The Japanese round trip preserves every original byte;
the English batch passes native rendering and save/load checks without forcing
the active font.
The [early-menu results](EARLY_MENUS.md) include measured menu contraction and
confirm that the naming keyboard normally selects font 1; that interface is
outside the 27-entry English batch. The separate [name-entry proof](NAME_ENTRY.md)
now uses font 0 for the Latin keyboard and seven-character field. Both keyboard
pages pass native checks for font selection, glyph bounds, and overlapping ink.

Before treating widths as project-wide guarantees, expand layout coverage,
extend control/substitution coverage beyond the first batch, and address
Latin text in contexts that normally select the 10-row variant. Accents and
typographic punctuation beyond printable ASCII were not audited in this pass.
