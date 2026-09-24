# Japanese-reference coverage audit

The post-game report exposed a reference-coverage problem, not missing English
translations. Authored-source counts had been mistaken for stronger runtime
coverage than they provide. One Japanese string can have several readers;
redirecting one reader does not translate the others.

## Confirmed defects and correction

The broader audit found **13 distinct affected sources at 15 missing pointer
words**:

- Four post-game menu labels: Story mode, Extra mode, Help and Cancel.
- Eight item-effect variants: burning, freezing, sand and wind, each with a
  single-item and plural-item message.
- “But nothing happened.” through three startup-cache references.

All already have independently authored English used through other references.
`tools/build_reference_coverage.py` connects the missing readers to those same
owned English strings. It adds no text/code allocations and changes no save
format or permanent RAM reservation. The existing fit-aware formatting remains
in use. [MEMORY_MAP.md](MEMORY_MAP.md#duplicate-reference-repair-2026-09-23)
records every pointer word before insertion; the generated combined ledger
rejects source mismatches and overlapping ownership.

Pre-fix ROM: `d1a1c0fde27919fc3b3ab484d6c6b7cc4995cebc51166df8489b98136da90c80`.
Corrected ROM: `d9fcb4b0ce9219679c22e40cc377ad64f26bd896feecb80ce18d6f28932fd82c`.
The ordinary inventory totals do not change: these are missing references to
existing entries, not 13 newly discovered strings or the 30 unowned drafts.

## Why the earlier checks missed them

[The post-game menu investigation](POSTGAME_MODE_MENU_AUDIT.md) shows that the
curated pointer list covered the other mode-menu table. The completion extractor
excluded these already-curated strings. The master inventory already contained
the missing reference candidates, but they had not been promoted to verified
owners. Worse, the old native menu test reached this exact menu but verified
row count and bounds against whatever language the ROM drew. Japanese passed.

The item messages had translated references in code/another table. Their
separate initialized pointer arrays remained Japanese in the ROM startup image
and were copied into RAM at boot. The audit disassembled the native selectors,
captured the cold-boot RAM values, then ran each selector and the real message
queue to confirm Japanese output. These are confirmed executable reader paths;
the audit did not naturally trigger every item-destruction event.

## Stronger build checks

`tools.verify_reference_coverage` is mandatory in `./build.sh` before the ROM
and BPS are published. It checks:

- All 15 repaired words against independently specified English and the
  intended existing allocation references. The previous ROM fails all 15.
- Exact expected English for 19 enumerated typed-menu tables, including both
  flag configurations for both mode-menu tables: 21 cases / 77 drawn rows.
  These are the tables enumerated by this suite, not every menu in the game.
- Cold-start initialization and all 11 affected native cache selectors, with
  expected English formatting and queue/history preservation checks.
- A natural cold-boot post-game new-game/name-confirmation route using a
  disposable copy of the supplied save, followed by exact mode-menu labels.
  The original save is hash-checked unchanged. This route opens Log 2; it is
  not a claim to test every Adventure Log slot or every post-game mode outcome.

The build receipt links and hashes the report for the exact published ROM.
The existing menu, combat, damage, companion, item, Trade and save-prompt gates
also remain mandatory. Tests verify expected content, not just successful
rendering of the content encountered.

## Repeatable broader scan

```sh
.venv/bin/python -m tools.audit_reference_coverage
```

This read-only scan writes `build/reference-coverage-audit/current/report.json`,
pinning the original/output ROM, master inventory and audit script. It scans
all byte alignments and all three GBA cartridge address windows for unchanged
original pointer-shaped words targeting Japanese in the current inventory,
including interior positions and suffixes. It preserves candidate distinctions
instead of silently treating numeric matches as real text pointers.

On the corrected ROM, the scan retains 1,741 candidate targets within 949
source entries. Of the exact source-start matches, 176 have authored English,
183 are retained resources and 10 are unclassified. These numbers are **not
counts of untranslated gameplay messages**. They include pointer-shaped
numeric coincidences, interior text fragments, Japanese input aliases and
superseded tables. No further confirmed reader defect was established in this
pass. None of the surviving authored candidates has an aligned primary-ROM
pointer in the examined code region below 00097000; this is a prioritization
observation, not proof that all other candidates are unused.

Explicit dispositions include 98 preserved blank-scroll matching references
and four original keyboard headers whose reader uses a replacement table.
High-data-array references remain unverified; they are not blanket-approved
for insertion or declared unused. Other raw candidates likewise require reader
or data-format evidence. The report retains every candidate for follow-up.

Earlier pre-fix evidence remains in `build/reference-coverage-audit/raw.json`,
`menus/report.json`, `cache-readers.txt` and `cache-runtime/report.json`;
`build/postgame-menu-audit/replay/` retains the user-save reproduction. Use each
report's ROM hash when comparing it with a current result.

## What prevents a 100% claim

The project still has 31 unclassified Japanese sources (30 drafts and one
unresolved phrase) without established insertion readers. They are distinct
from these repaired references. See [UNOWNED_TEXT_REVIEW.md](UNOWNED_TEXT_REVIEW.md).
The separate [text-discovery audit](TEXT_COVERAGE.md) and
`tools.audit_text_coverage` cover extraction leads beyond the current inventory.

Absolute-pointer scanning cannot prove coverage of computed/relative readers,
compressed text, alternate encodings or graphical lettering. Nor does a
controlled render prove every natural event and save-state branch. Full ending
playback and broader post-game/event coverage remain in
[PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).

The acceptance target is that every verified player-facing reference reaches
reviewed English (or an explicitly accepted preserved resource), with content
assertions on its reader. Unknown references and unexplored branches must stay
visible. “All catalog entries processed” is not that target, and passing this
new suite is not evidence that the entire game is 100% covered.
