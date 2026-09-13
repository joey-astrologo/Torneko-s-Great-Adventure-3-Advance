# Arrival lettering audition

[Open the audition studio](../build/arrival-cards/audition/index.html) in a web
browser. This self-contained HTML file works offline without a server or
installed fonts on the viewing computer.

- [Three starting styles](../build/arrival-cards/audition/arrival-audition-comparison.png)
- [All 36 Shiren-style cards](../build/arrival-cards/audition/arrival-audition-shiren.png)
- [Alphabet and marked supplements](../build/arrival-cards/audition/alphabet-review.png)
- [Native-size example](../build/arrival-cards/audition/arrival-audition-native.png)
- [Studio screenshot](../build/arrival-cards/audition/studio-preview.png)

## Review workflow

1. Start with the **Shiren**, **Papyrus** or **Rounded** preset. The font menu
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
field types, controls and card IDs. A different revision is rejected rather
than quietly producing different artwork.

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
66 grouped checks. It covers 36 cards ×3 presets ×4 floors (1, 9, 10, 99), plus
all 36 in title-only and original-floor modes. It exercises overflow/missing
glyphs, arena/puzzle rules, automatic/manual breaks, actual UI controls,
navigation, settings roundtrip, invalid import rejection and PNG dimensions.
PNG exports and HTML/font hashes are recorded. The studio screenshot, alphabet
and complete default sheet were visually reviewed.

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
.venv/bin/python -m tools.build_arrival_audition
.venv/bin/python -m tools.verify_arrival_audition
```

Regeneration uses Pillow and the installed macOS Papyrus/Comic Sans MS fonts.
The builder embeds all bitmaps/backgrounds in the HTML. Verification uses
installed Google Chrome in temporary headless profiles, exports PNGs/settings,
and closes its own browser processes. It does not use the user's usual Chrome
profile. Viewing the generated HTML needs only a modern browser.
