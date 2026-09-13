# Title-screen artwork audition

On 2026-09-13 the user requested an English title-screen proposal and an
audition process, following acceptance of the four screenshot fixes. This
reopened the earlier decision to retain the Japanese title **for artwork review**.
The user then approved Stone & gold and requested insertion, now complete in
the [cumulative build](TITLE_INSERTION.md). The studio preserves the approved
audition colours and settings separately from the game's native tile/palette
conversion. Its 29 browser checks still pass; older settings remain compatible.
The prose second pass awaits a separate go-ahead under the user's staged workflow.

[Open the offline title studio](../build/title-audition/index.html).
It works directly from disk without a server, external fonts or network calls.

- [Original/proposal comparison PNG](../build/title-audition/title-comparison.png)
- [English proposal at actual 240×160 size](../build/title-audition/title-english-native.png)
- [English proposal enlarged 4×](../build/title-audition/title-english-4x.png)
- [Studio screenshot](../build/title-audition/studio-preview.png)
- [Original generated artwork](../assets/title-screen/stone-gold-v1.png)
- [Exact generation prompt](../assets/title-screen/stone-gold-v1-prompt.txt)

## Proposed wording and direction

**Dragon Quest Characters: Torneko's Great Adventure 3 Advance — Mystery Dungeon**

This is an independent rendering of the Japanese logo, not a claim that the
GBA game received an official English title.

| Japanese lettering | Proposed English |
|---|---|
| ドラゴンクエスト キャラクターズ | Dragon Quest Characters |
| トルネコの大冒険3 | Torneko's Great Adventure 3 |
| アドバンス | Advance |
| 不思議のダンジョン | Mystery Dungeon |

Draft **Stone & gold** keeps the illustrated stone-scroll idea, large gold
Torneko lettering, prominent orange 3 and blue Advance accent. The subtitle
and series label sit in smaller stone bands. This follows the original title's
art direction; the separately approved Credits-adapted arrival lettering is
unchanged. Review the small bands at native size before selecting the design.

The built-in `image_gen` tool produced one 1536×1024 artwork draft using the
original title screenshot as its edit reference. It redraws the illustrated
scroll, crest and surrounding ocean. It does **not** preserve all original
pixels. The default browser preview restores the exact original bottom
18 screen rows, including the English `PUSH START BUTTON` prompt. This static
composition does not emulate prompt blinking or background animation.

The project-local [candidate manifest](../assets/title-screen/candidate.json)
records the original-ROM identity, image/prompt/reference hashes, proposal
status and default preview settings. The separate
[frozen approval](../assets/title-screen/approved.json) pins the accepted raster
and its original browser report. No partial fan-translation art or font
was used. The prompt's original screenshot was already pixel-identical to the
Japanese title; fresh Japanese/pre-title-baseline captures also match.

## Audition workflow

1. Compare the original and proposal side by side or with the comparison slider.
   The two native-size canvases remain available below the enlarged view.
2. Start with **Area average** reduction and **GBA colour depth**, the defaults.
   Nearest-pixel reduction gives harder edges. Full concept colours and closest
   original title colours are additional design previews.
3. Toggle the original start-prompt strip to compare it with the generated
   draft's footer. The default retains the original prompt.
4. Write review notes. **Import artwork PNG** accepts an opaque 3:2 PNG from
   240×160 up to 4096 pixels per side, so an artist can supply a later revision.
   Importing never uploads the artwork to a service.
5. Export the native PNG, 4× PNG or comparison sheet. **Save audition** downloads
   settings, notes and any imported artwork together as JSON. **Load audition**
   restores them after validating the source, artwork and renderer revisions.
   Nothing is silently persisted in browser storage.

Reset preview controls retains notes and imported artwork. Failed imports
leave the active draft unchanged. An imported full-screen image must be opaque;
the source ocean has holes behind the logo, so a transparent logo alone is not
a complete replacement screen. See [the original boot audit](BOOT_GRAPHICS.md).

## Validation and limits

[Browser verification](../build/title-audition/verification.json) passes 29
checks: both sampling methods and all three colour modes, five-bit channel
conversion, original palette membership, exact original/prompt pixels,
settings and imported-PNG roundtrips, invalid revision/type/image rejection,
slider endpoints, reset behavior and exported PNG dimensions.

Area averaging uses explicit weighted source-pixel coverage before any colour
conversion. Enlargement uses nearest-neighbour pixels. The enlarged preview
therefore displays the same 240×160 artwork as the native PNG, rather than
hiding small-screen limitations behind the generated high-resolution image.

The [fresh reference provenance](../build/title-audition/reference/provenance.json)
cold-boots the pinned Japanese ROM and preserved rendering-fix ROM for 600 frames
with no buttons, forced entry or RAM edits. Native map/tile copies and all four
boot selections pass; title pixels are identical. That comparison checkpoint is
`fd0c0dd97ffd205bcc4ba71711c76edcc6f33dad912731d7d9d629188414ace8`.
ROMs and user save/state files are hash-checked unchanged by the audition tools.
Using this preserved checkpoint keeps the studio reproducible after the latest
English build displays the localized title.

These are artwork and browser checks. Five-bit RGB conversion does not prove
the draft can use the existing 4bpp tile/palette layout. The original-colour
option picks the nearest colour from the captured palette globally; it does
not enforce palette-bank assignment per tile. The redrawn crest, fine edges,
small text and transition from the retained prompt strip may benefit from
pixel cleanup in a later art pass. The approved version's native palette/tile
packing, prompt animation, background composition and collision-checked
insertion now pass in the [separate insertion report](TITLE_INSERTION.md).

## Ownership and reproduction

This is read-only ROM research plus project-local art and tooling. The existing
title resource ranges are indexed in [MEMORY_MAP.md](MEMORY_MAP.md); no new ROM,
RAM or save space is allocated or released. The title remains outside the
9,318-entry ordinary text inventory, whose counts do not change.

```sh
.venv/bin/python -m tools.capture_title_audition
.venv/bin/python -m tools.build_title_audition
.venv/bin/python -m tools.verify_title_audition
```

The candidate PNG and prompt are versioned source assets. Rebuilding the page
does not call image generation again. The verification harness uses a temporary
headless Chrome profile and exports images/settings into `build/title-audition/`;
it never opens the user's ordinary browser profile. macOS Chrome may require
execution outside the filesystem sandbox, as with the earlier audition tools.

The [build manifest](../build/title-audition/build.json) pins image and tool
hashes. Preserve user-exported JSONs when revising the studio; incompatible
renderer revisions are rejected instead of silently changing an audition.
