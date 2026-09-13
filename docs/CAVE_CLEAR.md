# Native cave clear and save roundtrip

The current English ROM passes a successful three-floor Mysterious cave run,
the following Shrine of the Gods conversation, Ines joining the party, the
map handover, and a village priest save. A fresh emulator loads the earned
clear record and the progressed Adventure Log correctly.

The [accepted report](../build/completion/cave-clear/component-checkpoint.json)
pins the ROM, harnesses, replay, save and supporting reports. The uninterrupted
replay uses **435 normal inputs** from the earlier accepted native opening
checkpoint. It performs no intermediate state restores, coordinate/HP/flag
injection, or save edits. Its final screen and complete native save match the
recorded exploration.

Validation covers:

- 83 story messages with producer-to-reader provenance and glyph checks;
  11 paged messages and 220 whole-string draws, including combat, level-up,
  Recovery pot use, herb tutorials, shield equipment and the save service.
- All 17 result-animation steps, with 459 correct map cells per step and
  unchanged surrounding cells.
- The naturally earned **4,002-point, floor-three clear**, from native record
  creation through the physical save and cold result display. All 2,205 white
  text pixels in the cold result panel match, with no mismatches.
- 40 cold-load whole-string draws, including records, history, both Log labels
  and the saved `HP 18/18 Lv2 Trip 1` summary. Log 1 loads in Barinabo Village;
  the captured scene also shows Ines following Torneko.
- The complete eight-byte compact `Torneko` name through the native save/load
  readers. Log 2's entire seven-sector region is unchanged, and an independent
  cold load confirms its name.

The save is 65,536 bytes, SHA256
`ed02ce9c53d13f7f3055db319d6633aab5f48afb32c4d3da0327a08e0572f971`.
The ROM is unchanged:
[torneko3-inventory-notice-english.gba](../build/completion/inventory-notice/torneko3-inventory-notice-english.gba),
SHA256 `8757bf5cd89e6b935c8f99c431600eb6b5367ad9e9078158a84c047cf6d6e960`.
No new text, font, code, RAM or save-layout patch was needed.

Reproduce with the accepted files present:

```sh
.venv/bin/python -m tools.verify_cave_clear
.venv/bin/python -m tools.verify_cave_clear_save
.venv/bin/python -m tools.accept_cave_clear
```

The [replay](../build/completion/cave-clear/replay.json) joins the native
first-floor route, the first Recovery pot recovery, and the successful
continuation. An earlier unarmed detour that became surrounded remains in
the exploration archive but is excluded after the branch point. The replay
does not rely on a mid-run rewind. A preliminary explorer A-button enum bug
was corrected before this route; it was not a ROM defect.

[Clear screen](../build/completion/cave-clear/clear-route/third-floor-exit.png),
[cold result screen](../build/completion/cave-clear/cold/detail.png),
[loaded village](../build/completion/cave-clear/cold/world-menu.png), and
[checked native save](../build/completion/cave-clear/verification/earned.sav)
are preserved for review.

No watchpoint on the 31 unowned Japanese source starts fired. This route does
not establish those sources are unused, full-game text discovery, later
dungeon coverage, or dungeon suspend/resume. Those remain separate from this
successful-clear check. Graphics work is still deferred.
