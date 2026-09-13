# Credits-adapted arrival cards

The later [compact layout](ARRIVAL_LAYOUT.md) now centres the name/floor group
and reduces their visible gap to 7–8px. It preserves every approved raster and
passes fresh native constructor/transition checks. Positions and ROM hashes
below describe the original insertion checkpoint.

On 2026-09-13 the user approved **Credits adapted** and requested insertion.
The frozen [approval](../assets/arrival-cards/approved.json) pins the audition
renderer/font revisions, all 36 English titles and their 64 selectors, cream
lettering, 17px title height, one-pixel shadow, and matching centered 22px
floor lettering at y=100. The main Japanese title-screen logo remains intact;
this does not change the already-English ending credits.

The approved browser renderer exports the exact title rasters and floor lines.
The packer converts those into indexed GBA tiles with a shared 16-entry palette.
Only 12 colours are needed after RGB555 conversion. No additional colour
reduction is necessary. All title and floor resources fit their existing
160-tile slots; the extension retains the native constructor's upload, fades,
arena title-only rule and puzzle-100/suppression-flag branches.

Pre-rendered proportional floor lines cover every byte value (0–255) for both
ordinary and puzzle style. This avoids variable-width layout code or a new
runtime font buffer. Values above 99 are defensive coverage, not a claim about
natural dungeon depth. The added 696,254 bytes are allocated after the current
English build, leaving the original assets intact. There are no new save fields
or permanent RAM allocations. The shared allocator checks the entire cumulative
build, original-byte preconditions, collisions and alignment.

See [MEMORY_MAP.md](MEMORY_MAP.md#approved-credits-adapted-arrival-insertion-2026-09-13)
and the [allocation plan](../build/completion/arrival-credits/allocation-plan.json).

Accepted cumulative English ROM:
[torneko3-arrival-credits-english.gba](../build/completion/arrival-credits/torneko3-arrival-credits-english.gba)
(32 MiB), SHA256
`08239b255025e6e2627ec0184eb829cb453dc30b0aa7a518e7e8714fc678f2c6`.
It includes all previous translation and UI fixes. The cumulative ledger has
8,470 allocations and 10,115 checked patch owners; 1,130,424 appended bytes
are used and 15,646,792 remain available. Ordinary text inventory accounting
is unchanged: 8,422 authored, 822 retained and 74 unresolved candidates.

## Validation

The [mGBA report](../build/completion/arrival-credits/verification/verification.json)
passes **1,259 controlled constructor cases**: all 64 selectors at floor values
0, 1, 9, 10, 99, 100 and 255, exhaustive byte values for ordinary and both
puzzle IDs, and suppression-flag cases for every selector. It checks entire
tile buffers and tilemaps, palette staging, arena/puzzle suppression, balanced
stack and callee-saved registers, adjacent buffers, profile bytes and saves.
Original source graphics and tables remain byte-identical.

All 36 native title/floor-1 buffers decode exactly to the approved rasters
after hardware colour conversion. Separately, all 512 packed floor lines
roundtrip to their approved rasters. The largest title uses 78 tiles; the
largest floor uses 32, within their separate 160-tile capacities.

The normal-button cave route restores the accepted pre-stair fixture and
replays inputs 102–115. The natural floor-2 screen has **1,567 exact artwork
pixels**, with the complete 0x2800-byte queued VRAM upload matching its native
buffer. Source watches confirm reads from the appended pointer, palette and
floor-record tables. The captured transition fades into the translated tutorial;
after dismissing it, Torneko moves from (17,11) to (19,8). At frame 58415 the
new and previous ROMs have identical full-screen pixels, player position and
save bytes. Personal playtesting and natural visits to the other card identities
remain additional coverage, not prerequisites for this build.

- [Actual mGBA floor-2 screenshot](../build/completion/arrival-credits/verification/cave/native-second-floor.png)
- [Natural fade/transition sheet](../build/completion/arrival-credits/verification/cave/transition-sheet.png)
- [All 36 decoded native-buffer cards, 2×](../build/completion/arrival-credits/verification/native-buffer-cards.png)
- [Resumed gameplay](../build/completion/arrival-credits/verification/cave/gameplay-resumed.png)

The 36-card sheet reconstructs native tile buffers at full palette brightness;
it does not claim 36 naturally visited locations. The cave screenshot and
transition sheet are actual emulator frames. The controlled constructor queues
VRAM work; the normal frame route verifies the later upload and fade.

Reproduce from this repository (local raster export requires temporary
headless Chrome; building from the pinned exported PNGs does not):

```sh
.venv/bin/python -m tools.export_approved_arrivals
.venv/bin/python -m tools.build_arrival_credits --prepare
# Review/document any changed allocation spans before insertion.
.venv/bin/python -m tools.build_arrival_credits
.venv/bin/python -m tools.verify_arrival_credits
```

Other town-card families remain unconfirmed. This insertion covers the
complete discovered dungeon-card table and its aliases, not unknown graphics.
