# Remaining composed item names

This component has passed its controlled native checks. Its combined image is
linked in [COMPLETION.md](COMPLETION.md); translation work continues.

The [item-display catalog](../translations/item-display.json) adds 20 resources
through 21 pointers: fourteen item-category prefixes, the hidden-name
placeholder, three quantity formats, monster tracks and actor-specific graves.
Quantity display uses `%dx %s`, preserving the full singular item names already
in the glossary. Category labels name existing classes; they do not introduce
new item identities. Exact source/table ownership is in [MEMORY_MAP.md](MEMORY_MAP.md).

The [acceptance report](../build/completion/item-display/component-checkpoint.json)
records 1,197 native composition cases: all 370 items with and without prices,
246 unidentified-name rows, six custom-name width fixtures, all 200 grave-name
choices, three tracks contexts and two hidden-name properties. Twenty direct
previews additionally cover every resource, including category prefixes outside
the original custom-name mappings. All 1,217 Japanese relocation screenshots
match the preceding frontend image. The fourteen category pointers match the
ROM after cold initialization; restoring the older village fixture explicitly
refreshes that cached table for controlled cases.

Every output guard, glyph boundary and name/price-column check passes. The
seven-W custom fixtures test width in existing eight-byte slots; they do not
establish the item editor's accepted length. Natural item acquisition, naming,
shop transactions and status causes remain in the playtest backlog.

The original formatter keeps a 100-byte output, price column at x=130 and all
existing style/status/charge behavior. Its price digits use existing special
font glyph codes that the decoder labels with Greek letters; those labels are
not untranslated Greek prose. They should retain their original glyph values.

Rebuild with `.venv/bin/python -m tools.build_item_display build`.
Verify each `english`, `japanese`, and `baseline` variant with
`.venv/bin/python -m tools.verify_item_display VARIANT`, then run
`.venv/bin/python -m tools.summarize_item_display`.
The frozen harness and catalog are in `build/completion/item-display/`.
The complete images reconstruct from their shared ledgers, preserving all prior
patches and appended bytes. The English image uses 398,144 appended bytes.
