# Approved English title insertion

The user approved **Stone & gold** and requested build integration on
2026-09-13. The English title is now included by `./build.sh` in the cumulative
[ROM](../build/torneko-3-english.gba) and [BPS patch](../build/torneko-3-english.bps).

Accepted ROM SHA256:
`b80feb1177c9111f44edb1b0ffc8a63c89d94b7d4eccc9f383bc9b372d7b14a9`.
The 905,830-byte BPS applies to the pinned Japanese original and reproduces
the complete 32 MiB English ROM byte for byte.

[Approved audition versus actual game capture](../build/title-insertion/approval-vs-game.png)
shows the palette conversion. Native screenshots are also available with the
start prompt [visible](../build/title-insertion/verification/english-user-save/prompt-on.png)
and [hidden](../build/title-insertion/verification/english-user-save/prompt-off.png).

## Frozen artwork and native format

[approved.json](../assets/title-screen/approved.json) records the user's approval,
the displayed native raster, source/artwork hashes and original audition
settings. [approved.png](../assets/title-screen/approved.png) is the exact
240×160 image approved before tile conversion. The
[archived audition checks](../assets/title-screen/approved-audition-verification.json)
preserve the report referenced by that approval. Rebuilding never calls image
generation or takes unsaved browser edits as approved artwork.

The source image contains 2,797 RGB colours. The native title uses 4bpp tiles,
so each cell can select only one 16-entry palette, with index zero transparent.
The compiler assigns the upper 540 screen cells to 13 palette banks, each with
up to 15 opaque colours. It uses deterministic tile-colour clustering and
palette refinement, then packs the resulting indices into native patterns.
It adds no lettering, font substitutions or wording changes.

The resulting image has small colour differences from the audition: mean
absolute RGB error is 5.66 on the 0–255 channel scale, RMS error 8.91. The
linked comparison shows the actual result. These are measurement summaries,
not a claim of pixel identity to the higher-colour audition.

Original ocean bank 13 and prompt bank 14 are copied exactly; the separate
native font bank 15 remains unchanged. The original ocean map and all its
referenced patterns are retained. Foreground rows 18/19 retain the original
prompt cells, with their tile IDs updated by the packer. The bottom 16 visible
rows therefore remain pixel-identical in both prompt phases. The top 144 rows
contain the approved image, including its redrawn ocean and the two retained
audition-strip rows at Y142/143 after palette conversion.

The packed resource has 752 tile patterns: 218 retained patterns, including
the blank tile, and 534 new patterns. It fits the native title's BG character
area. The existing loader, fade and blink code are used without modification.
Only the title record's two pointers and tile count change: one checked
12-byte ROM patch. The original maps, tiles, palette and mode field remain
protected. There is no RAM or save-format change.

## Native verification

[Native verification](../build/title-insertion/native-verification.json) runs
the previous rendering-fix ROM and new title ROM with both an empty save and
a disposable copy of the user's existing save: four natural boot routes.
The harness uses normal frames/buttons, without forced CPU entry or altered
gameplay state. It verifies:

- Exact native map/tile copies and full-bright palette values; guards before
  the tile upload and through the remaining BG VRAM stay unchanged.
- All 240×160 rendered title pixels match the packed-resource decode.
- All 17 native fade values, both prompt phases and 121 consecutive blink
  frames per route: 484 checked frames, with identical old/new prompt timing.
- The prompt's cached 128 bytes remain intact while the original loop clears
  and restores its map rows.
- Start enters the illustrated main menu. An empty save can enter Settings;
  the existing save can enter Records. Both return to the main menu normally.
  These transitions and the earlier boot screens produce 22 unchanged image
  pairs across the two save profiles.
- The disposable existing save and all four user save/state files stay
  unchanged. Earlier cumulative allocations, patches and RAM ownership remain
  intact; the complete new ROM contains only the planned title changes.

The original code's `080877C8` routine encompasses the entire boot sequence;
the blink branches are inside it at `08087864` and `080878B0`. Returning from
Records goes to the illustrated main menu, not back to the title logo. The
fixtures follow these actual native paths. Broader gameplay checks retain
their separately documented ROM hashes and scope.

[acceptance.json](../build/title-insertion/acceptance.json) ties the source,
output, approval, packing, runtime and whole-image ownership checks together.

## Build and ownership

`tools.build_title_art` composes the existing `tools.build_rendering_fixes`
component through the same `RomBuild` allocator. The new resources occupy
29,120 appended bytes in two allocations. The complete ledger has 8,483
allocations and 10,122 checked original patch records, using 1,160,336 appended
bytes with 15,616,880 bytes remaining in the 32 MiB image.

Exact ROM/VRAM ranges and original reader evidence were recorded in
[MEMORY_MAP.md](MEMORY_MAP.md) before insertion. Machine-readable authorities
are [allocation-plan.json](../build/title-insertion/allocation-plan.json),
[packing.json](../build/title-insertion/packing.json) and the cumulative
[english-build.json](../build/title-insertion/english-build.json).

Normal rebuilding:

```sh
./build.sh
```

To regenerate the title component and its evidence from the frozen approval:

```sh
.venv/bin/python -m tools.pack_title_art
.venv/bin/python -m tools.build_title_art --prepare
# Document any changed ranges before insertion.
.venv/bin/python -m tools.build_title_art
.venv/bin/python -m tools.verify_title_art
.venv/bin/python -m tools.summarize_title_art
./build.sh
```

Existing prepared resources and earlier checkpoints are required as described
in [BUILD.md](BUILD.md). The [audition studio](TITLE_AUDITION.md) remains usable;
its original reference now explicitly uses the preserved rendering-fix
checkpoint so regeneration still works after the latest title becomes English.
Its renderer/settings revision is unchanged. Audition edits do not modify the
frozen build artwork.

This completes the approved title insertion. The prose second pass awaits the
user's next confirmation under the agreed staged workflow.
