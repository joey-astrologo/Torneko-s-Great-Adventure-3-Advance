# Conditional combat sentence joining

The approved [line-break audit](COMBAT_LINE_BREAK_AUDIT.md) is implemented for
**268 candidate sentence spans plus two critical/brutal-hit continuations**.
Newly generated messages use one line when their actual substituted ASCII text
fits **208 pixels and 59 history payload bytes**. Otherwise their original
breaks remain. Earlier sentences/events retain their breaks. Wording, entity
names, numeric values and font assets are unchanged.

The 35 marginal candidates, dialogue, indexed-glyph messages and other excluded
layouts remain unchanged. The existing damage/XP joining stays active. History
already stored in an old save state keeps its original lines; generate new
messages to observe the change.

## Build and ownership

`tools.build_combat_lines` follows `build_menu_fixes`. The immutable approved
selection, source bytes, pointer owners and unselected regression inventory are
in `translations/combat-line-joins.json`. This freezes the approved audit;
builds do not infer new candidates or require regenerating an audit against a
newer ROM.

A sorted ROM table maps 274 source entry/line/continuation addresses to the 270
approved spans. The new wrapper calls the previous damage/XP wrapper first.
In full-string mode it measures only the approved sentence span in the formatted
result. In line mode it uses an 80-byte transient lookahead buffer, and consumes
additional source lines only when the entire approved span fits. A full or
truncated lookahead cannot pass the 59-byte check. A destination filled to its
terminator limit is conservatively left unchanged in full-string mode.

The guard checks every byte, uses the existing font-width table, and replaces
only internal LF bytes with spaces. It preserves terminators, sentence boundaries,
continuation flags and native source advancement. Native formatter returns stay
on a terminating NUL but advance past a terminating LF; the source table models
that distinction explicitly. No successful joining can skip into the next
string. Leading `!` remains the native history-continuation marker, never a
visible exclamation mark. Critical/brutal continuations are separate rows from
the attacker prefix, retaining their history grouping.

The [memory map](MEMORY_MAP.md#approved-combat-sentence-joining-2026-09-19)
records the append range, exact superseded hook and transient stack lifetime
before insertion. The cumulative shared allocator rejects collisions and stale
source bytes. No new permanent RAM reservation or save field is introduced.
Earlier ROM text and allocations remain intact.

## Native validation

`tools.verify_combat_lines` compares the previous menu-fix ROM and the candidate:

- 1,620 full-format cases: every approved source with normal, wide, narrow,
  Japanese, item-suffix/long-enemy and maximum-slot fixtures. The initial run
  joined 484 cases and retained 1,136 layouts.
- 1,512 paired live queue/history checks, crossing both ring boundaries, with
  exact row bytes, source consumption, history headers and guard bytes checked.
  Another 108 deliberately oversized-original-row cases check formatter fallback
  only; they do not claim the stock history engine can store oversized rows.
- Four exact 208/209px and 59/60-byte acceptance/rejection boundaries, exercised
  through full formatting and live queue/history.
- 1,620 short-capacity full-format checks and 1,644 line-mode checks, including
  buffers of 1, 8, 16, 60, 64 and 80 bytes.
- 109 unchanged multiline sources covering the deferred, control, dialogue and
  already-handled cases.
- 16 critical/brutal sequence runs across both ROMs, with both attacker prefixes,
  normal/wide substitutions, retained attacker history and native continuation
  flags. Native rendered screenshots include those sequences, poison recovery,
  confusion recovery and the warehouse-full message with its first sentence
  preserved.

Every `./build.sh` runs this suite, the 376-case-per-ROM damage/XP suite, and all
seven menu regression routes before creating/checking the BPS and publishing.
The final receipt links each report with its hash. User save/state files are
hash-checked and never overwritten. Controlled native calls establish formatting,
queue/history and rendering behavior; natural gameplay coverage remains separate.

## Reproduce

```sh
.venv/bin/python -m tools.build_combat_lines --prepare
# If allocations change, update/review MEMORY_MAP.md before insertion.
.venv/bin/python -m tools.build_combat_lines
.venv/bin/python -m tools.verify_combat_lines
./build.sh
```

As with earlier components, the build uses pinned prepared resources and
historical component checkpoints; see [BUILD.md](BUILD.md).

## Published acceptance

`./build.sh` published ROM SHA-256
`0c21286fadcb59776b7a6639ce082a7a3180faa01621a8afc74c6d6601ebfc13`.
The 939,962-byte BPS reproduces the complete 32 MiB ROM byte for byte.
All counts above passed on that exact candidate, as did 376 legacy damage/XP
cases per ROM and seven menu routes. The actual pre-join ROM was rejected by
the combat publication gate without replacing the then-current outputs.

Representative native captures:
[critical hit with attacker](../build/combat-lines/verification/english/tutorial.001b5038-tutorial.001b5032-final.png),
[warehouse sentence boundary](../build/combat-lines/verification/english/gameplay.001b468f-final.png).
