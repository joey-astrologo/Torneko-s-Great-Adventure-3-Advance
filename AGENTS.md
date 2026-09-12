# Project rules

## Continue through completion

The user authorized completing the remaining translation work continuously on
2026-09-11. Do not stop after a section to ask for another "ready" message.
Continue through source review, independent translation, terminology research,
insertion, emulator checks and documentation. Keep useful progress updates and
reviewable intermediate builds. Stop for user input only when a concrete issue
requires their judgment or evidence that cannot be obtained independently.
Deferred personal playtesting is not such a blocker. Keep uncertainty and
unverified extraction candidates explicit; do not declare the game complete
merely because the current inventory has been processed.

## Record discoveries and prevent insertion collisions

The user requires location/range discoveries to be documented as they are made,
before those discoveries are used for insertion. This applies to ROM data/code,
pointer tables, text pools, font assets, RAM reservations and save-record fields.

- Maintain [docs/MEMORY_MAP.md](docs/MEMORY_MAP.md) as the central index. Record
  the address space, start and exclusive end, purpose/owner, evidence, certainty,
  and affected build or runtime context. Link detailed machine-readable sources
  rather than hand-copying thousands of entries into a second authority.
- Preserve all original ROM bytes except explicitly owned, checked patches.
  Unidentified space, zero/FF runs, extraction gaps and relocated source strings
  are not approved free space. Record evidence before approving any reuse.
- Allocate new text, tables, fonts and code through the build's shared allocator.
  Include alignment in the allocation ledger. Separate proof ROMs may reuse the
  same offsets; rebuild their components together instead of stacking patches.
- Before an insertion build, check the combined allocations and original-ROM
  patch ranges across all its components. Reject unexpected overlaps, duplicate
  owners, out-of-range writes and source-byte mismatches. Document and explicitly
  model intentional shared ownership or containment; never silently overwrite.
- For RAM/save changes, document sizes, lifetimes and adjacent fields. A save
  record offset is not a physical save-file address, and a transient stack buffer
  is not a permanent reservation.
- Update the map and relevant technical notes in the same work that establishes
  or changes a range. Generated reports must identify their source/output ROMs.

## Translation source

Use the pinned Japanese original as the source and build base. The partial fan
translation is a technical reference only; do not reuse its English or font
assets. Keep unverified extraction candidates separate from verified pointer
ownership. Preserve independently authored English and notes when regenerating.

## Series terminology

Follow [docs/TERMINOLOGY.md](docs/TERMINOLOGY.md) and the Japanese-identity entries
in [translations/glossary.json](translations/glossary.json). Use modern official
Dragon Quest terminology for items, enemies, spells and shared series terms,
with XI/XI S as the baseline and other modern official releases for gaps or
documented revisions. Match the exact Japanese entity and variant. Record the
reference game, source URL and evidence quality; a fan-maintained reference is
not itself an official source. Mark unresolved or Torneko-specific choices.
Preserve official localized puns when the species matches; do not replace them
with literal Japanese translations or infer mechanics from a name's wordplay.

Translate descriptions independently from Torneko 3's Japanese effects. Do not
import another game's mechanics or copy its description. Check all occurrences,
including synthesis headings and starter defaults, when changing a term. Keep
the full glossary name; record any necessary display abbreviation separately
after checking the real font/layout. Historical proof labels are not terminology
authorities. Apply the same review to enemy names before their first insertion.

## Playtesting and translation progress

The user may defer personal playtesting. Do not make it a prerequisite for
source research, glossary work or translation drafts. Track pending gameplay
coverage in [docs/PLAYTEST_BACKLOG.md](docs/PLAYTEST_BACKLOG.md), continue
appropriate automated validation, and distinguish reviewed language from
verified ROM insertion and runtime behavior.
