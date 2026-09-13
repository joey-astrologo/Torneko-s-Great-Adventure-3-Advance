# Results-screen correction found during normal play

The dungeon-defeat results screen now displays correctly. The earlier English
panel was 27 tiles wide, but its separate arrival animation still arranged
the text as 26-tile rows. The rendered bitmap was intact; the screen tilemap
misplaced it. Five checked Thumb instructions now use the existing panel's
width and position. Text, font, ROM allocations and save fields are unchanged.

Combined ROM:
[torneko3-result-runtime-english.gba](../build/completion/result-runtime/torneko3-result-runtime-english.gba),
SHA256 `7693b1ee1bcc67d47c04e1e0de3a5ecf17a61f18828711b845e2e41428293aff`.
The [ledger](../build/completion/result-runtime/english-build.json) preserves
all earlier allocations and patches and adds five owned halfwords. Exact
instructions and tilemap/buffer ranges are in [MEMORY_MAP.md](MEMORY_MAP.md).

[Native verification](../build/completion/result-runtime/component-checkpoint.json)
replays 18 normal inputs from the previously accepted floor-two checkpoint,
followed by two acknowledgements returning to town. It reproduces the defect
on the preceding ROM and verifies the corrected build:

- All 17 animation steps have the expected 459 map entries, with adjacent
  cells unchanged and identical frame pacing.
- RAM and VRAM contain identical text bitmaps. All 2,509 expected white text
  pixels appear on screen; the preceding ROM misplaces 1,891 of them.
- All 35 whole-string draws, score-record bytes, font state and return dialogue
  match between builds. Nineteen surrounding gameplay/return screenshots match.
- The original disposable cartridge save remains 65,536 bytes and unchanged
  in this route. A later save prompt and natural score persistence are still
  separate coverage; this test does not claim they occurred.

The earlier isolated ending fixture stopped before this animation and revealed
the window with the high-score detail routine. Its glyph checks remain useful,
but did not establish correct live dungeon-ending display. The new regression
checks actual tilemap entries and foreground pixels in addition to glyph bounds.

An additional normal-button menu exploration on an existing native-created
test score profile reaches the high-score list and detail screen. That detail
path has the expected 459 cells and identical RAM/VRAM bitmap; it uses the
descriptor-driven reveal routine and does not need the ending-animation patch.
Its [exploratory evidence](../build/completion/result-runtime/research/score-menu/readers.json)
is distinct from the accepted defeat regression. The same exploration found
that the title-menu label “Adventure records” is too wide for its actual
80px window; the subsequent [compact-display correction](UI_POLISH.md) now
passes full cold-boot menu navigation and actual score-detail pixel checks.

```sh
.venv/bin/python -m tools.build_result_runtime
.venv/bin/python -m tools.verify_result_runtime
```
