# Event commands found by the text extractor

The remaining-resource audit confirms that 205 apparent short strings are
event command prefixes. For example, a byte decoded as `H` is opcode `48`,
not dialogue. These entries retain their original bytes and are counted as
program data, never as authored English.

The proof follows the game's readers through a concrete chain:

1. The original scene cache selects a 36-byte scene descriptor.
2. The actor/object group reader selects a count/pointer pair and walks
   24-byte records with the native stride.
3. The record constructor reads one of its four script fields and registers
   that pointer in a native event-controller slot.
4. Native activation selects that slot. The dispatcher fetches the exact
   original eight-byte command, advances its cursor and selects its opcode
   handler. Execution stops before the event action.

[Candidate ancestry](../build/completion/scene-resource-audit/source-candidates.json)
records exact scene IDs, group words, record fields, original bytes and all
discovered owners. [Native verification](../build/completion/scene-resource-audit/native-verification.json)
records one complete native chain per classified source, controller guards,
the dispatch target, ROM/fixture/tool hashes and preserved command bytes.
All ranges and readers are indexed in [the memory map](MEMORY_MAP.md).

Group counts vary between scenes. A preliminary uniform-count scan was
rejected. The final structural scan stops at malformed pairs/records and
before another named descriptor resource; it only proposes candidates.
The native proof supplies selected scene/group/record indexes, so it does
not establish natural branch reachability or a complete event grammar.
Neither the candidate scan nor the proof grants writable space in the ROM.

The full native controller occupies 168 bytes for these activation tests,
including its saved state. Fetch-only tests used smaller fixtures; this audit
records the larger temporary range explicitly. No game RAM/save layout changes.

One additional apparent string, at `0091B688`, is independently confirmed as
an event command by the original opening-route trace. The other naturally
observed command candidate was already among the 205 and is counted once.

```sh
.venv/bin/python -m tools.audit_scene_resources prepare
.venv/bin/python -m tools.audit_scene_resources verify
.venv/bin/python -m tools.audit_retained_resources
```

The proof has been revalidated against the accepted text-polish ROM. A later combined
build must preserve or revalidate its source/pointer evidence before advancing
the retained-resource report.

Eight further extraction candidates lie wholly within the eight-byte commands
already fetched by this proof. Their exact containment is recorded in the
retained-resource report; these are operand/parameter bytes, not new commands.
The following command at `00B9F024` is excluded from that containment claim.
It now has separate evidence in the remaining-field audit: native fetch of
the preceding opcode 45, followed by a bounded slice from its callback return
to A7 fetch/dispatch. The virtual callback and natural event are untested.
