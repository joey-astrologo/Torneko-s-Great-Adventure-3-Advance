# Translate and revise text

Run commands from the repository root using `.venv/bin/python`. The source is
the pinned Japanese original. Do not copy English or fonts from the partial
fan translation. Read [TERMINOLOGY.md](TERMINOLOGY.md) for Japanese-identity
matching and modern official Dragon Quest naming.

## Find the current wording

```sh
.venv/bin/python -m tools.prose_review show core-gameplay 0 20
.venv/bin/python -m tools.prose_review status
.venv/bin/python -m tools.prose_review export
```

`show` uses zero-based catalog indices and an exclusive end index. `export`
writes reference JSON under `build/prose-review/effective/`; it does not build
a ROM. Catalog names and pinned hashes are in
`translations/prose-review/review.json`.

| Data | Role |
|---|---|
| `translations/<catalog>.json` | Historical Japanese sources, English and reader ownership |
| `translations/prose-review/revisions.json` | Reviewed wording overrides over those pinned catalogs |
| `translations/glossary.json` | Terminology identities, full names and evidence |
| `translations/unowned-text-review.json` | Uninserted drafts; not build-ready text |
| `translations/combat-line-joins.json` | Approved runtime joining spans, not a prose-editing file |

Effective catalog English is the language-review view. Later compact menu
replacements and runtime joining can change what appears on screen. Use the
current ROM and combined ledger to confirm final inserted/displayed wording.

## Author an edit

Translate naturally while preserving the Japanese meaning and game-specific
mechanics. Preserve typed controls, substitutions and continuation markers;
do not guess widths from character counts. Keep full glossary names separate
from justified display abbreviations. See [TEXT_SYSTEMS.md](TEXT_SYSTEMS.md),
[TRANSLATION_PIPELINE.md](TRANSLATION_PIPELINE.md) and the relevant family report.

For an entry already in `revisions.json`, edit its `english` (and applicable
`display`) and review reason. Keep the original `before`, Japanese, source hex,
ID, index and catalog metadata intact. For a previously unrevised entry, the
Python helper `tools.prose_review.revise(catalog, index, english, reason)` adds
an override while checking the pinned baseline; a pre-existing display override
also requires an explicitly reviewed `display` argument. It refuses duplicates.
This is a Python API, not a `revise` CLI command.

Export again to check baseline consistency and inspect the effective wording.
Do not edit generated exports or reset review inventory with `init` to bypass
hash failures. `mark` only records review progress; it does not review language.

## Insert and validate

**Editing a revision is not sufficient to update the published ROM.** The build
is a chain of checked component checkpoints and prepared plans. Changing an
earlier component can invalidate all downstream hashes, allocations and exact
message addresses, including the combat joining tables.

Two supported development patterns are:

- Prepare/rebuild the changed component and each dependent component in order,
  refreshing affected ownership, approved span addresses and native evidence.
- Add a new cumulative component after the current one, using `RomBuild` to
  append revised payloads and supersede exact owned pointer patches. Preserve
  prior allocations and source bytes; update any address-dependent runtime
  tables affected by relocated messages.

These require implementation work; there is no general one-command importer
that safely performs the whole chain. [PROSE_REVIEW.md](PROSE_REVIEW.md) documents
the earlier review component's commands and tests. Those are checkpoint-specific,
not a promise that an edited earlier plan will pass today's downstream build.

For either route:

1. Establish the actual reader, buffer and layout contract.
2. Document new/changed ranges in [MEMORY_MAP.md](MEMORY_MAP.md) before insertion.
3. Allocate through the shared allocator and check original bytes/ownership.
4. Run the affected native reader tests, including substitution extremes and
   scene/control behavior. Preserve independently authored translations when
   regenerating resources.
5. Integrate the component, then run `./build.sh` for the cumulative gates and
   ROM/BPS publication. Check the receipt and record remaining playtest coverage.

The 30 drafts and unresolved phrase must first gain verified reader ownership;
reviewing their English alone does not make them insertable.
