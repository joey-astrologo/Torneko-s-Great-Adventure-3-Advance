# Story/event text provenance

Follow-up: the [opening-story translation](OPENING_STORY.md) now relocates and
translates this opening section. Both natural dream responses pass in English,
extending the observed source union to 37 story messages. It also checks all
52 owned story operands and translates the separate event Yes/No table. The
original-ROM audit and historical counts below describe the earlier research.
The [first-village pass](FIRST_VILLAGE.md) adds ten naturally reached village
sources through the escort and first chief meeting, while checking 367 owned
event operands in controlled displays. Current translation progress is 4,634
of 9,318 known entries.

Audited 2026-09-11. The opening story's RAM text has a confirmed source chain:
**original event operand → story wrapper → shared formatter → versioned RAM
buffer → native character reader**. This closes the main opening-story RAM
question from [TEXT_COVERAGE.md](TEXT_COVERAGE.md), within the route described
below. It does not establish complete-game extraction.

The audit also records **134 distinct original English credit strings and one
punctuation-only Japanese dialogue source** outside the master inventory.
These are kept in a separate resource report. No English is taken from the fan
translation. The current master, authored translations, glossary and playable
ROM remain unchanged: 9,318 inventory entries, 4,110 translated/inserted and
5,208 remaining. Already-English credits do not increase translation progress.

## Natural route and what it proves

The unmodified 16 MiB Japanese ROM is booted with the disposable new-Adventure-Log
save produced by the preceding coverage audit. After 600 boot frames, the harness
traces normal button inputs: load the log, then 48 A presses with 300 released
frames between them. It follows the opening narration, voyage/birthday scene,
storm, village arrival and first bedroom conversation. No ROM patches, register
redirects, supplied text pointers or skipped waits are used in this capture.

| Observation | Result |
|---|---:|
| Fetched event commands | 2,702 |
| Story buffer versions / distinct original source starts | 36 / 36 |
| Sources already in the master | 36 |
| Attributed native story character reads | 1,803 |
| Unattributed story character reads | 0 |
| Observed story opcodes | 25: 26 messages; 27: 9; 2C: 1 |
| Largest observed formatted payload | 118 bytes |

The RAM buffer is reused for all 36 messages. The tracer associates a read with
the latest formatter output for that buffer and compares its exact bytes at the
actual RAM byte offset. It does not infer provenance by searching for similar
Japanese or equating source offsets with formatted offsets: substitutions can
change the latter. Each formatter input is checked against its preparation,
wrapper argument and the same event controller's fetched operand.

[Natural coverage](../build/story-provenance/natural-coverage.json) lists every
source ID. [The full trace](../build/story-provenance/natural/trace.json) records
commands, caller addresses, formatter output, reads, inputs and source hashes.
[Sampled route screenshots](../build/story-provenance/route-contact-sheet.png)
show the reached scenes; individual captures are in `build/story-provenance/natural/`.
Only this reached sequence is covered, not every dialogue branch in those areas.

## Reader and storage implications

`08064E42` fetches two words from the current event cursor: a command word and
operand. The command's low byte selects a handler in the 171-entry jump table.
The checked text handlers pass the operand as a direct ROM text pointer. They
do not obtain these messages from an additional compressed text bank.

Five wrappers feed `08061680`, which calls the existing shared formatter at
`08061726 → 0807D8CC`. Its output starts at `structure+0C`; its payload limit is
`structure+40B`, allowing **1,023 payload bytes plus a NUL terminator**. The next
word, `structure+40C`, holds the read cursor. In this route the structure is
`02033F48` and buffer is `[02033F54,02034354)`.

That is a per-message RAM limit. Expanded ROM storage does not enlarge it, and
the largest tested Japanese message, 118 bytes, is not a demonstrated English
stress limit. Future story insertion must budget the final substituted payload
and check page width/pagination separately. Source relocation remains subject
to the shared allocator and exact pointer ownership.

| Event opcodes | Text recipient | Behavior established |
|---|---|---|
| 23, 2A, 96 | `08061244` | Story preparation with flags 42. |
| 24, 2B | `0806128C` | Alternate window mode, flags 42. |
| 25, 2C, 97 | `080612D4` | Story preparation with flags 142. |
| 26, 2D | `08061320` | Alternate window mode, flags 142. |
| 27, 28 | `08061200` | Narration wrapper, flags E1. |
| 29 | `0806136C` | Queue a direct source pointer and two positions for later drawing. |

