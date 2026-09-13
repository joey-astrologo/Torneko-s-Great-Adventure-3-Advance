# Remaining gameplay text investigation

The seventeen gameplay/frontend candidates remain unowned after this pass.
Their exact source bytes are preserved in both the Japanese original and the
current English ROM. No draft was inserted, classified as unused, or released
as free space. Inventory accounting remains **8,422 authored + 822 retained +
74 open**.

The [source review](../build/completion/gameplay-candidates/source-review.json)
records a finding for each candidate. The
[native report](../build/completion/gameplay-candidates/native-verification.json)
pins both ROMs, the fixture, helper code and disassembly. Per ROM it checks:

- Four item-landing flag combinations, selecting the existing ground, water,
  and ground/water messages without changing the flags or adjacent bytes.
- All 64 dungeon-name getter entries. None selects the adjacent “Puzzle” label.
- All 370 item footers with zero enhancement and no synthesis effects. Outputs
  use the existing power/mark formats or separator; source records and the
  guarded 1,024-byte destination remain intact. The six weight labels do not
  occur in these outputs.
- Three frontend mode-confirmation selections, stopped before the message call
  or its consequences. These use the already translated scenario, extra and
  Barinabo Challenge confirmations.
- Six equipment/status flag combinations through the original item-name
  formatter, preserving its 100-byte output guards and inputs. These select
  custom prefix glyphs `8750..8753`, separate from the unresolved prose star.

The user's plating explanation is useful context. The Japanese Plating scroll
description independently confirms protection against weapon/shield
deterioration, but the unknown sentence has a literal `★` **after** `$i0は`,
inside `★間`. The tested status-prefix formatter does not produce that literal
glyph. This comparison does not establish the prefix symbol's mechanic or
resolve the sentence. Its English remains incomplete.

Disassembly also covers neighbouring actor-name, cure, explosion, defence,
pot-transit and trap routines. The projectile dispatcher's message tail selects
the already translated item-vanished source through `000183E0`; its other
branches include stack-derived pointers, so this is not complete provenance
coverage. The adjacent staff-light candidate remains unresolved. Neither
source proximity nor a missing literal reference establishes non-use.

Reproduce the controlled audit with:

```sh
.venv/bin/python -m tools.audit_gameplay_candidates
```

These checks add bounded reader evidence, not natural gameplay coverage. The
separate [normal-button cave clear and save](CAVE_CLEAR.md) has since passed.
Range ownership and fixture lifetimes are indexed in
[MEMORY_MAP.md](MEMORY_MAP.md).
