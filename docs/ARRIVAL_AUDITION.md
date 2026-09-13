# Arrival lettering audition

[Open the audition studio](../build/arrival-cards/audition/index.html) in a web
browser. This self-contained HTML file works offline without a server or
installed fonts on the viewing computer.

On 2026-09-13 the user approved **Credits adapted** and requested insertion,
following an earlier preference for Rounded. The [completed insertion](ARRIVAL_INSERTION.md)
covers all 36 cards and matching floor lettering. The studio remains available
for review with its original defaults unchanged. The separate
[ending-credit studio](CREDITS_AUDITION.md) retains its original Rounded audition
default; the game's already-English ending credits themselves are unchanged.

- [Four starting styles: Credits is the fourth row](../build/arrival-cards/audition/arrival-audition-comparison.png)
- [All 36 Credits-style cards](../build/arrival-cards/audition/arrival-audition-credits.png)
- [Credits source/adaptation alphabet](../build/arrival-cards/audition/credits-alphabet-review.png)
- [Credits-style native-size example](../build/arrival-cards/audition/arrival-audition-credits-native.png)
- [All 36 Shiren-style cards](../build/arrival-cards/audition/arrival-audition-shiren.png)
- [Alphabet and marked supplements](../build/arrival-cards/audition/alphabet-review.png)
- [Native-size example](../build/arrival-cards/audition/arrival-audition-native.png)
- [Studio screenshot](../build/arrival-cards/audition/studio-preview.png)

## Review workflow

1. Start with the **Shiren**, **Papyrus**, **Rounded** or **Credits** preset. The font menu
   also offers Papyrus Regular separately from the narrower Condensed face.
2. Select any of the 36 cards. Compare the Japanese original, enlarged English
   preview and 240×160 native-size preview.
3. Adjust height, spacing, colour, outline, shadow and wrapping. Choose
   **Location title only** or **Location title + floor**. Floor lettering can
   match the candidate or retain the original coloured artwork.
4. Try black, captured dungeon and captured village backgrounds, with adjustable
   dimming. The village backdrop is a design preview; a separate native town
   arrival-card family remains unconfirmed.
5. Inspect the gallery. Long names wrap; a ` - ` section separator becomes the
   line break when needed. An explicit newline in the wording field overrides
   automatic wrapping. Wording edits affect only this card's audition, without
   changing the translation catalog. **Restore this name** removes the override.
6. Export a card at 1×/3× or the complete PNG sheet. Blank titles, unsupported
   characters and layouts outside the title area/screen are flagged and block
   their PNG export. Settings can still be saved while adjusting a draft.
   Guides appear only in previews.
7. **Save settings** downloads a JSON; **Load settings** resumes it. Keep the
   JSON with preferred PNGs to retain the font, size, positions, wording and
   rendered line breaks. Changes are not silently saved in browser storage.

[Default settings](../build/arrival-cards/audition/default-settings.json) are
included. Imports validate the Japanese-ROM, font-asset and renderer revisions,
field types, controls and card IDs. The exact earlier three-style revision
is also accepted: its existing font data and bitmap composition were preserved.
Unrecognized revisions are rejected. The
[archived earlier studio](../build/arrival-cards/audition/archive/three-styles/index.html)
and its original settings remain available.

[Credits preset settings](../build/arrival-cards/audition/credits-settings.json)
are exported separately; the studio's original Shiren defaults are unchanged.
Appending `?preset=credits` to the HTML URL starts directly with the fourth
candidate without locking a selection.

All 64 selectors retain their 36 asset identities. The arena omits its floor
number; puzzle cards use Q1–Q99. The interface auditions floors 1–99, excluding
the native puzzle-number-100 suppression event. The main Japanese title-screen
logo remains preserved, following the user's earlier decision.

## Reconstructed font

[arrival-candidates.json](../assets/fonts/arrival-candidates.json) contains four
reusable bitmap faces covering all 95 printable ASCII characters, with baseline
offsets, advances and four-level alpha rows.

The Shiren face has **43 recovered source characters**: 41 letters, apostrophe
and hyphen. They are exact crops of the decoded Shiren title strips. Automatic
extraction is limited to words whose isolated ink runs match their character
count. Thirteen reviewed boundaries are explicit in
[the reconstruction tool](../tools/reconstruct_arrival_font.py), including
touching/overhanging letters. Each crop records its PNG, hash and coordinates.

The source lacks capitals `A E H K Q X Y Z`, lowercase `j q x`, all digits and
most punctuation. The other **51 printable characters** use clearly marked
**Papyrus Condensed supplements** from the installed macOS font. One pixel of
horizontal weight and a binary threshold make their strokes sit closer to the
source bitmaps. Space has a separately chosen advance. These are draft
supplements, not recovered Shiren characters.

