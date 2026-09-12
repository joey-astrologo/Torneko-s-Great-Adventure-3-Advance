# Shared keyboard completion

The six-resource keyboard component restores the conditional History label,
uses Page for both Latin and kana page switching, and translates the history
popup to Select / Erase. The shared hint reads `A: Enter  L: Page  R: Done`.

The chosen English font remains font 0. The unchanged kana password grid uses
its original ten-row font 1; font 0 caused 13 overlapping ink pixels in the
hiragana grid. Native calls switch only around grid drawing and restore font 0
for English labels. Compact alphabets, character limits and save fields retain
their earlier layouts.

The [source catalog](../translations/keyboard-completion.json),
[owner report](../build/completion/keyboard/source-owners.json), and
[memory map](MEMORY_MAP.md) identify the original resources and hook ranges.
Two existing name-component pointer patches are explicitly superseded; the
shared ledger retains their complete previous records and preserves all prior
appended data. Ordinary overlapping writes still fail.

[Acceptance evidence](../build/completion/keyboard/component-checkpoint.json)
covers eight native layouts (both codecs, pages and History states), four exact
original kana grid comparisons, 16 native history rows and guarded 16-byte
conversion / 32-byte printf buffers, the original popup reader, and four real
joypad regressions against the accepted merchant build. The input cases cover
seven-character Torneko, kana page/selection/erase/shortcut behavior and Done.
The Japanese control preserves earlier keyboard assets and relocates only the
unchanged popup; all 11 control screenshots match the preceding build.

History rows use the native buffer coordinates, which differ from the nominal
window height. All eight rows retain the preceding layout and pixels. Actual
ink checks are used for bottom-row hints and popup text, whose unused bitmap
rows can extend beyond their windows.

These controlled checks do not establish natural password exchange, history
selection/deletion or learned-scroll inscription behavior. In particular, the
original blank-scroll matcher needed an English compatibility extension;
that follow-up is now accepted in [INSCRIPTIONS.md](INSCRIPTIONS.md). Full item glossary names remain the
authority independently of the seven-character inscription field.

```sh
.venv/bin/python -m tools.build_keyboard_completion build
.venv/bin/python -m tools.verify_keyboard_completion english
.venv/bin/python -m tools.verify_keyboard_completion japanese
.venv/bin/python -m tools.verify_keyboard_completion baseline
.venv/bin/python -m tools.verify_keyboard_completion original
.venv/bin/python -m tools.verify_keyboard_input english
.venv/bin/python -m tools.verify_keyboard_input baseline
.venv/bin/python -m tools.summarize_keyboard_completion
```

English ROM: [torneko3-keyboard-completion-english.gba](../build/completion/keyboard/torneko3-keyboard-completion-english.gba),
SHA256 `8a6eb7fed361493b10383d792bd7a64e4fe4964a410f21c6551cc5aa8d3c178d`.
Japanese control SHA256:
`8ae65c07364bd839237764eeaba381b6800ea75cd2e95b1d7da5201709875972`.
