# Dungeon voice save prompt

The dungeon-only voice prompt (`church.00c79370`, church type 3 / slot 2)
previously contained a blank row after its first sentence and four total
lines. The approved layout preserves the wording on three consecutive lines:

```text
A voice comes from nowhere...
Traveller, shall I record your deeds
in your Adventure Log?
```

The original font-zero line widths are 147, 175 and 111 pixels, within the
208-pixel message width. The priest and unattended book prompts are separate
sources and are unchanged.

`tools.build_dungeon_save_prompt` composes this display override after item-line
joining. The historical church catalog remains the source checkpoint; the
current display is authored in that builder's `TEXT` constant. The shared
allocator owns a new NUL-terminated string and explicitly supersedes only the
voice prompt's pointer. See [MEMORY_MAP.md](MEMORY_MAP.md).

`tools.verify_dungeon_save_prompt` checks the original church selector and
native paged renderer, including one page with three consecutive text rows.
The normal build runs this check before publishing. Evidence is under
`build/dungeon-save-prompt/verification/` or the receipt's
`save_prompt_regression_report`. These are controlled native reader checks;
they do not perform a save transaction or modify user save files.

Verified component SHA-256:
`d1a1c0fde27919fc3b3ab484d6c6b7cc4995cebc51166df8489b98136da90c80`.
The native selector chose the relocated text, and the renderer produced exactly
one page with rows 2, 14 and 26. The screenshot is
`build/dungeon-save-prompt/verification/dungeon-save-prompt-p00.png`.
The test also compares every byte outside the owned pointer and new string
against the preceding item-lines checkpoint.
