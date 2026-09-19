# Mesen Warp-pot test

Load [tools/mesen/warp_pots.lua](../tools/mesen/warp_pots.lua) in Mesen's Script
Window. Stop the blank-scroll helper first; both use F8.

1. In a dungeon as Torneko, make a separate save state.
2. Make the **first two inventory slots** empty or expendable bread/scrolls.
   The script replaces those slots, and refuses equipment or existing pots.
3. Close menus, run the script, resume emulation and press **F8** (Fn+F8 if
   needed). You receive two identified **Warp pot[5]** items, once per run.
4. Put one pot on an open floor tile. Walk away, then **Push** the carried pot.
   Both pots need remaining uses. Establish successful travel first.
5. To investigate the draft failure message, try an occupied destination next.
   That is a test hypothesis, not a confirmed trigger. If Japanese text appears,
   capture a screenshot and a state just before the action if possible.

Restore the original test state to undo. Restart the script to activate it again.
The helper changes only two existing item records and the Warp-pot identification
entry in current RAM. It does not patch the ROM or write a save file directly;
saving in-game can persist the changes. The unknown destination-pot failure
sentence has not been inserted or altered.

Validation: Lua syntax and mocked Mesen callbacks passed, including refusal
without partial writes, menu/bank guards and once-per-run behavior. Native mGBA
on the current English ROM displays both items as `Warp pot[5]`; intervening
record bytes and user save files remain unchanged. See
[the inventory capture](../build/warp-pot-test/native/two-warp-pots.png) and
[report](../build/warp-pot-test/native/report.json). Actual Mesen execution and
successful/blocked pot travel are not claimed verified by these checks.

Addresses and evidence: [MEMORY_MAP.md](MEMORY_MAP.md#mesen-warp-pot-playtest-helper-2026-09-19).
