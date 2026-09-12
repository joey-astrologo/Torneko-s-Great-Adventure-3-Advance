# Remaining system labels

The [catalog](../translations/system-labels.json) adds 42 independently
translated original sources through 42 checked pointer words. It builds on
[world completion](WORLD_COMPLETION.md). Original fonts, source bytes, record
sizes and menu return values remain intact. All new text uses the shared
append allocator; the [memory map](MEMORY_MAP.md) records the owners and bounds.

The [checkpoint](../build/completion/system-labels/component-checkpoint.json)
records 549 English native cases and 549 Japanese relocation/control pixel
pairs, with both complete ROMs reconstructed from their ledgers.

| Reader/context | Checks |
| --- | --- |
| Extra Mode and party choice | Six mode labels, four party labels; original tables, order and return values; actual party caller uses row-count parameter 6. |
| Adventure Log summaries | All 64 dungeon-entry names formatted into the 64-byte title, then displayed with a seven-character wide name. Separate fixed 23-byte dungeon-menu copy is allocated with safe padding. Both slot selectors are exercised. |
| Growth labels | All 12 native indices, including Torneko/Tipper/Rosa/Ines and eight growth categories. Original 512-byte formatter and 192-pixel window, with 92 pixels available at x100. |
| Object names | Five native type-4 indices, including the retained empty row, plus unknown-object fallback; original 30-byte copy and record preserved. |
| Equipment cap | All 75 eligible item rows and their original 0..99 enhancement limits. `Max +%d` fits the actual 48-pixel field at x144. |
| Equipment statistics | All 370 item IDs plus nine visible/hidden mark fixtures. Native power calculation, two temporary printf strings and 1,024-byte composition are exercised; all item records stay intact. |
| Synthesis and visibility | Actual centered, coloured synthesis heading in window 1, including its activation; the Hocus Pocus visibility branch's direct message reader at y26. |
| Adventure context | Three original five-byte copies with four payload bytes. Full catalog Adventure uses the established display Trip; existing commands render Join Trip / Leave Trip. |
| Remaining messages | Two ally overflow sources, two retry prompts and suspend confirmation; original paged wrappers, full pages and retry source selection. |

Exact modern glossary names are retained for the four trials, characters,
Big bread and Mark. Growth categories are project labels, not claims of
official localization. The [initial draft](../build/completion/system-labels/initial-draft.json)
preserves the longer context proposal; it is superseded by the bounded display.

The synthesis heading keeps its original centering/colour controls. Its native
window must be activated before capturing the screen; a draw trace alone did
not establish visibility. Native glyph checks measure actual bitmap ink to
avoid treating blank rows in the 12-pixel font cell as clipped pixels.

These are controlled native reader checks with restored emulator fixtures,
explicit branch overrides and isolated instruction slices. Object/context
previews are identified as such. Natural mode availability, confirmation
responses, actual synthesis and full dungeon transitions remain in the
[playtest backlog](PLAYTEST_BACKLOG.md). This component does not establish
full-game text discovery.

```sh
.venv/bin/python -m tools.build_system_labels build
.venv/bin/python -m tools.verify_system_labels english summaries
.venv/bin/python -m tools.summarize_system_labels
```

The summarizer requires all nine suites in each of `english`, `japanese` and
`baseline`; `tools.verify_system_labels.SUITES` is the complete suite list.
Its frozen harness, catalog, helper hashes and fixture must match every report.
