# Remaining battle feedback and dungeon services

This component has passed its [native checks](../build/completion/battle/component-checkpoint.json):
843 English cases, 600 English screens and 302 Japanese pixel comparisons.
All 382 pointer words, both cold caches and 18 original table selections pass.
The complete combined ROM is reconstructed from its allocation ledger and
preserves every earlier patch and appended byte. See [COMPLETION.md](COMPLETION.md).

The [catalog](../translations/battle-completion.json) adds 298 sources through
382 pointers: 247 scrolling feedback messages and 51 paged shop, companion
and recruitment messages. Fourteen normalized Japanese matches reuse our own
earlier drafts. Other prose is independently translated from the original ROM.
Unreferenced leads and growth-type labels retain their separate review status.

Scrolling text is bounded by 208 pixels, 59 payload bytes per history row and
the original queue capacity. Paged dialogue retains the existing 1,000-byte
formatter and three-line page engine. Two original leading symbols in the
Yggdrasil-leaf messages retain their indexed `F9 AC` bytes and measured glyph
width; the extraction label `⑪` is not prose. Native checks include normal,
wide and narrow substitution fixtures, exact history copies and original
scrolling, complete dialogue pages, cold pointer caches and 18 table-selection
slices. [MEMORY_MAP.md](MEMORY_MAP.md) records their exact ownership.

The glossary adds **Kabuff** (スクルト) and **Kathwack** (ザラキーマ) from
secondary XI naming references: [Kabuff](https://dragon-quest.org/wiki/Kabuff)
and [Kathwack](https://dragon-quest.org/wiki/Kathwack). These are naming matches,
not primary-source verification or imported mechanics. All other spell/item
names use existing identities, including Squelch, Gust Slash and Blade of
Ultimate Power. The third revival-obstruction source repeats “wall” where
the parallel healing table says “crystal”; it is translated as written and
recorded in the catalog, without a game-logic change.

Rebuild with `.venv/bin/python -m tools.build_battle_completion build`.
Run native checks with
`.venv/bin/python -m tools.verify_battle_completion VARIANT`, for `english`,
`japanese` and `baseline`. Natural combat, successful shop transactions,
recruitment and item-state save persistence remain separately unverified.
