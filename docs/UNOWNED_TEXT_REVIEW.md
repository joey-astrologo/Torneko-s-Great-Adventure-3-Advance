# Japanese drafts awaiting reader context

[The review catalog](../translations/unowned-text-review.json) preserves 30
English drafts and one partially translated line across 31 inventory sources.
It covers a puzzle label, six weight labels, eight battle fragments, two script
test messages, two frontend messages, and twelve duplicate sound/warehouse
resources. Matching duplicates reuse this project's independent translations.

These drafts are not inserted and do not add verified pointer ownership. The
combined ROM still has 8,422 authored source entries; the 74-resource technical
queue remains open. Buffer capacities, layout and runtime use must be established
before a draft is promoted to a build catalog. No original space is released.

The incomplete line at `001B551C` reads `$i0は ★間に落ちて失われた。` in the
original font. The star is present in the actual bitmap. The draft preserves
an explicit unresolved-word marker rather than guessing a kanji or mechanic.
It is not ready for insertion. Other investigation can proceed independently.

The user supplied a further lead: stars in Mystery Dungeon can mark plated
weapons/shields protected against rust degradation. This is recorded as user
context, not yet verified for this particular Torneko 3 source. Here the literal
star sits within `★間`, after the `$i0` item substitution and `は`; it is separate
from a marker generated as part of the item name. The next gameplay-source
investigation should compare the equipment-status formatter with item-landing
and item-loss readers before assigning the phrase a meaning.

The [gameplay candidate pass](GAMEPLAY_CANDIDATES.md) now records that
comparison and seventeen per-source findings. Paired native landing, dungeon
name, item-footer, frontend-confirmation and status-prefix checks passed. None
established new candidate ownership; all seventeen remain in this review queue.

The high-ROM duplicates resemble parts of additional linked data images, but
that does not establish whether they are used. Their source ranges and the
comparison evidence remain leads in [the memory map](MEMORY_MAP.md).

A [limited computed-address scan](../build/completion/computed-text-review.json)
also found no new leads for the 74 remaining starts. It follows selected
constant operations for at most 48 straight-line Thumb instructions after
1,651 nearby literal-load seeds in `[080000C0,0809A800)`. Instruction boundaries
are provisional; branches, calls and unsupported operations stop each path.
Variable indexing, RAM-derived pointers, other code regions and cartridge
mirrors are outside this scan. Its negative result does not establish that
these resources are unused or grant insertion/free-space ownership.