Thirteen controlled native cases execute the original fetch/dispatch from
`08064E28` and stop at the recipient. They use synthetic command words in
disposable RAM and a real Japanese source pointer. This proves operand routing
for these branches, not that every matching ROM word is an event command or
that every branch is naturally reachable. The 96/97 cases also consume one
following 98 list record. That operand list is a separate consumer family;
its full display, capacity and source inventory remain to be audited.

Handlers can consume additional records, branch or replace the cursor. An
eight-byte fetch does **not** establish a fixed eight-byte grammar for every
script. The additional
[plain-header scan](../build/story-provenance/plain-header-scan.json) deliberately
checks only aligned pairs whose whole first word equals one of these opcodes.
It finds 3,362 pair shapes, including matches to 2,656 master source IDs and ten
pairs outside the master. Only the reviewed punctuation source among those ten
is confirmed here. Empty data, single Latin characters and assertion labels
illustrate the remaining ambiguity. Nonzero command parameters, unaligned
commands, RAM operands and other families are outside this narrow scan.

## Newly recorded resources

[reviewed-resources.json](../build/story-provenance/reviewed-resources.json)
contains exact source starts/ends, raw bytes, decoded tokens, command words and
operand locations. The [memory map](MEMORY_MAP.md#storyevent-source-provenance-2026-09-11)
records these ranges and their consumers. Neither report grants insertion
ownership or approves the gaps as free space.

The credits command span contains 135 positioned-text references to 134 distinct
strings: roles, staff names and original copyright lines, already in English.
Opcode 29 stores each direct pointer with signed positions in a 16-slot RAM
queue. The later consumer loads that pointer and passes it to the draw helper
at `08062A54`. It does not copy the string into the story formatter's buffer.

All 135 references pass controlled native queue writes and pointer/position
reads through the draw-call boundary. Fixtures rotate through all 16 slots,
verify that adjacent slots retain their bytes, and restore state between cases.
Negative x follows the native centering calculation; negative y uses relative
spacing. The queue writer has no visible bounds check, so these tests do not
approve adding slots or exceeding the original capacity. They do not play the
ending, render the entire credits sequence, or validate relocation.

The other source is the line `＊「……　……。` at `00AB94E8`. Its opcode-25 command
at `00AB94AC` passes the original pointer through the wrapper and formatter into
the native story buffer, with all 17 source bytes preserved. Its natural event
condition and eventual English presentation still need context. Both this line
and the credits lack the Japanese letters needed to pass the extractor's
language threshold, explaining their omission.

## Validation and remaining work

[Acceptance](../build/story-provenance/acceptance.json) records 163 passing unit
tests, the 36 natural source chains, 13 dispatch cases, 135 credit cases and the
punctuation formatter case. Seven new tests check provenance failures including
wrong event operands, changed source bytes, wrong versions of a reused buffer
and unattributed reads. Eighteen pre-existing translation/inventory/build files
match the hashes recorded before the audit. The Japanese ROM is checked against
the project manifest; all emulator state/save fixtures are disposable.

To reproduce, retain the preceding audit's `runtime/creation/created.sav` and
this audit's `before/hashes.json` preservation baseline, then run:

```sh
.venv/bin/python -m tools.trace_story_provenance
.venv/bin/python -m unittest discover -s tests > build/story-provenance/unit-tests.log 2>&1
.venv/bin/python -m tools.verify_story_provenance
```

The Ghidra listings are read-only exports from the pinned original project,
with exact instructions taking precedence over provisional decompiler output.
`tools/ghidra_scripts/InspectThumbRange.java` supports branch-range exports;
undisassembled/data halfwords remain marked rather than being forced into code.

Next translation milestone: the complete default-ally-nickname family, together
with its copy/display/save consumers and the related short name-format resources
found by the previous audit. Translate the family as a batch after confirming
its storage limits. Broader story translation can then use this event provenance
work to establish source owners and native layout cases.

Coverage work still includes later routes, selection-list operands, other RAM
producers, relative/computed text families, compressed resources, graphics
lettering and the earliest uninstrumented boot frames. Personal playtesting
remains optional; track those routes in [PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).
