# Text extraction coverage audit

Audited 2026-09-11. The expanded scan and opening-game reader checks improve
coverage evidence, but **do not establish that every game string has been found**.
Fourteen omitted UI resources now have checked static consumers. They include
formatting templates, unknown-name placeholders and a numeric glyph strip;
they are recorded separately from translation sentences.

The current inventory and English build remain unchanged: **9,318 master entries,
4,110 distinct translated/inserted entries, 5,208 remaining**. Catalog overlaps
are counted once. This is **44.11% by entries**, or **36.19% by extracted source
bytes** (149,717 of 413,712 bytes). These are inventory metrics, not a percentage
of all player-visible text or a prediction of remaining work.

## What was checked

[static-audit.json](../build/text-coverage/static-audit.json) pins the original
ROM, master, review queue and audit implementation hashes.

| Audit | Result / scope |
|---|---|
| Pointer words | All four byte alignments across the entire 16 MiB original, including the three cartridge windows at `08000000`, `0A000000` and `0C000000`. |
| Pointer-shaped matches | 355,195 words, normalized to 180,542 distinct targets. These include ordinary data and are not approved pointer owners. |
| Additional string-start scan | 1,349,799 non-empty, uncovered NUL-boundary starts examined, including unaligned starts outside mapped text banks. |
| Existing review queue | All 11,838 entries received a reproducible disposition. Decoder failure, weak/repetitive text, short formats and unresolved grammar remain distinct. |
| Candidate shortlist | 2,414 leads with raw bytes, exact spans, discovery method and references. Overlap, suffixes and false positives remain possible. |
| Other known fonts | All 4,704 rejected queue targets retried with fonts 1 and 2: 9,408 attempts, no successful Japanese decode of at least four characters. |
| Checked omitted resources | 14 resources with source bytes, literal words and disassembled consumers recorded. |
| Native digit conversion | All eleven lookup symbols pass the original eight-position conversion loop, including the slash/star sentinel and guard bytes. |
| Native opening routes | Japanese title/settings, new Adventure Log/name creation and opening story. All observed ROM-backed text is covered at valid source boundaries. |

The broadened scan uses the installed mGBA source's cartridge-window mapping:
mask with `SIZE_CART0-1` and reject offsets outside the physical input. See
`.tools/src/mgba/src/gba/memory.c`, including `LOAD_CART` and byte loads.
It preserves odd targets as data addresses rather than silently treating them
as Thumb function pointers. Pointer-shaped words remain candidates even when
their normalized address is an existing string start.

## Confirmed omissions