The alphabet proof marks supplements in amber; the studio lists those used by
each card. Matching floor numbers therefore use draft digits. The full Papyrus
Regular, Papyrus Condensed and Comic Sans MS comparison faces are rasterized
from the installed fonts. Source hashes and collection indexes are recorded;
the outline font files are not bundled.

Spacing is newly reconstructed for all faces. The Shiren typeface's identity
and original kerning are not established, and no candidate has final approval.
The font JSON is generated: change recovery choices in the reconstruction tool
before regenerating. Keep user wording/settings in exported audition JSONs;
regeneration does not modify those files.

## Validation and limits

[Browser verification](../build/arrival-cards/audition/verification.json) passes
77 grouped checks. It covers 36 cards ×4 presets ×4 floors (1, 9, 10, 99), plus
all 36 in title-only and original-floor modes. It exercises overflow/missing
glyphs, arena/puzzle rules, automatic/manual breaks, actual UI controls,
navigation, settings roundtrip, invalid import rejection and PNG dimensions.
PNG exports and HTML/font hashes are recorded. The studio screenshot, alphabet
and complete default sheet were visually reviewed.

The fourth candidate additionally checks its actual preset button, all-card
coverage without external glyph supplements, derived small-cap metadata,
settings roundtrip, known legacy settings and rejection of an unsupported
literal `@`. All 52 source glyph descriptors/bitmaps match the pinned ROM,
and all 78 derived glyphs pass metric/alpha checks. The Credits alphabet,
complete card sheet and four-style comparison were visually inspected.

These are artwork/browser checks. **No English arrival card has been inserted
into the GBA ROM.** Tile-pattern counts are preliminary display evidence, not
allocator reservations or a complete palette/storage/runtime proof. Custom
floor lettering/position may require renderer/atlas changes. After choosing a
direction, review supplements and layouts before implementing a combined,
collision-checked insertion.

No source ROM, accepted English ROM, external Shiren asset or save was changed.
The [memory map](MEMORY_MAP.md#arrival-font-reconstruction-and-offline-audition-2026-09-12)
records this distinction. Main title-logo and ending/credit artwork are outside
this audition, and the separate town-card family remains unconfirmed.

## Reproduce

With earlier extraction artifacts and native background captures present:

```sh
.venv/bin/python -m tools.reconstruct_arrival_font
.venv/bin/python -m tools.reconstruct_credits_arrival_font
.venv/bin/python -m tools.build_arrival_audition
.venv/bin/python -m tools.verify_arrival_audition
```

Regeneration uses Pillow and the installed macOS Papyrus/Comic Sans MS fonts.
The builder embeds all bitmaps/backgrounds in the HTML. Verification uses
installed Google Chrome in temporary headless profiles, exports PNGs/settings,
and closes its own browser processes. It does not use the user's usual Chrome
profile. Viewing the generated HTML needs only a modern browser.

## Fourth candidate: adapted credits lettering

The user requested a fourth arrival style based on the original credit font
on 2026-09-12. The complete underlying font table supplies every capital and
digit, including characters absent from the credit text itself. See the
[ending-credit review](CREDITS_AUDITION.md) for its original presentation.

[credits-arrival-candidate.json](../assets/fonts/credits-arrival-candidate.json)
is a separate authoring asset combined with the original four font faces by
the arrival builder. It supplies 78 inputs from **52 original-ROM glyphs**:
26 capitals, 26 derived small capitals, ten digits, space, 14 reviewed
punctuation marks and copyright. No external or partial-patch glyphs are used.

The large credits letters have a slanted shape with a blue/dark fringe; the
original lowercase slots contain a different upright small-cap design. This
adaptation uses the large design consistently, with 17-pixel capitals/digits
and 13-pixel small capitals for lowercase input. It removes the darkest fringe,
normalizes the remaining fill to four alpha levels, narrows the letters to 82%
of proportional width, and gives them new spacing. The preset displays this
mask in warm white with a small shadow. It is a modified display alphabet,
not a claim to have found conventional lowercase letters in the ROM.

The original copyright slot is explicitly mapped to `©`. Literal `@` and
the original box-shaped `_` slot are omitted to avoid showing the wrong symbol;
unsupported inputs produce the studio's usual missing-glyph warning. All
current arrival names, floor numbers and F/Q suffixes are covered.

Source byte ranges, transformations and hashes are recorded in the asset and
[memory map](MEMORY_MAP.md#credits-derived-arrival-font-candidate-2026-09-12).
The original shared font JSON, existing three styles, and ending-credit studio
remain unchanged. On 2026-09-13 this fourth option became the approved style;
the [frozen approval](../assets/arrival-cards/approved.json) and
[insertion report](ARRIVAL_INSERTION.md) record its exact settings and native
validation. Editing an audition does not silently update the inserted artwork.
