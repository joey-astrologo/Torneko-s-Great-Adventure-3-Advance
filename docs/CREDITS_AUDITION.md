# Ending-credit lettering audition

The Japanese original already uses English for the credit title cards, staff
roles, names and copyright. This pass exports **31 text cards**, with 140
positioned references to 139 distinct strings. Five opening strings expand the
earlier audit of 134 staff/copyright sources. None are fan-patch English or new
translations; the translation inventory counts remain unchanged.

The original credit font now also supplies a fourth
[arrival-card candidate](ARRIVAL_AUDITION.md#fourth-candidate-adapted-credits-lettering).
Its modified capitals/small capitals are a separate audition asset; the
ending-credit studio and original credit resources remain unchanged.

- [Original credit cards, 2× PNG](../build/credits/credits-original.png)
- [Original cards at 1×](../build/credits/credits-original-1x.png)
- [Font comparisons, including dense staff pages](../build/credits/audition/credits-comparison.png)
- [Open the offline credits studio](../build/credits/audition/index.html)
- [All 31 Rounded audition cards](../build/credits/audition/credits-audition-rounded.png)
- [Studio screenshot](../build/credits/audition/studio-preview.png)

These show the isolated text layer on black. The original tile buffers match
native game rendering; the fully visible colours are reconstructed from the
original palette. They are **not screenshots of a natural ending playthrough**.
Scene illustrations, fade timing, and any separate ending artwork are outside
this export. This does not establish that every ending graphic lacks Japanese.
The subsequent [scene-graphics review](GRAPHICS_REVIEW.md) separately exports
the five background scenes selected around these credits, including the
already-English END artwork. Its native decoder checks cover the source
backgrounds; complete ending playback, fades and actor/object overlays remain
outside that pass.

## Audition workflow

Open the HTML in a browser; it is self-contained and works offline. It starts
with **Rounded**, following the user's preference for the arrival-card audition
on 2026-09-12. This is a starting candidate, not a final selection.

1. Compare the original and candidate, then inspect the native 240×160 preview.
   Select any of the 31 cards from the gallery or use Previous/Next.
2. Try Rounded, Rounded with small staff names, Papyrus Condensed, or the
   recovered Shiren lettering. Font selectors also offer Papyrus Regular and
   the original small font. Roles/titles and names can use different faces.
3. Adjust role, name and introductory-title heights independently. Compare
   original positions or centred lines, letter spacing, vertical spacing,
   colours, and crisp/soft edges. Original row baselines remain the starting
   layout; this audition does not silently shrink or wrap crowded lines.
4. The original decorative font renders lowercase role bytes as small capitals.
   The default comparison keeps that visual convention; the Roles control can
   instead show the lowercase source spelling. Names and copyright remain
   unchanged. The introductory title is the original credit text, not a
   replacement for the main title-screen logo.
5. Export individual cards at 1×/3×, the complete sheet, or the preset comparison
   sheet. Out-of-area text, overlapping line pixels and missing glyphs are
   flagged. Invalid candidate cards cannot be exported individually, and a
   complete-sheet export requires all 31 to fit. The preset comparison always
   shows its labelled starting styles, independently of current controls.
6. Save settings to JSON to retain the audition and rendered line positions.
   Load settings resumes them after validating ROM, combined font and renderer
   hashes and field types/ranges. Changes are not automatically persisted.

Rounded is more readable than the thin Papyrus and downscaled Shiren samples
on these dense pages. Keeping the original credits styling is also viable:
there is no missing English translation in this specific family. These are
visual observations, not a font decision. The native-size view is the useful
test; enlarged sheets can make very fine strokes look more convincing.

## Sources and native verification

[The manifest](../build/credits/manifest.json) records the exact command bytes,
source starts and exclusive ends, font descriptor/bitmap ranges, palette,
window descriptor and per-line coordinates. The central
[memory map](MEMORY_MAP.md#font-assets-and-inspected-code) records these occupied
ranges and the fixture's RAM usage. No source gaps have been approved for reuse.

The credit reader chooses **font 2**, a 12-row decorative font, and palette
`00CA178C`. It uses a 208×136 window at screen (16,16). Signed x selects native
centering; negative y adds relative vertical spacing. The existing queue has
16 slots; the largest card here uses eight. All cards are bounded by the
original `00281B2E` presentation command in this reviewed script span.

The byte `@` draws **©** in font 2. The readable manifest and candidate cards
preserve that symbol. Candidates use a marked monochrome derivative of this
original symbol; it is not replaced with a literal at sign or lost during font
switching. The Shiren face's missing letters remain marked Papyrus supplements,
as documented in [the arrival-font reconstruction](ARRIVAL_AUDITION.md).
All comparison art is generated from pinned bitmap data without depending on
browser-installed fonts. No outline font is bundled.

[Native verification](../build/credits/native-verification.json) passes all 31
cards, 140 original command references and **1,971 glyphs**. Each page restores
the original-ROM fixture, queues its actual source commands, and executes the
original setup and draw instructions. It checks glyph identity, font, spacing,
all coordinates, queue consumption and every decoded text-buffer pixel against
independent extraction. Native palette staging also matches the original 16
packed words. The fixture skips full ending fades, palette upload timing and
scene transitions; it is not natural gameplay reachability evidence.

[Browser verification](../build/credits/audition/verification.json) passes 24
grouped checks, including all 31 cards in all four presets (124 layouts),
alternative alignment/case, crowding and missing-glyph failures, copyright,
actual controls, settings roundtrip/rejection, PNG sizes and guide exclusion.
The comparison sheet and studio screenshot were visually inspected.

## Reproduction and status

```sh
.venv/bin/python -m tools.extract_credits
.venv/bin/python -m tools.verify_credits
.venv/bin/python -m tools.build_credits_audition
.venv/bin/python -m tools.verify_credits_audition
```

The native verifier uses the disposable original fixture
`build/story-provenance/natural/final.state`. Font packaging uses the existing
`assets/fonts/arrival-candidates.json`. Chrome verification uses a temporary
profile and saves the default PNG exports; it does not open a personal profile.
Generators and JSON reports identify their inputs and hashes.

**This ending-credit audition made no ROM insertion, translation change,
permanent RAM allocation or persistent save edit.** The Japanese-original SHA-256 remains
`35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02`;
the English ROM used for that audition was
`8757bf5cd89e6b935c8f99c431600eb6b5367ad9e9078158a84c047cf6d6e960`.
The subsequent [arrival insertion](ARRIVAL_INSERTION.md) uses the approved
Credits-adapted style for dungeon cards and floor lettering. It does not alter
these original ending credits or this studio's saved defaults.
The main Japanese title logo remains preserved; separate town-card and ending
illustration discovery remains open.
