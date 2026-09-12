# World merchant dialogue

The [native checkpoint](../build/completion/merchants/component-checkpoint.json)
passes **132 sources / 453 pointers**, 282 English cases / 279 screens and
147 Japanese pixel comparisons. It includes ordinary shop voices, the Medal
King, Samson/Douglas player shops, blacksmith and synthesis dialogue.
The latest combined ROM is linked in [COMPLETION.md](COMPLETION.md).

Each source uses its original printf argument order and dollar substitutions.
The original 256-byte printf buffers and 1,024-byte world text buffer pass
native bounds checks. Wide item names and signed integer fixtures exercise
layout; eighteen separate capacity cases exercise 99-byte item-name arguments.
All world pages execute the original preparation, glyph and continuation-scroll
code. Snapshot presentation and explicit continuation input are controlled;
these fixtures do not execute successful transactions or establish natural NPC
access, forging effects, medal totals or persistence.

The 19 merchant indices, four player-shop flag choices and three-row shop menu
pass native checks. Record IDs, stock, starting cash and other nontext words
remain unchanged. The apparent inventory text `Pて` at `0087185C` is the
50,000-gold field and is excluded from translation. Exact source spans and
ownership are recorded in [MEMORY_MAP.md](MEMORY_MAP.md) and the
[owner report](../build/completion/merchants/source-owners.json).

The [catalog](../translations/merchants.json) is independently translated from
the original Japanese ROM. Existing Mini medal, Medal King, Samson, Douglas,
King and synthesis terms are retained. Anonymous speakers remain `???`, with
casual and polite merchant voices kept distinct. No fan-patch prose is used.

Rebuild with `.venv/bin/python -m tools.build_merchants build`.
Run `.venv/bin/python -m tools.verify_merchants VARIANT` for `english`,
`japanese` and `baseline`, then `.venv/bin/python -m tools.summarize_merchants`.
The full image ledger confirms preservation of all earlier patches and appended
bytes. No font, layout, code, RAM or save expansion was needed.
