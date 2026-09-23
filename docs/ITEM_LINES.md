# Item-message line joining

The item-line component follows companion combat in the cumulative build.
It fixes short eating and item-hit messages that remained split because their
native item icons and colour controls were not understood by the earlier
joiner. It also conditionally joins the world message `$t obtained\n%s!`,
including gold pickups. [The audit](ITEM_LINE_BREAK_AUDIT.md) explains the
coverage gaps.

The existing combat allowlist is unchanged. `tools/item_lines.asm` recognizes
item icons 8740–874F using widths measured from the original font-zero
bitmaps/advances, colour sequences 030502–030507, and reset 0306.
All encoded bytes still count toward the 59-byte history limit. The pixel
limit remains 208. Unknown glyphs/controls, oversized spans and truncated
buffers retain their existing line breaks. Colours and icons are preserved.
This applies across approved item-bearing messages, not just the three
reported examples. Previous actor-name, XP and damage behavior remains in
the fallback chain.

The acquisition template is formatted with `%s` into a stack buffer before
entering the world display. A source-address combat allowlist cannot identify
that RAM buffer. A separate trampoline at 08062294 checks the exact acquisition
caller (return 08062D65) and its template in r8. It expands into bounded
80-byte temporary scratch, checks the same safe limits, and changes the
original buffer's LF to a space only if the expanded line fits. Other callers
and templates retain original behavior. The native world prologue is replayed.
No catalog wording or save format changes.

See [MEMORY_MAP.md](MEMORY_MAP.md) and
`build/item-lines/allocation-plan.json` for allocation/patch ownership and
stack lifetimes. Original Japanese instructions were inspected in
`build/item-lines/research/acquisition.txt`; native baseline item output is
recorded in `build/item-lines/research/native-names.json`.

## Build and verification

The normal `./build.sh` command includes this component and runs
`tools.verify_item_lines` against the candidate ROM before publication. Its
report/hash and counts are recorded under `item_regression_*` in the build
receipt. The suite generates native names for every item row and enhancement
fixtures, checks all approved item-bearing combat templates with native names,
checks actual queue/history output, and exercises the original acquisition
printf and world call instructions. It includes rendering, unsupported input,
capacity and unrelated-caller checks. Native unidentified/custom names and
cursed-item flags are covered too. The companion suite now uses colour 7F
as its unsupported-colour probe: colour 4 is a legitimate custom item colour. These are controlled native fixtures;
ordinary gameplay replay remains useful independent coverage.

Old entries already stored in the message history retain their previous line
breaks. Test newly generated messages after loading the rebuilt ROM.

## Verified result (2026-09-23)

Component ROM SHA-256:
`47230aec8306c652860712e50a3b97c1690a90d386ffccd61ee9da2397e95b33`.
The component suite passed 1,867 formatter cases (1,715 joins / 152 fallbacks),
1,759 native queue/history checks, four exact 208/209-pixel and 59/60-byte
boundaries, eight acquisition payloads and an unrelated-caller negative check.
Ten native rendering fixtures cover combat and world output, including cursed
and unidentified items. Acquisition presentation uses a fresh window fixture
with the output already verified through the actual acquisition caller.

`build/item-lines/verification/report.json` records the candidate hash and
results; `build/item-lines/baseline-rejection.json` confirms the old companion
build fails the new regression suite. The suite also checks that every ROM byte
outside the two owned hooks and appended allocation matches that baseline,
and that user save files remain unchanged. Publication reruns this suite
alongside the existing menu, combat, damage, Trade and companion gates.
