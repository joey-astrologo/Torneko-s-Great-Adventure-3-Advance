# Screenshot rendering corrections

Accepted 2026-09-13. The four screenshot reports are corrected in the cumulative
English ROM, SHA256
`fd0c0dd97ffd205bcc4ba71711c76edcc6f33dad912731d7d9d629188414ace8`.
Run `./build.sh` for the latest [ROM](../build/torneko-3-english.gba) and
[BPS patch](../build/torneko-3-english.bps); see [build instructions](BUILD.md).

Review the [before/after PNG](../build/rendering-fixes/verification/before-after-2x.png)
or its [native-size version](../build/rendering-fixes/verification/before-after.png).
The comparison uses the accepted arrival-card ROM as its baseline:
`08239b255025e6e2627ec0184eb829cb453dc30b0aa7a518e7e8714fc678f2c6`.
Both ROMs derive from the pinned Japanese original. No fan-patch assets are used.

## Corrections

| Report | Result |
|---|---|
| Name entry cuts off `B: Erase` | Move the shared B-button hint from X170 to X156 inside the 208px field. Both `B: Erase` and empty-name `B: Cancel` fit. Update the initial page render, per-character redraw and clearing rectangle together. |
| Records menu's top-right border is damaged | Reduce the category panel from 26 to 20 tiles (160px), keeping its native position, height and selection behavior. All 11 category labels fit, including the cursor/inset; the right corner remains on screen. |
| Location panel overlaps the action menu | Move location content from X104 to X112 and reduce its width from 120px to 112px, in both dungeon and town descriptors. The action panel's outer right edge and location panel's outer left edge meet at X104 without overlap. |
| XP gain uses an unnecessary second line | Join the final numeric line after formatting the actual name and number when the result fits the 208px message area and 59-byte history payload. The same rule also fixes the matching level-up line seen in the screenshot. Long or unsupported substitutions retain their existing wrapping. |

The font, message wording, game mechanics, name capacity, save format and
history record sizes are unchanged. This component adds 792 ROM bytes,
including alignment, through 11 shared-allocator entries. Its eight checked
patch ranges include two explicit supersessions of earlier window patches.
The complete output is checked against exactly those owned changes.

## Status-only place names

Several full town names exceeded even the old 120px panel. These seven private
status forms fit the corrected 112px panel. The full glossary names and shared
place tables remain unchanged, including dialogue and destination lists.

| Full place name | Status panel |
|---|---|
| Seabed mountain rest stop | Seabed Mt. rest stop |
| Great Baleina castle town | Great Baleina town |
| Madame Gracos's bazaar | Mme. Gracos's bazaar |
| Mountain Foothills shrine | Foothills shrine |
| Ruins rest stop - South | Ruins rest - South |
| Ruins rest stop - North | Ruins rest - North |
| Northern Plateau shrine | N. Plateau shrine |

The [town preview sheet](../build/rendering-fixes/verification/town-displays.png)
renders each form through the native town status reader in a controlled scene.
It does not depict natural visits to those destinations. Exact Japanese
identities, full/display strings, widths and source pointers for all 30 place
records are recorded in the
[allocation plan](../build/rendering-fixes/allocation-plan.json).

## Message behavior and runtime checks

Only four already translated templates are eligible:
`gameplay.001b4e23`, `gameplay.001b4e38`, `gameplay.001b4e7b` and
`gameplay.001b4e91`. No other dialogue is reflowed. The wrapper calls the original
formatter and measures the final numeric line with the actual font-0 glyph
extents. It replaces a line feed with a space only when the joined line fits.
Non-ASCII names, controls and oversized substitutions preserve the original
wrapping.

The combat queue asks for one source line at a time. A bounded lookahead is
therefore needed in that mode: format the eligible pair into an 80-byte local
buffer, join only if it fits the screen, history and caller buffer, then advance
past both consumed source lines. On failure, return the original first line
and source position. This uses transient stack storage, with no permanent RAM
allocation. The shared native tracing helper accepts extra breakpoints so the
fixture can observe the wrapper's second, internal formatter call.

The [acceptance report](../build/rendering-fixes/acceptance.json) pins the ROM,
inputs, harness and result artifacts. Checks include:

- Cold name-entry navigation, all seven erases, empty-name Cancel and page
  changes, checking both hint draw paths and their pixel bounds.
- Normal close/reopen navigation from the supplied Records and status states,
  with window geometry and glyph bounds traced.
- All 64 dungeon selectors using the original puzzle classifier and floor 99,
  plus all 30 town headers; 94 controlled location cases.
- 166 formatter cases per ROM, including short/wide names, ordinary and signed
  integer extremes, non-ASCII names, limited buffers and unselected templates.
  Seventy-five cases compact successfully; full-message and fallback source
  returns are preserved.
- 140 queue/history cases per ROM, checking native line consumption, stored
  records and guards. Controlled XP/level examples also render in the supplied
  gameplay state's live queue and history screen.
- Whole-image comparison, unchanged earlier allocations, explicit patch
  supersession, and unchanged permanent RAM/save layout.
- SHA256 checks that all four supplied save/state files remain unchanged.

XP examples use controlled substitution slots and native message functions;
these checks do not claim to award XP or gain levels through natural combat.
Broader personal playtesting remains tracked in [the backlog](PLAYTEST_BACKLOG.md).

## Using older saves and states

The supplied `.ss0` files load directly through mGBA's native state API; no
PyBoy conversion is needed. Automation uses disposable ROM/save copies.
Loading a state restores its already drawn windows, so close and reopen a menu
to see the new geometry. Already stored history entries retain their old line
breaks; newly generated XP/level messages use the correction. The comparison's
history panel intentionally shows both old records and the new single-line
entries together.

## Reproduction and ownership

```sh
.venv/bin/python -m tools.build_rendering_fixes --prepare
.venv/bin/python -m tools.build_rendering_fixes
.venv/bin/python -m tools.verify_rendering_fixes
.venv/bin/python -m tools.summarize_rendering_fixes
./build.sh
```

Preparation requires the earlier cumulative checkpoints and prepared arrival
resources, as described in [BUILD.md](BUILD.md). If preparation changes any
range, update [MEMORY_MAP.md](MEMORY_MAP.md) before insertion. The prepared plan
pins source bytes, earlier patch ownership, builder/assembly hashes and exact
appended assets. The builder rejects changed preconditions and allocations.

The current combined ledger has 8,481 allocations and 10,121 checked original
patch records, using 1,131,216 appended bytes and leaving 15,646,000 bytes in the
32 MiB image. Source/output hashes and exact owners are in
[english-build.json](../build/rendering-fixes/english-build.json).

This completes the screenshot-fix step. The user requested confirmation before
starting the title-screen audition or prose second pass.
