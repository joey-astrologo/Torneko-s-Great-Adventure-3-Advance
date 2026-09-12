# Japanese drafts awaiting reader context

[The review catalog](../translations/unowned-text-review.json) preserves 30
English drafts and one partially translated line across 31 inventory sources.
It covers a puzzle label, six weight labels, eight battle fragments, two script
test messages, two frontend messages, and twelve duplicate sound/warehouse
resources. Matching duplicates reuse this project's independent translations.

These drafts are not inserted and do not add verified pointer ownership. The
combined ROM still has 8,422 authored source entries; the 79-resource technical
queue remains open. Buffer capacities, layout and runtime use must be established
before a draft is promoted to a build catalog. No original space is released.

The incomplete line at `001B551C` reads `$i0は ★間に落ちて失われた。` in the
original font. The star is present in the actual bitmap. The draft preserves
an explicit unresolved-word marker rather than guessing a kanji or mechanic.
It is not ready for insertion. Other investigation can proceed independently.

The high-ROM duplicates resemble parts of additional linked data images, but
that does not establish whether they are used. Their source ranges and the
comparison evidence remain leads in [the memory map](MEMORY_MAP.md).
