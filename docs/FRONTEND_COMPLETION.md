# Remaining frontend text

The [frontend component](../build/completion/frontend/component-checkpoint.json)
has passed its controlled native checks. It adds 48 sources through 48 reviewed
pointer words: mode help, save/recovery warnings, title/mode labels, shutdown
notices and Adventure Log summaries. The 96 English source cases, three native
menus and fourteen original summary-reader fixtures produce 157 checked
screens. All 86 Japanese relocation screenshot comparisons match.

The three long help strings use the same native paged service engine through
`080853BC`; all their pages are checked. Their descriptions retain Torneko 3's
own rules, including Extra mode's lack of persistent achievements/items and
Trial of illusion's EXP/recruitment restrictions. Existing Adventure Log,
Story/Extra/Barinabo modes, Torneko, Tipper, Rosa, Ines and dungeon terminology
is preserved. The [catalog](../translations/frontend-completion.json) retains
full wording and separate compact summary forms (`Trip %d`, `Lv%d`).

The native 92-byte summary reader fits seven-character Torneko and its HP,
level and adventure-count rows in the original 208x40 window. Both slots pass
normal and field-boundary fixtures, missing statistics, improper suspension
and Extra mode variants; record bytes, neighboring guards and font state stay
intact. Both existing Adventure Logs also pass button-driven cold loads through
the title/slot screens and into the opening. No window or save-layout patch is
needed for this component.

These tests distinguish controlled display/record fixtures from accepting
initialization, recovery or deletion prompts. Their real gameplay/save
consequences remain in the [playtest backlog](PLAYTEST_BACKLOG.md). Unreferenced
messages and high data-array references are not silently promoted. The earlier
name confirmation and default-name patches retain their existing ownership.
Exact ranges and exclusions are in [the memory map](MEMORY_MAP.md).

Both images reconstruct exactly from their ledgers; protected Japanese sources,
earlier patches and appended bytes remain unchanged. The combined English ROM
is [torneko3-frontend-completion-english.gba](../build/completion/frontend/torneko3-frontend-completion-english.gba),
SHA256 `2d2bd38acc79fa6d7f2752ad1b89415967ec07dcd5941bc632a06b3e65fd805c`.
The appended region uses 397,958 bytes.

Rebuild with `.venv/bin/python -m tools.build_frontend_completion build`.
Run `tools.verify_frontend_completion` for `english`, `japanese` and `baseline`,
then `tools.summarize_frontend_completion`, using the same Python invocation.