[reviewed-resources.json](../build/text-coverage/reviewed-resources.json) is the
exact resource record: fourteen source ranges, raw bytes/tokens, literal words,
native load instructions, roles and evidence. All are outside the current master.
The [memory map](MEMORY_MAP.md#extraction-coverage-audit-2026-09-11) indexes their
ranges and reader context; none of the findings authorizes allocation or reuse.

The omissions include:

- Colour/name/level templates in the actor-name helpers, including the paths
  that decode a stored nickname before formatting it.
- Ally-list row and current/total count formats.
- Level/HP and unknown-name displays.
- Choice-row colour wrappers and record-list name formats.
- The numeric picker's `＊０１２３４５６７８９` strip: eleven **two-byte glyphs**,
  indexed directly by arithmetic, followed by NUL. Treating it as an ordinary
  translated sentence would break that structure.

Most of these have few Japanese letters, so the broad extractor's language
threshold excludes them. An existing ROM reference alone does not overcome that
filter. They demonstrate a real inventory gap even though much of their content
needs formatting/layout treatment rather than an English prose translation.

The native digit probe executes `0807B7B8–0807B7EA` on the original ROM and checks
all eleven symbols through eight output positions. Its CPU registers and input
are supplied; it is not a complete interactive number-picker test. Disassembly
establishes the other resource consumers; their complete natural callers and
future relocation still need context-specific checks.

The record-list format near `00C4CE7C` uses a record's `+17` text field, and its
reader separately uses a `5C` stride. This is a lead for later name/save work;
it does not identify a physical save offset or establish ranking compatibility.

## Candidate review and false positives

The [candidate TSV](../build/text-coverage/candidates.tsv) and
[full candidate JSON](../build/text-coverage/candidates.json) contain the
shortlist. [Review dispositions](../build/text-coverage/review-dispositions.json)
account for every original queue entry. [Additional references to known sources](../build/text-coverage/extra-known-references.json)
retain byte-boundary classifications without granting pointer ownership.

| Existing queue disposition | Count |
|---|---:|
| Weak decoded candidate | 6,954 |
| Decoder rejected | 4,704 |
| Short/format candidate with a pointer in the code region | 84 |
| Japanese-like candidate | 78 |
| Repetitive decoded candidate | 11 |
| Unresolved grammar | 7 |

These are mechanical classifications, not final text/non-text verdicts. Sampled
rejected prefixes and new leads include long repeated kana, numeric patterns
and adjacent font indexes that decode as unrelated kanji. This is why the 2,414
leads are not added to the translation denominator. The audit does not delete
existing master candidates on a heuristic either.

The other fonts' ordinary character-code sets are subsets of font 0, but their
indexed descriptor orders differ. The [font recheck](../build/text-coverage/font-recheck.json)
therefore records font context explicitly. Its empty rescue list applies only
to the tested rejected starts and threshold; alternate-font text elsewhere
remains possible.

## Native coverage and its limits

[runtime-coverage.json](../build/text-coverage/runtime-coverage.json) records each
route and trace hash. Across those routes, 33 distinct master sources were
observed through the shared readers:

- 346 aggregated ROM character-read records, all at valid source boundaries.
- 19 ROM draw-input records and 13 ROM formatter-input records, all at source starts.
- Zero uncovered or invalid ROM text events.
- 577 RAM/other character-read records and 15 RAM/other draw-input records are
  retained separately; they do not prove where those strings originated.

Counts are the trace's aggregated records, not distinct sentences or total
executed calls. Fonts 0 and 1 were observed. Instrumentation starts after 600
boot frames, so the earliest boot/logo sequence is outside this trace.

The subsequent [story/event provenance audit](STORY_PROVENANCE.md) tracks 36
opening-story messages from original event operands through the shared formatter
to versioned RAM reads, with zero unattributed story reads on that route. It also
records 134 original English credit strings and one punctuation-only dialogue
source outside the master. These are separate from this audit's 14 UI resources.
The original shared hooks alone do not track every RAM producer. Opening routes cannot establish
later towns, dungeons, companions, results, endings or unused/debug content.
No complete-game reachability claim follows from zero misses on these routes.

Remaining audit work is explicit:

1. Extend the now-checked opening-story source chain to later routes and other
   RAM producers. Audit the separate 96/97 selection-list operands and remaining
   event families; see [STORY_PROVENANCE.md](STORY_PROVENANCE.md).
2. Review the short resources with the next relevant insertion family, starting
   with default ally nicknames and the name/level wrappers found here.
3. Add later gameplay routes and inspect relative/computed references, compressed
   resources and lettering stored in graphics. These formats require their own
   readers; broad successful decoding is insufficient.

Translation can continue alongside these checks. Personal playtesting remains
optional for current translation work; deferred routes are in
[PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).

## Validation and reproduction

[acceptance.json](../build/text-coverage/acceptance.json) pins all audit artifacts
and confirms that the pre-audit catalogs, master, glossary, extraction reports
and current English ROM are unchanged. The original source remains pinned to
SHA-256 `35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02`.
The unit suite passes **156 tests**; six new tests cover cartridge normalization,
unaligned end-of-file pointers, odd targets, source boundaries and overlap rejection.

```bash
.venv/bin/python -m tools.audit_text_coverage
.venv/bin/python -m tools.trace_text_systems --output build/text-coverage/runtime
.venv/bin/python -m unittest discover -s tests > build/text-coverage/unit-tests.log 2>&1
.venv/bin/python -m tools.verify_text_coverage
```

The verifier also reruns the small native digit probe and the other-font recheck.
It requires the existing pre-audit hash snapshot and reader listings, and refuses
stale inputs. The new listing was exported read-only with
`InspectThumbFunctions.java` for `08045088`, `08049184`, `0806DCDC`, `08071700`,
`0807B294`, `0807B604`, `0808467C` and `080853E0`; its hash is recorded with the
resource manifest. The older actor-name listing is preserved as a separate
evidence artifact.
