# Menu rendering and publication regression checks

The 2026-09-19 menu component fixes all six supplied screenshot cases plus the subsequently supplied Trap state.
It follows `build_damage_lines`; ROM allocation and original-byte ownership are
recorded in [MEMORY_MAP.md](MEMORY_MAP.md) and
`build/menu-fixes/allocation-plan.json`.

| Case | Cause and correction | Regression check |
|---|---|---|
| Automatic idle menu missing its right shading | Independent stock scanline clipping masks still ended at the Japanese width. Extend the affected right endpoints by 8px, retaining corner insets and opacity. | Close the supplied menu, wait 1,900 frames without input, require the real compact profile and full shading coverage on every affected row. |
| Full status menu missing corner shading | The same precomputed masks cover the old command width where the location panel is absent. | Reopen normally; check all command rows including corners and inspect native screenshots. |
| Ground popup clips and corrupts background menus | Popup profiles restore Japanese bitmap widths/offsets while preserving English bitmap contents. The original English sentence also exceeds the popup. | Match parent geometry on profiles5–10, with location fields on5/7/9. Use the104px display “Nothing at your feet.” Check unchanged command/location/status bitmap bytes and positions when opening, cancelling and reopening. |
| Stairs and Trap submenus corrupt background menus | Same cached-content descriptor mismatch. | Replay actual Stairs and Slowing trap selection and cancellation; verify all three cached panels retain their geometry, buffer offsets and exact pixel bytes on each opening. Status time may advance on parent redraw. |
| Casino Exchange clipped | 42px label plus4px inset exceeds40px window. | Approved28px “Trade” display at the casino-specific pointer. Re-enter the conversation to discard the old state’s cached label pointer, then check label and glyph bounds. |
| Warehouse lower-right panel corrupted | Opening actions changes the cached counter width from5 to6tiles without redrawing its bitmap in that stride. | Keep counter5tiles and actions6tiles. Verify exact counter bitmap/geometry before and after repeated action-menu openings. |

No new code hooks, permanent RAM, save fields, fonts or opacity settings. The
component appends94bytes including padding and makes220 owned patch changes.
All earlier allocated text/code/assets remain untouched. The original Japanese
ROM remains the only build base; the fan patch is not used.

## Automated build gate

`./build.sh` now runs `tools.verify_menu_fixes.run` against its freshly rebuilt
candidate **before publishing** the convenient ROM, BPS and receipt. Seven local
fixtures are pinned by filename and SHA256 in `tools/menu_fixtures.json`.
A missing or changed fixture is an explicit build failure, not a skipped test.
Keep those states under `saves/`; tests never overwrite them. Each emulator uses
an isolated temporary ROM and cartridge save. The checks also compare cartridge
save contents before/after navigation and hash user save files before/after.

The receipt records the report hash and location. Hash-specific reports and
opened/closed/reopened screenshots are under
`build/menu-fixes/publication-checks/<ROM SHA256>/<suite hash>/`. These tests cover the listed
regressions; they do not replace every prior component’s gameplay coverage.

`tools.verify_menu_publication_gate` feeds the actual known-bad pre-fix ROM into
the publisher using a temporary test substitution for the component builder.
The real native checks reject its missing shading, and the test requires all
latest ROM/patch/receipt/ledger hashes to remain unchanged. Evidence is in
`build/menu-fixes/publication-rejection-check.json`.

Standalone commands:

```sh
.venv/bin/python -m tools.build_menu_fixes --prepare
# Review/document allocation changes before insertion.
.venv/bin/python -m tools.build_menu_fixes
.venv/bin/python -m tools.verify_menu_fixes --baseline
.venv/bin/python -m tools.verify_menu_fixes
.venv/bin/python -m tools.verify_menu_publication_gate
./build.sh
```

The baseline mode records the seven actual unfixed cases for comparison; it does
not assert that they are fixed. The normal mode and build gate enforce fixes.

## Pending coverage and existing states

The supplied Slowing trap state reproduces the same corruption under stock
profile7 in the pre-fix ROM. The corrected ROM preserves all three background
panels through real Trap selection, cancellation and reopening. This is now the
seventh required fixture in the publication gate. Other trap identities, town,
transformed-character and other menu variants remain supplemental coverage.

An old state can restore old window bitmaps or cached text pointers. Close and
reopen menus to redraw them; for the casino, finish the conversation and talk
again. The tests deliberately do this through normal buttons, with no RAM edits
or forced program counters. The state and its original screenshot remain intact.
