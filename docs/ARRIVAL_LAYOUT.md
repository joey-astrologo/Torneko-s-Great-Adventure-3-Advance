# Compact arrival-card layout

The user requested improved vertical centring and less space between the name
and floor line on 2026-09-13. The approved Credits-adapted rasters place the
title at y=27 and the floor at y=100: a 55–56px empty gap. This inherited the
audition's separate title/floor regions; the hardware does not require it.

The revised layout moves the title down 32px and the floor up 16px. The name
starts at y=59 and the floor at y=84, leaving 7–8px between their ink bounds.
Their combined extent is approximately y=59–107, centred near y=83 on the
160px screen. The arena's single title moves to y=75–92 so it is centred
without reserving an absent floor line. Font, sizing, colours, horizontal
alignment, wording and raster pixels remain unchanged.

The map routine repositions the existing native tilemap cells. It leaves every
previous asset allocation intact and supersedes only the already owned arrival
map hook. [MEMORY_MAP.md](MEMORY_MAP.md) records the code/map ranges before
insertion; the [allocation plan](../build/arrival-layout/allocation-plan.json)
pins exact source bytes, prior ownership and the one new code allocation.

This covers all 36 discovered card identities and 64 selectors, including
ordinary/puzzle floors and the arena. A separate town-card family remains
unconfirmed; the earlier town-entry captures show fades rather than a title
from this table. The change therefore does not claim to modify unknown town
graphics.

The [native acceptance report](../build/arrival-layout/acceptance.json) passes
**1,259 constructor cases**, covering every selector, ordinary and both puzzle
classifiers, all byte floor values for representative selectors, arena behavior
and suppression. Entire tilemaps, unchanged tile buffers/palette, callee-saved
registers, stack balance, adjacent memory and save bytes pass. All 36 decoded
native previews match the original rasters exactly at their new positions.

The normal cave floor-two transition also passes: all 1,567 artwork pixels,
the full queued VRAM upload, fade, tutorial dismissal and resumed movement.
After the card clears, the previous prose ROM and new ROM produce the same
screen, frame, player position and save. All supplied user save/state files
remain unchanged. These checks cover the discovered family and one natural
transition, not natural visits to every possible location.

- [Before/after native screenshot](../build/arrival-layout/verification/before-after.png)
- [All 36 cards at their new positions](../build/arrival-layout/verification/all-cards.png)
- [Actual native floor-two screenshot](../build/arrival-layout/verification/cave/native-second-floor.png)
- [Fade and transition frames](../build/arrival-layout/verification/cave/transition-sheet.png)

The cumulative ROM SHA256 is
`421b353440e6d277109f8bddb852e7fc967eb44291c5c0d6cb7bb07af7029ade`.
`./build.sh` includes this component and publishes the usual
[ROM](../build/torneko-3-english.gba) and
[BPS patch](../build/torneko-3-english.bps). The complete image reconstructs
from the previous prose build plus the one owned hook and 164 bytes of new
code (165 bytes including alignment). All previous allocations and unrelated
patches remain byte-identical. No translation or discovery count changes.

Reproduce using the existing approved artwork and native fixtures:

```sh
.venv/bin/python -m tools.build_arrival_layout --prepare
# Document any changed ranges before insertion.
.venv/bin/python -m tools.build_arrival_layout
.venv/bin/python -m tools.verify_arrival_layout
./build.sh
```

The original audition approval remains the authority for the font and raster
assets. Its frozen y positions describe the historical insertion; this later
user-requested layout component supersedes their on-screen placement.
