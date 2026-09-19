# Companion combat message joining

Approved following the [companion combat audit](COMPANION_COMBAT_AUDIT.md).
The fix composes after medal-trade and handles the existing native coloured
monster names in both the damage/XP and broader combat joining paths.

Examples now join when they fit:

- Goot1 gained 6 XP.
- Goot1 took 6 damage.
- Goot1 reached level 6.
- Critical hit! Goot1 took 6 damage.
- Goot1 is no longer confused.

The nickname keeps its original colour, and the following text returns to its
normal colour. Names with level suffixes and multiple styled actors use the
same conditional rules. No translations or nickname/save fields changed.
The separate defeat sentence still stays separate from the following XP gain.

## Implementation and boundaries

The new wrappers recognize the observed `03 05 05` ally-colour sequence and
`03 06` reset. These contribute zero pixels, but all bytes still count toward
the **59-byte history payload limit**. Visible text must fit **208px**.
Unsupported or incomplete controls, overlong names/numbers and insufficient
output buffers keep the original wrapping. The damage helper now also rejects
a buffer whose terminator reaches the capacity limit: tests found it could
otherwise join a partially formatted defeat/XP message.

The source allowlists and approved sentence spans are unchanged. This covers
both the eight affected earlier templates and 168 affected broader combat
spans identified by the audit; it does not approve the 35 deferred marginal
spans or join unrelated sentences/dialogue. Byte and width limits still mean
some long substitutions legitimately remain multiline.

The new component appends 880 bytes of code plus two alignment bytes. The
[allocation plan](../build/companion-combat/allocation-plan.json) and
[memory map](MEMORY_MAP.md#companion-combat-insertion-2026-09-19) document the
new wrapper ranges and intentional formatter-hook supersession. Old wrappers,
text, tables and other allocations remain intact. No permanent RAM or save
reservations are added; wrapper stack frame sizes remain unchanged.

## Native checks

Every `./build.sh` runs `tools.verify_companion_combat` on the exact candidate,
in addition to the earlier menu, combat, damage/XP and medal checks. Its report
and hash are recorded under `companion_regression_*` in the build receipt.

The new suite uses actual native nickname generation and all three actor-name
formatters, then exercises:

- Both generated forms: coloured Goot1 and coloured Goot1Lv99, plus mixed actors,
  wide values, unsupported colour controls and incomplete controls.
- All 280 existing source entries across six profiles, including non-actor
  controls; 2,923 total full-format comparisons with boundary/capacity cases.
- 1,684 native queue/history cases, with ring wrap and byte-preservation checks.
- Exact 208/209px and 59/60-byte boundaries. The byte fixture has two styled
  names, so all ten invisible control bytes count.
- 1,239 short-destination/line-mode cases across all 177 affected source keys.
- Six attacker/ordinary/critical/brutal continuation sequences preserving
  history flags and the preceding attacker record.
- Six native rendered examples; glyph identity and horizontal bounds are
  checked, with foreground pixels checking name colour and reset in four.

Oversized artificial source rows that already exceed the stock history limit
are not enqueued; this is not a claim to expand the engine's history capacity.
User saves are hashed before and after, while emulator sessions use disposable
states and cartridge saves. These tests exercise controlled native paths, not
a natural Tipper-section battle replay.

The new suite rejects the pre-fix medal-trade ROM on the native coloured XP
case. A complete ROM comparison confirms changes are confined to the owned
formatter hook and the new append allocation range.

[Native report](../build/companion-combat/verification/report.json) ·
[XP example](../build/companion-combat/verification/english/gameplay.001b4e23-final.png) ·
[Damage example](../build/companion-combat/verification/english/gameplay.001b4dac-final.png)

The component ROM SHA-256 is
`67a15ab8f3bc6d1d56526383278c304b382c271b6f7997468010df7b800e9582`.
Use `build/torneko-3-english.json` for the latest publication receipt and its
exact candidate-bound reports.

```sh
.venv/bin/python -m tools.build_companion_combat --prepare
# Document changed ranges before insertion.
.venv/bin/python -m tools.build_companion_combat
.venv/bin/python -m tools.verify_companion_combat
./build.sh
```

Generate fresh combat messages when playtesting: old saved message-history
rows retain their earlier line breaks.
