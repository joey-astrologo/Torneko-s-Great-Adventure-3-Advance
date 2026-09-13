# Apparent strings inside animation resources

Five more extraction candidates are confirmed as scenery data through native
readers. No ROM bytes or artwork are changed. The accepted inventory-notice
ROM remains SHA256
`8757bf5cd89e6b935c8f99c431600eb6b5367ad9e9078158a84c047cf6d6e960`.

| Candidate ROM offset | Verified role |
| --- | --- |
| `0092C610` | Four final scene-0 metatiles, followed by the first zero byte of a separate animated tile asset. The apparent string crosses an asset boundary. |
| `00AA6678` | Tile pixels within scene 54, animated frame 62. |
| `00A00BF8`, `00A00BFC`, `00A00C00` | Three four-byte RGB values within scene-30 palette-animation row 2, frame 6. Their zero bytes are color components. |

The [native report](../build/completion/resource-boundaries/native-verification.json)
pins the source/current ROMs, harness, fixture, helper files and disassembly.
It verifies native scene descriptor selection/copy, four guarded metatile
copies, full 2,336-byte and 1,536-byte animated tile uploads and their adjacent
VRAM. The scene-54 fixture advances the native 12-byte frame pointer 62 times;
it bypasses countdown timing and does not establish natural scene reachability.

For the RGB candidates, native scene initialization populates the palette
timer records. Twenty-eight bounded update calls execute their real countdowns
and select the seventh stored palette frame. All fifteen native color writes
match the source values and the actual palette buffer. No text renderer is
entered by these checks. Palette-update calls are controlled fixtures rather
than normal gameplay elapsed frames.

Exact occupied ranges and existing RAM/VRAM lifetimes are indexed in
[MEMORY_MAP.md](MEMORY_MAP.md). A pointer-shaped value in unrelated tile bytes,
or the duplicate high-ROM pointer table, is not granted insertion ownership.
All five source spans remain byte-identical to the original.

Current inventory: **8,422 authored sources + 822 retained resources + 74
technically unclassified candidates = 9,318**. The remaining queue contains
31 Japanese review sources, 42 original ASCII sources without confirmed reader
context, and one combined character-map candidate. It still includes the 30
uninserted drafts and one unresolved Japanese word. Graphics lettering remains
deferred; this audit only identifies false prose decodes.

```sh
.venv/bin/python -m tools.audit_resource_boundaries
.venv/bin/python -m tools.audit_retained_resources
.venv/bin/python -m tools.audit_current_text_review
```
