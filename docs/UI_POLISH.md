# Compact records menu label

The title menu now shows **Records**, fitting its existing 80px window.
The full “Adventure records” wording remains in the translation catalog.
Normal menu navigation exposed that the 86px full label exceeded the 76px
space after its text inset. The menu appears only when a valid records profile
is available; empty and single-Adventure-Log saves without that profile do not
show this row.

Latest combined ROM:
[torneko3-ui-polish-english.gba](../build/completion/ui-polish/torneko3-ui-polish-english.gba),
SHA256 `e21304fe82c1875b228b5185099636467f1f84cfec02e1e2c9b71d5bec5c0272`.
This includes the earlier [dungeon results-screen correction](RESULT_RUNTIME.md)
and [Recovery pot tutorial correction](TEXT_POLISH.md).

The [ledger](../build/completion/ui-polish/english-build.json) explicitly
supersedes the owned menu pointer at `00C7828C` and appends eight bytes at
`01069FE8`. The original source and earlier full English allocation remain
intact. The append ends at `01069FF0`: 434,160 bytes including alignment,
8,427 allocations and 10,110 checked patch records. No menu layout, font,
action, RAM or save field changes.

[Native verification](../build/completion/ui-polish/component-checkpoint.json)
checks three fresh emulator/save contexts and 46 English draws. Normal buttons
navigate Records, categories, list, detail and back on a native-created test
score profile. All 459 detail-map cells and 2,421 white text pixels are correct.
The preceding build reproduces the clipped title label twice; all its other
observed draws pass. Other menu strings, navigation frame timing and disposable
save bytes are identical between builds. This is menu testing using controlled
score records, not a claim of naturally earning those records.

The retained-resource audits also pass on this ROM. Accounting stays at
**8,422 authored sources + 817 retained + 79 technically unclassified = 9,318**.
The [UI-polish catalog](../translations/ui-polish.json) supplies the explicit
display override in the extraction browser without replacing its full wording.

```sh
.venv/bin/python -m tools.build_ui_polish
.venv/bin/python -m tools.verify_ui_polish
```
