# Memory map and insertion ownership

Latest combined component build: [continuous completion](COMPLETION.md), occupied
append `[01000000,01069FFA)`; 434,170 bytes,
8,428 allocations and 10,110 checked original patch records.
Exact owners and explicit shared ownership are in
[its ledger](../build/completion/inventory-notice/english-build.json).
The combined text components have passed their documented native checks.
The opening, first-cave and native defeat/save/cold-reload routes also pass
their separately pinned normal-button regression checks.
Full-game translation and discovery
remain in progress. Historical ranges describe their own ROM hashes.

## Extraction coverage audit (2026-09-11)

Read-only discovery under owner `text-coverage`; no insertion ownership or new
free space is granted. The source is the pinned 16 MiB Japanese ROM. The audit
records all byte-alignment pointer candidates in cartridge windows starting at
`08000000`, `0A000000` and `0C000000`, normalized with a `01FFFFFF` mask and
restricted to physical source bytes. These pointer-shaped values may be data.

| ROM occupied range, end exclusive | Reader evidence and resource role |
|---|---|
| Sources beginning `000A9FE8`, `000A9FF4` | Name-format templates used by `080329EC` and `08032B4C`, literals `00032B20` and `00032C78`, passed to native printf at `08032B16` / `08032C6E`. Relevant to the future nickname-copy/capacity audit. |
| Sources beginning `000D96EC`, `000D9970`, `001B4475` | Level/HP format and unknown-name placeholders; literal words `00045244`, `000491B8`, `0006DDB8`. Verified static consumers in `08045088`, `08049184`, `0806DCDC`. |
| Sources beginning `00C3E0B4`, `00C3E0C0`, `00C3E0D0` | Ally-row name/level variants and page/count format in `08071700`; literals `000717E0`, `00071900`, `00071914`. |
| Sources beginning `00C42158`, `00C421C4`; digit strip `[00C421CC,00C421E3)` | Choice-row format, eight-digit numeric format, and eleven two-byte full-width symbols followed by NUL. `0807B604` maps ASCII slash/digits through `(byte-2F)*2`; its loop at `0807B7B8–0807B7EA` writes eight glyphs plus NUL. Preserve stride and sentinel roles. |
| Sources beginning `00C4CD04`, `00C4CE7C`, `00C4CE88` | Name/level and record-list formats plus star marker, readers `0808467C` / `080853E0`. The latter passes a record's `+17` text field to printf and separately uses a `5C` record stride. Save/ranking identity, capacity and persistence are not established by this static observation. |
| Temporary fixture RAM `[03007C00,03007D00)` | Disposable CPU-stack area for the isolated original digit-conversion loop. Input `[03007C0C,03007C14)`, guarded output `[03007C28,03007C39)`. Lifetime is one controlled loop call; CPU context and bytes restored afterwards. This is not a game allocation or save field. |

The generated `build/text-coverage/reviewed-resources.json` pins exact source
starts **and exclusive ends**, raw bytes, literal words, consumers and evidence
for all 14 resources. `short-readers.txt` supplies new disassembly; the two
actor-name helper listings remain in
`build/enemy-items/research/enemy-functions.txt`. All 14 are tracked outside the
master while their insertion/translation treatment is decided. Original source
bodies, pointer words, code, current translated ROM and catalogs are unchanged.
See [the coverage report](TEXT_COVERAGE.md) for scope, candidates and limitations.

## Gameplay help investigation (2026-09-10)

Owner `gameplay-help`; recorded before insertion. All intervals below have an
exclusive end. `translations/gameplay-help.json` pins the exact 191 parsed
sources and pointer owners; `build/gameplay-help/research/` holds the reader
disassembly. Envelopes are occupied source data, never reusable space.

| Space / occupied range | Role and evidence |
|---|---|
| ROM `000EA448–000EA470` | Ten help pointers, indexed by `(menu_id-9)*4` in `08078450`. Source bodies span `000EA470–000EAEE3` (exact ends in catalog). Patch the ten words; preserve source bodies. |
| ROM `001B4EA6–001B4EF0`, `001B4EF0–001B4F0C` | Seven ally order names and seven pointers. Base literal consumers `0001C18C`, `00072BB4`, `00072D48`, `000734E4`. Keep order IDs and table shape. English must fit the existing 30-byte actor slot and 120px budget. |
| ROM `001B4F0C–001B4F38`, `00C3E334–00C3E3B8` | Order unlock and result messages. Exact four selected strings/checked code literals in catalog; `$m0` carries an order name. |
| ROM `001B5B1D–001B65CF` | Next combat/item-effect block: select verified literal and typed ability/speed table owners only. Sources referenced solely by high-address cancellation tables, unreferenced `001B5F14`, and `$i2` source `001B5EBF` remain unpatched pending their reader/slot audit. |
| ROM `000A6C84–000A7C44` | Occupied 36-byte ability record envelope; selected message pointer fields are at +8, with native callbacks retained. Only catalog-listed fields are owned. Two speed-result tables are `000A67E4–000A67F4` and `000D9304–000D9314`. |
| ROM `001B780D–001B7CBC`, `001B7CBC–001B7DBC`, `001B7DBC–001B7DC6` | Conditional shop status sources, 64 status-summary pointers and normal-condition fallback. Reader `0805E1E0` selects states, formats each into 64-byte records, then fills a display pointer list. Four conditional/fallback literals are `0005E358`, `0005E390`, `0005E3EC`, `0005E744` (four bytes each). |
| RAM `02007968–02008968`, `02008968–02008A68` | Existing 64-by-64-byte status text scratch and 64-pointer active-status list. `0805E1E0` prepares them; `0805DFA8` draws up to eight rows at x8, y18+14*n. No reservation or expansion. |
| Stack `sp+4–sp+204` in `08078450` | Existing 512-byte help formatter buffer. The function allocates `0x204` bytes after its register push. Native fixture SP `03007E00` places output at `03007BF4–03007DF4`. Stock window 20 is 208x136px at (16,16); English limited to ten lines. |

The previous combined build ends at ROM `0100F66C`. New assets use the same
append allocator after all previous components; the generated combined ledger
is authoritative for exact destinations. No source/padding reuse, font changes,
permanent RAM changes or save changes are planned. `$x` indentation and
`$/NNN` wrapping are replaced by measured English layout. The staff-category
glyph in two ability messages is expressed by the existing English word
“staff”; semantic substitutions are preserved.

Native reader details: `08072A78–08072D1C` constructs the existing ally-order
window at tile (7,4), width 16 tiles, with names drawn at x4. Its row list is
filtered by unlocked order IDs, then dereferences the seven-word table. The
verifier supplies level 99 to the original unlock helper and stops after all
seven rows draw. It does not command allies or alter a persistent save.
The help fixture also calls the original `0808BB14(0)` window-enable operation
that follows the opening animation; glyph traces alone do not prove a visible
screenshot. Status row 63 ends at `02008968`: the following four bytes are
the active-list pointer intentionally written by the same reader. Guard checks
permit that precise write and check the remaining neighbour bytes unchanged.

Completed combined allocation: `[01000000,01011230)`, 70,192 bytes including
alignment; this component adds 7,108 bytes after the core-gameplay checkpoint.
There are 2,036 allocations and 2,325 checked original patch ranges. See
`build/gameplay-help/english-build.json` and `acceptance.json`, tied to English
SHA-256 `42c41d0c8592aebe135b9076dfe67089b1c2f1b154fae105fd542b4a69b987e5`.

Historical research leads (now reviewed in the [ally/service section](#ally-and-service-menus-2026-09-10)): the ally-menu and
management source pool is within ROM `00C3DB00–00C3E480`, including menu pointer
records around `00C3DB7C–00C3DDF8` and `$j2`-dependent add/remove labels.
The warehouse menu/service pool follows within `00C3E498–00C3EE00`.
`build/gameplay-help/research/source-pools.txt` inventories these candidates and
their unverified pointer hits. The existing enemy builder already owns the
ally Max HP/species format literal `000732C8–000732CC`; do not patch it again.
Nine tutorial pointers at `001B4AF8–001B4B1C` reference the preceding tutorial
pool. Their `$w` controls and the previously deferred initialized-table/`$i2`
readers are now covered by the [tutorial/gameplay investigation](#tutorials-gameplay-feedback-and-history-2026-09-11).

Speed-table reader confirmation is in `research/speed-readers.txt` under this
milestone's build directory. `0801C2F4` copies all four words from the first
table via literal `0001C398` and selects a message from its local copy;
`0803D164` copies the second four-word table via literal `0003D18C` before
evaluating the actor's speed. Their source-table fields, not these base
literals or local copies, are the catalog's checked insertion owners.

## Core gameplay investigation (2026-09-10)

Owner `core-gameplay`. This section records the new sources **before insertion**.
Evidence is under `build/core-gameplay/research/`;
`translations/core-gameplay.json` is the exact per-string source/pointer index.
Envelopes include unrelated data and are never free-space declarations.

| Space / occupied range | Role and evidence |
|---|---|
| ROM `001B3BF0–001B3DB1` | Common water/ground errors, four status printf templates, eight two-column command rows. Literal consumers in `0806C8C8` and `0807621C`; preserve style, column positions and printf argument order/types. |
| ROM `001B4060–001B40D6` | Shared no-effect/action-restriction messages; multiple code literal owners. Debug references remain distinct from gameplay ownership. |
| ROM `001B40D6–001B4136` | Three **32-byte fixed choice records**, down/up/enter. `080207DC` multiplies the helper result by 32; base literal `000207EC–000207F0`. Relocate all three together, keeping padding and `$C1` choice state. |
| ROM `001B4136–001B4140` | Separate two-choice trap activation row, pointer `000205A4–000205A8`. |
| ROM `001B44B7–001B47EA`, `001B4B44–001B4EA6`, `001B51AF–001B5B1D` | Selected inventory, ordinary combat, hunger, status and item-use sources. Exclude the already owned protagonist pair and four sources without verified readers. Preserve originals, including skipped tutorials and concatenated battle fragments between envelopes. |
| ROM `00C3FF04–00C40254` | Settings labels/prompts. Label callbacks return string pointers near `080784E8–08078648`; `080786AC` formats each row into a 256-byte stack buffer, adds a style wrapper in a second 256-byte buffer, then draws at x4 inside a 152px window. Binary option controls, source `*` marker and the original `83 C1` submenu glyph remain intact. |
| ROM `00C3EE90–00C3EED0` | World command window descriptor (64 bytes), referenced by `00076234–00076238`. First record x=2 tiles, width=9; English needs width=10 (80px), ending at x96 before the x104 header. Copy/relocate descriptor; preserve originals. |
| RAM `0200A1BC–0200A284`, `0200A34C–0200A3A6`, `0200A1AC–0200A1B8` | Existing substitution slots used by `0807D8CC`: two 100-byte item names, three 30-byte actor names, three 32-bit numbers respectively. Slot bases are computed from biased literals `0807D9F0` / `0807DA0C`. These are occupied transient game data, never new reservations. |
| ROM `00C46D58–00C46D5D` | Formatter layout alternatives: CR/NUL versus empty NUL. `$/NNN` compares its coarse accumulated width with `232-NNN` and conditionally inserts CR. English replaces these Japanese layout hints with explicit measured line breaks; argument substitutions remain intact. |
| CPU code `0807ADA4–0807B1C2` | Existing message engine: 1,000-byte local output at `sp+4` through `sp+3EC`, three lines per page, 12px row step. Native fixtures must distinguish this reader from the story engine. No code/RAM/save expansion is currently proposed. |

All checked original pointer patches and appended assets join the existing
shared `RomBuild` ledger. Four unreferenced source candidates (`001B4563`,
`001B530A`, `001B551C`, `001B565D`) are not approved for insertion; the third
also has an unresolved extracted glyph. The interior pointer candidate
`00DC8570` into the `00C40208` control sequence is not an insertion owner.

Further reader confirmation: ROM `000A6518–000A6528` is two pairs of
item-restoration messages. `0801377C` reads `pair+0/+4` and advances by eight.
ROM `000A6534–000A655C` is the related five-pair item-loss message table,
referenced by code literals `00016114` and `00017104`. ROM
`000D90A4–000D90B0` is a three-pointer paralysis result table consumed by
`080365E0`. The five ability message fields at `000A6D40–000A6D44`,
`000A6D64–000A6D68`, `000A6D88–000A6D8C`, `000A6DAC–000A6DB0`,
`000A7C28–000A7C2C` occupy +8 of 36-byte ability records, alongside the
original native callbacks. These typed table fields are checked pointer owners;
native payload fixtures do not claim to trigger every corresponding ability.

ROM `00CA2874–00CA2DB4` is the occupied 21-by-64-byte stock window descriptor
table. `0808B60C` reads `table + window_id*64` using literal `0008B674`.
Records 1 (`00CA28B4–00CA28F4`) and 4 (`00CA2974–00CA29B4`) hold the dungeon
main-command panel. Checked **two-byte geometry patches** at `00CA28B8–00CA28BA`
and `00CA2978–00CA297A` change only its width from 9 to 10 tiles. This is an
explicit original-data patch, not source-space allocation. World mode uses
the separately relocated descriptor above. Native message window 18 is 208px
wide (26 tiles); the English wrapper therefore reserves 208px per line even
though the old conditional-break heuristic uses a nominal 232px threshold.

The collision check identified three **existing curated owners**, which this
component must reuse: `settings.reset` at `0007856C–00078570`,
`settings.message_speed` at `000785B4–000785B8`, and `settings.display` at
`00078634–00078638`. They retain their earlier allocations and exact English
bytes in both variants; the new catalog validates equality and records the
reuse explicitly. Thus the 262-entry scope contains 259 new entries and three
previously inserted rows. No duplicate patch or replacement allocation is made.

Native command coverage found an additional fixed table: ROM
`001B3CAB–001B3D23` has **four 30-byte records** (Items/Map, Items/Allies,
Abilities/Map, Abilities/Allies). `0806CB98–0806CBA6` multiplies the selected
variant by 30 using base literal `0006CC04–0006CC08`. Repoint this base once
and relocate the entire table, including NUL padding. The three computed rows
were absent from the pointer-only master extraction. English retains the
30-byte stride; Abilities has a
separate measured `Skills` display label in the 32px left column.

Settings definitions occupy ROM `00C3FBA0–00C3FE5C`: 35 records of 20 bytes,
with the label callback at +16. The selected row's y coordinate is read from
existing RAM `020091B0–020091B2`; native row fixtures temporarily set it to
zero. Selection colours occupy `020398DF–020398E2` and are observed during
natural left/right navigation. The arena-dependent Suspend/Quit labels use
the existing dungeon-index byte `02004FF0–02004FF1`.
The selected-option cache begins at `02009168` (literal `00078760`);
Display setting ID 30 occupies `020091A4–020091A6`. Natural navigation verifies
that its value changes and is restored. The colour bytes are transient and
reflect the last rendered row, so they alone do not prove the selected setting.

The original main-command second row starts at y13 in a 24px-high window.
Font 0 stores 12 bitmap rows, but the selected Latin command glyphs occupy only
10 or 11 rows. Native acceptance checks every nontransparent bitmap pixel for
these rows; adding a blank twelfth row to the test's bounds would report a false
overflow. No vertical window or font patch is needed.

The new formatter guard fixture temporarily uses RAM
`0203F1F8–0203F5F0`: eight guard bytes, a 1,000-byte destination, and eight
guard bytes. A separate printf call reuses its first 256 bytes with its own
guard. These are disposable test buffers after state restoration, not game RAM
allocations. With fixture SP `03007E00`, the message engine's local output is
`030079C4–03007DAC`; addresses differ from callers with another stack depth.

Completed [core-gameplay acceptance](CORE_GAMEPLAY.md) records the current
English appended interval `01000000–0100F66C`: 63,084 bytes used and
16,714,132 bytes remaining, with 1,845 allocations and 2,066 checked original
patch ranges. The [build ledger](../build/core-gameplay/english-build.json)
is authoritative for individual owners. The dungeon-interface section below
retains the preceding component's evidence and allocation snapshot.

## Dungeon interface investigation (2026-09-10)

Owner `dungeon-interface`; evidence in `build/dungeon-interface/research/`.
These discoveries precede insertion; native acceptance is recorded separately
in [DUNGEON_INTERFACE.md](DUNGEON_INTERFACE.md). All new assets use the shared
append allocator alongside the completed enemy/item components.

| Space / occupied range | Role and evidence |
|---|---|
| ROM `001B3F60–001B4060` | 64 dungeon pointers, 36 unique sources. Helper `0805F33C` selects the first/second 32-row half using RAM `02004F8C–02004F90`, then reads at `0805F35A`. Source envelope `001B3DB1–001B3F5D` stays protected. |
| ROM `001B421C–001B4278` | 23 trap/stair/teleportal pointers. Helper `0801B454` reads row `record+8` for kind 3, copies 30 bytes and forces NUL at byte 29. Source envelope `001B4140–001B4219` protected. |
| ROM `0086F4D8–0086F52C` | Object messages: **seven triples**, 21 pointers / 12 sources. `08062DD0` multiplies object type by 12; offsets 0/4/8 are unopened/search-empty/result messages. Calls `08062294` and the story engine. Source envelope `0086F52C–0086F697` protected. |
| ROM `001B4281–001B446D` | **41 fixed 12-byte action records**, three style bytes `03 05 07`, at most eight text bytes plus NUL/padding. Computed readers bypass the broad pointer scan; this adds 40 previously uncatalogued strings. Relocate the entire 492-byte table, retaining stride/style/padding. |
| ROM `0006FBF4–0006FBF8`, `0007003C–00070040`, `00075760–00075764` | Three action-table base literals, all originally `081B4281`. Owned checked relocation patches. Readers multiply the command ID by 12, copy into 100-byte stack buffers and update the style byte for disabled commands. Action 9 can use a caller-provided label instead. |
| ROM `001B4278–001B4281` | Separate unstyled `????` Japanese placeholder. Referenced by literals `00020760–00020764` and `000702A8–000702AC`; owned checked pointer replacements. This is **not** part of the action table. |
| ROM `00C3DA60–00C3DA6A`, `00C3EE5C–00C3EE66`, `00C3EE84–00C3EE8E` | Styled Discard overrides, source strings remain protected. Exact parsed lengths in the catalog are authoritative. Checked pointer owners `0006F5EC–0006F5F0`, `00075768–0007576C`, `000761B4–000761B8`. |
| RAM `0203F000–0203F00C`, `0203F200–0203F21E` | Disposable native-call fixture record (kind, actor, row) and guarded 30-byte trap output. Reused only after restoring state, not permanent allocations. Synthetic stack `03007E00`; no save changes. |

Dungeon copying at `080018E2` is bounded to 100 bytes; another name-format
consumer near `08002964` writes a 64-byte field. New dungeon labels are capped
at 29 bytes, leaving room for their wrappers. This conservative limit does not
certify every later ranking/result context. Source strings and discovered
padding are never reclaimed. Exact per-string sources, pointer words, appended
allocations and checked patches are emitted in the new catalog/build ledgers.

Native action traces show a 32-pixel window at `(192,24)`, beside the
160-pixel inventory ending at x=176. English relocates the 64-byte window
descriptor blocks referenced by `0006FAA0–0006FAA4`, `0006FFB4–0006FFB8`
and `00075750–00075754`; original blocks remain protected. In their second
16-byte window record, x becomes tile 23 and width becomes 6 tiles (48 pixels),
ending at x=232 with an eight-pixel gap after the inventory. No RAM reservation
or font change is involved. Japanese relocation retains original geometry.
The build checks each exact descriptor and records its source and replacement.

Descriptor source ranges are ROM `00C3DA74–00C3DAB4`,
`00C3DAC4–00C3DB04`, and `00C3EE1C–00C3EE5C`. Warehouse actions draw in
the **third** window record (window 2) at x4; its width is also expanded to six
tiles. Thus the common text budget is 44 pixels. The warehouse's second record
is the aligned lower side panel; both keep x=184.

Search tracing also found ROM `0091784C–00917850` and
`00917854–00917858`: owned pointer fields for empty-ground search and its
result. Protected sources are `00917884–00917897` and `00917860–00917883`.
These are separate event-script copies of the object-table messages and are
included to cover the actual world-menu Search route.

ROM `001B453E–001B4552` is a **two-record, ten-byte protagonist-name table**,
not the Adventure Log name. `$t` at `0807DA60–0807DA7A` selects protagonist
index via `08000E9C`, multiplies by ten and substitutes that record. Relocate
the complete pair, retaining stride and padding: Torneko / Tipper, matching the
existing glossary. Checked base-literal owners are ROM `00032A18–00032A1C`,
`00032B78–00032B7C`, `00032CD8–00032CDC`, `00032D9C–00032DA0`,
`00032DE8–00032DEC`, `00078940–00078944`, `0007DA7C–0007DA80`.
Existing actor-copy consumers select the second record with `+10`; this is
preserved. No Adventure Log RAM, save format, or user-entered name is changed.

Native dungeon status header `0806C8C8` uses a **120-pixel** window at x104,
y24. The branch through `0806CCEC` adds a **puzzle number** (Japanese 問題),
not a floor number. Source format ROM `00C3D910–00C3D91C` stays protected;
owned pointer `0006CD18–0006CD1C` selects the appended English
`03 12 %s #%d NUL` format, preserving both printf arguments and centering.
The unnumbered format at `00C3D91C` stays unchanged. Display dungeon names
are limited to 98 pixels, leaving 22 for ` #99`; canonical full names remain
separate. Native tests exercise all 64 rows with puzzle number 99 as a width
stress fixture, without claiming every dungeon naturally uses that branch.

Additional fixture-only state: the active protagonist selector is the signed
halfword at RAM `020014CE–020014D0` (reader `08000E9C`); the warehouse's
caller-supplied command-label pointer is RAM `02009110–02009114` (literal
`08075764`). Tests set a valid caller label before invoking `080755C0`.
These are occupied game fields, restored between cases, not new reservations.
Dungeon header probes likewise temporarily set RAM `02004FF0–02004FF1`
(dungeon index within mode half) and `02004FF1–02004FF2` (puzzle number).
Species/actor-copy helpers select the built-in protagonist pair with the byte
at RAM `02004FF4–02004FF5`; both values are covered by restored-state copy
fixtures. Current English append usage is `01000000–0100DB83` (56,195 bytes,
including padding), with 1,590 allocations / 1,672 checked original patches.
This is a build snapshot, not an allocation address for the next component.

This is the central index of discovered locations and allocation ownership.
Update it when a range is discovered or changed. The standing project rule is
in [AGENTS.md](../AGENTS.md). Discoveries must be recorded before insertion uses
them; insertion builds must check the combined allocation and patch records.

All ranges on this page use **[start, end)**: the start is included and the end
is the first byte after the region. Sizes are `end - start`. ROM tables below
use **file offsets**, RAM tables use **CPU addresses**, and record fields are
explicitly relative. An overview/enclosing range can contain several assets and
padding; it does not declare its gaps free or replace exact source spans.

The map is for the 16 MiB Japanese original, SHA-256:

```text
35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02
```

## ROM allocation policy

| File range | Status / owner | Evidence |
|---|---|---|
| `00000000–01000000` | Original ROM protected by default; only declared patches may change bytes | Pinned base, builder source checks |
| `01000000–02000000` | Appended allocation arena, shared by every component in a given build | [Expansion proof](STORAGE.md), `AppendAllocator` |
| `00CF3B44–00D00000` | FF-pattern candidate; **not approved for reuse** | [Storage audit](STORAGE.md) |
| `00FD7AF4–01000000` | Trailing FF candidate; **not approved for reuse** | [Storage audit](STORAGE.md) |
| `00CB1B64–00CB4E9C` | Zero-filled region with descriptor references; **not free space** | Storage audit and references from records at `00CC1B94` |

For the primary ROM view, CPU address = file offset + `08000000`. Other
cartridge views alias storage and must not be counted as additional capacity.
No original-ROM bytes are currently approved for allocation. Repointing a
string does not make its original bytes available for reuse: other readers,
aliases or computed references may still use them.

## Original text tables and their source envelopes

The table layouts are statically checked against the pinned ROM. Their runtime
reader/relocation coverage is still incomplete. Every range is protected.

| Role | Table file range | Enclosing source-text file range |
|---|---|---|
| Item names, 370 pointers | `0018F16C–0018F734` | `0018F734–00190807` |
| Unidentified-item names, 246 eight-byte records, pointer at +4 | `00190808–00190FB8` | `00190FB8–00191C14` |
| Character/monster names, 200 pointers | `00192568–00192888` | `00191C14–00192565` |
| Ally dialogue, 200 eighty-byte records, 20 potential pointer fields each | `001A60B0–001A9F30` | `00192888–001A60AF` |
| Ally nicknames, 200 pointers | `001A9F30–001AA250` | `001AA250–001AAAC1` |
| Monster traits, 200 pointers | `001ACB74–001ACE94` | `001AAAC1–001ACB71` |
| Item descriptions, 370 pointers | `001B3498–001B3A60` | `001ACE94–001B1EF1` |
| Synthesis descriptions, 100 pointers | `001B3A60–001B3BF0` | `001B1EF1–001B3497` |
| Dungeon names, 64 pointers | `001B3F60–001B4060` | `001B3DB1–001B3F5D` |
| Trap names, 23 pointers | `001B421C–001B4278` | `001B4140–001B4219` |
| Object messages, 21 pointers | `0086F4D8–0086F52C` | `0086F52C–0086F697` |
| Candidate name-filter terms, 165 pointers | `00C45DE4–00C46078` | `00C4607C–00C4672F` |

Authoritative layout definitions: `TABLES` in
[extract_master_text.py](../tools/extract_master_text.py). Generated
[tables.json](../build/text-extraction/tables.json) records each row, null field,
pointer location and target. Source envelopes above were calculated from those
targets and their decoded ends, including terminators. Duplicate pointers share
source storage and must retain explicit ownership.

The [master catalog](../translations/master.json) is the detailed index of
9,318 extracted source spans: `[offset, offset + bytes_including_nul)`. It also
records interior references and possible pointers. Its `verified_pointer_owners`
are distinct from candidates; extraction alone does not approve repointing.
The [curated anchors](../translations/anchors.json) remain the existing builder's
source of verified pointer ownership.

The [enemy-name batches](ENEMY_NAMES.md) add 128 language drafts and the
[trait batches](ENEMY_TRAITS.md) add 80 descriptions against those existing
source records. They do not promote character/monster or trait pointer
candidates to verified insertion ownership or allocate ROM, RAM or save space.

The combined [enemy/item investigation](ENEMIES_AND_ITEMS.md) has additionally
located these occupied ranges (static evidence in
`build/enemy-items/research/enemy-functions.txt`; native confirmation follows below):

- Monster name formatter entries at GBA `080329EC`, `08032B4C`, `08032CA4`,
  `08032D6C`, `08032DC0` copy at most 30 bytes and terminate at index 29.
  Their table-base literals occupy ROM `[00032ADC,00032AE0)`,
  `[00032B48,00032B4C)`, `[00032C3C,00032C40)`, `[00032CA0,00032CA4)`,
  `[00032D00,00032D04)`, `[00032D68,00032D6C)`, `[00032DBC,00032DC0)`,
  `[00032E84,00032E88)`. These are existing code/data, never free space.
- Ally details function `08072FBC` reads the species-name table through
  ROM `[000732C0,000732C4)` and traits through `[000734F0,000734F4)`.
  The species label uses existing RAM `[0200A34C,0200A36A)` (30 bytes).
  Page/selection globals are RAM `[02000628,0200062C)` and
  `[02000634,02000638)`; record pointers start at `02008E68` (full extent
  unestablished). Traits are formatted into a local 512-byte stack region
  at `sp+20C`, then drawn at local y=74; the native window height is 112 pixels.
- Encounter details function `0807993C` reads traits through ROM
  `[00079B88,00079B8C)`, using an eight-byte record selected from RAM `020091D0`.
  The count is RAM `[02009254,02009258)`; the list's full extent remains
  unestablished. Disposable emulator fixtures may replace the first existing
  record `[020091D0,020091D8)` and restore the entire state afterward.
  Formatting uses two existing 512-byte stack regions starting at local
  `sp+10` and `sp+210`; these are transient, not permanent reservations.

Native confirmation is now recorded in the disposable `native-probe/trace.json`
and `ally-probe/trace.json` under `build/enemy-items/research/`. The encounter
reads are at GBA `08032DA6` (name) and `080799F8` (trait); ally reads are
`08073248` and `080734C8`. Both draw with original font 0 into 192-pixel windows.
Ally traits begin at y=74, allowing three lines. English traits use a conservative
188-pixel limit. Full drafts and separate display text are in
`translations/enemies.json`, whose exact `offset`, `source_hex`, and
`pointer_offset` fields index all 400 immutable source spans and pointer owners.

The enemy component owns the complete ROM name pointer table
`[00192568,00192888)` and trait pointer table `[001ACB74,001ACE94)` (200 words
each). Their existing source envelopes are `[00191C14,00192565)` and
`[001AAAC1,001ACB71)`; the catalog provides exact individual spans, including
the separate character row. Relocation appends all payloads through `RomBuild`
and changes only the checked pointer words; source strings remain protected.

English-only details layout patches owned by `tools/build_enemies.py`:

- ROM format-pointer words `[000732C8,000732CC)`, `[00079B84,00079B88)` and
  `[000799A8,000799AC)` are caller-owned literals for ally species, encounter
  header and alternate encounter header. Source strings begin at ROM `00C3E3E4`,
  `00C41484`, and `00C413D4`; exact parsed ends are protected by the ledger.
  New formats preserve all dynamic arguments and are allocated in appended ROM.
  The ally format reserves space for the full species name; the encounter header
  places level and multiplier on its second line.
- ROM `[00079A16,00079A18)` is the encounter separator y immediate (18 to 31).
  `[00079A22,00079A24)` is the encounter trait y load, replaced with local y=39.
  The shared row-position table at ROM `00C402E0` stays unchanged. These two
  checked halfwords affect this details function only. Native English acceptance
  must verify both layouts after insertion.

Research fixtures use EWRAM `[0203F000,0203F040)` as a disposable stored-ally
record and `[0203F040,0203F080)` as zeroed caller mode data. The stored record's
kind/species/level bytes are at offsets 0/2/3; its pointer is temporarily written
at `[02008E68,02008E6C)`. The fifth ally-details argument is the mode pointer
on the caller's stack, while r0 is a frame callback. These are fixture-only
replacements inside a fully restored emulator state, not build reservations or
save-format changes. Full record and pointer-table extents are still unproven.

The encounter multiplier is existing RAM `[02009228,0200922C)`; the controlled
header fixture sets it to 123 to exercise the displayed `12.3x` argument. Native
windows report a height of 112 pixels. Ally trait rows at y=74/87/100 end at
112; the English encounter traits use y=39/52/65. No RAM/save capacity changes
are needed for these layouts.

Guarded helper fixtures additionally use disposable EWRAM
`[0203F000,0203F150)` for a zeroed *live-actor-shaped* record (different from
the stored-ally shape above), species at `+08`, hero flag at `+05`, and the
existing byte `+137` observed through ROM literal `[00032D40,00032D44)`.
Output `[0203F200,0203F21E)` is 30 bytes, with eight-byte guards immediately
before and after; `03007E00` is a disposable call stack top. Tests restore the
complete state for every call. These are test scratch, never permanent claims.
Item helper fixtures similarly guard their 100-byte destination
`[0203F100,0203F164)` with eight-byte sentinels. The enemy table-base literals
at ROM `[00080BFC,00080C00)`, `[00080EA0,00080EA4)`,
`[00080EC4,00080EC8)`, `[00080F18,00080F1C)` belong to existing item formatting
paths, including disguised Mimics. They are occupied, unchanged original data.

The coarse discovery banks are recorded in `TEXT_BANKS` in the extractor and
the generated [coverage report](../build/text-extraction/coverage.json). They
cover other message/UI pools, event data, menus/help and debug/auxiliary data.
They contain non-text too and are **search boundaries, not allocation regions**.
See [extraction notes](TEXT_EXTRACTION.md) for their limitations.

## Font assets and inspected code

| File range | Role and evidence |
|---|---|
| `00C93B4C–00C97A58` | Font 0: 1,345 descriptors × 12 bytes |
| `00C9E5CC–00C9F7B4` | Font 1: 382 descriptors × 12 bytes |
| `00CA1300–00CA178C` | Font 2: 97 descriptors × 12 bytes |
| `00CA2674–00CA2874` | 256-entry single-byte-to-glyph map, two bytes each |
| `00C7C100–00C7DBB8` | Font-0 printable ASCII bitmap slots identified in the storage audit |
| `00084A10–00084E80` | Inspected title-menu code region; end is an inspection boundary |
| `0008BC4C–0008CD70` | Inspected glyph/text routines and literals; not an exclusive asset allocation |

Font layouts are defined in [font_metrics.py](../tools/font_metrics.py), with
decoding in [game_text.py](../tools/game_text.py). All referenced bitmap storage
is protected even where this overview does not enumerate it. The
[font notes](FONTS.md) and [text-system notes](TEXT_SYSTEMS.md) record reader entry
addresses; an entry address alone does not establish a function's byte extent.

## Current appended allocations, by build

The item and context rows below include the 2026-09-10
[terminology corrections](TERMINOLOGY.md). The planned shared ledgers were
checked before writing the revised ROMs; no source ownership or RAM/save
reservation changes are needed. Some internal item offsets move even though
the ordinary-item envelope is unchanged. The English context envelope grows
by four bytes.

These are **snapshots**, not fixed addresses for future manual insertion.
Catalog edits can move assets. Read the report for the exact output ROM being
used and let its allocator choose the next address.

| Build | Occupied envelope, including alignment | Exact ledger |
|---|---|---|
| Current ally-dialogue English build | `01000000–01019EBD` (106,173 bytes) | [ally-dialogue/english-build.json](../build/ally-dialogue/english-build.json): complete `ledger`, plus the 16 prior payload reflows in `history` |
| Ally-dialogue Japanese relocation control | `01000000–01019319` (103,193 bytes) | [ally-dialogue/japanese-build.json](../build/ally-dialogue/japanese-build.json): complete `ledger` |
| Earlier tutorial/gameplay English build | `01000000–01014614` (83,476 bytes) | [tutorial-gameplay/english-build.json](../build/tutorial-gameplay/english-build.json): complete `ledger` |
| Earlier ally/service English build | `01000000–010127D1` (75,729 bytes) | [ally-services/english-build.json](../build/ally-services/english-build.json): complete `ledger` |
| Ally/service Japanese relocation control | `01000000–01012B8D` (76,685 bytes) | [ally-services/japanese-build.json](../build/ally-services/japanese-build.json): complete `ledger` |
| Earlier complete enemy/item English build | `01000000–0100D320` (54,048 bytes) | [enemy-items/english-build.json](../build/enemy-items/english-build.json): complete `ledger` |
| Earlier complete enemy/item Japanese relocation control | `01000000–0100BC40` (48,192 bytes) | [enemy-items/japanese-build.json](../build/enemy-items/japanese-build.json): complete `ledger` |
| Ordinary 27-entry English build | `01000000–01000311` (785 bytes) | [english-build.json](../build/translation/english-build.json): `allocations`, `pointer_changes` |
| Name-entry build, including its text batch | `01000000–010009E0` (2,528 bytes) | [build.json](../build/name-entry/build.json): `text_build.allocations`, `allocations`, `text_build.pointer_changes`, `patches` |
| Combined menus, name entry and complete item tables, English examples | `01000000–01006D2F` (27,951 bytes) | [items/english-build.json](../build/items/english-build.json): complete `ledger` |
| Combined build with all item text relocated in Japanese | `01000000–01006D27` (27,943 bytes) | [items/japanese-build.json](../build/items/japanese-build.json): complete `ledger` |
| Combined items plus unidentified/synthesis tables, English examples | `01000000–01008FDA` (36,826 bytes) | [item-contexts/english-build.json](../build/item-contexts/english-build.json): complete `ledger` |
| Combined items plus Japanese unidentified/synthesis relocation | `01000000–01008FB2` (36,786 bytes) | [item-contexts/japanese-build.json](../build/item-contexts/japanese-build.json): complete `ledger` |


The earlier [combined enemy/item milestone](ENEMIES_AND_ITEMS.md) supersedes the small-draft
snapshots below. Its English components occupy item payloads
`[010009E0,01006E86)`, context payloads `[01006E88,010095D1)`, enemy payloads
`[010095D4,0100D2EC)` and three appended formats through `0100D320`.
Alignment is owned by the shared ledger. The Japanese control uses
`[010009E0,01006D27)`, `[01006D28,01008FAA)`, `[01008FAC,0100BC40)` respectively,
and keeps the original enemy layout. Exact per-string sources and pointers are
in the three family catalogs; the ledger owns 1,486 table-pointer words plus the
existing menu/name patches and, for English only, five enemy layout patches.
No additional permanent RAM/save reservation is introduced.

All 200 name and 200 trait rows now have native detail-screen coverage, including
30-byte guarded copies and shared enemy-name use in revealed-Cannibox item
formatting. `tools/verify_enemy_guards.py` records that a disposable item flag
mask `0x50000` selects species row 66 through GBA `08080B86`. Other reveal states
and the remaining item/actor consumers are not thereby certified. Original
item 127's bundle selector remains a separate case as documented below.

The two historical item builds share the first 2,528 bytes with the verified name build.
Their 719 item allocations occupy `[010009E0, 01006D2F)` in English and
`[010009E0, 01006D27)` in Japanese, including alignment. Individual addresses
differ by language. Their full ledgers contain 760 allocations and 792 original-ROM
patch ranges. The item component owns exactly the 740 four-byte words in the
two item tables above; it adds no code patches or RAM/save reservations. Exact
source spans and intentional pointer aliases are in
[items.json](../translations/items.json). All old item strings stay protected.

The context builds preserve the English ordinary-item component's allocation
envelope `[01000000,01006D2F)`. One alignment byte precedes their new payloads:
the 344 context assets occupy `[01006D30,01008FDA)` in English and
`[01006D30,01008FB2)` in Japanese, including subsequent alignment. Complete
ledgers contain 1,104 allocations and 1,138 patch ranges. The new component owns
only the 246 unidentified-name pointer fields at record `+4` and 100 synthesis
pointer words. Category fields at record `+0` are explicitly protected across
components. [item-contexts.json](../translations/item-contexts.json) records
exact spans, category metadata and the intentional three-row placeholder alias.

The name-entry build owns these additional assets:

| Owner ID | Payload file range |
|---|---|
| `name.compact-map` | `01000314–01000514` |
| `name.keyboard-page-0` | `01000514–0100063C` |
| `name.keyboard-page-1` | `0100063C–01000764` |
| `name.keyboard-input` | `01000764–010008B8` |
| `name.keyboard-pages` | `010008B8–010008C8` |
| `name.keyboard-header-0` | `010008C8–010008E4` |
| `name.keyboard-header-1` | `010008E4–01000900` |
| `name.keyboard-headers` | `01000900–01000910` |
| `name.hint-7bed0` | `01000910–0100091A` |
| `name.hint-7bed4` | `0100091C–01000925` |
| `name.hint-7beec` | `01000928–01000943` |
| `name.confirmation` | `01000944–01000969` |
| `name.code` | `0100096C–010009D8` |
| `name.default` | `010009D8–010009E0` |

The gaps in that table are allocator alignment, included in the occupied
envelope. The name build has its own text batch, including its seven-letter
explanation override; do not substitute the ordinary build's payloads by hand.
Earlier title/expansion/text-system proof ROMs also reuse appended addresses.
They are independent images, not patches to stack onto the current build.

For each original-ROM patch, the build ledgers record offset, expected bytes,
replacement bytes and purpose. Its exact range is
`[offset, offset + len(bytes.fromhex(before)))`. Check all text pointer changes
and code/data patches together. Parent envelopes and the assets they contain
are intentional containment, not independent allocations that should be counted
twice.

The item-text work has consolidated allocation and patch enforcement in
[rom_build.py](../tools/rom_build.py). The shared build rejects cross-component
patch/asset collisions and checks the complete image against its combined
ledger. Existing component report sections are retained for compatibility;
the additional `ledger` section is the complete ownership record.

The 2026-09-10 map audit checked the generated ROM hashes, payload hashes,
alignment accounting and original/replacement bytes. The ordinary build's
27 allocations and 27 patch ranges have no overlaps. The name build's combined
41 allocations and 52 patch ranges also have no overlaps. The table/source
envelopes, font-table ranges and named asset ranges above match their detailed
records. This audit describes these output images; future builds need the same
checks against their own complete ledgers.

The completed item build also passes complete-image ledger verification and
[native relocation checks](ITEM_TEXT.md#verification-and-limits). Its 740 item
pointer patches are checked together with the existing 52 menu/name patches;
every allocation and every preserved original byte is included in finalization.

## RAM and save-field ownership

| Address space / range | Role, lifetime and evidence |
|---|---|
| RAM `02004F82–02004F88` | Original six-byte current-name buffer; do not enlarge in place |
| RAM `02004F88–02004F8C` | Adjacent live gameplay field; must be preserved |
| RAM `0203BB38–0203BB40` | Eight-byte name-entry reservation; name build extends startup's BSS clear end to include it |
| RAM `02010A90–02034A90` | Game heap region initialized by `08087E00`, size `24000`; occupied runtime arena |
| RAM `02033F54–02034354` | Observed story formatter buffer, 1,023-byte payload plus NUL; inside the runtime arena |
| RAM `03007BA0–03007CA1` | Observed settings formatter stack buffer, 256-byte payload plus NUL; transient |
| RAM `03007900–03007CE8` | Observed message formatter stack buffer, 999-byte payload plus NUL; transient |
| RAM `03007540–030075A4` | Observed 100-byte item-information name buffer on the controlled village route; transient stack storage |
| Adventure Log record `+0010–+0018` | Name build's eight-byte stored name; includes former alignment bytes `+16/+17` |
| Adventure Log record `+0018` onward | Existing flags/following fields retain their offsets; extent not fully mapped here |
| Cartridge save file `00000000–00010000` | Existing 65,536-byte FLASH save; no save-size expansion |

Buffer ranges reflect the recorded calls, not universal limits for every
reader. Stack buffers can overlap because their lifetimes differ; they are not
free permanent RAM. The story buffer is contained within a larger runtime arena,
so those two rows describe nested storage. Save-record offsets are not physical
save-file addresses. See [name-entry notes](NAME_ENTRY.md) and
[formatter evidence](TEXT_SYSTEMS.md) before changing any of them.

The default-name pointer patch is at ROM `[00085904, 00085908)`, its slot-offset
instruction patch at `[000858CC, 000858CE)`, and the BSS-end literal patch at
`[00087A04, 00087A08)`. All other name code/literal changes are enumerated in
the name build's `patches` ledger. Ranking/result-name storage remains unresolved
and must not be inferred from the Adventure Log record layout.

## Item-reader investigation

The [item-text notes](ITEM_TEXT.md) record newly inspected reader entries
`08080A5C` (item-name formatting) and `0806DCDC` (item information display),
including their buffers and pointer loads. The description-table literal at
ROM `[0006DE84, 0006DE88)` is occupied source data. The existing item tables and
their source envelopes above remain protected; reader discovery does not make
their old storage reusable.

The [controlled inventory fixture](ITEM_TEXT.md) identifies the occupied RAM
head pointer `[0200C640, 0200C644)` and the first record's inspected slice
`[0200A480, 0200A498)`, with item index at record `+0E`. The selecting ROM literal
occupies `[0007612C, 00076130)`. These are existing live storage, not free RAM.
Record-relative `[+10,+12)` supplies the signed enhancement in the tested
weapon/shield formatter cases. No permanent inventory or save layout is changed.
For special item ID 127, byte `[+15,+16)` selects the name-table row at
`08080B4E`; the controlled fixture's zero selects row 0. Its own placeholder
row has static relocation coverage, not a native display claim.
Native-call test scratch described in the item notes is disposable emulator
state and does not reserve or approve permanent game storage.

## Unidentified/synthesis readers

[ITEM_CONTEXTS.md](ITEM_CONTEXTS.md) records the separate unidentified-name
and synthesis-description tables already listed above, their record layouts,
reader literals and temporary fixture state. Newly located occupied RAM includes
the identification word `[0200C71C,0200C720)` and 370-entry halfword mapping
`[0200C722,0200CA06)`. Record byte `+12` is the observed synthesis-effect count;
selected effect codes are read at `+4+index`. No permanent layout is changed.
The reader literal ranges `[000810BC,000810C4)`, `[000812B4,000812BC)` and
`[0006E024,0006E02C)` are protected original-ROM data.
The same investigation locates the mode word `[02000000,02000004)` (literal
ROM `[00000350,00000354)`) and the custom-name helper's slot base `0200CA06`.
The latter's full arena extent is not established; no space there is approved
for new storage. The synthesis wrapper's instruction audit establishes its
1024-byte observed stack range
`[030079A8,03007DA8)` via `0806E1C0`'s clear/termination operations. The custom
name index table occupies ROM `[00C4C4FC,00C4C7E0)`; its observed indices reach
RAM `[0200CA06,0200D0AE)`. This is occupied reachable storage; the full arena's
extent remains unverified. All these locations are documented in the context
notes before the new catalog's insertion is used.

Native tests now read all 246 unidentified-name pointer words through
`0808109A`/`0808113E` and all 100 synthesis pointer words through `0806DFD8`.
The complete ledgers preserve the adjacent category words and original source
text. See [the recorded fixture scope](ITEM_CONTEXTS.md#verification-and-fixture-scope)
before extending those runtime claims to natural dungeon gameplay.

## Ally and service menus (2026-09-10)

Discovery record established before the first `ally-services` insertion. All
ranges below are occupied; ends are exclusive. The pinned source bytes and exact
pointer-word ranges (each `[offset,offset+4)`) are enumerated in
[ally-services.json](../translations/ally-services.json). Each source range is
`[offset,offset+len(source_hex)/2)`. Only listed verified owners may be patched;
excluded owners retain their prior bytes. New assets use the shared append
allocator after the complete gameplay-help components. No original text, gap,
RAM buffer or save field becomes reusable.

| Address space / range | Purpose, owner, evidence and context |
|---|---|
| ROM `[00C3DB78,00C3DE18)` | Twelve ally command tables, seven 8-byte records apiece: command ID at +0, label pointer at +4. `08071294–080712B4` selects a 56-byte table and copies it into existing RAM. Only verified label-pointer fields belong to this milestone; command IDs and unrelated rows remain intact. |
| ROM `[00C3DE18,00C3E498)` | Ally menu labels/messages/status source envelope. Individual protected strings and literal owners are pinned in the catalog. Existing order messages and the enemy component's Max HP/species pointer `000732C8` retain their existing owners. `08070AF8`, `08071ED4`, `08072FBC` establish readers; Ghidra listings in `build/ally-services/research/`. |
| ROM `[00C3E498,00C3E4C8)`; `[00C3E4C8,00C3E4D4)` | Four warehouse menu records (12 bytes: label, enabled pointer, result ID), followed by a zero record. `080738CC` passes this table to `0807ADA4`; `0807B294` measures and draws its rows. The leading ASCII `*` selects the default. |
| ROM `[00C3E4D4,00C3F140)` | Warehouse, inventory-transfer, discard, synthesis and merchant-message source envelope; only catalog-listed strings/owners are claimed. The high candidate pointer `00CE20C4` to warehouse Cancel is unreviewed and excluded. Already owned secondary-popup data/labels remain with their prior components. |
| ROM `[00C3ED84,00C3ED8C)` | Two protagonist-name pointers in warehouse UI order Torneko, Tipper. Pointer identity verified against original bytes. Distinct from the earlier fixed protagonist-name table. |
| ROM `[00C3F140,00C3F150)` | Four merchant message pointers; single/multiple sale confirmation and completion. `080773D8` consumer; dollar slot contracts retained. |
| ROM `[00C3F158,00C3F17C)`; `[00C3F17C,00C3F188)` | Three gold-bank 12-byte menu records plus zero terminator; Deposit is the default. `08077628` passes the table to the common service engine. |
| ROM `[00C3F150,00C3FB9C)` | Bank/token-exchange labels and messages, including original 20-gold-per-token rule. Individual ownership in catalog excludes embedded tables and unrelated bytes. `08077628`, `0807789C`, `08077B7C` and `0807B604` establish formatting/numeric input. |
| ROM `[00C3FB5C,00C3FB6C)` | Four token/header pointers selected by `08077B7C`: combined, gold, tokens, combined. Native formatter capacity 100 bytes; dollar 0=tokens, dollar 1=gold. |
| ROM `[00C3DA6C,00C3DA74)`; `[00C3DB04,00C3DB0C)`; `[00C3DB54,00C3DB6C)` | Additional Sell, target prompt, unavailable-row source ranges. Typed style/column controls and printf arguments retained. Actual terminators/padding are distinguished by catalog source lengths. |
| ROM `[00C411B0,00C411B6)`; `[00C41ACC,00C41AD2)` | Two Japanese Battle context labels, selected through literals `00079444` and `0007A1A8`. Original callers `08079288`/`0807A064`; full English Battle, four-byte display Bout. |
| RAM `[02008E38,02008E3D)` | Existing ally `$j2` context field: `08070B96–08070BA6` copies five bytes and forces byte 4 to zero. Formatter `0807DAD4–0807DB06` reads it. Four payload bytes only: Trip/Bout. No expansion. |
| RAM `[02008E50,02008E60)` | Existing ally-list title buffer. `08070B8C–08070B94` copies 16 bytes, forces byte 15 to zero; fallback source `00C3DF94`. Full English Ally list fits. |
| RAM `[020090C0,020090F8)` | Existing active seven-record ally command table copied by `08071294`. Occupied transient UI data; no new allocation. |
| RAM `[0200A3C4,0200A428)` | Observed shared bank/token header destination. Token reader explicitly caps output to 100 bytes; bank uses sprintf. Lifetime belongs to service UI; no enlargement. |
| RAM `[0200915C,0200915D)` | Token-header selection byte read by `08077B7C`. Fixture changes are discarded with emulator state. |

The ally details reader `08072FBC` uses a 512-byte stack formatter and draws
Attack/Defence at y30/y42 in its existing 188-pixel content area. New templates
retain the first numeric column at x46 and move the second column from x68 to
x104 (`03 08 68`); both signed 32-bit numeric stress values and English labels
must fit without overlap. This is an owned text-control change, not a code or
window-descriptor patch. The existing enemy Max HP/species row is unchanged.

The service engine `0807ADA4` formats into 1,000 bytes (in a fixture entered
with SP `03007E00`, `[030079C4,03007DAC)`). Ally-manager messages can first pass
through a 512-byte buffer. Native page boundaries occur at `0807B044`; continuation
returns through `0807B166` to `0807AE34`. These are transient stack/control-flow
observations, not permanent RAM reservations. Multi-page help must be checked
through this native page loop. Test scratch continues to use the disposable
ranges documented for previous interface fixtures; no game/save layout changes.

Additional reader evidence before the revised service build:
`0807191C` reads the active 8-byte ally records, formatting each label into the
existing stack slice `[SP+84,SP+C1)` (61 bytes, inclusive formatter end at +C0).
The service builder conservatively permits 60 bytes. Both original ally menu
layouts are retained and tested. `0807B604` sizes its number picker for
`digits*10+12` pixels rounded to tiles; `0807B822` spaces numeric/unit glyphs
at 10 pixels. The seven-digit fixture has an 88x16px panel: the first unit glyph
starts at x73. Full `tokens` overflows; display `T` fits. This is a catalog
abbreviation for the existing `00C3F808` source, not a descriptor/code patch.
The prompt and balance retain full `tokens`. Gold uses `G`.
The numeric renderer's temporary assembled string occupies `[SP+28,SP+4C)`;
the test skips only the preceding message call, then executes original number
conversion, unit concatenation and drawing. No permanent RAM is allocated.
The bank extra-header descriptor occupies ROM `[00C3F1A8,00C3F1BC)`:
16 descriptor bytes plus pointer `0200A3C4`, a 200x16px window drawing at x4/y2.

Final service verification uses disposable scratch `[0203F100,0203F102)` for
a Thumb `BX LR` frame-yield callback, within the existing fixture scratch
envelope. It is never inserted in the ROM or persisted in a game save. The
message continuation begins at `0807B142`, runs the original 18-step redraw
loop through `08094B98`, and retains the live draw callback read from RAM
`[03000054,03000058)` (observed Thumb address `03000AA9` in the fixture).
The frame-yield trampoline `08094BB8` branches through r9; it must receive a
valid callback. Skipping the redraw loop causes overlapping test pages.
Separate real-handler button routes retain the live callback and normal waits.
The token header's native end pointer is destination+100 (inclusive); the
translation/verifier conservatively require NUL within the first 100 bytes.
Source envelopes above can include alignment; exact string ends are in the
catalog. Combined final ownership and preserved bytes passed acceptance at
English SHA-256
`d8e185dac51a357dc6a39640062e13d796805b12d9f98d9e5a557004f93f922e`.

Final transfer-caller check before revision: `080755C0` draws the caller label
for command 10 through RAM pointer `[02009110,02009114)`, read at `080756E6`.
It is a pointer to variable-length text, not a fixed action-table record.
The already-owned warehouse popup is 48px wide, drawing at x4: **44px available**.
New source labels `00C3E548` / `00C3E550` therefore use **Withdraw (43px)** and
**Deposit (34px)**. Full `To storage` measured 53px and was rejected for this
caller. The existing popup descriptor/owner remains unchanged. Both labels now
have direct native command-10 caller tests in this actual popup.

## Tutorials, gameplay feedback and history (2026-09-11)

Established before `tutorial-gameplay` insertion. All ends are exclusive and
all original ranges below are occupied. Exact protected source strings and
checked four-byte pointer owners are in
[the catalog](../translations/tutorial-gameplay.json); the shared allocator
adds this component after all ally-service allocations. No original gaps,
relocated source bytes, RAM or save fields become free space.

| Space / range | Owner, evidence and context |
|---|---|
| ROM `[001B47EA,001B4AF8)` | Nine item-tutorial sources; one `$w` command per source. `08020804` selects a tutorial through `08020D26–08020D2E`, then `080207F0` queues it through `0805D3D4`. Exact source ends exclude padding. |
| ROM `[001B4AF8,001B4B1C)` | Nine tutorial pointers, indexed in original order. No table enlargement. |
| ROM `[001B5021,001B7590)`; `[001B7720,001B780D)` | Source envelopes for the selected gameplay messages, object/effect labels and damage fragments. Already-owned sources/occurrences and unrelated gaps are excluded; the catalog enumerates 285 new source entries overall. |
| ROM `[001B7590,001B7720)` | 100 effect-name pointers, 98 distinct sources. Three indices share `なし`. `080397D8–080397F4` selects a name, copies 100 bytes into `$i1`, then forces its final byte to NUL. |
| ROM `[000A6C84,000A7C44)` | Existing 36-byte ability records: selected text pointers at +8 and alternate +12; only catalog-listed words patched. Prior components retain other owners. |
| ROM `[00CAFE88,00CB0F44)` → RAM `[02000000,020010BC)` | Initialized EWRAM image, copied by startup `08087950` through `0808796C→08087C4C`. Literals `000879F8/FC`, `00087A00` pin end/start/source. Not text free space or a new RAM allocation. BSS starts `020010C0`; previous BSS/name ownership is unchanged. |
| ROM `[00CAFEE8,00CAFF08)` → RAM `[02000060,02000080)` | Eight object-category pointers. `0800AC28–0800AC46` masks a category with 7 and copies the selected label into an existing 100-byte item slot. |
| ROM `[00CAFF80,00CAFF8C)` → RAM `[020000F8,02000104)` | Three strength-loss pointers. Selection at `08036B30–08036B3A`, literal `00036B54`. |
| ROM `[00CAFF8C,00CAFFF0)` → RAM `[02000104,02000168)` | Five cancellation groups of five pointers, including null entries. `0803B38C` reads this table via literals `0003B43C/0003B520`. Preserve nulls, group shape and separator `[00CAFFF0,00CAFFF4)`. |
| ROM `[00CAFFF4,00CB0094)` → RAM `[0200016C,0200020C)` | Twenty trap-message pairs, including one null pair. `08046228–08046236` selects trap index*8 + context*4. Nulls and following unrelated pointers remain intact. |
| RAM `[0200A1BC,0200A34C)` | Four existing 100-byte `$i0`–`$i3` fields. Starts: `0200A1BC`, `0200A220`, `0200A284`, `0200A2E8`. Formatter `0807D9E0–0807D9EE` computes these addresses. `$i3` directly precedes the actor slots; no enlargement. |
| RAM `[02007430,02007440)` | Dungeon message queue indices, countdown and draw position. `0805D0B4` resets, `0805D3D4` enqueues and `0805D4C8` renders. |
| RAM `[02007440,02007940)` | Sixteen 80-byte live queue rows; at most 15 pending rows. Mode-1 formatter receives row+79 as inclusive end. `0805D45C` formats and `0805D46A` records history. |
| RAM `[02007940,02007944)`; `[02007948,0200794C)` | Queue flags, then 32-bit history write index. Leading ASCII `!` is consumed at `0805D410–0805D41C` and clears the new-message flag; it is not displayed. |
| Runtime structure `[base+1979C,base+19C9C)` | Twenty 64-byte message-history records, with `base = u32[0200000C]`. Each has three header bytes, **59 payload bytes**, NUL at or before +3E, and an untouched final byte. `0805D9C8` copies each live row. This is a structure offset, not a physical save offset; save persistence is not established. |
| RAM `[020398E8,020398E9)` | Existing pause/scroll flag set by renderer `0808CBA0` for binary `03 1F`; `$w` becomes these two bytes in `0807D8CC`. The queue renderer checks it before a scroll wait through `0805D708`. |

New English is bounded by both 208px line width and the tighter **59-byte
history payload**, after substitutions and pause expansion. Item/effect labels
are limited to 144px and their existing 100-byte slots; accepted font-0 ASCII
has a minimum 3px advance, giving at most 48 payload bytes. Actor slots allow
29 bytes, protagonist names seven, and signed numeric substitutions eleven.
Source table shape, controls, substitution identity/count and leading `!`
contracts are checked before allocation. Research listings live in
`build/tutorial-gameplay/research/` (`readers*`, `messages`, `queue`, `pause`,
`draw`). These do not imply that all extracted candidates are insertable.

Disposable native fixtures may use `[0203E000,0203E500)` for a guarded history
ring and temporarily substitute `u32[0200000C] = 0203E000-1979C`; the opening-world
state has no dungeon structure. This is test-only RAM, not a production
reservation. Queue tests stop before its unrelated scheduler call at `0805D488`.
The idle CPU and original world-structure pointer are restored for frame
presentation; full raw state is restored before the next case. Existing
scratch `[0203F000,0203F600)` remains disposable. Cold-boot tests independently
verify each initialized table against its ROM image; restoring an older state
requires refreshing only these four static table slices from that proven boot.
No cartridge/save format or runtime buffer is expanded by this milestone.

Final acceptance for this component pins English SHA-256
`66c53aa470d31c73e093f5c053ea38e525ea8c47d8070266be4595626c270f24`,
combined append `[01000000,01014614)`, 2,459 allocations and 2,867 original
patch ranges. Native tests independently cover all 100 effect-copy indices,
eight object-copy indices, nine tutorial selections, three strength selections,
25 cancellation selections and 40 trap/context selections, including nulls.
All four initialized pointer-table ranges are covered without new RAM fields.
The new English obeys history capacity. A separate static audit of unchanged
earlier core/help templates flags 16 lines under maximum narrow-name assumptions
in `build/tutorial-gameplay/research/earlier-history-audit.json`; this is not
proof those synthetic values are naturally reachable. Natural history usage
and ranking/save persistence remain separate follow-up work.

## Ally dialogue and history reflow (2026-09-11)

Recorded before the `ally-dialogue` insertion. All ranges are occupied and ends
exclusive. The [new catalog](../translations/ally-dialogue.json) owns the first
50 ordinary-species dialogue sets (rows 1–50, eight responses each). Source bytes
and individual pointer words are pinned there; remaining table words are not
claimed. Original source text, null fields and padding remain intact.

| Space / range | Owner, evidence and context |
|---|---|
| ROM `[001A60B0,001A9F30)` | Existing 200-by-80-byte ally dialogue table. `0803C3C8` reads actor species at +8, computes species*80 + response*4, and loads a pointer at `0803C3E0`; base literal `0003C438`. Only the selected 400 words belong to this component. |
| ROM `[001A6100,001A70A0)` | Selected row envelope, rows 1–50. Each row owns only its first 32 bytes (eight pointer words); the remaining 48 bytes and all other rows are preserved. |
| ROM `[001928EB,001973BB)` | Selected source envelope. Exact noncontiguous protected string ranges are authoritative in the catalog; intervening padding is not reusable. |
| Actor structure `[+8,+A)`; `[+54,+5C)` | Existing signed species ID and 32-bit current/max HP fields read by `0803C2BC`. Ordinary responses 0/1, 2/3 and 4/5 use thresholds `floor(maxHP*8/10)` and `floor(maxHP*4/10)`, with a random choice within each pair. Native fixtures check both sides of each threshold at max HP 100. No actor/save field expansion. |
| Code calls `08025F64`, `08037928` | Both pass responses 6/7 to `0803C3C8` after `0808DE30(2)+6`, at `08025EFE–08025F04` and `080378EE–080378F4`. Source content and these callers identify the level-up pair. Full function listings for `08025EC4` and `080377C8` are in `level-readers.txt`; natural level transitions remain pending. |
| RAM `[0200A34C,0200A388)` | Existing two 30-byte actor substitutions `$m0`/`$m1`, populated through `0803C41A→080329EC` and `0803C424→08032B4C`. Actual display names can be custom nicknames; the new dialogue does not alter naming/save rules. |
| Code `0803C428–0803C430`; `0807ACFC–0807AD5A` | Selected dialogue enters wrapper `0807ACFC(source,1)`, then existing paged engine `0807ADA4(source,callback,0,0,0,1,1)`. Existing 1,000-byte formatter and three-line page loop; no dialogue pointer-table enlargement or renderer patch. |

Reader listings: `build/ally-dialogue/research/dialogue-reader.txt` and
`dialogue-ui.txt`. Special rows 191/192, special ability interceptions (including
rows 26/34), natural conversations, custom/default nicknames and level-up
triggers must not be inferred from the ordinary table-selector fixture.

The history audit reflows 16 existing core/help messages using whitespace only.
Their original catalog English/source/notes stay unchanged. The current combined
builder passes an optional layout callback into their original components;
those components retain their allocation and patch ownership. Each revised
payload has exactly its previous byte length, so all previous allocation
addresses and original pointer patches remain stable. The changed allocation
IDs and old/new payloads are enumerated by `history` in the new combined build
report. Reflow checks all 311 earlier core/help message templates against both
208px width and the established 59-byte history payload, retaining at most three
lines. Historical builders keep the prior default layout and remain reproducible.
No second component patches or reallocates those 16 owned strings.

Native fixtures reuse the documented disposable actor record at
`[0203F000,0203F150)`, formatter scratch and queue/history backing. Species/response
selection stops before unrelated name/state mutation; paged text runs the
original formatter and page renderer with the caller's `(0,1,1)` stack flags.
Frame-yield and input waits can be bypassed only in those disposable fixtures;
normal-button route coverage is recorded separately. New ROM bytes are allocated
through the shared allocator after `[01000000,01014614)`.

Completed combined English append: `[01000000,01019EBD)`, 106,173 bytes;
400 new strings occupy `[01014614,01019EBD)`. There are 2,859 allocations and
3,267 checked original patch ranges, with 16,671,043 append bytes remaining.
The exact output ROM hash and owners are in
[english-build.json](../build/ally-dialogue/english-build.json).
[acceptance.json](../build/ally-dialogue/acceptance.json) confirms unchanged earlier
allocation addresses, original patches and RAM/save reservations; only the 16
declared earlier payloads change. All 311 earlier core/help messages retain
their complete native history payload under three substitution profiles.

## Remaining companion dialogue (2026-09-11)

Owner `companion-dialogue`; recorded before insertion. All ends are exclusive.
The [catalog](../translations/companion-dialogue.json) pins 1,224 remaining
non-null main-table fields and three conditional Rosa alternatives. The earlier
400 `ally-dialogue` pointers retain their owner. Together these cover every
non-null field in the 200-record main table; reserved/test-style strings are
included without claiming that they are normally reachable.

| Space / occupied range | Evidence and allowed ownership |
|---|---|
| ROM `[001A60B0,001A6100)` and `[001A70A0,001A9F30)` | Main table row 0 and rows 51–199. Own only the 1,224 non-null words listed in the catalog: eight fields per ordinary row and all 20 fields for rows 191/192. Preserve every null word and the earlier rows 1–50. Existing reader `0803C3C8`, base literal `0003C438`. |
| ROM `[00192888,001928EB)` and `[001973BB,001A60AF)` | Remaining main-table source envelopes; exact protected sources and ends are in the catalog. These are occupied source bytes, not free-space grants. |
| ROM `[001B4F38,001B4FE1)`; table `[001B4FE4,001B4FF0)` | Three Rosa alternatives and their pointer table. Literal `0003C43C` supplies the table to native loads at `0803C412`. Own only its three pointer words; preserve source bytes, gap and literal. |
| Code entries `0805ECDC`, `0803C2BC`, `0803C3C8`, `0803E2E8` | Listings in `build/companion-dialogue/research/special-readers.txt`. `0805ECDC` identifies only 191/192 as special NPCs. Their response bases are 0/5/10, plus `random(5)`; after counter >3, field 19 is selected. The ordinary 0/2/4 plus binary choice path remains unchanged. |
| Actor offsets `[+13B,+13C)`, `[+C4,+C6)`, `[+0,+4)` | Existing one-byte NPC talk counter, signed condition field and flags. `0803C2BC` increments +13B; `0803C3C8` refreshes Rosa's condition via `0803E2E8`, then flag bit 1 chooses the alternate table indexed by clamped `response/5` (0–2). +C4 nonzero bypasses the refresh's inventory scan. No actor/save expansion. |

Level callers documented above choose `random(4)+15` for special NPCs, keeping
15–18 separate from silence field 19. A native fixture can supply +C4=1 to
preserve a controlled Rosa flag and execute the real branch without depending
on an absent dungeon inventory. This does not establish the natural inventory
condition. The already documented disposable actor record `[0203F000,0203F150)`
contains these fields. Its selector lifetime ends before the paged fixture
reuses `[0203F100,0203F102)` for its BX-LR yield callback. Formatter, stack and
history scratch retain their previously documented lifetimes and guards.

New text is appended after the previous combined end `01019EBD` with the shared
allocator, after every earlier component including the 16 history reflows.
No source reuse, table enlargement, renderer/font patch, permanent RAM change
or save-layout change is authorized by this discovery.

Completed combined English append: `[01000000,0102B977)`, 178,551 bytes.
The 1,227 new strings occupy `[01019EBD,0102B977)`, adding 72,378 bytes;
16,598,665 append bytes remain. The combined ledger has 4,086 allocations and
4,494 checked original patch ranges. Output SHA-256:
`50c06a6dfc6b5eb471eba234ce76c48038b1d99ce1a55935c4cb5b8e04f7cc68`.
[The ledger](../build/companion-dialogue/english-build.json) and
[acceptance](../build/companion-dialogue/acceptance.json) confirm preservation of
all earlier allocation records/payloads, original patches, null words and
RAM/save reservations. The new owner covers only its 1,227 pointer words and
appended strings. Every original source remains protected.

## Story/event source provenance (2026-09-11)

Research owner `story-provenance`; original Japanese ROM only, no insertion
allocation or permanent RAM/save change. All ends below are exclusive. Listings
and exact source records live in `build/story-provenance/`; see
[STORY_PROVENANCE.md](STORY_PROVENANCE.md) for proof scope and reproduction.

| Space / occupied range | Evidence and context |
|---|---|
| ROM `[00064E28,00064E68)` and dispatch table `[00064E68,00065114)` | Event interpreter fetch at `08064E42` reads a command word and operand together. Table has 171 four-byte targets for opcodes 1–AB. Individual handlers may consume extra records or change the cursor; this is not permission to decode every script as fixed eight-byte instructions. |
| ROM `[0006552C,00065600)` and `[00066306,000663CA)` | Text-command branches, including 23–2D and 96/97. Operand remains a direct source pointer in the checked wrapper calls; 29 queues positioned text instead. 96/97 consume following 98 records into a separate list before showing their prompt. 98 is not an ordinary story-text wrapper opcode. `dispatch-text.txt` contains instructions and literals. |
| ROM `[00061200,000613B0)`, `[00061680,00061760)` | Five story wrappers, the positioned-text queue writer at `0806136C`, and story preparation. Formatter call `08061726` uses source r3 from preparation, output `structure+0C`, limit `structure+40B`. Listings: `story-wrappers.txt`, `positioned-text.txt`. |
| RAM pointer `[03000010,03000014)`; UI-root-relative `[+50,+480)` | Existing story structure, at root+50; at least 430 bytes used including state fields. Observed structure `02033F48`. No claim this address is permanent in every game context. |
| Structure-relative `[+0C,+40C)`, `[+40C,+410)` | Existing 1,024-byte formatted text buffer (1,023 payload bytes plus NUL), followed by its read cursor. Natural trace observes buffer `[02033F54,02034354)`. Versions identify repeated reuse; this is a runtime message limit, not the ROM allocation limit. |
| Event-controller-relative `[+24,+28)`, `[+34,+38)`, `[+38,+39)` | Current command cursor, last fetched cursor, current opcode. Native event fetch and wrapper association use these fields. Controller extent and save representation are not inferred. |
| UI-root-relative `[+8D8,+958)`, `[+958,+998)`, `[+998,+99C)` | Existing 16 pairs of signed positions, 16 source pointers and count. Queue writer `0806136C` increments count without a visible bounds check. Positioned consumer `[000629C4,00062A6A)` loads the pointer directly and draws at `08062A54`; it clears the count afterwards. Negative x invokes native width centering; negative y is relative spacing. `positioned-draw.txt` records the consumer. |
| RAM `[02000430,02000434)` and `[02008B80,02008B98)` in the one-choice fixture | Existing count and first 12-byte selection record plus terminator, written by 96/97. Fixture has exactly one following 98 record. This does not establish the full list capacity or any save-field mapping. |
| ROM credits command envelope `[0091D6C8,0091DD00)`; text envelope `[0091DDB0,0091E667)` | 135 positioned commands reference 134 distinct existing English credit strings. Exact commands, sources, terminators and intervening non-owned gaps are recorded in `reviewed-resources.json`. These are original credits, not fan-patch translations. No pointer-patching ownership is granted here. |
| ROM command `[00AB94AC,00AB94B4)`; text `[00AB94E8,00AB94F9)` | Opcode 25 references the punctuation-only line `＊「……　……。`, omitted by the Japanese-letter filter. Original source bytes and native controlled-reader evidence are recorded separately from the master. |

Disposable native probes use controller scratch `[0203F000,0203F080)` and
synthetic command/list scratch `[0203F100,0203F120)`, restored from the original
trace's final state before each case. Stack scratch `[03007800,03007E00)` is
temporary during forced Thumb calls. These reuse earlier fixture addresses in a
separate process/lifetime, not alongside actor/history fixtures. Queue checks
seed only the existing root-relative arrays and count above; each case restores
the snapshot before use. No test writes to a cartridge or persistent user save.

## Default ally nicknames (2026-09-11)

Owner `ally-nicknames`; recorded before insertion. Original Japanese source and
existing companion build are pinned in `build/ally-nicknames/before/`. Ends are
exclusive. Exact per-row source/pointer records will be in
`translations/ally-nicknames.json`; this family covers 200 table rows, with 198
distinct immutable sources. It includes protagonist/NPC/reserved rows without
claiming normal monster recruitment for those rows.

| Space / occupied range | Reader, purpose and ownership |
|---|---|
| ROM `[001A9F30,001AA250)`; sources `[001AA250,001AAAC1)` | Existing default nickname pointers and source envelope. Native species*4 lookup `0802926E–0802927A`, base literal `[00029310,00029314)`. Own the 200 table words only; exact noncontiguous source bytes remain protected. |
| Actor-relative `[+130,+136)` | Six-byte compact nickname: at most five character IDs plus zero. Recruitment writes via `080292BA`, editor copies at `080292C4` and commits at `0802934A`; explicit final zero at +135. Adjacent +136 and +137 are not extension space. |
| Persistent party-record-relative `[+4,+A)` within 20-hex-byte records | `0804A460` copies six bytes from actor+130 at `0804A516` and writes zero at record+9. Species is +2; another field at +3; fields at +A onward are not nickname storage. This is a record offset, not a physical save-file offset. The serializer and cold-load block are mapped and tested below. |
| ROM `[0007D29C,0007D2A4)` | New bounded recruitment-encoder entry hook. The original encoder assumes two input bytes per character and cannot encode ASCII defaults. A caller-specific hook may handle the recruitment call (`LR=080292BF`); all other callers and original Japanese inputs must resume the original prologue/body unchanged. The earlier `name-entry` decoder hooks at 7D228/7D258 remain separately owned. |
| Recruitment stack-relative `[+28,+48)`, `[+48,+66)`, `[+68,+6E)` after its prologue | Concatenated default+duplicate suffix, copied default (30 bytes), and six-byte editor buffer. Existing format `%s%s` literal `[00029314,00029318)` points to `000A6BD4`. Duplicate counter helper `08000DF0` cycles 1–9 after its initial zero; suffix lookup `0807D28C`. Generated English defaults must retain a suffix within five output IDs. |
| ROM sources `000A9FE8` and `000A9FF4`; literal words `[00032B20,00032B24)`, `[00032C78,00032C7C)` | Existing colour/name/level templates identified by the coverage audit. Readers `080329EC`/`08032B4C` decode actor+130 into a 32-byte local and format into the existing 30-byte substitution outputs. Their controls and `Lv%d` need no prose translation; they will be checked with actual compact nicknames. No patch ownership is granted to their words in this pass. |

New nickname strings and encoder code must append through the combined allocator
after `0102B977`, preserving every earlier allocation/patch. Keep the six-byte
actor/party fields and five-slot nickname editor. Full reference names remain
in the catalog; short display names are explicit project choices. A duplicate
suffix can replace the fifth base letter when necessary, never spill into the
next actor/record field. Existing Japanese compact names remain decodable.

Disposable native fixtures use actor `[0203F000,0203F150)`, guarded name output
`[0203F200,0203F21E)`, source scratch `[0203F300,0203F380)`, optional persistent
record `[0203F400,0203F420)`, and temporary stack `[03007800,03007E00)`. State is
restored between cases; no permanent RAM reservation or user-save modification.

Additional native fixture fields: `[0203F500,0203F650)` is a zeroed viewer actor;
`[0200000C,02000010)` temporarily points to a controlled game header at
`02008000`. Only its compared actor ID `[0200804E,02008050)` and viewer pointer
`[02021EE4,02021EE8)` are supplied. These are short-lived probes in restored
snapshots; the town fixture normally has no dungeon game header. This prevents
name formatters from treating open-bus values as hallucination state. Native
record restore `0804A314`, specifically copy `0804A374`, confirms the reverse
six-byte transfer from record+4 to actor+130. The original suffix table includes
full-width **0** as well as 1–9; every generated default has a digit. Thus a
five-letter base becomes its first four letters plus that digit; custom input
still has five editable character slots.

The editor display probe enters `0807BAD4` with the native recruitment arguments
`(0, 0, six-byte buffer, 5, caller frame callback, 0)`. It reuses the already
documented source scratch at `0203F300`, and the game's existing editor buffer
`[02009DF8,02009E18)`; only the first six bytes are nickname data. Selector,
page and cursor globals `02009DF4`, `02009DE8`, `02009DF0` keep their existing
four-byte fields. A callback-preserving redirect at `0806DCDC` provides a live
UI context; it is a disposable test entry, not a recruitment gameplay route.
Later all-row display fixtures may replace only those six editor bytes and
request a native repaint. The ROM/editor limit and permanent RAM remain intact.

Save consumer discovery (before save-fixture writes): the original Adventure
Log serializer `08001EF4` copies **130 complete 32-byte records** from RAM
`[0200EE80,0200FEC0)` to Adventure Log-relative `[+4490,+54D0)` in its loop
`08002184–080021BE`. Its inverse `080022D4`, loop `08002500–0800253A`, restores
the same bytes. Evidence: `build/name-entry/storage-functions.txt`,
`build/name-entry/load-function.txt` and literal words `00022A8/00022C0`,
`0002704/0002708`. The active ten-record pool `[0200FD80,0200FEC0)` is the final
ten records of that serialized block, reached via `u32[020008C8]` on the town
fixture. Nickname fields are still `[record+4,record+A)`; all remaining record
bytes are occupied. The following 40-record and two-NPC transfers use different
source ranges (`0200FEC0`, `02010500`) and are outside this fixture's writes.

Disposable save probes may seed only the six nickname bytes of the first block
immediately before the native serializer loop. They must compare every other
record byte before/after seeding, capture the native serialized records and
check the corresponding complete block after a cold cartridge load. These
controlled name-field fixtures do not create valid recruited-party gameplay
state. **4490 is relative to an Adventure Log, not a physical FLASH address.**
Cartridge size remains `[00000000,00010000)`; no save record is expanded.

Completed nickname build: [ALLY_NICKNAMES.md](ALLY_NICKNAMES.md) and
`build/ally-nicknames/acceptance.json`. The combined English image preserves all
prior allocations/patches and uses appended `[01000000,0102C088)` including
padding (180,360 bytes). The new owner starts with alignment after `0102B977`;
198 strings precede the ASCII-ID table `[0102BF90,0102C010)` and the 120-byte
encoder `[0102C010,0102C088)`. The 200 pointer words and eight-byte encoder hook
are the only new original-ROM patches. Exact ranges and protected sources are
in `build/ally-nicknames/english-build.json`; the Japanese comparison variant
has its own ledger. Actor names, party records, save size and all earlier RAM
reservations remain unchanged.

## Opening story and first bedroom (2026-09-11)

Owner `opening-story`, recorded before insertion. Exact sources, immutable
command words and individual operand locations are indexed in
`build/opening-story/source-owners.json`, pinned to the Japanese original and
the preceding natural story trace. It covers 44 distinct sources / 52 operand
words: 36 naturally traced opening messages, the dream-refusal response,
six first-bedroom return/rest messages, and the shared sleeping-Tipper line.
The first narration source/operand already belongs to `story.opening_01` in
the curated build and must reuse its allocation and wording; 43 sources and
51 operand words are new ownership. No event command word is patched.

| Space / source-start group (exact exclusive ends in report) | Evidence, purpose and restrictions |
|---|---|
| ROM source starts `0091B8C8–0091BBB4`, `0091BD6C/0091BDC4` | Prologue, voyage setup and dawn narration. Exact NUL-inclusive ends are given by each source record. Native opcodes 25/27 and preparation flags 142/E1 are traced. Gaps and script bytes are occupied, not allocation space. |
| ROM source starts `00C2F37C–00C2F660` | Twelve birthday/dream/storm messages, including the unchosen refusal branch. Operand `00C2F1A8` retains command word `0001012C`; its choice behavior must survive relocation. New refusal operand is `00C2F1B0`. |
| ROM source starts `009FDDC0–009FDED8`, `00A00208–00A00364` | Chief's introduction and the two villagers' exchange in the opening. Exact traced operands/source bytes are in the ownership report. |
| ROM source starts `009C1C80–009C213C` | Initial bedroom, return/rest dialogue and sleeping-son observation. Nine existing event operands reference the one `009C1EB0` source; all nine opcode-23 words are explicitly recorded and must share one relocation. Remaining rest/return messages use their own original opcodes/choice parameters. |
| Existing story structure `[root+50,root+480)` | Reuses the previously mapped story engine and 1,023-byte payload limit. Narration has centered lines; dialogue has native continuation tabs. Font 0 layout and choice prompts must be checked in the actual engine. No buffer/save expansion is planned. |

New payloads append after the current combined cursor `0102C088` through the
shared allocator. Preserve all earlier allocations/patches, including the first
narration, and all original source bytes. Disposable controlled event-reader
probes may reuse `[0203F000,0203F080)` as controller scratch and the previously
mapped stack `[03007800,03007E00)`. They may point the controller cursor to an
actual original event command; they must not infer an eight-byte grammar for
other script regions. They restore a snapshot between cases. Native story
preparation/rendering uses its existing UI buffers and fields, with no permanent
RAM reservation or user-save changes.

Opening formatter guards use disposable `[0203F200,0203F600)` (1,024 bytes),
with eight sentinel bytes immediately before/after, during a separate native
formatter call. This reuses earlier fixture RAM with a new isolated lifetime;
it is never concurrent with nickname/viewer probes. The real story buffer and
read cursor continue to be used for the event-to-display check.

The natural English opening exposed a separate event Yes/No table, still
Japanese in the preceding build. Before insertion: ROM `[0086F49C,0086F4C0)`
contains three 12-byte records (two choices and terminator). Pointer words
`[0086F49C,0086F4A0)` and `[0086F4A8,0086F4AC)` target Japanese Yes
`[0086F4C8,0086F4CD)` and No `[0086F4C0,0086F4C7)`. Return values at record+8
are **1 for Yes and 0 for No**; record+4 and the terminator remain occupied.
Literal references `000613CC`, `000613EC`, `0006233C` identify shared event
choice readers; native width reads at `0808CB5A` reached both original strings
during the dream question. Only the two table pointer words gain new ownership,
with appended Yes/No strings. Code, geometry, default selection and return
values remain unchanged. These two additional label sources bring the catalog
to 46 entries (44 story + two choice labels), with 45 new sources and 53 new
pointer patches. Natural Yes and No routes must verify the branch behavior.

Accepted result: [opening story](OPENING_STORY.md) and
`build/opening-story/acceptance.json`. English ROM SHA-256
`2e05c0b030450216a47cdc76ecbb3d18195d6b0fa75bb4b3f5790e54701559e3`
owns appended `[01000000,0102CC13)` (183,315 bytes including padding). This pass
adds `[0102C088,0102CC13)` (2,955 bytes), leaving 16,593,901 appended bytes.
The English ledger records all 45 allocations and 53 new pointer patches;
Japanese relocation is a separate control image with its own ledger. Earlier
allocations, payloads, patches and source bytes are preserved. No RAM/save
reservation changes occur.

All 52 story operands pass native English display and Japanese pixel controls.
The two normal-input opening routes verify the original Yes/No behavior and
complete glyphs for 36/37 messages respectively, with zero unattributed reads.
The trace waits for the last bedroom message to display, not merely for its
formatter to queue it. Both Adventure Logs preserve seven-character Torneko
through actual FLASH saves and fresh-core loads. Later bedroom/rest event
outcomes remain outside the natural-route proof.

## First village departure arc (2026-09-11)

Owner `first-village`, recorded before insertion. The pinned Japanese extraction
in `build/first-village/source-owners.json` lists **281 source ranges and 367
individual event operands**, including shared references. Each entry gives its
inclusive ROM start, exclusive NUL-inclusive end, exact source bytes, command
word, operand location and receiving native wrapper. Range groups below select
source starts; their gaps, scripts and other data are occupied and are not free
space. Earlier opening-story sources are excluded and retain their ownership.

| ROM source-start selection, start inclusive / end exclusive | Purpose |
|---|---|
| `[009C2264,009C4820)` | Tessie's follow-up, morning/departure, both companions, map and bread, related return/rest messages. |
| `[009CDA68,009CE000)` | Fisherman's household, children and companion-dependent replies. |
| `[009D5660,009D7201)` | Chief's first meetings, messenger interruption, departure and related Torneko return/companion-switch conversations. |
| `[009E178C,009E1F60)` | House map, Rosa's introduction, caretaker, family comments and bed prompt. |
| `[009EA22C,009EBFC0)` | Village greeting/escort, residents, exit guard and repeatable dungeon/companion advice. |
| `[00B6E5A8,00B6F95F)`, `[00B6FC08,00B6FD50)` | Northern shrine explanation, Ines/Rosa choice branches and shrine attendants. |
| `[00B7A904,00B7A9F0)` | Ines's shrine directions and the unreadable ancient-writing observation. |

Only the recorded four-byte operands gain patch ownership. Native dispatch
branches for 23/25/26/2A/2C are already recorded in
`build/story-provenance/dispatch-text.txt`; opcode 26 invokes `08061320`, and
2A invokes `08061244` with its original choice parameters. Their command words,
branch targets and all original strings remain unchanged. Fake-controller
native checks alone establish reader behavior, not natural event reachability.

New payloads append after `0102CC13` through the shared allocator, preserving
all previous allocations, patches and reservations. No code or font insertion
is planned. Controlled probes reuse the isolated opening-story controller
`[0203F000,0203F080)`, guarded formatter area `[0203F200,0203F600)` plus eight
sentinels on each side, and stack `[03007800,03007E00)`. Restore a snapshot
between cases. Only the existing protagonist selector `[020014CE,020014D0)` is
varied for the one `$t` source, testing both Torneko and Tipper. No persistent
RAM or save-field expansion is introduced.

Natural route exploration continues a documented opening snapshot with normal
buttons, restoring it only between disposable sessions. A complete replay must
identify the source ROM/save and every input; no coordinate, scenario flag or
event-cursor injection is allowed in a route described as natural.

Accepted result: [first village](FIRST_VILLAGE.md),
`build/first-village/english-build.json` and `build/first-village/acceptance.json`.
English SHA-256
`0deb82fc65a1c776bb08e81d313990bc79a3833c0b2d2171968ffbcb7dc986ae`
owns `[01000000,01031C46)` (203,846 appended bytes including alignment).
This pass adds `[0102CC13,01031C46)` (20,531 bytes), leaving 16,573,370 appended
bytes. All 281 new sources use the 367 individually owned pointer patches;
all earlier payloads, patches, source bytes and RAM/save reservations remain
unchanged. The separate Japanese control image ends its append span at
`01032398`; its ledger is not to be stacked with the English image.

Native acceptance covers 368 English cases and Japanese pixel pairs (the `$t`
observation has two protagonist profiles). A fresh-core, normal-button opening
and first-chief-meeting route covers 46 sources / 3,838 native story reads with
no unattributed reads. Ten of these sources are newly translated village text.
All remaining scene triggers and choice outcomes have controlled display
coverage only. Both Adventure Logs preserve seven-character Torneko through
native FLASH saves and cold loads. The original 65,536-byte save layout remains.

## Early journey and place records (2026-09-11)

Before insertion, [source-owners.json](../build/early-journey/source-owners.json)
pins **194 Japanese sources**, their exclusive ends, **290 event operands**,
**30 place-record pointers** and **two Zoom UI literals** against original SHA
`35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02`.
The source-selection envelopes `[00B7A55C,00B7AD80)`,
`[00B84F18,00B87E00)`, `[00B92D68,00B93E00)`,
`[00B9EACC,00B9F200)` and `[00BA871C,00BA8E80)` include gaps and event data;
only the exact recorded operands are patch owners. Three previously inserted
shrine sources retain their first-village ownership. Nine short extraction
candidates inside event data are explicitly excluded, not promoted to text.

| Address space and exclusive range | Owner, evidence and restrictions |
|---|---|
| ROM `[00872E84,00872FEC)` | Thirty 12-byte place records: source pointer + two signed 32-bit map coordinates. Indices 0–27 are locations; 28 is From the beginning, 29 Invalid. These final labels are administrative records, not claims of playable locations. Exact records/source ends in the ownership report. |
| ROM `[00066CC8,00066CE0)` | Name getter `08066CC8` sign-extends the index, multiplies by 12 and loads field zero. Literal at `00066CDC`. No bounds check; fixtures use only indices 0–29. |
| ROM `[00066CE0,00066D04)` | Coordinate getter `08066CE0` copies fields +4/+8 and returns whether X is nonnegative. Literal at `00066D00`. Preserve both fields, including negative island/region sentinels. |
| ROM `[0006040C,00060420)` | Current-place name reader calls the getter using game variable 6. |
| ROM `[00076624,00076820)` (partial function listing) | Place selection draws names via getter at `000766A8` then native text at `000766BC`. Selected name is read again at `000767BE`, copied with limit 30 at `000767CA`, and terminated at byte 29 (`000767D0`). See [reader disassembly](../build/early-journey/place-readers.txt); the listing ends before the function does. |
| RAM `[0200A34C,0200A36A)` | Existing 30-byte `$m0` slot also holds the selected place name; literal `00076828`. At most 29 payload bytes + NUL. This is another transient use of an already occupied actor slot, not free space. Controlled copy fixtures may sentinel this slot and eight adjacent bytes on each side, restoring state after every case. No reservation or size change. |
| RAM `[02000430,02000434)` and `[02008B80,02008BD4)` | Existing count and six 12-byte advice choice records plus terminator. Four opcode-97 prompts consume six contiguous opcode-98 entries each. Native dispatch `08066306–08066396` writes pointers, zero field +4, ordinal field +8, then a null/null/-1 terminator. This establishes six-choice use only, not maximum capacity. Fixture state is restored per case. |

The six advice labels are sources `[00B86294,00B862D4)`, with exact NUL ends
in the report. Original command headers, list order and branch ordinals remain
owned by the game. Controlled fixtures select the actual ROM prompt cursor
using the already documented controller `[0203F000,0203F080)` and stack,
and exercise the original menu; no permanent RAM or save edits are approved.
The same fixture scratch area may hold the eight-byte result of the native
coordinate getter, isolated from the formatter scratch at `0203F200`.
Place-selection drawing fixtures execute the original window setup and row
loop `[08076672,080766C8)`, with one known table index on the disposable stack.
Their explicit stack arguments occupy `[03007E00,03007E08)` above the existing
call-stack scratch; this eight-byte extension is fixture-only and restored
after each case. Selected-name copy fixtures execute `[080767BC,080767D2)`.
The destination heading source `[00C3F010,00C3F017)` has checked literal owner
`000767E8`; confirmation source `[00C3F018,00C3F02F)` has owner `0007682C`.
The latter uses the existing `$m0` substitution above. These two sources are
included in the **194 entries / 322 checked pointer words**. Their exact terminator
ends are pinned by the refreshed source-owner report (no trailing alignment
bytes are part of a source). Confirmation fixtures may use the existing bounded
message engine and guarded formatter scratch with native copy output, restoring
state per case. Three stack arguments use `[03007E00,03007E0C)` in that helper.
Native window setup shows a **32px heading window at (16,24)** and **160px
destination window at (64,24)**, with destination text inset 4px. Full
Destination measures 53px; its display form Go to measures 26px. All thirty
full place labels fit both the remaining 156px and the 29-byte payload; no
place abbreviation, geometry patch or RAM expansion is required.

Accepted English payloads use the shared allocator after the first-village
append end `01031C46`, occupying new data/alignment `[01031C46,01034789)`:
11,075 additional bytes. The combined English ledger uses 214,921 appended
bytes and leaves 16,562,295 available. The separate Japanese control ends at
`01034B2F`. Earlier allocation/patch ownership is unchanged. All Japanese
source bytes remain occupied and preserved; no gaps, relocated sources or
zero runs become free space. [Acceptance](../build/early-journey/acceptance.json)
pins 274 native story cases, 64 place/confirmation/advice cases, all 338
Japanese pixel pairs, the natural opening/first-chief regression and both
Adventure Logs' native seven-character Torneko save/cold-load checks.

## Continuous story completion (2026-09-11, in progress)

The user authorized continuous completion of the remaining translation. This
does not turn the [remaining review queue](../build/completion/remaining.json)
into insertion ownership. Its ordinary-story leads still require Japanese
review, source reconstruction, exact operand records and native checks.

The cumulative [story ownership report](../build/completion/story/source-owners.json)
records the precise ranges and command/operand words of independently reviewed
entries in `translations/story-completion.json`. Initial lighthouse review:
147 sources / 182 operands, with source starts in `[00BB35EC,00BB5A50)` and
`[00BBDF6C,00BC0570)`. Only the report's exact words may be patched; these
envelopes include unrelated gaps and are not free space. Later sections extend
the report before being used by the builder, with prior entries preserved.

The existing native event dispatch, font 0, story buffer and fixture reservations
remain in use. Opcodes 23–28 and 2A–2D have source-register/wrapper evidence in
the [dispatch listing](../build/story-provenance/dispatch-text.txt) and native
provenance probes. This stage excludes positioned sources, choice-prefix
records and additional formatter grammars until separately reviewed. Centered
narration uses the existing `$c` mechanism and original three-line page.

The next cumulative review contains **438 sources / 542 operand words**. Source
envelopes (exclusive ends, with gaps still occupied) are lighthouse
`[00BB35EC,00BC056B)`, companion scenes `[009407E8,009461DC)`, castle states
`[00952720,00958177)`, four interview labels `[00955C84,00955CA5)`, and 44
individually listed exact repeats/transition prompts across
`[009430A4,00C0B537)`. The ownership report remains the authority for each
actual source and operand; none of these envelopes is a writable pool.

Choice-prefix review now includes the Samson interview prompt at event command
`00955938`, operand `0095593C`, followed by four 8-byte opcode-98 records
`[00955940,00955960)`. Their pointer words are `00955944`, `0095594C`,
`00955954`, `0095595C`, in Background / Skills / Hobbies / Finish order.
Opcodes 96/97 use the already documented dispatch `[08066306,08066396)`.
The parser bounds reviewed lists to six choices and records their exact count,
prompt and ordinal. Existing native count `[02000430,02000434)` and table
`[02008B80,02008BD4)` suffice; the four-choice terminator occupies
`[02008BB0,02008BBC)`. No RAM or save expansion is introduced. Native menu
fixtures restore the documented world state, dispatch the actual ROM prefix,
check the ordered records and terminator, then call the existing menu drawer.
Positioned text and additional formatter grammars remain separate.

The subsequent cumulative draft report contains **827 sources / 1,003 operands**.
Additional source envelopes are royal scenes `[009642B8,0096A7ED)`, chambers
`[00974CD0,00975AF5)`, kitchens `[0097F13C,009800D1)`, gates
`[0098C324,0098D651)`, monster lodge `[009A4DB4,009A5907)`, Medal King
dialogue `[009A5958,009A5BFF)`, and Tipper village states
`[009A6FBC,009A8B1B)`. Exact per-source terminator ends and all operand words
are recorded in the cumulative ownership report before building the `royal`
checkpoint. The prior 438-source castle checkpoint has passed 553 story and
one four-choice native menu cases, with all 554 Japanese screenshot pairs
identical. Its English append uses 243,355 bytes and leaves 16,533,861 free;
the entire prior early-journey append `[01000000,01034789)` is byte-identical.

The next `coast` checkpoint freezes **1,418 sources / 1,726 operands** from the
same cumulative ownership report. Additional source envelopes are Tipper
village `[009A6FBC,009B4AB1)`, awakening `[009C4AA8,009C56FF)`, departure
`[009D7324,009D8F01)`, Barinabo's later state `[009E9EE4,009EC561)`, village
celebration `[009F96FC,009FF523)`, Costa Libera `[00A0AC38,00A0ED0D)`, its
service-room dialogue `[00A1BA88,00A331F5)`, arena visitors
`[00A475C4,00A4D163)`, and home dialogue `[00A74270,00A752AB)`.
The 194 exact-repeat sources remain individually owned across
`[009430A4,00C0B537)`; [reuse reports](../build/completion/reuse/) record the
150 new exact Japanese matches to already authored prose. Unknown owners and
choice prefixes are excluded from that automatic reuse. No envelope or gap
is free space. [Five language revisions](../build/completion/language-revisions-01.json)
record intentional corrections within the new cumulative drafts; frozen
checkpoints and the original 4,828-source baseline are preserved.

The 827-source `royal` checkpoint passed 1,020 native story cases and one
four-choice menu, with all 1,021 Japanese screenshot pairs matching. Its normal
opening/escort/chief route covers 46 messages with zero unattributed reads.
Both Adventure Logs preserve the seven-character Torneko name through native
FLASH save and cold load. These regressions use the existing documented
fixture reservations and unedited disposable save files; they establish no new
RAM/save ownership or natural reachability of the additional story scenes.

The shared allocator rebuilds from the pinned original through the accepted
early-journey components, then appends reviewed story data after `01034789`.
It rejects duplicate owners, unexpected overlaps and source-byte mismatches.
Original command parameters and source bytes remain occupied and unchanged.
English and Japanese control images have separate complete ledgers. Any
checkpoint is a preserved intermediate build, not complete-game acceptance.

The `story-pages` checkpoint freezes **2,258 sources / 2,810 exact operand
words** from the cumulative ownership report, including the remaining ordinary
story prose through the ending, rest stops, postgame Conklave Village, castle
town and lighthouse-house statue advice. The report pins every exclusive source
end and four-byte pointer owner before insertion. Its chapter envelopes contain
unrelated scripts/data and remain occupied. Sixteen short ASCII prefixes of
aligned binary event data are [excluded from ordinary prose insertion](../build/completion/story/short-source-review.json);
the two password-hint sources remain separate until the input path is reviewed.
Neither category creates free space or counts as translated Japanese.

Additional native choice prefixes use the existing count/table RAM and drawer:

| Prompt command (ROM offset) | Count | Exclusive opcode-98 record range |
| --- | ---: | --- |
| `00AFCCE0` | 4 | `[00AFCCE8,00AFCD08)` |
| `00AFCE18` | 3 | `[00AFCE20,00AFCE38)` |
| `00AFD874` | 4 | `[00AFD87C,00AFD89C)` |
| `00AFD9AC` | 3 | `[00AFD9B4,00AFD9CC)` |
| `00AFDC2C` | 6 | `[00AFDC34,00AFDC64)` |
| `00AFDE44` | 5 | `[00AFDE4C,00AFDE74)` |
| `00BCAACC` | 6 | `[00BCAAD4,00BCAB04)` |

The first six lists are Conklave dungeon selection/information menus; the last
is statue advice. Each eight-byte record's pointer is at +4. Original command
flags and choice ordinals remain unchanged. Three-, five- and six-choice native
terminators occupy `[02008BA4,02008BB0)`, `[02008BBC,02008BC8)` and
`[02008BC8,02008BD4)` respectively, within the existing fixture reservation.
No permanent RAM/save change is introduced. All eight cumulative menus,
including Samson's four choices, receive ordered-record and native drawing
checks against their frozen Japanese controls.

## Pet names and the tree password: reader audit (2026-09-11, in progress)

[Native input dispatch](../build/completion/story/input-dispatch.txt) establishes
opcode `30` for a name loaded from script variables and opcode `31` for an
empty password. Both clear the existing compact buffer `[02008BF0,02008BF8)`
and call `08061584` with the limit from command bits 8–15. The dog command
`[00A0DF28,00A0DF30)` is `00570730`; the first cat command
`[00A744C8,00A744D0)` is `005F0730`. Both request seven characters. The gate
command `[00C1528C,00C15294)` is `00000731` with operand `08C15394`.
The Japanese comparison source `[00C15394,00C153A3)` is seven CP932 characters
plus NUL, ヒラケヨハイレ. This audit does not yet authorize replacement; hints,
keyboard input, conversion and comparison must be verified together.

The [pet reader](../build/completion/story/pet-readers.txt) `08000888` reads
compact IDs from the original 16-bit script-variable array at `020010C0`,
looks each up through `0807D20C`, and already supports both one- and two-byte
output glyphs. `$p1` / `$p2` load variable indices 0057 / 005F from ROM
`[00C46D6C,00C46D70)`, then request seven slots. Thus dog IDs occupy
`[0200116E,0200117C)` and cat IDs `[0200117E,0200118C)`. Adjacent variables
0056, 005E and 0066 remain separate; no terminator may be written beyond the
seven 16-bit slots. The output needs at most 14 glyph bytes plus NUL. This
uses original occupied RAM and does not establish a physical FLASH offset.
Controlled fixtures may fill these existing slots, guard adjacent variables,
and restore the complete state after each case. No capacity expansion or
permanent new RAM reservation is approved or required by this finding.

The [input wrapper](../build/completion/story/input-callers.txt) `08061584`
uses the existing story root from `[03000010,03000014)`: state +0, input mode
+8D4, stage +488, limit +48C, compact-buffer pointer +490, result +498. These
are fields in an occupied runtime structure, not standalone free RAM. Input
fixtures may invoke the native wrapper/dispatcher with the existing disposable
controller and call stack, then run the original UI callbacks with joypad input.

The [completion callbacks](../build/completion/story/input-return.txt) establish
that password input is type-zero compact text, converted at `08064BDC` through
`0807D228` into a 16-byte stack buffer `[sp+4,sp+14)` (hex offsets). A native
byte comparison against the opcode-31 operand keeps result 1 on an exact match
and changes it to 2 on mismatch; cancellation passes its distinct result.
The comparison ends at `08064C0A`, then original `08066C1C` chooses the branch.
Controlled callback fixtures use `sp=03007C00`, so the buffer is
`[03007C04,03007C14)` and result `[03007C7C,03007C80)`, within the already
reserved disposable call-stack area. No game stack size is changed.

The [pet commit callback](../build/completion/story/input-callbacks.txt)
`[08064B70,08064BA2)` writes only on result 1, through
[writer `08000818`](../build/completion/story/pet-writer.txt). It copies up to
seven compact bytes into seven halfwords, zero-filling unused slots without
writing an eighth halfword. Its fixture result occupies
`[03007C78,03007C7C)`. The original keyboard body at `[0806248C,080624BC)`
calls `0807BAD4` with type zero and the existing story callback `0805FF61`;
`[08062822,0806282C)` stores the native return at story-root +498. Input
fixtures exercise this path with normal frames after actual event dispatch.

Before the `story-special` insertion, its [exact ownership report](../build/completion/special/source-owners.json)
pins **32 source strings / 33 operand words**: the 29 `$p1`/`$p2` story
sources, both spoken tree-password hints, and its opcode-31 comparison string.
The independently authored keyword is `LETMEIN`, seven uppercase letters. Both
hints use exactly that spelling. The build patches only the listed pointer
words; the original comparison, input limit, compact map, branch metadata and
pet storage remain unchanged. All new payloads go through the same allocator
after the frozen 2,258-source story build. Previous source strings stay occupied.

The [native input audit](../build/completion/input-audit/keyboard-probe.json)
used actual command dispatch, the original keyboard and real joypad entry of
LETMEIN / Biscuit / Mittens. The original Japanese keyword correctly rejected
LETMEIN; both pet commit/getter cases retained all seven letters and preserved
adjacent variables and the guarded 15-byte output bound. This is controlled
input/reader evidence, not natural adoption/gate reachability or save proof.

All six naming contexts and the gate command are pinned in
[input-owners.json](../build/completion/special/input-owners.json). The four
additional cat commands use the same seven-slot variable range and native
callbacks; they grant no additional patch ownership. Keyboard fixtures now
run dispatch through `0806566E`, including its original `08069948(0,8)` call
before yielding to normal frames, so input state matches the full command.

[Variable-block copies](../build/completion/story/pet-variable-copies.txt)
`08000B58` / `08000B70` serialize/restore the full 1,024-byte script-variable
array `[020010C0,020014C0)`. Save caller `08002012` and load caller `0800238C`
use record-relative `[1B88,1F88)` (literals `00002298` / `000026DC`). Dog
names therefore occupy record `[1C36,1C44)` and cat names `[1C46,1C54)`.
These are offsets within a decoded Adventure Log record, **not physical SRM
addresses**. Existing adjacent flags/variables retain their ownership. Native
save fixtures may seed only these two seven-halfword name fields immediately
before `08002012`, compare the full serialized variable block after `08002016`,
and check native restore after `08002390`. Native FLASH/checksum handling and
the 65,536-byte physical save size remain unmodified.

## Shared story events (2026-09-11)

The [shared-story ownership report](../build/completion/shared-story/source-owners.json)
pins **78 sources / 105 pointer operands** in the 0091 script region before
insertion. These are shared object-search messages, monster-elder/synthesis
services, transition narration, bonus-cave events and two original fallback
diagnostics. Their exact NUL ends and native command headers are recorded;
unrelated debug globals and weak binary decodes remain separate. These sources
were outside the initial ordinary-story queue's 0094 lower bound, illustrating
why processing that queue alone cannot establish complete text extraction.

Synthesis prompt command `00918BB4` is followed by three opcode-98 records
`[00918BBC,00918BD4)`. Their pointer words are `00918BC0`, `00918BC8`,
`00918BD0`: Synthesize / About synthesis / Cancel. Original branch parameters
and ordinals remain intact. Existing three-choice RAM, font 0 and the same
native menu drawer apply. No additional RAM or save allocation is made.
Payloads append through the shared allocator after the pet/password component;
all previous source and appended bytes are preserved. The cumulative ownership
ledger must validate the combined build before it is written.

### Arena, entry conditions and save notices (continuous completion)

Before insertion, the [arena source-ownership report](../build/completion/arena/source-owners.json)
pins 108 original sources and 128 checked pointer words to the Japanese SHA256.
It records exact exclusive ends; the broad `[00C4029C,00C420AD)` selection
is not a free-space claim. Four shared save notices near `0086EF3C` are also
included with their exact source spans. `C411B0` and `C41ACC` retain the earlier
ally-service owners. Colour-only printf wrappers and `dv_save_*` resource keys
are not new translation sources. All payloads use the cumulative shared
allocator after shared-story. Original source bytes remain protected.

The typed arena/church menus use 12-byte `[pointer,0,return_value]` records,
followed by a 12-byte zero terminator. Exact occupied ranges are
`[00C40260,00C4029C)`, `[00C402F4,00C40330)`,
`[00C40358,00C40394)`, `[00C403E0,00C4041C)`,
`[00C4044C,00C40470)`, `[00C414B8,00C414F4)`,
`[00C41530,00C4156C)` and `[00C4158C,00C415BC)`.
Counts are 4/4/4/4/2/4/4/3. Return values (including the nonsequential
registered-battle menu and Yes=1/No=0) and terminators stay unchanged.
Native menu reader `0807B294` is exercised through drawing at `0807B3B6`.

[Original readers](../build/completion/arena/research/readers.txt) establish:

- Arena records `[020091D0,02009220)` contain ten eight-byte entries, species
  halfword at +0 and level at +4. Odds `[02009228,02009250)` are ten signed
  32-bit tenths. Count `[02009254,02009258)` is separate. Fixture seeding is
  disposable and restored per case; gaps/neighbours are not reservations.
- List reader `[08079868,0807992E)` uses window template 3 and ten original
  y positions `[00C402E0,00C402F4)`, x=4. Its 0x90-byte stack frame holds
  formatted row `[sp+10,sp+50)` (64 bytes) and name `[sp+50,sp+90)`.
  Source `C41484`, newly owned literal `79934`, is
  `%2d:%sLv%d <03 09 7C>%d%c%d倍`. The final three arguments are integer
  quotient/remainder of odds divided by ten and a literal period. Its English
  payload moves the odds column to `A0` (160px) and uses `x` for the multiplier;
  printf argument order, original source and code remain intact. Native layout
  checks must establish all species names fit without crossing this column.
- Popup reader `[0807993C,08079C0C)` has a 0x424-byte local frame, row buffer
  `[sp+10,sp+210)` and name/trait work area beginning `sp+210`. Its header
  uses window template 12, x=4/y=2; later trait draw is a separate source.
- Source `C413D4` is a shared `%sLv%d` form. It feeds both arena headers and
  the 30-byte `$m0` slot through `080797EA`. Enumerate all translated species
  with level 99 against that smaller destination, not the roster's capacity.
- Entry-condition reader `[0807A68C,0807AA78)` copies a 64-byte window
  template `[00C41E24,00C41E64)`. Selected flags determine its height and
  row spacing. It renders the heading and all selected single-line coloured
  warnings, then Yes/No in window 1. The companion substitution uses a
  300-byte stack buffer `[sp+44,sp+170)` inside its 0x194-byte local frame.
  Fixture draws stop at `0807A8F4` before input polling; they do not execute
  dungeon entry or prove its inventory/level/save consequences.
- Numeric betting input calls `0807B604` at `08079738` with three digits,
  default/minimum 10, maximum min(balance,100), and source `C41314` as its
  single-cell unit. English uses `T`, consistent with existing token inputs.
- Balance header `08079F88` formats `C414A4` into a bounded 100-byte area;
  original `$d0` is temporarily populated and then restored. Saving notices
  at `7ACEC`/`7ACF4` are passed to original save wrappers, not story opcodes.

Fixtures reuse the previously documented formatter scratch/guards and callback
at `0203F100`. Native arena/entry frames and extra call arguments use only the
existing disposable stack envelope `[03007800,03007E40)`; this extends the
prior fixture argument envelope by 52 bytes for the entry function's eleven
arguments. It is not game RAM or save expansion. All ranges above remain
occupied. Reader evidence is structural; runtime acceptance is recorded
separately in the arena component report.

The arena odds generator at `[08078EC8,08078F5A)` initializes a missing
entry to 10 tenths, otherwise applies a random 9/10/11 factor and clamps to
`[11,9999]` tenths (literal `[00078F48,00078F4C)` = 9999). Thus the real
maximum display is `999.9x`; the static 9999.9x fixture is an additional digit
of stress. The generator also clears an eleventh eight-byte sentinel record
`[02009220,02009228)` before the odds array; readers above draw ten rows.
See [generation disassembly](../build/completion/arena/research/arena-generation.txt).
The balance destination is `[0200A3C4,0200A428)`, already used by token
and bank headers. The name/level destination is `[0200A34C,0200A36A)`;
its following actor slot is independently owned and checked for corruption.

Ownership reconciliation before the successful arena build: literals
`[000799A8,000799AC)` and `[00079B84,00079B88)` already belong to the
enemy component's two-line popup headers (documented above). The allocator
rejected the first overlapping build attempt. These two owners are now recorded
as excluded in the arena catalog; their prior allocations, pointer patches,
separator y31 and trait y39 remain unchanged. The arena list's separate
`79934` pointer and name/level pointers `7984C`/`798D0` are new owners.
The successful cumulative ledger must contain each of these patches once.

Arena save-notice fixtures also set the existing one-byte Adventure Log selector
`[02004F80,02004F81)` to 0/1, restoring state per case. Formatter `$j0` reads
it through literal `0007DAF4` and selects fullwidth `１`/`２` from original
`[00C46D64,00C46D6B)`. This preserves the earlier two-slot glyph convention;
it is not a save-field expansion. Existing callback words `[02008E28,02008E30)`
select the game window constructors used by `0806C7F8`/`0806C814`; fixtures
observe these values and use their native constructor code.

Native [baseline list probe](../build/completion/arena/research/list-probe/probe.json)
confirms window 3 is only **160x128px**, not 208px: long English names overlap
the original odds column. Its immutable 64-byte template is
`[00CA2934,00CA2974)`, x=2/y=3 tiles, width=20/height=16. The arena component
copies that template through the append allocator and changes only copied
width from 20 to 26 tiles (208px, screen x16..224). It does not alter stock
window 3 for other callers.

The English-only hook owns `[00079868,00079870)` (original halfwords
`B5F0 B0A4 2003 2101`). An allocated Thumb trampoline replays the original
push/sub prologue, sets r1=r2=1, and calls native descriptor constructor
`0806C814` with the allocated copied descriptor. It then resumes at
`08079876`, immediately before the original font setup. The hook is an
absolute Thumb load/BX because appended ROM is beyond Thumb BL reach. It
preserves the caller's saved registers/return address and original stack size;
it adds no permanent RAM. The shared allocator records exact code/descriptor
ranges and hashes. Japanese-control builds retain the original instructions
and geometry. Full native list tests must cover all ten row positions and
both protagonist paths, buffer bounds and the original popup regression.

Arena isolated printf/copy fixtures use name scratch `[0203F080,0203F0C0)`
(64 bytes) with eight-byte guards on each side; this is disposable, outside the
story controller and before the callback at `0203F100`. Actor-slot guards may
temporarily occupy the last eight bytes of the prior item slot and the first
eight bytes of the next actor slot only in restored isolated-copy cases; no
live combined substitutions run while those sentinels are present.

The [arena generator table audit](../build/completion/arena/research/generator-bounds.json)
records all 101 pointer entries in each occupied table
`[000F2584,000F2718)` and `[000F3D54,000F3EE8)`, plus every selected
four-byte species/level record through its zero-species terminator. Original
generator `[08078D48,08078F90)` selects these tables; observed table levels
are 1..9 and 1 respectively. Thus the level-99 display/copy cases exceed all
arena-generated levels. The tables and their referenced records are read-only
evidence, not insertion or free-space authority.

### Adventure-history records (continuous completion)

Before insertion, [history source owners](../build/completion/history/source-owners.json)
record **100 distinct nonempty Japanese sources / 104 value pointer words**.
The complete typed table `[00C4D250,00C4D5B8)` contains 108 eight-byte
`[ASCII key pointer,value pointer]` records and an eight-byte zero terminator.
The `log_error` record and three blank values are intentionally preserved;
`[00C4E4E0,00C4E4E9)` is its four fullwidth question marks plus NUL, a
punctuation-only resource outside the initial inventory. It is neither hidden
Japanese prose nor approved free space. The report records every key, value,
source exclusive end and terminator; the broad source envelope is not owned.

Native lookup `[08087788,080877C0)` scans the original eight-byte table via
literal `[00087790,00087794)`. It returns the value on exact key match.
Formatter/display selection `[08086C30,080871E2)` constructs `log_*` keys,
reads actual history counters, and uses the original shared formatter in mode 1
with 512-byte output capacity. Preserve all keys and counter semantics.
Display `[08086B18,08086C30)` uses window template 20, ten rows at x4,
y=3+13*row, and native scrolling/wait helpers. Controlled all-key fixtures
establish lookup/format/draw coverage separately from earning each achievement.

`log_2_9` (Barinabo mode) concatenates a mode prefix, the dungeon label and
`log_2_9b` (floor reached) through the unchanged `%s%s%s` at `00C4E510`.
The `log_2_9a` dungeon-cleared suffix is a separately retained table entry.
`log_3_*b` is shared by five dungeon records and uses `$i0` for the recorded
elapsed time, formatted by `08086F30–08086F52` through original
`%4d:%02d:%02d` at `00C4E530`. Numeric `$v07`
fields and their preceding opaque `03`/column controls must survive encoding.
Fixtures reuse existing number/item/hero slots and guarded formatter scratch;
no history counter, RAM allocation or save-record size is enlarged.

History context fixtures observe the existing root pointer `[02000004,02000008)`
(value `02004DE8` in the saved fixture). Five dungeon progress records have
20-byte stride at root+`34`, floor at +`36`, turn count +`38`, and elapsed
seconds/minutes/hours halfwords at +`42`/+`44`/+`46`, each plus 20*index.
The Barinabo floor is the halfword `[root+9E,root+A0)`; its dungeon byte is
`[02010619,0201061A)`. These are existing runtime counters. Controlled tests
seed only these fields after restoring state, and never claim to earn an
achievement or write a physical save offset. The first history draft
misidentified the `$i0` field; its correction to elapsed time is recorded in
[the draft revision](../build/completion/history/draft-context-revision.json)
before native acceptance.

### High-score/result reader investigation (continuous completion)

Read-only evidence in [result readers](../build/completion/results/research/readers.txt)
and [record readers](../build/completion/results/research/record-readers.txt)
establishes a **48-byte high-score record**: reader `0800177C` addresses
`02002FE8 + category*960 + row*48`. The eight displayed categories have twenty
records each, occupying `[02002FE8,02004DE8)`; the history root begins at the
exclusive end in the observed fixture. This is separate from the 92-byte
Adventure Log summary records read by `080853E0`.

High-score fields read so far include cause halfword +0, involved actor +2,
flags +4, an auxiliary halfword at +6 (role still under review), three-byte score +A, three-byte gold +D, three-byte EXP
+10, three-byte adventure count +13, floor byte +19, strength +1B/+1C and
level +1D. `0800155C` reads the dungeon ID from bits 0..5 of byte +1A.
`08001584` selects Torneko/Tipper from bit 6 of that byte;
`080015B0` reads its bit 7 (special record styling). The high-score list and
detail functions use the existing `$t` protagonist substitution, not the
Adventure Log compact-name converter. This is reader evidence; full record
creation and save persistence are still under investigation.

Disposable high-score probes may seed one complete 48-byte record at the
start of an existing category, with state restored each time, then execute
`0800177C(category,row,guarded_destination,200,mode)` in modes 0/1/2.
The destination uses documented formatter scratch and sentinels. No persistent
record size or physical save-file offset is changed. Literal words, result-key
and relation-prefix tables remain occupied and require their own ownership
report before insertion.

The [controlled result probe](../build/completion/results/research/probe/record-probe.json)
executes both protagonist bits in all three native prefix modes. It confirms
that `$t` is Torneko/Tipper rather than the editable Adventure Log name.
The seeded actor ID 1 is Drooling ghoul (not Slime); dungeon selection follows
byte +1A's low six bits, independently of the auxiliary +6 field. The
original result formatter also abbreviates list output with ellipses; this
is separate from full result-detail text and must be preserved in its tests.

The [third reader](../build/completion/results/research/ending-reader.txt) is
`0805BEFC`, the dungeon-ending screen. It shares result causes and actor-relation
formats with the list and detail readers. Exact proposed text ownership is in
[result source owners](../build/completion/results/source-owners.json): 185
resources / 284 pointer words, including three scoped empty relation copies and
one short relation format outside the master inventory. All source ranges remain
occupied. The following tables are typed, not inferred free space:

| ROM file range | Owner / reader evidence |
| --- | --- |
| `[000DB17C,000DB308)` | 99 cause-indexed actor-relation pointers. Six unique formats. Literals `00001A2C`, `0005C4C4`, `000868A0`. Each reader formats into the existing 30-byte `$m1` slot `[0200A36A,0200A388)`. English moves the particle/relationship wording into the result tail; the six formats copy `%s`. |
| `[000DB33C,000DB35C)` | Eight compact category pointers, used in the dungeon-ending score/rank row. Full category wording is retained separately from measured display labels. |
| `[000DB3B8,000DB6E8)` | 101 eight-byte key/value records plus eight zero bytes at `000DB6E0`. 97 unique Japanese cause tails. Literals `00001B68`, `0005C674`, `00086A0C`. ASCII lookup keys stay unchanged. |
| `[00C4CF68,00C4CF94)` | Eleven high-score/category labels, including history, campaign and the empty-score notice. |
| `[0018F16C,0018F734)` | Existing 370-pointer item-name table, also copied to `$i2` for result messages. The high-score record's halfword **+6 is an item ID**, consumed at `08001AFE` and `080869B0`; it is not the dungeon ID. This component preserves prior item-table ownership. |
| `[0009B34C,0009B34D)`, `[000DC7A0,000DC7A1)`, `[00C4D1B8,00C4D1B9)` | Empty unknown-actor relation source copies, owned only through words `00001AA0`, `0005C53C`, `00086914`. English needs `something` in these three relation slots; other empty strings stay unchanged. |
| `[00CA2D74,00CA2DB4)` | Original 64-byte window-20 descriptor: x/y 2/2, width/height 26/17 tiles. Private result-detail descriptor copies it and changes x/width to 1/27, giving 216px. The original descriptor and other window-20 users remain unchanged. Native edge/border/layout checks are pending. |
| `[0008651A,00086524)`, `[0005C0AC,0005C0B6)` | Proposed English-only result-detail constructor hooks, replacing the three argument moves and call to `0806C7F8`. Each allocated shim calls the existing custom-descriptor constructor `0806C814` with r1=0/r2=1 and resumes immediately after the original call. The high-score **list** constructor at `080860EE` remains original. |

All new result text, the private descriptor and code shims use the cumulative
allocator. No RAM reservation or save-field expansion is proposed. Fixtures may
copy a private descriptor into already documented disposable formatter scratch
for a native construction probe, restoring the state before each case. Detail
format helpers `08086AEC` and `0805C7DC` retain their original 200-byte buffers.
Result control `$+`, the original CR/two-row contracts and optional remark logic
must be verified through their real readers before this component is accepted.

The first 232px proposal was **rejected before acceptance**. Its complete images
and ledgers are preserved in [rejected-width232](../build/completion/results/research/rejected-width232/rejection.json).
Native constructor `0808B6FC` calculates tile storage from base `02035DDC`
(literal `0008B7EC`), starting window 0 at tile 2, address `02035E1C`.
The 29*17*32-byte clear reaches `[02035E1C,02039BBC)`, overwriting the font
pointer table at `[020398EC,020398F8)`. A 27*17*32-byte window occupies
`[02035E1C,0203977C)`, below that state; both 26- and 27-tile controls preserve
the font pointers. See [constructor/storage disassembly](../build/completion/results/research/window-storage.txt).
The larger geometry is not approved for any existing buffer.

The revised 216px result panel uses a private **370-pointer item display table**,
derived from the already translated item pointers. It changes only the three
result-consumer table literals `[00001B60,00001B64)`, `[0005C668,0005C66C)`,
`[00086A04,00086A08)`. Eight names over 91px receive documented abbreviated
display forms in these result contexts; full glossary and inventory names are
preserved. Cause 33 joins the actor and item with a compact colon. Enumerating
the maximum actor, original special marker and item width must fit 216px.
All table/name allocations use the shared ROM allocator. No RAM expansion is
made. Native window-0 state is the existing 64-byte record
`[02034CD8,02034D18)`; +14/+18 hold bitmap pointers, +24 is the byte count.

The [record writer](../build/completion/results/research/record-writer.txt)
`080011F0` inserts/shifts whole 48-byte high-score rows. It selects four dungeon
categories (default, IDs 20/18/31) plus four for the second protagonist. Its
game-state root is `u32[0200000C]`; fields read include actor pointer +19EE4,
cause/actor/flags/item/transform halfwords +20E64/+20E66/+20E68/+20E6A/+20E6C,
floor halfword +20E70 and score inputs +14E4 (u32), +150C (s16), +14DC (u32).
Controlled record-creation fixtures may seed these existing fields after state
restore, then exercise all eight categories and verify full-row shifting. They
may use documented formatter scratch for returned score/category words. This
does not create persistent RAM reservations or claim natural dungeon outcomes.

The shared score/history profile is **8,108 bytes** at
`[02002FD4,02004F80)`: 20-byte header, 160*48-byte scores and 408 history bytes.
Header +0 is the checksum; +4/+8/+C are native identity/version words. The
checksum helpers `080015BC` / `080015E0` cover words +10 through +1FA8.
Reader `08001610` checks the identity and checksum after reading this block
through `08087CBC`, starting at FLASH sector 14. Writer `080016DC` updates its
header and calls `08087D20`. The sector wrappers establish 4,096-byte sectors:
the profile payload occupies physical save bytes `[0000E000,0000FFAC)` inside
the final two sectors `[0000E000,00010000)`. Sector-write padding is separate
from semantic profile fields; it remains under native verification. The
earlier Adventure Log regions must remain byte-identical during profile-only
tests. See [FLASH reader](../build/completion/results/research/score-flash.txt)
and [writer](../build/completion/results/research/score-flash-writer.txt).

Profile fixtures use an existing native two-Adventure-Log save as their input,
the documented original profile RAM and disposable status words at `0203F200`.
They call the native checksum/header/write path after its message-window call,
then load the resulting save in a fresh core. Original 65,536-byte size and both
seven-character Adventure Log names remain explicit regression checks.

The saved village fixture has `u32[0200000C] == 0`, so it is **not** a live
dungeon-state fixture. Isolated record/ending-reader probes may temporarily
point it at `02010A90` inside the original heap, seeding only the documented
root-relative fields above. The actor pointer uses existing disposable actor
scratch `[0203F000,0203F150)`, with species +8, HP +54/+58 and EXP +9C. No whole
heap clear is permitted. Do not resume gameplay or invoke heap allocation in
this synthetic context. Restore the original saved state before FLASH work or
frame rendering, transferring only the native-created profile bytes required
by that test. This is controlled record construction, not natural dungeon
entry or a new permanent RAM layout.

The ending-display fixture may execute `[0805C0AC,0805C62A)` with the original
`0x188`-byte frame's established locals and the synthetic root described above.
This includes the original result constructor, record creation and all header,
statistic, category, equipment and cause formatting. It stops before gameplay
consequences. The original heap bytes and root/selector fields are restored
before advancing display frames; the native result tilemap is revealed through
`0808BB14`, as in the original score-detail flow.

The category selector `08085FB0` constructs its own 64-byte stack descriptor
with x/y 3/2 and width 18 tiles (144px). A proposed checked English patch at
`[00085FCC,00085FCE)` changes `mov r0,#18` (`12 20`) to `mov r0,#26` (`1A 20`),
making this one menu 208px. Its dynamic height/count table remains unchanged.
The selector enumerates occupied score categories, then history, or the missing
profile notice. Campaign is a preserved typed-array label with no selection
path established in this routine. Native category tests must distinguish those
paths from direct label coverage. The wider stack descriptor remains below the
original tile-buffer limit for the selector's maximum nine rows.

Ending fixtures temporarily set the existing dungeon ID byte
`[02004FF0,02004FF1)` and protagonist-mode byte `[02004FF4,02004FF5)`, read at
`0805C0C2`/`0805C0CC`. They restore these fields before display frames.
Category selection uses the existing byte-index array starting at `020105F8`;
this reader writes at most nine bytes. Its height table starts at ROM
`00C3D8C6`; count 9 selects 14 tile rows, so the wider menu uses 11,648 bitmap
bytes within the original buffer.

Native profile save verification confirms the full two-sector write behavior:
`08087DBC` always writes/verifies 4,096 bytes. The second call receives the
original source pointer, so the full backing read is
`[02002FD4,02004FD4)`. The trailing 84 bytes beyond the semantic profile are
copied into `[0000FFAC,00010000)`; the profile reader/checksum ignores them.
They are **not new score/name fields or available insertion space**. Tests
compare the full native 8,192-byte sector image as well as the 8,108-byte
semantic profile and preserve all earlier Adventure Log sectors.

The results component is accepted by [the complete native/ledger report](../build/completion/results/component-checkpoint.json):
1,794 English screens, 1,128 Japanese pixel pairs, 16 native record writes,
original FLASH persistence and both Adventure Log cold loads. Final combined
English SHA256 is `6db4a44bb2f06ff976cae82bedb18224c35b6bc8c302d2257169240a6cb2bbff`;
389,072 bytes of the appended region are used. Earlier allocations/patches
and original protected sources are verified unchanged.

### Church and save-service dialogue (continuous completion)

Before insertion, [church source owners](../build/completion/church/source-owners.json)
records 62 Japanese prose sources through 70 positional table words. The table
`[00C78B04,00C78CA8)` contains five types, each 84 bytes / 21 pointers. The
remaining 35 words reference internal identifier placeholders; their bytes and
IDs are preserved. Sources occupy the envelope `[00C78CA8,00C7A2E4)`, including
those identifiers and padding; only exact source spans in the report are text
owners, and none of this occupied envelope becomes free space.

[Native readers](../build/completion/church/research/readers.txt)
`080787F4`, `080788C8`, `08078A60`, and `08078BC4` calculate
`00C78B04 + type*84 + slot*4` and pass selected prose to the existing paged
service engine (`0807ADA4`, via wrappers where applicable). Types 0, 1 and 4
have priest dialogue; types 2 and 3 skip the greeting/menu path and enter the
save flow. Slot 1 is an internal menu identifier, not a displayed choice label.
The existing four-choice menu at `00C40260` is already owned by arena services.
The selected type uses existing RAM `[020091C0,020091C4)`; it is not a new
reservation. Level checks fill the existing 30-byte `$m0` slot and numeric
`$d0` slot, with separate Rosa/Ines follow-up paths.

New prose will be allocated through the combined allocator after adventure
results. No new code, table shape, RAM, save fields or menu return values are
required. Fixtures restore the saved village state and use the existing guarded
formatter buffer, paged-engine scratch/callback and native stack documented for
ally services. Controlled source selection and complete pages do not establish
natural church reachability or the consequences of accepting a save prompt.

Church [component acceptance](../build/completion/church/component-checkpoint.json)
now passes: 124 English cases / 162 complete pages and 86 Japanese pixel pairs,
with all 105 table words and 14 native source selections per variant. The exact
combined English SHA256 is `0ecfdac89e15a543194587cf10e18fc3ebde2f0d30cec23b92f66fe72cee124c`.
Original sources, previous patches and earlier appended data remain unchanged.

### Remaining frontend mode/save text (continuous completion)

Before insertion, [frontend owners](../build/completion/frontend/source-owners.json)
records 48 sources through 48 reviewed words. The exact source spans and Thumb
literal loads are authoritative; their wider envelopes `[00C78298,00C78B04)`
and `[00C7A2E4,00C7ACB0)` include prior owners, unreferenced text and padding.
No part of these envelopes is free space. Extra exact sources in `00C4CDxx` /
`00C4CExx` / `00C4CFxx` are enumerated in the same report.

Typed menu owners are the two text words in `[00C4CD0C,00C4CD30)` (two
12-byte yes/no records plus zero record), the Barinabo label at `00C4CD58`
within the existing five-choice mode table `[00C4CD40,00C4CD88)`, and words
`00C7828C` / `00C78294` in the six-pointer title table
`[00C78280,00C78298)`. Mode table attribute `02002FE4` and all return values,
default markers, other labels and terminating records remain intact. Earlier
name confirmation word `00085950` and compact default word `00085904` remain
owned by name entry; those already translated sources require inventory
reconciliation, not another insertion.

The high data-array candidates `00CE2304`, `00CE2320`, `00CE233C` and
`00CE2364` are still unreviewed. They occur among descending four-byte interior
addresses, not an established independent service reader. They are excluded
from insertion; no unreferenced source is promoted by that pattern alone.

[Frontend readers](../build/completion/frontend/research/readers.txt) identify
`080853E0` as the Adventure Log selector. Its summary records have a 92-byte
stride: compact name at +0, flags +8, signed 16-bit current/max HP +0C/+0E,
signed 16-bit adventure count +10, level byte +14, suspension byte +15 and
mode byte +16. The name/context header also reads a string starting +17.
The transient stack after its prologue contains the joined 200-byte row
`[sp+4C,sp+114)`, decoded name `[sp+114,sp+128)` (20 bytes), trip suffix
`[sp+128,sp+13C)` (20 bytes), record-base pointer at +148 and previous selected
row at +14C; the allocated frame is 150 hex bytes. The translated `%d` trip
suffix and HP/level printf preserve argument order/types. Native layout must be
checked in the actual summary window before acceptance.

Planned controlled summary fixtures may reuse `[0203F000,0203F0B8)` for two
92-byte records, with the existing native-call stack at `03007A00`; this is a
separate lifetime from earlier fake actors and not a game RAM reservation.
Paged messages use the previously documented service/formatter fixtures.
All new prose is appended through the shared allocator after church services.

The frontend summary fixture's guards extend its scratch range to
`[0203EFF8,0203F0C0)` around the two `[0203F000,0203F0B8)` records. Entry SP
`03007C00` becomes `03007A90` after the native selector's pushes and 150-hex-byte
frame. The native default window group gives summary window 2 a 208x40 area
at screen `(16,112)`; its HP line begins at local `(16,12)`. Both signed-field
extremes and actual 1,023-HP / level-99 fixtures fit without a window patch.
The selector uses existing status words `[020105E0,020105E8)`; fixtures set them
to valid and restore the state for each case. Typed-mode fixtures use the
existing unlock flag `[02002FE4,02002FE8)`, with original reader selection and
return values. No permanent RAM or save change is made.

The full mode-help wrapper `080853BC` calls the same paged service engine
`0807ADA4`; [window/wrapper disassembly](../build/completion/frontend/research/windows.txt)
confirms complete native page verification applies to these long help strings.

Frontend [component acceptance](../build/completion/frontend/component-checkpoint.json)
passes 157 English screens, 86 Japanese pixel pairs, both seven-character
Adventure Log cold loads, and complete reconstruction from allocation/patch
ledgers. Combined English SHA256:
`2d2bd38acc79fa6d7f2752ad1b89415967ec07dcd5941bc632a06b3e65fd805c`.
Appended usage is 397,958 bytes; no window, code, RAM or save change was needed.

[Code-owned text reconciliation](../translations/code-owned-text.json) links six
existing checked pointer replacements to inventory entries, without granting a
second owner or changing any bytes. Exact words `0006CD18`, `000732C8`,
`0007BED0`, `0007BED4`, `0007BEEC`, `00085950` and their allocation IDs/payloads
are verified against the accepted frontend image. This is accounting for earlier
authored work; source ranges retain their original owners and protections.

### Remaining composed item names (continuous completion, research)

[Item display readers](../build/completion/item-display/research/readers.txt)
identify `08080A5C` as the existing bounded 100-byte item-name formatter
(already exercised by the original item/context milestones). Its 14 category
labels use initialized ROM pointers `[00CB0684,00CB06BC)` copied to
`[020007FC,02000834)` by the existing startup copy. The labels' exact sources
start at `00C4C820` through `00C4C854` in reverse table order; these are occupied
source bytes. The category prefix is used for named unidentified items, not
an inferred new item identity. The other pending text resources are hidden-name
`00C4C858`, quantity formats `00C4C87C`, `00C4C884`, `00C4C88C`, monster-tracks
`00C4C8A4`, and grave format `00C4C8B4`. Pointer words and full source spans must
be enumerated before their insertion.

Existing numeric/enhancement/charge/price formats in this block have Latin
printf tokens and binary controls; successful decoding alone does not require
replacing them. `00C4C800` / `00C4C810` place price text at absolute window-local
x=130 using `03 09 82`; both have multiple readers. Their language and original
control bytes remain unchanged pending the complete composition/layout check.

Planned item-format fixtures reuse original 24-byte item records
`[0203F000,0203F018)`, option halfword `[0203F100,0203F102)`, and the existing
100-byte guarded output `[0203F200,0203F264)` with eight-byte guards on each
side. These scratch lifetimes are separate from previous fake actors and
frontend summary records. `08080A5C` uses a 280-hex-byte local frame plus
32 pushed bytes; fifth argument is at native post-prologue `sp+2A0`. Native
formatter arguments/flags and the existing stack/copy limits stay unchanged.
Cold startup must verify the category table's initialized RAM copy; a restored
older village state contains the old pointers, so any controlled fixture
refresh of that table must be explicit and distinct from cold-start evidence.

The [item-display source report](../build/completion/item-display/source-owners.json)
now enumerates all 20 sources and 21 pointer words before insertion. Category
labels retain their original category indices; quantity formats retain the
native `%d,%s` argument order, and the grave format retains its one actor-name
`%s` argument. Existing item names, unknown-name dictionaries and price/style
controls keep their existing owners. New text is appended through the shared
allocator after the accepted frontend component. No code or RAM patch is
planned for this initial translation candidate.

The preliminary 370-item [native composition survey](../build/completion/item-display/research/composition-probe/probe.json)
passes on English candidate
`1e9540ec1448916fa6c23e07307f24bc9f8e5191f8a983714860cf2d9d52294e`.
It verifies cold category-table initialization, existing 100-byte output guards,
full native glyph/ink bounds and no advance crossing the x=130 price column.
These selected field fixtures do not yet establish complete component coverage.

The formal controlled fixtures also use original hidden-name halfword
`[02006188,0200618A)`. The formatter tests it together with byte +13 hex in
the original 28-byte item-property rows at `000E07F4`; its exact gameplay status
meaning is not established. Item 349's +10-hex halfword selects the existing
200-entry actor-name table at `00192568` for its grave format. Item 348 tests
the original context word `[02000000,02000004)` via `0800033C` and, when it is
one, reads the root pointer `[0200000C,02000010)` plus 4C hex. The matching and
different-actor fixtures temporarily point that root at `02010A90` and populate
only `[02010ADC,02010ADE)`; they snapshot and restore both global words and
that occupied heap field before UI/frame processing. This is not free heap or
a new game reservation.

Unknown-name fixtures use the previously owned dictionary fields at
`0200C71C` and `0200C722+2*item`, and existing eight-byte custom-name slots at
`0200CA06+slot*8`, where the signed slot index comes from `00C4C4FC+2*item`.
The seven-W custom-name cases are direct width fixtures in those slots; they
do not establish the input limit of the item-name editor. Each case restores
the original state before installing its isolated item/context fixture.

[Item-display component acceptance](../build/completion/item-display/component-checkpoint.json)
passes 1,197 native combinations, 20 resource previews and 1,217 Japanese pixel
pairs. Both complete images reconstruct from the shared ledgers; every prior
patch and appended byte is preserved. English SHA256
`1e9540ec1448916fa6c23e07307f24bc9f8e5191f8a983714860cf2d9d52294e`,
with 398,144 appended bytes used. No window, code, RAM or save patch was needed.

### Direct dungeon events (continuous completion, research)

[Dungeon-event source ownership](../build/completion/dungeon-events/source-owners.json)
enumerates 63 sources / 82 pointer words in the occupied source envelope
`[000A3FC4,000A607C)`. Exact source ends in the report take precedence over this
selection envelope. The arena pause menu is `[000A3FA0,000A3FC4)`, two 12-byte
records and a zero terminator. Its nonpointer fields/default marker retain
their native meaning. Two abort prompts occupy initialized pointer words
`[00CAFEB0,00CAFEB8)`, copied by the original startup image to
`[02000028,02000030)`. Reader `080084D0` selects these by protagonist; the
following internal identifier at `00CAFEB8` is not a third translated prompt.

The companion/tutorial dictionary `[000A536C,000A546C)` has 31 eight-byte
key/value records and a zero terminator. Reader `080092E4` builds an identifier
in its original 64-byte local buffer and calls `0807DC98(key, table)` at
`08009472`, followed by `0807ACFC` for the returned text. Keys and their
formatters remain internal resources. [Reader evidence](../build/completion/dungeon-events/research/tutorial-reader.txt)
establishes value-only insertion; four shared warnings have multiple keys.

The [direct event readers](../build/completion/dungeon-events/research/readers.txt)
and [wrappers](../build/completion/dungeon-events/research/wrappers.txt) establish
boss dialogue through `0807ACFC`, rescued-villager dialogue through `08009160`
and choices through `08009170`. Those wrappers all enter the existing paged
engine `0807ADA4`; choice/default parameters and scene logic are unchanged.
High data-array references remain excluded until independently understood.
New prose will append after item-display through the shared allocator.

Planned controlled checks reuse existing service fixtures: substitution slots,
guarded output at `0203F200`, callback scratch `[0203F100,0203F102)` and native
stack at `03007E00`. Tutorial lookup fixtures may put a key of at most 63
characters plus NUL in `[0203F000,0203F040)`, separate from earlier fake item
records. Cold startup will verify the two abort pointers; restored state cases
must explicitly refresh that cache. No permanent RAM or save change is planned.

The isolated boss-text selector slice `[08008616,08008690)` reads protagonist
byte `[02004FF4,02004FF5)` and first/repeat encounter bits 0/1 in
`[02005EE0,02005EE1)`. Four controlled combinations establish both possible
text pointers without entering the actor/animation setup. Arena-abort selection
slice `[08008534,0800853E)` reads `[02009264,02009265)` and indexes the existing
two-word cache; these fixtures set indices 0/1 and r7 to `02000028`. State is
restored between cases. These are original fields, not new reservations or
proof of natural scene reachability.

[Dungeon-event acceptance](../build/completion/dungeon-events/component-checkpoint.json)
passes 126 English source cases / 185 screens and 116 Japanese pixel pairs,
with all 31 tutorial key lookups, four boss/two abort selector cases and the
native arena pause menu. All prior writes are preserved and both complete
images reconstruct from ledgers. English SHA256
`8c082e005b119c5385c80f2a814adbb505e4eae5e866fe76e7ecff791d019160`,
with 404,842 appended bytes used. No code, RAM or save patch was needed.

### Remaining battle, shop and companion-action messages (research)

[Battle source ownership](../build/completion/battle/source-owners.json)
enumerates 298 sources / 382 pointers, including the separate Rosa message at
`001B4FF0` and selected sources in `[001B7DC6,001B9DF1)`. The 12 growth-type/
character labels `[001B98D6,001B997C)` belong to a separate reader and are
excluded. Two unreferenced prose leads (`001B8A4A`, `001B93ED`) remain in the
discovery queue. Exact source ends and pointer fields in the report are the
insertion authority; no whole envelope or former source storage is free.

The [native readers](../build/completion/battle/research/readers.txt) and
[dialogue readers](../build/completion/battle/research/dialogue-readers.txt)
distinguish 247 scrolling feedback sources from 51 paged shop, companion and
recruitment prompts. Rosa's quoted complaint at `001B4FF0` enters `0805D3D4`,
so quotation marks alone do not establish a paged dialogue reader. Recruitment
confirmation uses the paged engine, while successful joining/departure messages
enter the queue. Native queue/history and page limits retain their earlier
documented fields and capacities.

Additional occupied pointer tables are `[000DB0FC,000DB108)` (three blocked
healing messages), `[0009B660,0009B66C)` (three blocked revival messages),
`[000DB15C,000DB16C)` (four wind stages), and `[000D95E0,000D9600)` (eight
shop charge/haggling choices, including duplicate sources). The first pair is
consumed by `08025174`; the wind table is selected at `0805A8BC–0805A8C2`.
Shop function `08044150` copies all eight pointers into its existing local
stack array, then indexes initial and haggled prompts. [Table-reader evidence](../build/completion/battle/research/table-readers.txt)
keeps those values separate from gameplay operations and counters.

Initialized pointers `[00CAFE98,00CAFEA4)` map to `[02000010,0200001C)`;
`[00CB0098,00CB00A4)` map to `[02000210,0200021C)`. These are slices of the
existing startup image, not new RAM. Cold startup and explicit cache refresh
after older state loads must be checked independently. Existing 36-byte ability
records continue beyond the earlier selected envelope: records at `000A7C44`
and `000A7C68` contain the new message words `000A7C4C` and `000A7C70`.
Only their text words are owned; callbacks and the following record stay intact.

Two Yggdrasil-leaf messages begin with original indexed glyph `F9 AC`, whose
font-0 descriptor has code `874A`, bitmap `[00C82760,00C827A8)`, nine-pixel
advance and eight-pixel ink extent. Unicode extraction displays it as `⑪`;
the [bitmap inspection](../build/completion/battle/research/glyph-f9ac.png)
shows that viewing label is not prose to translate. Keep its original indexed
bytes before the new English and include its two bytes/nine pixels in history
and layout bounds. No glyph asset is changed.

Planned battle fixtures reuse the documented guarded history at
`[0203E000,0203E500)`, original queue/formatter slots and existing scratch/stack.
New text will append after the accepted dungeon-event component through the
shared allocator. All original table shapes, callback words and prior owners
remain unchanged.

Battle table-selection fixtures may use the existing native-call stack at
`03007C00`. Wind selection reads its original local offset +198 hex at
`[03007D98,03007D9C)`; the isolated slice `0805A8BC–0805A8C4` receives offsets
0/4/8/12. Shop selection copies `[000D95E0,000D9600)` into transient
`[03007C00,03007C20)` at `08044196–080441A6`, then exercises both original
indexing slices `080441C0–080441C6` and `080441DE–080441E6`. These scratch
lifetimes are separate from earlier selector cases and are not RAM reservations.
Blocked recovery/revival fixtures execute only the original pointer loads at
`08025256`, `08025270` and `08025278`, with r6 set to each existing table.

Battle component acceptance: 298 sources / 382 pointer words pass 843 English
cases, 302 Japanese pixel pairs, both cold tables and 18 selector cases.
The [checkpoint](../build/completion/battle/component-checkpoint.json) verifies
full image reconstruction and all previous patches/appended bytes. Combined
append use is 415,386 bytes through exclusive offset `0106569A`.
English SHA256 `5591e461e494946a56464327842cf8ef4a691a716a2ae14932ed451c945d2f04`.
No original source pool is released for reuse.

## World merchants (2026-09-11, in progress)

Owner `merchants`; original source and research are pinned under
`build/completion/merchants/`. These findings precede insertion and disposable
runtime fixtures. All ends are exclusive; surrounding bytes stay occupied.

The merchant table `[0086FB34,00870760)` contains 19 records of A4 hex bytes.
Reader `0806309C` selects index × A4 from literal `08063160`. Each record has
an identifier at +0, twenty text pointers in `[+4,+54)`, and ten eight-byte
stock rows in `[+54,+A4)`. Record IDs are 3B through 4C with a second 4C row;
they are not nineteen unique consecutive IDs. The final record starts at
`008706BC` and is used directly by Medal King reader `08063884`. Only the
reviewed text words may change; identifiers, stock and table dimensions stay.

Player-shop records `[0087185C,008718DC)` are two 40-hex-byte records. The
first word is 50,000 / 5,000 gold, followed by 0100 / 0140 (purpose not yet
established), then fourteen text pointers in `[+8,+40)`. Native `08063B2C`
loads the table at `08063B4A` and adds 40 hex only when flag 0F equals 2.
The inventory's apparent `Pて` string at `0087185C` is the integer 50,000,
not prose. Its literal `00063B94` must not be redirected as a text pointer.

Menu `[0087231C,0087234C)` contains three twelve-byte Buy/Sell/Cancel records
and the zero terminator. Sources in `[00870760,00872ABC)` are a discovery
envelope, not contiguous patch ownership. Exact source spans, literal loads,
and typed text words will be recorded in `source-owners.json` before a build.

[Native readers](../build/completion/merchants/research/readers.txt) cover
ordinary shops, blacksmith `08063404`, synthesis `08063624`, Medal King and
player shops. They format printf templates with `08096744` before calling
world wrappers `080622D4` (mode 0142) or `08062294` (mode 0042 for receipts /
observations). These wrappers call `08061680` with the existing UI-root+50
story structure and its documented 1,024-byte text buffer. They do not call
the dungeon `0807ADA4` message engine. [Wrapper evidence](../build/completion/merchants/research/world-wrappers.txt)
records the source and mode setup and the waiting function `08062250`.

Ordinary shop local frame is 2E0 hex bytes below the saved registers; a
256-byte formatted string starts at sp+84, followed by a 100-byte item-name
buffer at sp+184. Blacksmith likewise has a 256-byte printf buffer and a
100-byte item name. Synthesis uses two 100-byte names and separate 256-byte
printf buffers; the two-name confirmation must stay within 256 including NUL.
Medal King and player-shop printf destinations are also 256-byte local arrays.
These are existing transient buffers, not permanent RAM reservations.

Disposable merchant checks may reuse the earlier fixture destination
`0203F200` with 1,024-byte capacity/8-byte guards, a separate 256-byte printf
buffer `[0203F800,0203F900)` with 8-byte guards, and two synthetic item-name
strings `[0203F000,0203F064)` / `[0203F080,0203F0E4)`. Each case restores the
world snapshot and uses the existing native-call stack. The original story
structure, actual table selectors and menu draw paths will be exercised;
fixture input advancement is distinct from natural shop transactions.

The world renderer is `08061760`. Its state +8 uses 6 for the three-line
continuation wait and 9 for the end-of-source wait; the read cursor is +40C.
Disposable page fixtures may execute this function directly, with an explicit
successful input return at `08061D3C` only when continuing state 6. Native
scroll/line setup still runs. For screenshot presentation, a temporary Thumb
self-loop at `[0203F100,0203F102)` holds the main thread while mGBA presents
two frames with IRQs enabled; the full previous CPU context is restored. This
avoids the unrelated saved event script replacing a multi-page test message.
The story cursor/payload must remain unchanged through presentation. These
are controlled rendering fixtures, not a claim of natural NPC interaction.

The [merchant owner report](../build/completion/merchants/source-owners.json)
now lists 132 exact sources and 453 pointer words. Source reconstruction and
all typed/literal owners pass; `[0087185C,00871860)` is explicitly excluded
as cash. The English catalog retains printf argument order, reserves 99 bytes
per item name / 11 per signed integer and bounds all printf results to 256
bytes including NUL. Subsequent world formatting remains within 1,024 bytes.

The initial IRQ-only presentation experiment did not submit window graphics
and is not used for acceptance. The tested page fixture instead snapshots the
complete core at each native pause, temporarily uses continuation-wait state 6
for two ordinary presentation frames, and restores that exact snapshot before
continuing. The source payload and cursor must remain unchanged even before
restoration. No injected spin code or held event-interpreter breakpoint is
needed. Renderer calls, line counters, continuation scrolling and glyphs remain
native; only the explicit continuation input return is controlled.

Merchant component acceptance: all 132 sources / 453 pointer words pass 282
English cases, 279 screens, 147 Japanese pixel pairs, 23 original record
selections and the three-row menu. The [checkpoint](../build/completion/merchants/component-checkpoint.json)
reconstructs both complete images and verifies all previous patches/appended
bytes. Combined append use is 423,557 bytes. English SHA256
`9d735a15224915e4436cc8e21b1ff426f598f72ab226c638e68cb2421d6e4904`.
No source pool, record metadata, font, code, RAM or save layout is changed.

## Remaining keyboard and inscription research (2026-09-11)

[Corrected readers](../build/completion/remaining-ui/research/keyboard-readers.txt)
establish keyboard entry `0807BB74`. Its r1 is codec type; r2 points to input;
r3 is the requested limit (clamped to 30). The sign of sixth argument selects
header pair: nonnegative allows History, negative hides it. Header index uses
this sign and page; grid index uses codec type and page. Therefore a shared
`abc/ABC` header is incorrect for the preserved type-one kana password grid.
The previous name patch also omitted the allowed History label. A common
`Page` button / `L: Page` hint and the correct conditional History label can
cover both codecs while leaving every compact mapping and grid unchanged.

Original headers `[00C45424,00C454E4)` are four positioned resources; table
`[00CB0620,00CB0630)` initializes RAM `[02000798,020007A8)`. The accepted
name component instead owns the literal `[0007BEE4,0007BEE8)` and points to
its appended header table. Literal `[0007BEEC,0007BEF0)` owns the shared hint
from source `00C46740`. Correcting those two literal patches requires explicit
whole-patch supersession with the original owner/ID and exact current bytes;
it must not weaken ordinary overlap checks or rewrite earlier appended assets.
The old patch record must remain in the final ledger's supersession history.

History row format `00C46748` is read through literal `0007CDD0` by actual
function `0807CD14`, with a 16-byte decoded-name buffer and 32-byte printf
buffer. The two-row Select/Erase popup source `00C46758` is read through
literal `0007CF18` by function `0807CDD8`. These literal addresses are not
function entries. Their adjacent windows, history records and selection results
retain the original layout; controlled fixtures must check both Latin and
legacy Japanese names.

The blank-scroll name dictionary `[000DFCC0,000DFF18)` contains 49 twelve-byte
records and a zero terminator: hiragana pointer, katakana pointer, item ID.
Item list `08070540` uses each ID and the original learned-item predicate
`0800111C`; `0807F130` performs two-byte comparisons against the two aliases
when a blank scroll (item 198) is read. A Latin keyboard alone does not make
that matcher support English. This is a confirmed remaining compatibility task;
no dictionary, matching code or name/save capacity is changed yet.

The [keyboard completion owner report](../build/completion/keyboard/source-owners.json)
lists all six reviewed resources and exact original spans. New insertion owns
only popup literal `[0007CF18,0007CF1C)`, and supersedes the two name-component
literals above as whole four-byte patches. `RomBuild.supersede_patch` requires
the previous owner/ID, exact current bytes, original bytes and unchanged size;
its nested `supersedes` record preserves the old owner and replacement. All
normal overlap checks remain strict. Nine ledger tests pass, including the
historic name-build hash, atomic rejection of stale/partial/wrong-owner
supersession, and ordinary overlap rejection after a supersession.

The component's Japanese control keeps the previously accepted English
headers/hint and relocates the unchanged Japanese popup. Its pixel comparison
therefore covers preservation of the earlier keyboard and popup relocation;
corrected header wording is established by English native checks, not by
claiming those corrected headers match Japanese pixels.

Blank-scroll caller `0807009C` passes a seven-position limit at `08070120`,
commits eight bytes into item record `[+4,+C)`, terminates +B, then calls the
matcher at `08070146`. Long English inscriptions cannot be assumed to fit
this field. Original learned-scroll selection is a separate path; the alias
and matcher work remains pending and will retain the full item glossary names.

Keyboard-only disposable fixtures reuse a zero-terminated 32-byte input at
`[0203F300,0203F320)` and a temporary Thumb `BX LR` frame callback at
`[0203F100,0203F102)`. Native keyboard entry receives that callback as its
fifth argument; it is not a persistent code/RAM allocation. The original
32-byte editor buffer `[02009DF8,02009E18)`, page word `02009DE8`, cursor word
`02009DF0` and selection word `02009DF4` retain their documented meanings.

The preserved type-one hiragana grid has 13 overlapping ink pixels between
adjacent rows when drawn with font 0. The first controlled fixture confirms
75 glyphs on ten-pixel row spacing. The original font-1 grid draws ten bitmap
rows; restoring font 1 only for that grid avoids altering the chosen English
font or password alphabet. Type-zero grids continue using font 0, and headers /
hints must stay font 0 for intact English descenders.

Keyboard completion will own two new eight-byte instruction patches:
`[0007BE08,0007BE10)` and `[0007BE30,0007BE38)`, both previously unowned.
The first selects font from existing codec-type stack word `[sp+90,sp+94)`
(hex) immediately before the grid; the second restores font 0 immediately
after it. Appended Thumb trampolines replay the replaced instructions and
resume at `0807BE10` / `0807BE38`. Their transient eight-byte pushes adjust
the type load to sp+98 and stay within the existing call stack. All other
register values needed by the continuation and the original stack arguments
must be preserved. Code and pointers allocate through the same shared ledger.
These hooks apply only to the English candidate; the control retains the
previous keyboard. Native grid ink tests and original-font comparison remain
required before acceptance.

Keyboard history fixtures may populate the first eight existing eight-byte
records `[02009E80,02009EC0)` and set the native count word
`[0200A1A8,0200A1AC)` to eight. The array/count locations come from literals
`0007CDCC` / `0007CDC8`; this fixture does not assert total array capacity.
The native history reader receives rows 0..7 and codec 0 or 1. Its actual
16-byte decode / 32-byte printf stack buffers are retained. Isolated capacity
checks may reuse `[0203F400,0203F410)` and `[0203F500,0203F520)` with eight-byte
guards on each side. All these writes are disposable emulator fixtures.

Keyboard completion accepted: six resources, two exact pointer supersessions,
one popup pointer, and two eight-byte font hooks. All eight native layouts,
16 history rows, 16 guarded decode/printf pairs, four original kana grid
comparisons, four real joypad regressions and 11 control pixel pairs pass.
[Checkpoint](../build/completion/keyboard/component-checkpoint.json) reconstructs
complete ROMs and checks the preserved supersession history and earlier assets.
Combined appended use: 423,848 bytes. English SHA256
`8a6eb7fed361493b10383d792bd7a64e4fe4964a410f21c6551cc5aa8d3c178d`.

The history window constructed by `0807D02C(1,0)` has nominal 128×112 pixels
at (48,24), while its native row renderer uses buffer y coordinates
16+14×row. The eighth row passes the descriptor's nominal height; original,
control and candidate preserve all eight rendered rows and the same pixels.
This is recorded as native buffer/viewport behavior, not evidence of a new
allocation or grounds for enlarging the window. Guarded decode/printf checks
and horizontal ink checks apply to all rows. Keyboard hints / popup use actual
ink bounds, since their last blank bitmap row can extend beyond the window.

### Blank-scroll English inscription compatibility

The corrected reader investigation establishes that `08070798` displays the
first alias from each record in `[000DFCC0,000DFF18)`, rather than a full item
name. It reads the table through literal `[000707E0,000707E4)`, formatting
into its existing 32-byte stack buffer. Its `%2d` / positioned `%s` format
at `00C3DB6C` is already language-neutral. The learned-list constructor
`08070540` retains the original dictionary and `0800111C` learned predicate;
selection commits the selected ID at `0807066C..08070682` through the original
flags/accounting path. Thus a parallel table can display seven-letter English
inscriptions while full item names elsewhere retain the glossary wording.

The 49 records reference 98 kana resources within `[000DFF18,000E03A0)`.
Their exact spans will be frozen in the inscription source-owner report.
All original dictionary records and kana bytes remain protected. New English
aliases use at most seven Latin alphanumeric characters, with unique
case-insensitive spellings. Their parallel twelve-byte records, strings and
matcher code allocate through the shared ledger. Only literal `000707E0`
redirects the learned-list display to the parallel table.

A new eight-byte hook owns `[0007F170,0007F178)` after the original matcher
has performed its eligibility/accounting checks and decoded the compact name
into its 64-byte stack buffer. An appended routine first checks English aliases
case-insensitively and confirms the original learned predicate. A match resumes
the existing success path at `0807F216` with r7 pointing to its parallel record.
Otherwise it replays the replaced dictionary-load/test and resumes `0807F178`
or the original empty-table failure at `0807F240`. The original Japanese matcher
and both original dictionary literals `0007F22C` / `0007F260` remain intact.
The routine uses a transient 28-byte register-save frame, no new persistent RAM.

Learned flags read by `0800111C` occupy `[02002549,02002551)` for item IDs
190..246, derived from literals `00001154` (`020014C0`) plus `00001158`
(`1089`). Disposable inscription fixtures may vary these eight bytes and reuse
the existing 24-byte item record at `[0200A480,0200A498)`, compact input
`[0203F300,0203F320)`, and guarded 64-byte decoded-name scratch at
`[0203F400,0203F440)`. A synthetic learned-list ID array may use
`[0203F600,0203F662)` (49 halfwords) with external guards. These are fixture
writes, not save-layout changes or new reservations.

Inscription fixtures may also reuse `[0203F000,0203F064)` as a terminated
Japanese source string for the native compact encoder `0807D29C`. This allows
both kana variants and mixed kana spellings to pass through the original
encoder rather than inventing compact IDs. English test input uses the already
verified Latin compact mapping. Native learned-list constructor evidence is
`08070540..080705C2`; UI selection remains separate from formatting checks.

The original learned-list constructor's 370-halfword temporary ID array is
`[sp+4,sp+2E8)` after its 32-byte register-save and 768-byte local frame.
At the isolated fixture SP `03007E00`, that is `[03007AE4,03007DC8)`.
Checking the array after `080705A6` proves learned filtering without changing
its size. Real joypad inscription fixtures may redirect the existing inventory
callback at `0806DCDC` into complete original caller `0807009C`, passing the
original callback and existing item record; `0807014A` observes the native
matcher result before the original post-edit UI handling. No synthetic stack
buffer is substituted for the original seven-position editor in that route.

Inscription component accepted: 98 original kana sources / 49 item identities,
549 English matcher cases, 255 legacy regressions, 294 English/Japanese result
comparisons, 51 native learned-list selections and 49 displayed rows. Seven
control screenshots match; four real joypad cases run the complete original
item-name caller and commit the existing eight-byte field. The
[checkpoint](../build/completion/inscriptions/component-checkpoint.json)
reconstructs full images, preserves original dictionary/kana bytes and all
previous patches/allocations. Combined append use: 425,356 bytes.
English SHA256 `577f519029f96c714ba1f1a53c68bdee0007d15e9bd67ca65f88217e455848f1`.
No permanent RAM or save expansion was required. Exact source spans are in the
[source owner report](../build/completion/inscriptions/source-owners.json).

### Retained name-filter data

The former candidate name-filter table is now reader-confirmed. Function
`0807D1A0` reads literal `[0007D1BC,0007D1C0)` pointing to 165 words at
`[00C45DE4,00C46078)`, followed by the zero word `[00C46078,00C4607C)`.
It normalizes the entered compact name through `0807D3C8`, converts each
original Japanese filter term through `0807D29C`, and compares compact bytes
with `080967CC`. This data is matching policy, not displayed dialogue.
The 165 source strings span `[00C4607C,00C4672F)`; exact spans/pointers are
recorded in `build/completion/retained-resources.json`. Preserve the original
strings and filter logic. Do not invent translations to mark these internal
resources as authored English. This classification does not claim a new
English-language filtering policy or modify an existing build.

### Remaining Zoom and world-item messages

Zoom's no-destination path `08076624` calls selector `080604A8`, removes the
first byte from its result, then passes the body to `0807AD68`. Prefix `*`
sets speech flag 1; prefix `-` sets flag 0. Those bytes are protocol markers,
not displayed punctuation. Selector literals `[000604CC,000604D0)`,
`[000604E0,000604E4)` and `[000604E8,000604EC)` reference three messages.
Its indexed cache pointer at `000604FC` targets `[02000400,0200042C)`,
initialized by eleven ROM words `[00CB0288,00CB02B4)`. The 13 distinct sources
span `[0086F0AC,0086F42A)`; the source-owner report will record exact ends.
The first cache entry duplicates the third literal target. Positive restriction
selectors 1..10 use subsequent cache entries; selector fixtures must preserve
the prefix/speech contract and prove the initialized cache, not only ROM words.

The four item/gold observations `[0086FAA4,0086FB34)` use literals `00062E74`,
`00062E78`, `00062E7C`, `00062E80`, and `00062F34`. Native `08062DD0` formats
found-item text into a 256-byte buffer, with a separate 100-byte item name,
then displays via world observation wrapper `08062294`. `08062CC0` handles
full money/full inventory/success messages, and `08062EA4` also consumes the
success message. These are text-owner discoveries, not authorization to change
item granting, stock, money caps or transaction flags.

Two warehouse messages are inline initialized strings, not pointer seeds:
source starts `00CB04E8` / `00CB057C` map to RAM `02000660` / `020006F4`.
Existing function `080738CC` loads those RAM addresses from four-byte literals
`0007394C` / `00073994` and calls `0807AD68` with speech flag 1. Redirecting
those two literals to appended text is sufficient; the original initialized
string storage stays occupied and unchanged. Do not expand an inline string
into the following startup fields. Exact strings and patches will be frozen
in the world-completion owner report before building.

The two remaining debug strings `00916BE4` / `00916C0C` are indexed through
cache words `[02000464,0200046C)`, initialized from `[00CB02EC,00CB02F4)`.
Leaf selector `08060F08` loads the cache base from `00060F14` and returns a
signed-halfword-indexed pointer. Its displayed consumer is still unreviewed;
those two debug resources are excluded from the current world insertion.

World completion accepted: 19 sources / 21 pointers, 40 English cases /
40 screens, 20 control pixel pairs, 13 native Zoom selectors/marker handoffs
and two inline warehouse readers. Actual paged wrapper `0807AD68` supplies
its `[0,1,speech]` extra arguments to the native page engine; word wrapping,
continuations and flags are checked. World observations retain their separate
256-byte printf / 1,024-byte formatter capacities. Original startup strings,
previous patches and appended bytes remain intact; the
[checkpoint](../build/completion/world-completion/component-checkpoint.json)
reconstructs both complete images. Combined appended use is 426,467
bytes. English SHA256
`d15009ca598199febd4b0468638c161ad63574281abccb43f887ddd08ce25a7f`.

### Remaining system-menu and status readers

The corrected [system-reader listing](../build/completion/remaining-ui/research/system-readers.txt)
uses actual entries `080027B0`, `0800398C`, `08003A40`, `08003CBC`,
`08005050`, `080050B0`, `0801B454`, `0801EA9C`, `0801FBCC`,
`08034A70`, `0803EF0C`, `0805C998`, `08060458`, `080604A8` and `08062DD0`.
Raw PUSH-like halfwords in pointer literals do not establish function entries.

`080027B0` populates an Adventure Log summary. Source `0009B4DC` is copied
with an explicit 23-byte length into summary +27 (hex) in the dungeon-menu
case. Any replacement for that particular fixed copy must include 23 allocated
bytes, including safe termination/padding. Source `0009B4F4` is a `%s` entry
summary, formatted into the existing 64-byte summary field `[+27,+67)`;
`0009B4FC` is the separate language-neutral dungeon/floor format. No summary
field or save record may be enlarged merely by relocating its string.

`0800398C` draws all six extra-mode menu rows from `[0009B504,0009B51C)`
through literal `00003A3C`, preserving the row selector array. Its nominal
window is 18 tiles (144 pixels) wide. `08003A40` draws four adventure-party
choices from literals `00003C40`, `00003C44`, `00003C48`, `00003C4C`; its
window specification starts at `0009B5B8`, and its height comes from the
existing row-count table `00C3D8C6`. Return codes come from five words at
`[0009B5A4,0009B5B8)` (0,1,2,3,-1), including Cancel. Labels do not authorize
changing those return values or either window table.

Retry selector `080050B0` returns source `0009B6C4` or `0009B6AC` through
literals `000050C0` / `000050CC`. Caller `08003CBC` passes the result to the
original confirmation reader `0807B1CC`. Its companion-selection UI references
source `0009B66C` and heading `0009B6A0` through `00004A38` / `00004A3C`.
Related dungeon-menu sources `000A6900`, `000A690C`, `000A6940`, `000A6948`
have distinct reviewed literals `0001F204`, `0001FF64`, `0001FF68`, `000200DC`;
high `CE` data references remain unreviewed and excluded.

Special monster-house name records have parallel bases `000AE574` and
`000C5E44`, each 20 records of 44 bytes. The base-pointer pair
`[000D9070,000D9078)` is indexed by the existing protagonist selector.
`08034A70` copies the selected name into a 30-byte destination and explicitly
terminates destination +29; the fallback name at `000D9078` is copied through
literal `00034B00` with the same bound. Only the first word of each 44-byte
record is a name pointer; other record fields remain occupied. Full names
must fit 29 encoded bytes unless that native buffer is deliberately redesigned.

The status-label table `[001B994C,001B997C)` contains 12 pointers: Torneko,
Tipper, Rosa, Ines and eight growth-type labels. Source `ポポ口` at `001B98DF`
is the original indexed-glyph rendering for the Tipper row, not a distinct
character identity. Reader `08072FBC` selects its label through literal
`00073348` at `080732F8..08073306`, formats through `0807D8CC`, then draws
at x=100,y=0 in window 0 at `08073312..0807331C`. The selector is read from
its original local stack word +458 (hex); isolated tests must provide a valid
original-sized stack context, not assume entry SP is the local SP.

Retained-key review also uses the already accepted typed dictionaries:
108 adventure-history pairs plus terminator at `[00C4D250,00C4D5B8)`, read
by `08087788`, and 31 tutorial pairs plus terminator at
`[000A536C,000A546C)`, read by `0807DC98`. Each eight-byte record has a key
pointer followed by a displayed-value pointer. Only values were translated;
keys and their source strings must remain unchanged. Prior component native
lookup checks establish those roles. The retained-resource report records
exact key spans and verifies their bytes/pointer words in the latest ROM.
Of these 139 distinct keys, 138 are master-inventory entries and one is outside
that inventory. Do not count any of them as newly authored English.

Object-label reader `0801B454` uses four pointers `[000A66F0,000A6700)`
for record type 4, through literal `0001B494`. Its fallback unknown-object
literal is `0001B4A8`. Both paths copy 30 bytes and terminate +29; the
original type/handle/index record remains unchanged.

Equipment detail source `001B446D` (`上限+%d`) is loaded via `0006DE40` and
drawn at x=144,y=3, leaving 64 pixels in the existing 208-pixel window.
The native argument is signed halfword +4 in 28-byte item records based at
`000E07F4` (literal `0006DE44`). All 75 rows with types 0..2 have values
0..99. That actual input bound controls this field's English width. It does
not justify reducing general printf capacity checks for unrelated readers.

Sources `001B4484` / `001B448D` belong to `0806E1C0`: two 64-byte temporary
printf buffers are concatenated into a caller-owned 1,024-byte destination.
The first counts visible equipment marks, subtracting mark bytes with bit 80;
the second formats the result of `0807EC14`. Existing glossary `Mark` is the
identity for 印; avoid introducing an unrelated Seal label. No mark-array or
item-record capacity is changed. Source `001B447E` is a special visibility
message for item 209 (Hocus Pocus scroll) and reaches `0806E2CC`; it is not
proof of a generic unidentified-stat label. Synthesis heading `00C3DA2C`,
read through `0006DD5C`, retains controls `03 12` and `03 05 04`.

System-label verification uses an isolated local stack at `03007800` for
the growth reader slice `080732F8..08073320`: output
`[0300780C,03007A0C)` (512 bytes), formatter context
`[03007A0C,03007C0C)` (512 bytes), selector word
`[03007C58,03007C5C)`. These are transient test fixtures, restored between
cases, not new game reservations. The equipment-cap slice uses the same
local SP with its 64-byte output at `[03007868,030078A8)`.
Adventure Log display reader `080853E0` reads the title at +17 (hex) in
each original 92-byte record, via `08085560..0808556C`, composing
`%s[%s] %s` with the player name. The title occupies `[+17,+57)` (64
bytes); the larger profile's source title remains at `[+27,+67)`.
The existing 184-byte two-record fixture at `0203F000` supplies these
fields without changing save structure. Whole composed lines need width
checks, not just isolated dungeon names.

The companion chooser copies config +20 through `08070B96..08070BA6`
into `[02008E38,02008E3D)` with a five-byte copy and forced terminator
at +4. Its adventure heading therefore has only four encoded bytes.
The candidate full word "Adventure" does not fit this native field. Its three
remaining occurrences use the established ally-service display "Trip", keeping
the full catalog wording and original draft. No buffer is enlarged.
Reader evidence: [additional system readers](../build/completion/remaining-ui/research/system-confirm-readers.txt).

Native preset 12 actually produces a 192-by-112-pixel window in these detail
fixtures. The equipment cap at x144 has 48 pixels, and growth text at x100
has 92 pixels; earlier provisional 208/64/108 measurements were too generous.
The builder now checks these observed smaller limits. Equipment statistics
use the same original window at x0,y100. All original 24-byte item records
in the fixture remain intact, including enhancement/mark fields.
The only discovered call to party chooser `08003A40` is `080038FE`, with
r0=6, so its actual window height is selected by row-count-table entry 6.
The four labels are still drawn as four rows. The earlier count-4 exploratory
fixture was not evidence of the real caller's geometry.
Dungeon-menu copies at `0801FF4A..0801FF54` place the error/context pointers
at local SP+28/+2C in a configuration beginning at SP+C; these remain
configuration +1C/+20. Suspend confirmation at `080200AC..080200B2`
uses wrapper `0807B208`, while retry uses `0807B1CC`.

The complete type-4 object-name selector table is `[000A66EC,000A6700)`:
index 0 points to the original empty string `000A671C`, and indices 1..4
select Fire pillar, Ice, Sand pillar and Wind pillar. The four nonempty
pointer words `[000A66F0,000A6700)` are owned by this component. The literal
`0001B494` points to the full five-entry base, not the first translated word.
The native test covers all five indices plus the unknown-object fallback;
the earlier index-0..3-only probe missed Wind pillar and is superseded.

System labels accepted: 42 protected sources / 42 pointer words, 549 English
native cases and 549 Japanese pixel pairs. Both complete images are reconstructed
from original ROM plus the cumulative allocation/patch ledger; all prior patches,
appended bytes and protected original sources remain intact. Combined appended
use is 427,239 bytes. English SHA256 `e57a95e98f74f5cbf4ea745b4f192096d38a05331ede5daf780b40b27d7ccdf1`.
Exact allocation/source spans: [build report](../build/completion/system-labels/english-build.json).
Acceptance: [checkpoint](../build/completion/system-labels/component-checkpoint.json).

### Themed houses and remaining companion commands

Planned encounter-UI component, based on the accepted system-label ROM.
The two 20-record house tables `[000AE574,000AE8E4)` and
`[000C5E44,000C61B4)` retain their 44-byte stride and all 40 bytes after
each first-word name pointer. Their 20 shared source strings occupy exact
parsed spans within `[000AE8E4,000AEA25)`; the fallback starts at `000D9078`.
Only the 40 first-word pointers and fallback literal `00034B00` are owned.
Initializer `08034A48` passes the existing dungeon structure's 30-byte
name field `[+1977A,+19798)`, followed by theme ID `[+19798,+1979A)` and
rank `[+1979A,+1979C)`, to `08034A70`. The structure base is read through
`0200000C`; offsets are hex and are not save-file addresses. No field expands.
Selector `08034B80..08034B9E` uses protagonist word `02004F8C` to select
one of the two bases at `000D9070`. All themes and both protagonists need
native bounded-copy coverage. The second caller `0803C1E4` passes a null
text destination; it does not establish another displayed-name buffer.

Companion menu tables are `[000D9340,000D9370)`, `[000D93C8,000D93F8)`,
`[000D9580,000D95B0)`, `[000D9638,000D9668)` (three 12-byte rows plus
zero terminator each), and `[000D9680,000D96BC)` (four rows plus terminator).
Only each row's first pointer word is text; availability pointers and return
codes remain unchanged. Sixteen words address 15 distinct strings because
Cancel at `000D9668` is shared. Sources occupy parsed spans in
`[000D9370,000D96D8)`, excluding intervening structures.
Original menu consumers: `0803EF0C` / literal `0003EF58`, `0803F7BC` /
`0003F818`, `08043BC4` / `00043C64`, and `08045088` / `00045250` and
`0004525C`. The spell menu's three availability bytes are the existing
`[02006B58,02006B5B)`; caller `080451FC..0804520C` derives them from the
entity's spell flags. Fixtures may cover all eight enabled combinations but
must retain the original availability-pointer and return-code words.

New text will use the cumulative append allocator. Original name pools,
zero terminators, record payloads and any excluded references stay occupied.

House-entry reader `080336F4` copies the dungeon name field through
`0803376E..0803377E` into the existing 30-byte `$m0` slot
`[0200A34C,0200A36A)`. It queues source `001B50C5` through literal
`000337C0` for mode 1; mode 2 uses the separate appearance narration
`001B50CD` via `000337C4`. Both narration sources already belong to the
tutorial-gameplay component and must not receive a second patch owner.
Encounter fixtures exercise the real 30-byte field-to-slot copy before
the already documented queue/history fixture changes its temporary base.
The source field's neighboring bytes and the other actor slots are preserved.

The early-world emulator snapshot has no active dungeon-structure base.
For the isolated house-field reader only, disposable controller scratch
`[0203F042,0203F060)` supplies the 30-byte source, with adjacent sentinels.
The pointer word at `0200000C` temporarily receives `0203F042-1977A`
(`020258C8`, aligned), so the native offset arithmetic reaches that field.
This models only that single accessed field, not an allocated full structure.
The pointer is restored immediately after `0803376E..08033780`; subsequent
formatting/queue calls never run against the synthetic base.

House narration correction: existing source `[001B50C5,001B50CC)` / pointer
`[000337C0,000337C4)` currently has tutorial owner
`tutorial.001b50c5.000337c0`, whose accepted replacement is `09012BFC`.
The encounter component explicitly supersedes that exact four-byte patch
in English, preserving its complete prior ledger record, to add the missing
indefinite article: "It's a $m0!". The 36 newly translated sources remain
distinct from this one previously authored correction. The original Japanese
bytes and previous allocated English stay occupied. The Japanese control
retains the accepted tutorial English narration, so its comparison isolates
the 36 newly relocated resources instead of reverting an older component.

Retained-result review confirms the 101 key/value pairs plus terminator in
`[000DB3B8,000DB6E8)`. Original result keys remain separate from translated
cause values. The accepted result component already exercises all 101 keys
for both protagonist contexts through the native result/list readers
(including `0800177C`); the retained audit now verifies key bytes and pointer
words in the accepted system-label ROM. These add 101 retained inventory
entries, not authored English or reusable ROM space.

Encounter UI accepted: 36 new sources plus one corrected announcement,
58 pointer words, 54 native cases and 54 Japanese pixel pairs. All previous
appended bytes and original sources remain intact; the only changed prior
patch is the explicitly superseded tutorial narration at `000337C0`.
Both complete images reconstruct from their ledgers. Combined appended use
is 427,696 bytes. English SHA256 `263c9ac4b2321967a30cafc7fdb59c078629969aa373e51109ce840b4d5dc878`.
Exact sources/allocations: [build report](../build/completion/encounter-ui/english-build.json).
Acceptance: [checkpoint](../build/completion/encounter-ui/component-checkpoint.json).

### Remaining arena outcome text

Three remaining sources are `[000DC870,000DC883)` (No winner),
`[000DC884,000DC89D)` (positioned winner/odds row) and
`[000DC8A0,000DC8A9)` (additional winners). Reader `0805C998` uses literals
`0005CB7C`, `0005CC8C` and `0005CB94`, respectively. These three four-byte
literal words are new owners; source bytes and the older arena/result owners
remain occupied. Original window preset 20 is constructed at `0805CB1E..28`.
The row formatter at `0805CC16..42` uses a 200-byte local buffer at SP+14
(hex), followed by draw x12 and rows spaced 13 pixels apart. It retains a
dynamic colour byte, No.%d, name position control `03 08 2C` and odds position
`03 08 A4`. No-winner text draws at x48,y56; the additional-winners label
draws at x160 after the eighth displayed winner. Name input is the original
30-byte actor slot `0200A34C`; odds come from `02009228`, already documented
with the generator's 9999-tenths upper bound. Only 倍 becomes `x` in the row.

Isolated arena-row fixtures may use local SP `03007B00` and its 200-byte
buffer `[03007B14,03007BDC)`, inside the existing disposable stack envelope.
Extra printf arguments occupy SP+0/+4/+8. Guards beside the buffer are for
the bounded instruction slice, not a changed live stack-frame layout.

Arena outcome text accepted: three sources and three literal pointer words,
205 native cases and 205 Japanese pixel pairs. Earlier patches, allocations
and original protected sources are unchanged; both ROMs reconstruct from
their ledgers. Combined appended use: 427,751 bytes.
English SHA256 `f71bc1e8151508385d92fd287ea8e16ed5206571b79892cc001a738a55720fdf`.
[Build report](../build/completion/arena-final/english-build.json),
[checkpoint](../build/completion/arena-final/component-checkpoint.json).

The heading at ROM `000DC838` is **not an ordinary text source**: native
`0805D070` reads one-byte indexes terminated by zero, then blits each selected
16×16 tile with 16-pixel advance. Literal `0005CB78` refers to this heading;
the graphic atlas base is loaded through `0005D0B0`. No insertion ownership
is granted yet. See [native reader](../build/completion/remaining-ui/research/arena-heading-reader.txt).

Further arena graphics reader evidence: ROM `[003C8CA0,003C9A20)` contains
the 27 addressed 16×16, 4-bpp cells (128 bytes each), based at literal
`[0005D0B0,0005D0B4)`. Index zero terminates a heading; nonzero index N
selects cell N−1. Six index sequences occupy `[000DC838,000DC843)`,
`[000DC843,000DC84B)`, `[000DC84B,000DC852)`, `[000DC852,000DC85B)`,
`[000DC85B,000DC864)` and `[000DC864,000DC86E)`; trailing bytes through
`000DC870` remain unowned. Source pointer words are respectively `0005CB78`,
`0005CF0C`, `0005CF4C`/`0005CF8C`, `0005CF90`, `0005CF50`, and `0005CF28`.
The only direct Thumb calls to `0805D070` are at `0005CB3E`, `0005CED8`,
`0005CF1E`, `0005CF36`, `0005CF40`, `0005CF5E`, and `0005CF68`.
This establishes occupied graphics resources, not free space. Exploratory
native renders use the already documented arena window/session fixtures;
no RAM or ROM patch is needed to inspect each source.

Arena graphics insertion plan (reader ownership confirmed): replace the seven
source pointer words above and the atlas-base word `0005D0B0` with appended
index sequences/atlas. Keep every sequence's original cell count and every
native caller position. English phrases are rasterized from pinned original
font 0 into the same 16-pixel-high strips and packed as four 8×8 GBA tiles per
cell. All new bytes use the combined allocator; original atlas/descriptors
stay protected. Japanese controls relocate byte-identical original assets.
No executable code, RAM reservation, save field or palette pointer changes.

The actual arena palette is ROM `[003C9CA0,003C9CE0)`, sixteen 32-bit RGB
values loaded by `0805CAFC..0805CB1C` (literal `0005CB74`) and
`0805CE96..0805CEB6` (literal `0005CF08`) into palette bank 14. The unused
gap after the addressed atlas cells is not insertion space. Graphics proof
must include this native palette setup, not a palette inherited from a world
save. Existing window 0 descriptor `[02034CD8,02034D18)` supplies buffer+14,
tile width+4 and height+6; blitter `0808C2D8` copies 8×8 tiles and sets bank 14
in the tilemap at `02034DDC`. These are original occupied engine structures.

Manual source transcription from the indexed graphics: `今回の勝利モンスター`
(winning monsters), `今回の対戦結果` (battle results), `ポポロの仲間`
(Tipper's allies), `<<<勝利>>>`, `<<<敗北>>>`, `<<<引分け>>>`.
The shared IDs 6/7 in both the first heading and victory establish that the
first heading refers to **winners**, not the combatant roster. These six
resources are outside the 9,318-entry ordinary-string inventory.

Graphics proof executes original palette/window initialization
`0805CAFC..0805CB38`, then the winner heading slice `0805CB38..0805CB52`;
team-result initialization/draw is `0805CEB8..0805CEEC` followed by
`0805CEEC..0805CF78`, stopping before the input wait. Team result selector
is the original transient local `SP+1C` with SP=`03007B00`; values 0/1/2
select draw/defeat/victory. The native result-status byte selected through
literals `0005CF2C`, `0005CF54`, `0005CF94` is preserved as a game write and
must equal 2/0/1, respectively. Fixtures restore the complete state each case.
Full allocated window tile-buffer comparisons check changes only inside the
requested 16×16 cells. No guard bytes are written into neighbouring data.
Actual arena preset 20 has a **208×136** visible/allocated bitmap (26×17
tiles), using original static RAM `[02035E1C,0203955C)`, 14,144 bytes. This
buffer is above the game heap, not allocated within it; descriptor+24 is
`3740` bytes and both +14/+18 point at `02035E1C`. The first exploratory
graphics proof rejected an incorrect heap-range assumption before drawing.
Existing font state beginning at `020398EC` remains outside this bitmap.
The native result-status byte is `[02000790,02000791)`.

Arena graphics accepted: six indexed phrases outside the ordinary inventory,
eight pointer words, five native displays and five Japanese control pixel
pairs. All original assets/palette and earlier patches/allocations remain
intact. Both complete images reconstruct from their ledgers; combined appended
use is 433,958 bytes. English SHA256 `a3f1088e83d01bf2692806e67fe80c5a842fd3eedb6d9d2f1beb86f97ee2e79d`.
[Build report](../build/completion/arena-graphics/english-build.json),
[checkpoint](../build/completion/arena-graphics/component-checkpoint.json).

### Remaining-resource classification: scene metadata investigation

Original scene pointer cache `[0200046C,02000604)` is initialized from ROM
`[00CB02F4,00CB048C)` (102 pointers); the next word `00CB048C` is zero.
Accessor `0806C5F0` indexes this table with a signed scene ID and uses the
36-byte fallback descriptor `[00916BC0,00916BE4)` for negative IDs. Each
scene descriptor is nine words; `08067022..0806702E` copies exactly 36 bytes.
Descriptor +14/+18/+1C/+20 refer respectively to actor groups, object groups,
trigger groups and map data. These are occupied resources, not text/free space.

Actor reader `080690FC` and object reader `0806B598` select an eight-byte
count/pointer group using an unsigned-byte group index, then walk 24-byte
records. Their record constructors read +8/+C/+10/+14 as four script roots
and register them with `08064454` in the controller's slots +10/+14/+18/+1C.
Controller activation is `0806452C`; command fetch `08064E42` reads two words,
advances the active cursor by eight bytes, then dispatches on the low byte.
Script root bytes often decode spuriously as `H`, `K`, `p`, etc.

The group count varies by scene; a preliminary uniform-27-group scan was
rejected after malformed records. A bounded structural scan now stops at the
first invalid count/pointer or script-pointer record and before other named
descriptor resources. It supplies candidates for native reader verification,
**not** a complete scene grammar, natural reachability claim or insertion
ownership. Reports retain exact scene/group/record ancestry. Reader listings:
[scene readers](../build/completion/remaining-ui/research/scene-readers.txt),
[record constructors](../build/completion/remaining-ui/research/scene-record-readers.txt),
[controller registration](../build/completion/remaining-ui/research/event-controller-readers.txt),
[command fetch](../build/completion/remaining-ui/research/event-dispatch-full.txt).

Native classification fixtures may reuse the already mapped 128-byte event
controller `[0203F000,0203F080)`, restoring the original world state between
cases. They must check the original scene cache, record-root selection,
registered slot and fetched command bytes, stopping at the dispatch boundary
before executing candidate event actions. No original program bytes change.

Controller activation needs a larger fixture than fetch-only tests:
`08064488` saves/clears a second 68-byte state at controller+64 (hex), through
controller+A8. The scene classification fixture therefore uses disposable
`[0203F000,0203F0A8)` plus eight-byte guards, still below the existing separate
script fixture at `0203F100`. The earlier 128-byte controller is sufficient
only for narrower fetch fixtures; it is not the full controller size.
Native activation writes the selected slot at +20, state 2 at +22 and script
pointers at +24/+28; fetch writes current-record pointer +34 and opcode +38.
The first audit attempt stopped on uninitialized cold-cache evidence before
activation. Subsequent proof must boot before checking that cache.

Scene command classification accepted for 205 master entries. Exact source
prefix spans, enclosing eight-byte commands and scene/group/record-pointer
ancestry are authoritative in
[native verification](../build/completion/scene-resource-audit/native-verification.json).
Each follows native group selection, record stride, script registration,
activation, fetch and dispatch with intact 168-byte controller guards.
No ROM bytes change, and no surrounding script space is released.

The retained-resource report also classifies original kana grid spans
`[00C454E8,00C4568E)`, `[00C45690,00C45822)`, `[00C45824,00C459B1)`,
`[00C459B4,00C45B41)` and compact-map spans `[00C467EC,00C4696B)`,
`[00C4696C,00C46AEB)`. Original bytes remain intact; type-zero's appended
map retains the original 191 entries. Existing native keyboard evidence
establishes their input-alphabet purpose. These spans include the ordinary
decoder's terminators; they are not released as insertion space.

Seventeen ASCII placeholders in the already mapped five-by-21 church table
are retained positional values; 35 pointer words select them. They are not
asserted to be lookup keys. Exact strings/words remain in
[retained resources](../build/completion/retained-resources.json).
Original opening command `[0091B688,0091B690)` accounts for one further
misdecoded prefix; the original natural trace fetched its exact bytes.
The previously mapped player-shop field `[0087185C,00871860)` is integer
50,000 rather than Japanese text. Accounting at that checkpoint was 635 master
entries plus one outside; 266 ordinary inventory entries remained open.

### Scene background graphics and tile-index resources

Scene descriptor+0 points at a 24-byte graphics header. Native `08066FE4`
reads header u16+0 as format `0202` or `0303`, u16+2 as the count of 8×8
tiles including synthetic blank tile zero, u16+6 as metatile count including
blank zero, pointer+C as stored 4-bpp tile bytes, and pointer+10 as metatile
u16 tile-index definitions. Stored tile span is `(count−1)*32` bytes;
metatile span is `(count−1)*4*2` or `(count−1)*9*2` bytes. The native loops
explicitly begin at tile/metatile index 1 and construct the blank entry.

Native tile copy `08067198..080671A6` copies sixteen halfwords per tile.
Metatile copy `0806725C..0806726E` copies four/nine halfwords, after native
format selection `080671CC..08067230`. Exact scene/header/asset ranges for
the 71 matching extraction candidates are indexed in
[graphics candidates](../build/completion/remaining-ui/research/scene-graphics-candidates.json).
These are occupied graphics assets. All 71 native-copy classifications pass;
no graphics bytes are patched or released.

The copy proof reuses mapped scratch `0203F200` with 36-byte descriptor,
32-byte tile or up-to-18-byte metatile buffers and eight-byte guards. Existing
stack fixture `03007800` holds a temporary original graphics-header pointer
for the native format selector. Original format state is changed only by its
native selector in disposable emulator fixtures; all adjacent fields must
remain unchanged. The complete save state is restored between candidates.
The format/tiles-per-metatile pair occupies `[02008CB8,02008CBC)`;
`00067180` and `00067324` both point at that original state. The format
selector also reads the existing destination pointer at `0300001C`, but the
bounded selector stops before any writes through that pointer.
The copy fixtures enter at `08067196` / `0806724E` so the native code
initializes its loop counter once. The first exploratory test put register
overrides at the loop head, which reset the counter repeatedly and was
rejected by the step limit; it supplied no classification evidence.

Accepted [native graphics proof](../build/completion/scene-graphics-audit/native-verification.json)
covers all 71 candidates. Eight additional candidates lie wholly within the
previously verified eight-byte event commands; exact containment is in the
retained-resource report. Current accounting is 714 retained master entries
plus one outside, with 187 ordinary inventory entries still open.

### Remaining auxiliary resources: native audit scope

The global event-program table has eight-byte records rooted at ROM `00929EE8`.
Native `08066EF4` indexes signed ID×8 and reads pointer field +4 through literal
`00066F18`, then activates an event controller with `08064488`. Selected words
`00929F44`, `0092A17C`, `0092A1EC`, `0092A2DC` point to command records
`[00917898,009178A0)`, `[009187C4,009187CC)`, `[00918BA4,00918BAC)`,
`[0091CE6C,0091CE74)`. This proves selected records only, not the table's full
extent. The audit redirects the native controller argument to the already
mapped guarded 168-byte temporary fixture before activation. No live global
controller or ROM program is changed.

Actor records `[009A8B1C,009A8B34)` and `[009EC564,009EC57C)` are selected by
scene 15/22 actor group zero, words `009A8FCC` / `009ECB04`. The first byte is
an actor type/ID used as a numeric selector by constructor `08069350`, read
at `08069368`. The audit stops at `0806936A`, before actor allocation/actions.

Numeric record `[0086F698,0086F6A8)` has 16-byte stride; `08062D94` reads its
first two signed halfwords and passes them to event-flag query `08000660`.
The four-byte records `[00872ABC,00872AC4)` have the same pair of numeric
fields, selected by `08063D5C` (query) / `08063D8C` (query/set). The audit stops
before the flag call and does not change flag state.

The suffix pointer table ROM `[00CB0640,00CB0668)` is initialized at RAM
`[020007B8,020007E0)`. Native `0807D28C` selects the ten original full-width
digit strings `[00C46C14,00C46C3B)` through that table. These are existing
nickname suffix assets; the earlier recruitment proof establishes their use.

Kana conversion `0807D2F8` searches the zero-terminated half-width lookup at
`00C46BDC`, then reads the matching two-byte full-width glyph from `00C46B6C`
(literals `0007D344`, `0007D348`, `0007D390`). The apparent larger string
starting `00C46AEC` includes a preceding resource and is not covered by this
reader alone. Conversion fixtures use existing scratch `0203F200` for output
and `0203F300` for input with eight-byte guards; no text asset changes.

Compact default-name records `[00C4CE97,00C4CEA3)` have two six-byte rows,
selected by protagonist byte `[02004F80,02004F81)` in `080858B4`. Native
`080858C4..080858D8` selects/copies the row into local stack+8 before calling
the compact-name editor; the apparent `Ey...` text is compact character IDs.
The audit temporarily uses the already mapped stack at `03007800`, guards a
six-byte copy at +8, and restores the complete emulator state between rows.

The compact-default audit must run its selector/copy on the Japanese ROM:
the accepted seven-letter name component intentionally redirects `00085904`
and clears the slot-dependent index at `000858CC` so both new Logs default
to Torneko. The original two compact rows remain protected source assets, not
the active English default. An initial audit expecting them through the changed
English pointer was rejected; this was a fixture assumption, not a ROM failure.

### Neutral formatting and original English diagnostics

[Reviewed source manifest](../build/completion/neutral-resource-audit/source-review.json)
indexes 64 exact original source spans, literal words, load instructions and
consumer listings. It includes six result-key printf templates, three heart
prefix templates, neutral menu/item/name formats, and original English debug
text. These sources/words remain occupied and unchanged; this review does not
allocate space or authorize text replacement. Native one-instruction probes
may confirm each literal resolution with CPU context restored and no RAM writes.
Static consumer review remains distinct from a full execution/display test.

Source bytes `83 C5` in templates `0009B408`, `000DC790`, `00C4D1A8` have CP932
viewing label eta, but the original font-zero descriptor at
`[00C94B9C,00C94BA8)` points to a heart bitmap `[00C822E0,00C82328)`.
Preserve that graphic marker. Conversely indexed `F8 A0` in candidate
`001B551C` really depicts a star: descriptor `[00C9414C,00C94158)`, bitmap
`[00C7E500,00C7E548)`. The phrase's unusual `★間` needs context review; it
must not be silently corrected to a guessed Japanese kanji.

The [auxiliary and neutral audit](AUXILIARY_RESOURCES.md) classifies another
22 typed numeric/input resources and 64 unchanged formats/original English
diagnostics. Current inventory: **8,417 authored + 800 retained + 101 open =
9,318**. No ROM allocation or source bytes change in this classification pass.

### Remaining sound-test help and dungeon-floor summary

The sound-test function `08090960` has four Japanese help pointers in startup
ROM `[00CB07EC,00CB07FC)`, copied to RAM `[02000964,02000974)`. In order they
select BGM, ME, SE and Return help sources at `00CAF2E0`, `00CAF2CC`, `00CAF2B8`,
`00CAF29C`. Exact string ends are recorded by `translations/remaining-display.json`
before insertion. Only those four pointer words may change; surrounding debug
labels, state and native menu remain intact. Similar high `CE...` arrays have
not been established as owners and are excluded.

Native selector `08090CC8..08090CD2` uses row `r7` and writes the selected text
cursor at help state+10. Original help state `[02039F90,02039FA4)` consists of
phase, selected row, X, Y and source cursor. Initialize via `08090CB4..08090CD2`;
per-character loop `08090CD8..08090D20` decodes at `08090CE2` and draws at
`08090D10`, updating cursor/X itself. A zero glyph ends the help. Temporary
stack `03007800` supplies its local glyph word at +2C. This is an existing
state machine exercised in restored emulator fixtures, not new RAM storage.

The live-dungeon log summary format `[0009B4FC,0009B503)` is selected through
literal `[000029F0,000029F4)` by `080027B0`. Native slice `080029C6..080029E2`
reads dungeon ID byte `[02004FF0,02004FF1)` through `0805F33C`, and floor byte
`[02004FF1,02004FF2)`, then formats into its existing 64-byte field at record+27
(hex). The English format is `%s %dF`; its full byte domain is floor 0..255.
No profile/record size changes. Proofs reuse guarded `0203F200` (64 bytes),
then the existing two-by-92-byte display fixture at `0203F000` and actual
`080853E0` Adventure Log renderer, with seven-letter names and both log slots.

The controlled native sound-test setup confirms that help preset 2 is a
208×40 panel at screen origin (16,112), using font 0 with zero extra spacing.
The character loop itself handles cursor advance and termination. Original
ASCII title/options use a separate tile-map renderer `0808CA0C` and remain
unchanged. The fixture retains the early-world background, so these checks do
not claim natural entry into the diagnostic menu or audio playback coverage.

Remaining display accepted: five source strings / five pointer words,
132 native English cases and 132 Japanese control pixel pairs. The cold sound
cache, glyph positions, live-floor formatter, log records and buffer guards
pass; previous source bytes, patches and appended assets remain unchanged.
Combined appended use is 434,053 bytes. English SHA256
`f0c51f1b3a4229964d23a2f0416bb854dafe1196799ce4ccea2302b211e7fb97`. [Build ledger](../build/completion/remaining-display/english-build.json)
and [checkpoint](../build/completion/remaining-display/component-checkpoint.json).

### High-ROM duplicate-image leads (unresolved)

The main startup copies IWRAM from ROM `[00CB0F44,00CB1B64)` to
`[03000000,03000C20)` through `08087980..08087992`, with source literal
`00087A14`. Apparent code at ROM `00CF0000` matches a 32-byte run at
`00CB1078` and `00CE2D18`. Candidate duplicate-image bases `00CE2BE4` and
`00CEFECC` are comparison leads only: the first differs in 67 bytes over the
C20-byte comparison, mostly relocated RAM/ROM literals; the second differs
more widely and its true start/extent are not established by that local match.
Neither high candidate base has a direct 32-bit ROM-address occurrence.

The earlier diagnostic text also has counterparts at `00CE0770..00CE0948`
and `00CEDA7C..00CEDC9C`, with different help-table words at `00CE248C` /
`00CEF7A0`. This resembles additional linked data images but does not prove
that they are unused. They remain protected, unclassified leads. No insertion,
free-space reuse, blanket duplicate translation or runtime reachability claim
is authorized by this comparison. Main code also accesses audio data above
`00D00000`; high address alone is not an unused-data criterion.

[Unowned language review](../translations/unowned-text-review.json) now indexes
31 exact Japanese source spans with preserved raw tokens: 30 English drafts
and one unresolved phrase. All have empty verified-pointer ownership. This
catalog is separate from builds and grants no source-byte patch or allocation;
its matching high-ROM duplicates remain protected regardless of apparent use.

### Final typed fields and original ASCII startup values

ROM `[00C3D8F0,00C3D910)` contains eight numeric values
`500,4000,2500,650,1500,8500,700,200`. Native `0806F34E..0806F35E`
selects an index from `0808DDC0(8)`, reads the selected word and supplies it
as an extra argument to item formatter `08080A5C`. Thus candidate `00C3D90C`
is the final integer 200. The bounded audit may select each valid index and
stop before the stack store; it does not change item state or translate numbers.

The previously mapped ally command table starts with integer command ID 100 at
`[00C3DB78,00C3DB7C)`. Native `08071294..080712B4` reads table selector
`[02000624,02000628)` and copies seven eight-byte command/label pairs to the
existing `[020090C0,020090F8)` buffer. The audit restores state, selects table
zero, compares all 56 bytes against the current ROM and checks adjacent bytes.
Relocated label-pointer fields retain their prior owners; the numeric ID does
not become a translation source or additional patch.

ROM `[00C454D4,00C454E8)` holds five signed X offsets `-2,46,86,130,170`.
Native `0807C07C..0807C086` selects a word and adds the window's X position.
Candidate `00C454E4` is the final coordinate 170, not a kana character.
Only read-only native indexing is needed for this classification.

Original ASCII startup label pointers `[00CB07A0,00CB07C8)` are copied to
`[02000918,02000940)`; identifier pointer `[00CAFEB8,00CAFEBC)` is copied to
`[02000030,02000034)`. Eleven corresponding source strings are explicitly
ASCII, including `arena_abort_ask2` and diagnostic category labels. Cold
startup establishes their initialized-pointer ownership. Their later readers
are unconfirmed: retain the original English/identifier content without
claiming visible diagnostic-menu or dictionary-lookup coverage.

A further [native field audit](../build/completion/remaining-field-audit/native-verification.json)
confirms three numeric fields and eleven original ASCII startup values. The
later consumers of those ASCII values remain unconfirmed. Current inventory:
**8,422 authored build-catalog sources + 814 retained + 82 open = 9,318**.
The separate 30 uninserted drafts remain part of the open technical queue.


### Cold-boot and title graphics (new coverage)

Original-ROM reader `0808508C` selects 16-byte records through literal
`0808519C → 08C77BBC`. The contiguous candidate record span is
`[00C77BBC,00C77C6C)`, eleven entries. Fields are tile/map pointer, 240-word
original RGB palette pointer, 32-byte tile count and two-map mode byte.
[Exact resource ranges](../build/completion/boot-graphics/research/resource-ranges.json)
pin all source bytes. These occupied resources are not available for reuse.

Natural cold boot selects records 1, 0, 9 and 2 at frames 8, 163, 317 and 471
respectively: Square Enix, Chunsoft, copyright and the Japanese title. Both
original and current English ROMs execute the same reads and exact copies;
[Japanese proof](../build/completion/boot-graphics/research/japanese/provenance.json),
[English proof](../build/completion/boot-graphics/research/english/provenance.json).
These probes supply no input, forced function entry or RAM writes.

Title record `[00C77BDC,00C77BEC)` owns maps `[00C5151C,00C5251C)`,
627 tiles `[00C5251C,00C5737C)` and palette `[00C5737C,00C5773C)`.
Two 32×32 halfword maps are copied by `08085138–08085160` into existing
heap allocations addressed by `020105D4` and `020105D8` (observed
`[02034290,02034A90)` and `[02033A90,02034290)` during boot). Native
`080851EE–08085212` copies the tiles into `[06008000,0600CE60)` VRAM.
The reader saves two prompt rows from map 0, offset `480`, in existing
`[0201054C,020105CC)`; `080877C8` alternately restores or clears those
rows to blink the original English start prompt. Those ranges are existing
engine state, not new permanent allocations.

The title logo contains Japanese lettering baked into tiles, outside the
9,318-entry ordinary text inventory. Mapping it does not establish that other
graphics have no text. No title insertion has been performed at this stage.


Further typed-resource reader discoveries: world-label records
`[00872E84,00872FEC)` are 30 twelve-byte records. Native `08066CC8`
reads each label pointer, while `08066CE0` copies its two signed coordinates.
Candidate `00872FE8` is the last Y coordinate (33), not punctuation.
The labels retain ownership in their existing translation component.

Scene 5 trigger group 27 is `[00946BE4,00946BEC)` (one record).
Native `0806C390` selects the 12-byte trigger `[00946B00,00946B0C)`,
whose +8 word selects the descriptor at `009461DC`. Constructor
`0806C520–0806C524` dereferences its +4 word (`009461E0 → 08946070`)
and stores the event-program pointer in the existing 28-byte runtime
trigger's +18 field. Its cached runtime-array pointer is `03000038`;
`0806C55C` reads the program pointer and the actor caller `0806A42E–0806A44C`
passes it to `08069A70`. This establishes a different indirection from the
actor/object script-root tables; the descriptor prefix is not itself being
classified as opcode 07. Candidate `00946070` starts command bytes
`5a00010003000000`. Bounded native verification remains required before
retained-resource promotion.

The next controlled field checks reuse previously documented scratch
`0203F200` for an eight-byte coordinate pair or a guarded 28-byte trigger,
with eight-byte guards. A temporary fixture redirect of existing
`[03000038,0300003C)` may point only at that one trigger for index-zero
getter checks, with surrounding bytes verified and the fixture reset
between cases. This is not a new runtime or save reservation.

The two further typed-resource checks now pass in the remaining-field audit:
all thirty world-coordinate pairs and the complete trigger selection,
constructor/getter, supplied-controller activation and command fetch chain.
The original source bytes and surrounding fixture guards are intact.
The user has explicitly chosen to preserve the Japanese title artwork. It is
intentional retained art; no title allocation, patch or redraw is authorized
as necessary work under the current translation plan.

Short-label rescan: `[00ADCE8C,00ADCE8F)` and `[00ADDEA0,00ADDEA3)`
match the font-zero bytes for “Yes”, but both lie inside the already mapped
scene-60 metatile array `[00ADA080,00ADE07C)` (header `00AE045C`).
This is static containment in an existing indexed asset, not a newly found
prose reader. No additional graphics work or insertion is performed.
[Rescan parameters and leads](../build/completion/remaining-ui/research/short-label-rescan.json).

The natural cave replay observes existing queue renderer call `0805D55C`
and scroll completion `0805D63C`, without redirecting execution. The former
passes an existing 80-byte queue row to `0808CB84`; the latter follows the
native six/twelve-callback scrolling loops. These observations distinguish
the documented temporary y38 staging row from a static text overflow in the
208×40 viewport. There is no new ROM, RAM or save reservation.

Continuation candidate `[00B9F024,00B9F02C)` contains
`a700000000000000`, immediately after the reader-confirmed opcode-45
command `[00B9F01C,00B9F024)`. Scene 81/object group 10/row 0/field +14
selects that first command through pointer word `00B9F660`.
Its native handler `08065772..08065782` calls a virtual function at
`0806577A`, then branches unconditionally from `0806577E` to fetch
`08064E3C`. The callback's behavior has not been executed by this review.
The following A7 handler `08066492` selects return value zero and reaches
the common epilogue at `08066498`.

A bounded continuation check may reuse scratch controller
`[0203F000,0203F0A8)` and previously used transient stack area with
`SP=03007800`. It must explicitly start after the unexecuted callback,
stop before the epilogue, preserve guards and distinguish typed-command
evidence from natural event/callback coverage. The
[instruction listing](../build/completion/remaining-ui/research/command-45-continuation.txt)
records both handlers. No source bytes or pointers are available for reuse.

The continuation check now passes in the 17-resource remaining-field audit.
It preserves all controller bytes apart from the expected cursor/current
command/opcode fields. `00B9F024` is retained as command A7; the virtual
callback and natural temple event remain untested.

### Recovery-pot tutorial wording correction

Normal floor-two play found that source `[001B492F,001B498D)` names its
action “Press” in the earlier English draft, while the live action menu uses
“Push”. The tutorial's owned pointer is `[001B4B08,001B4B0C)`, selected by
the existing nine-row tutorial reader. Its current patch is
`tutorial.001b492f.001b4b08`, owner `tutorial-gameplay`, with original pointer
`081B492F` and earlier English pointer `09012934`. The earlier appended
payload `[01012934,01012992)` remains occupied.

Owner `text-polish` may explicitly supersede that one pointer through
`RomBuild.supersede_patch` and append the corrected text through the shared
allocator. It must preserve the original source, old English allocation,
all other pointer/code patches, `$w` pause, 80-byte queue rows and 59-byte
history limit. The baseline comparison keeps the earlier English ROM
unchanged. No RAM/save changes are needed.

The accepted correction appends `[01069F88,01069FE5)` (93 bytes), after
three allocator-owned alignment bytes. The superseding pointer targets
`09069F88`; the ledger preserves the full prior patch ownership. The baseline
comparison uses the earlier English ROM unchanged. Native pot pickup,
tutorial scrolling, action selection and HP recovery pass on both ROMs.
See [TEXT_POLISH.md](TEXT_POLISH.md) and its complete image reconstruction.

### Natural results-screen tilemap correction (2026-09-12)

Normal floor-two defeat on text-polish ROM SHA256
`09bb26e91250a7a958783f12fed53ca3e687cab1387c93448deea48afc8c1a2b`
exposes a layout defect. The 27-by-17-tile bitmap is intact in the existing
`[02035E1C,0203977C)` buffer and matches `[06000040,060039A0)` in VRAM.
The native ending animation nevertheless reveals it at x=2 with 26 tiles
per row. All 459 cells differ from the constructor's x=1 / width=27 layout.
[The read-only diagnosis](../build/completion/result-runtime/research/tilemap-diagnosis.json)
pins the ROM and RAM/VRAM snapshots. This is a tilemap defect, not damaged
translation payloads or a new RAM allocation.

The existing BG0 tilemap is `[02034DDC,020355DC)`, copied to
`[06006000,06006800)` in this result context. Rows have 32 halfword entries.
Literals `0005C790` and `0008BBCC` identify its RAM base. The live ending
animation `[0805C692,0805C6F8)` clears and reveals 17 rows at y=2; its
hardcoded x/width operands are independent of the descriptor. Owner
`result-runtime` may patch only the following checked Thumb halfwords:

| ROM file range, exclusive end | Original → corrected instruction / bytes |
| --- | --- |
| `[0005C6A8,0005C6AA)` | Clear-row base: `add r5,r0,#4` → `#2`; `051d` → `851c`. |
| `[0005C6AE,0005C6B0)` | Clear count minus one: `mov r1,#25` → `#26`; `1921` → `1a21`. |
| `[0005C6B4,0005C6B6)` | Clear rightmost offset: `add r0,#50` → `#52`; `3230` → `3430`. |
| `[0005C6CE,0005C6D0)` | Reveal-row base: `add r4,r0,#4` → `#2`; `041d` → `841c`. |
| `[0005C6D8,0005C6DA)` | Reveal count minus one: `mov r1,#25` → `#26`; `1921` → `1a21`. |

These changes keep the original animation, frame pacing and input loop.
They use the existing 216px panel and introduce no text, font, RAM or save
changes. All prior allocation and patch ownership must remain byte-identical.
The high-score detail path instead calls the descriptor-driven `0808BB14`
at `08086A28`; its reveal loop reads x/width from the live window record.
See [native reveal listings](../build/completion/result-runtime/research/reveal.txt)
and [ending listing](../build/completion/results/research/ending-reader.txt).
The earlier isolated ending fixture stopped at `0805C62A` and manually used
`0808BB14`; it did not exercise the defective ending animation. New acceptance
must follow normal buttons through that animation and compare the actual
tilemap and displayed pixels, in addition to glyph bounds.

### Compact title-menu records label (2026-09-12)

Normal cold-boot menu exploration on result-runtime ROM `7693b1ee...8293aff`
shows that the existing title window has x/y=3/2 and width/height=10/6 tiles
in `[02034CD8,02034D18)`: 80px wide, with text beginning at local x=4.
“Adventure records” measures 86px in font 0, exceeding the 76px label space.
The [menu capture and window dump](../build/completion/result-runtime/research/score-menu/readers.json)
record the live context; `window.bin` in that directory contains the record
after returning to the title menu.

Source `[00C782B0,00C782BB)` is Japanese 冒険の記録. Its owned pointer
`[00C7828C,00C78290)` originally targets `08C782B0`; current patch
`frontend.00c782b0.0x00C7828C`, owner `frontend-completion`, targets `09060388`.
That full English allocation `[01060388,0106039A)` remains occupied.
Owner `ui-polish` may append the 36px display form “Records” and explicitly
supersede this one pointer via `RomBuild.supersede_patch`. Full wording
“Adventure records” remains the English catalog authority; only this menu
display uses the short form. Original source, all prior allocations, native
menu layout, row actions/ordinals and save fields remain unchanged. The new
payload and alignment must use the shared allocator and complete ledger.

Accepted UI-polish ROM SHA256
`e21304fe82c1875b228b5185099636467f1f84cfec02e1e2c9b71d5bec5c0272`
appends `[01069FE8,01069FF0)` after three alignment bytes and points the
owned title-menu word to `09069FE8`. Full-image reconstruction and prior-byte
preservation pass. Three cold-boot save contexts establish that the Records
row is conditional on a valid records profile; normal navigation on that
profile passes categories/list/detail/back checks. See [UI_POLISH.md](UI_POLISH.md).

Read-only computed-reference review on the pinned Japanese ROM scans halfword
positions in `[080000C0,0809A800)` for nearby literal loads and selected
straight-line constant operations. The [machine-readable report](../build/completion/computed-text-review.json)
records the input source queue, harness hash and limitations. It found no
new references to the 79 open starts; this is neither exhaustive code
disassembly nor evidence of unused text. No ROM/RAM reservation or insertion
permission follows from the scan.

### Empty-inventory notice and natural save route (2026-09-12)

The fresh two-Log Torneko route on UI-polish ROM `e21304fe...c0272` generates
a different dungeon layout from the older Japanese-Log checkpoint. Its
recorded normal buttons end in a **floor-one defeat**, not a cave clear or
floor-two pickup. The village priest's Pray/save interaction then writes a
native save; a fresh core displays the earned She-slime defeat, floor 1,
score 1 record and reloads Log 1 in Barinabo Village. These exploratory
artifacts live in `build/completion/roundtrip/`; the complete replay and popup
correction subsequently passed as documented below.

The same route reaches a 128px empty-inventory popup. Passive watchpoints
confirm native load `08020484` reads the already owned word
`[00020488,0002048C)`, targeting `09065030` in that build. Native printf
then reads that exact string. See [reader trace](../build/completion/roundtrip/research/empty-probe/trace.json)
and [getter/popup disassembly](../build/completion/roundtrip/research/inventory-error-reader.txt).
Getter `08020400` selects source `[001B98C2,001B98D6)` for selector 3;
its earlier catalog classified the resource with queue messages, but the
observed reader uses the single-line popup `08020498`.

| Address space / range, exclusive end | Owner, role and evidence |
| --- | --- |
| ROM `[001B98C2,001B98D6)` | Original Japanese empty-inventory source; stays protected. |
| ROM `[00020488,0002048C)` | Existing patch `battle.001b98c2.0x00020488`, owner `battle-completion`, original pointer `081B98C2`, current `09065030`. |
| Appended ROM `[01065030,01065050)` | Earlier full English allocation, retained intact. “You are not carrying any items.” measures 157px and clips in this 128px reader. |
| ROM `[000A69C0,000A69E7)` | Original printf format: `%s`, 36 literal spaces, NUL. Literal `[00020520,00020524)` selects it at `080204E4`; `080204EA` formats the notice. Padding is native blank fill, not additional translated text. |
| ROM `[000A6980,000A69C0)` | Existing custom 64-byte popup descriptor, 16 by 2 tiles at x/y 7/9, selected through literal `[000204B8,000204BC)`. |
| ROM `[00CA29B4,00CA29F4)` | Original window-template 5. Its fourth 16-byte record at `[00CA29E4,00CA29F4)` supplies the observed same 128px popup. Other window records remain untouched. |
| EWRAM `[02034D98,02034DD8)` | Existing window-3 runtime record in the observed inventory context: x/y 7/9, width/height 16/2 tiles. |
| IWRAM `[03007C38,03007D38)` | Observed 256-byte transient printf destination at caller-frame SP+4; `08020498` reserves 0x104 stack bytes. This is not a permanent allocation. |

Owner `inventory-notice` may append the short display “No items.” and explicitly
supersede only the existing `00020488` pointer, retaining full English and the
earlier allocation. The independently translated, larger paged-message source
`00C3EE68` and its pointer `00076144` remain unchanged. The new reader-specific
catalog must identify the popup role and preserve Japanese/source metadata.
Other getter outputs already measure at most 104px. No code, window, font,
RAM or save expansion is proposed.

Popup verification must observe `080204EA`/`080204FA` and validate the native
text plus exactly 36 trailing spaces. Check all visible text ink inside 128px
and all glyphs against the source. The original padding advances beyond the
window with transparent space glyphs; this narrowly verified behavior must
not relax overflow checks for other text. Natural save tests may passively
observe existing name-copy points `080027D0`/`0800230A`, record creation
`080011F0` and profile write `080016DC`, using the name/profile ranges already
documented above. No name, record, HP or scenario values may be injected.

Accepted inventory-notice ROM SHA256
`8757bf5cd89e6b935c8f99c431600eb6b5367ad9e9078158a84c047cf6d6e960`
appends `[01069FF0,01069FFA)` and changes the owned word to `09069FF0`.
Complete image reconstruction, prior-allocation preservation and paired native
popup checks pass; see [INVENTORY_NOTICE.md](INVENTORY_NOTICE.md).
The [native save roundtrip](NATIVE_SAVE_ROUNDTRIP.md) also passes on this ROM,
including fresh creation of both seven-letter logs, native priest saving,
earned records and independent cold loads of both logs. Profile RAM
`[02002FD4,02004F80)` matches native save-file bytes `[0000E000,0000FFAC)`;
the 48-byte first score is at profile-relative `[00000014,00000044)`.
The existing eight-byte name remains at `[0203BB38,0203BB40)` and native Log
record-relative `[00000010,00000018)`. These are observations of existing
fields, not new reservations or a physical Log-sector mapping. No save layout
changes were required for the observed route.

### Remaining resource boundaries: read-only investigation (2026-09-12)

Owner `resource-boundaries` investigates five extraction candidates through
existing scene asset readers. This is classification/preservation work; no
artwork changes, source reuse or insertion ownership follows. The pinned
Japanese original and inventory-notice ROM are the comparison contexts.
Listings are in `build/completion/resource-boundaries/research/` and the earlier
`build/completion/remaining-ui/research/scene-readers.txt`.

| Address space / exclusive range | Evidence and current interpretation |
| --- | --- |
| ROM `[00941018,0094103C)`, `[0093FE3C,0093FE54)` | Scene 0 descriptor and graphic header, selected through the existing scene cache and reader `0806C5F0`; header format `0202`. |
| ROM `[0092C238,0092C630)` | Header +16 selects 127 stored four-halfword metatiles (count 128 includes implicit zero entry). Candidate `[0092C610,0092C631)` spans the last four records and the first byte of the following asset, rather than one NUL-terminated resource. Native copy verification pending. |
| ROM `[0093FCB0,0093FE30)` | Thirty-two 12-byte animation records selected by scene-0 header +20. First record +4 points to tile bytes `[0092C630,0092CF50)`, 73 tiles ×32 bytes. Its first byte supplies the apparent candidate's terminator. |
| ROM `[00A016CC,00A016F0)`, `[00A01664,00A016CC)` | Scene 30 descriptor and thirteen 8-byte palette-animation records. Row 2 at `[00A01674,00A0167C)` contains period 4, count 17 and pointer `08A00A70`; native initialization/update confirmation pending. |
| ROM `[00A00A70,00A00E6C)` | Proposed 17 frames ×15 four-byte RGB values. Three apparent strings `[00A00BF8,00A00C04)` lie in frame 6 at color indexes 8–10. These are structurally color values; native palette consumer verification is still required. |
| ROM `[00AA7638,00AA765C)`, `[00AA760C,00AA7624)` | Scene 54 descriptor and header; format `0303`, 48 animated tiles and 64 animation records. |
| ROM `[00AA7300,00AA7600)`, `[00AA75E8,00AA75F4)` | Animation table and its row 62. Row +4 selects `[00AA6640,00AA6C40)`, 48 tiles ×32 bytes, enclosing candidate `[00AA6678,00AA6681)`. Native frame selection/copy confirmation pending. |
| EWRAM `[02008BF8,02008C70)` | Existing fifteen 8-byte palette-animation states, populated by `0806752C..08067588` from the selected scene descriptor. Adjacent earlier keyboard buffer `[02008BF0,02008BF8)` has a separate context/lifetime. |
| EWRAM `[02008C70,02008C88)` | Existing animated-tile state: flags +0/+1, countdown +2, map pointer/count +4/+8, current 12-byte frame pointer +12, tile destination +16, tile byte count +20. Native initializer `08067588`, updater `08067F20`. |
| EWRAM `[02008C90,02008CB4)` | Existing copied 36-byte scene descriptor. Native copy `08067022..08067030`. Scene ID is the adjacent halfword `[02008C88,02008C8A)`; format state is separately indexed above at `02008CB8`. |
| IWRAM `[030032A0,03003AA0)`, `[03003AA0,03003D20)` | Existing 512 four-byte palette values and 32 twenty-byte bank states. Native `08089D0C` writes one color and marks the selected bank plus global flag `[03000044,03000045)` dirty. No permanent scratch reservation is added. |

Bounded fixtures may execute native descriptor/state initialization and selected
copy/update paths in disposable cores. Reuse the already mapped guarded copy
scratch `0203F200` and temporary stack `03007800`; compare adjacent fields,
source bytes and the exact native outputs. These are controlled reader tests,
not natural scene or animation reachability claims.

Native upload `08068118` reads the current frame's +4 tile pointer, destination
and byte count from the animated-tile state, then calls `08088F44`. Initialization
`08067588..080675B6` derives destination `06008000 + header.tile_count*32` and
length `header.animated_tile_count*32`: scene 0 uses VRAM
`[06009B80,0600A4A0)`, scene 54 `[0600E2A0,0600E8A0)`. The proposed fixtures
compare these native writes and surrounding bytes without adding guards in
VRAM. Frame selection uses the native 12-byte advance/wrap slice
`08067FDA..08067FEE`; timer pacing remains outside that bounded slice.

The [completed native audit](RESOURCE_BOUNDARIES.md) confirms all five candidates:
four guarded metatile copies, 2,336/1,536-byte exact tile uploads with unchanged
adjacent VRAM, and 28 palette-update calls with all fifteen selected RGB writes
matching the source. Earlier “pending” rows above record the pre-verification
interpretation; the report now supplies its positive native evidence. No ROM
or artwork changed. Accounting is now 8,422 authored + 822 retained + 74 open.

### Gameplay candidate readers and status markers (2026-09-12)

Owner `gameplay-candidates` is investigating seventeen unowned gameplay/frontend
sources on the pinned Japanese original and the unchanged inventory-notice ROM
(`8757bf5c…e960`). This adds evidence, not insertion ownership or free space.
The complete candidate bytes remain authoritative in
`translations/unowned-text-review.json`. Disassembly is under
`build/completion/gameplay-candidates/research/`; switch-entry listings are
provisional code slices, not claims of independent callable functions.

| Address space / exclusive range | Role, evidence and permitted investigation |
| --- | --- |
| ROM `[000190A0,000190D8)` | Item-landing selector and its literals. Instructions read existing flags at `020060F9` then `020060F8`, returning the owned ground, water, or ground/water message at `001B550B`, `001B5532`, or `001B5544`. The literal-star candidate `001B551C` is absent from these branches. A paired native four-boolean-case check is permitted; it cannot prove global non-use. |
| EWRAM `[020060F8,020060FA)` | Two existing one-byte landing-selector flags. Exact gameplay producers/semantics remain under investigation. Disposable fixtures may set each to 0/1 and restore the state between cases; adjacent bytes must remain intact. No new reservation. |
| ROM `[0006E1C0,0006E2CC)` | Native item footer formatter and literals. Two transient 64-byte stack strings form strength and synthesis-count text in a caller-supplied 1,024-byte output. Code indexes item properties by signed item ID at record +14. Six adjacent weight-label candidates are not named in this function. |
| ROM `[000E07F4,000E306C)` | Existing 370 ×28-byte item properties, already consumed by item-name/display paths. Footer uses byte +0 as type. This range is preserved; no new callback-table interpretation is asserted. |
| EWRAM `[0203F000,0203F018)`, `[0203F100,0203F102)`, `[0203F200,0203F600)` | Reuse of previously documented disposable item record, formatter options and 1,024-byte output scratch. Eight-byte output guards precede/follow the output. Footer/status fixtures restore the native state between cases, retain input record/options and check output guards. Temporary native stack remains the existing `03007E00` harness stack. These are fixture lifetimes, not game reservations. |
| ROM `[00080C0C,00080C44)` | Fourteen native item-format branch pointers selected inside `08080A5C`. Equipment enhancement formatting begins at `08080C44`. New switch-entry listings complement the earlier item-display function listing. |
| ROM `[00CB06BC,00CB0728)` → EWRAM `[02000834,020008A0)` | Existing 27-pointer item-icon cache. Formatter may choose rows 25/26 for particular status flags. Icon meanings require independent evidence; CP932 character names do not identify these custom bitmap symbols. |
| ROM `[00C4C944,00C4C954)`, `[00C4C954,00C4C964)` | Existing four-pointer status-prefix table and four short glyph strings, selected near `080811FC` using equipment/status flags and options. Encoded glyphs `8750..8753` have bitmaps `[00C82910,00C82A30)` (four ×72 bytes). The E-shaped equipped marker and accompanying small symbol are distinct assets from the prose star; the small symbol's mechanic is not yet established. |
| ROM `[001B5521,001B5523)`, `[00C9414C,00C94158)`, `[00C7E500,00C7E548)` | Literal indexed star `F8A0` in candidate `001B551C`, its font-0 descriptor and 72-byte bitmap. Descriptor code `819A`, advance 12. Original bitmap confirms a star. This occurrence is after the item substitution and Japanese topic particle, inside `★間`. No mechanical interpretation or insertion is approved. |
| ROM `[00085B48,00085C50)` | Existing frontend mode-choice routine and literals. Its three confirmation branches select `00C7A990`, `00C7A9C0`, `00C7A9F0`; help selects `00C7A554` or `00C7A73C`. The adjacent candidate `00C7876C` does not appear in those literals. Bounded pointer-selection tests do not exercise confirmation consequences. |
| EWRAM player-relative `[+002C,+0030)` | Observed two existing little-endian 16-bit tile coordinates during normal first-cave inputs. On the recorded fresh two-Log route, player is `0202DA6C` (root `02013B18`, pointer at root +`19EE4`). Movement changed X/Y consistently with the native screen. Observation only; no coordinate writes or permanent absolute-player allocation. |

The normal-button cave exploration records input frames, screenshots, state and
native save snapshots under `build/completion/cave-clear/`. It is exploratory
until independently replayed and checked. An initial explorer mistakenly
treated the A-button enum value zero as false; that fixture-only attempt was
rejected, and the continuation restarted at its native first-floor checkpoint
with corrected enum-vararg key handling. No ROM fix or gameplay-state injection
was involved.

The paired native audit now passes the four landing cases, 64 dungeon-name
rows, 370 zero-enhancement/no-synthesis footers, three confirmation selections
and six status-prefix cases per ROM. Source records, options, output guards
and selected flag neighbours remain intact. See
[GAMEPLAY_CANDIDATES.md](GAMEPLAY_CANDIDATES.md); all seventeen remain open.
Additional preserved code evidence: projectile dispatch `[00015744,000184BC)`
and its nine-pointer tail switch `[00018220,00018244)`; branch `08018384`
loads the already owned item-vanished source through `[000183E0,000183E4)`.
These are protected existing code/literals, not new patch ownership. Native
item-icon getter `[0007E88C,0007E8C0)` normally returns item-property byte +1,
with a special item-342 branch. No plating-effect meaning follows from it.

### Natural successful clear and native save (2026-09-12)

The [accepted cave-clear roundtrip](CAVE_CLEAR.md) adds runtime evidence on the
unchanged inventory-notice ROM. No new allocation, source reuse or patch is
introduced. Native creator `080011F0` runs at frame 86724, profile writer
`080016DC` at 123356, and Adventure Log name copy `080027D0` at 123440 in the
435-input uninterrupted replay.

The existing first 48-byte score at EWRAM `[02002FE8,02003018)` / profile-relative
`[00000014,00000044)` now has cause 91 (clear), zero actor/item relation fields,
score 4002 in its three-byte +10 field, floor 3 at byte +25,
and dungeon/protagonist byte +26 equal to zero (these three offsets are
decimal). Existing cause key `result_91`
selects original source `[000DB8D4,000DB8E5)` through owned word
`[000DB67C,000DB680)`. These are observations of native fields, not changes.
The complete record agrees at native ending, saved profile and cold load.

The previously established save layout has two seven-sector Adventure Log
blocks `[00000000,00007000)` and `[00007000,0000E000)` followed by the shared
profile sectors. Log 2's entire second block remains byte-identical to the
fresh two-Log input; both Logs cold-load. Profile payload `[0000E000,0000FFAC)`
matches final native RAM `[02002FD4,02004F80)`. The compact eight-byte name
at `0203BB38` and Log-record-relative +16 (decimal) retain `Torneko`; this does not put
a new name field in the 48-byte score record. See earlier name/save notes
for record-versus-physical-address distinctions.

All 17 result reveal steps keep the existing 27×17 panel mapping correct;
the cold result has 2,205 exact white foreground pixels. Native save SHA256:
`ed02ce9c53d13f7f3055db319d6633aab5f48afb32c4d3da0327a08e0572f971`.
The natural Shrine of the Gods meeting, Ines joining and map handover add
story coverage, without claiming ownership of any deferred arrival/map art.

### Original dungeon arrival cards (2026-09-12)

The user requested original Japanese review PNGs before English artwork
auditions. These discoveries protect existing resources; they authorize no
ROM patch, source reuse, RAM reservation or save change. Source is the pinned
Japanese ROM `35bfff00…4d02`. The unchanged English ROM `8757bf5c…e960`
provides the normal-button cave/shrine comparison route.

| Address space / exclusive range | Purpose / owner / evidence |
| --- | --- |
| ROM `[003903D0,00390410)` | Sixteen original arrival palette words, packed `AABBGGRR`; native reader `080051F2` feeds palette entries E0–EF. Confirmed by native source watch and displayed colours. |
| ROM `[00390410,003BFFD0)` | 36 distinct original arrival assets. Each contains a 0x800-byte 32×32 halfword tilemap, followed by its counted 8×8 4bpp tiles. Exact individual protected spans, counts, hashes and all selector aliases are in the generated manifest below. All adjacent asset ends join exactly; the envelope is not free space. |
| ROM `[003BFFD0,003C13D0)` | Original 160-tile / 0x1400-byte atlas for digits 0–9, F and Q. Renderer copies it after the title's 160-tile slot; exact native VRAM comparison confirms the copy. |
| ROM `[003C13D0,003C1450)` | 64 signed halfword title tile counts, paired with the pointer table. Counts exclude the preceding 0x800-byte tilemap. |
| ROM `[003C1450,003C1550)` | 64 original arrival pointers; native `080051A6` selects `dungeon_id + 32 * bank`. 64 selectors resolve to 36 unique assets. This is the complete table, not proof of every selector's natural reachability. |
| ROM `[0009B6FC,0009B72C)` | Twelve word-sized atlas starting tile indexes, used by `0800511C`. Digits use 2×5 tiles; F/Q use 3×5. |
| ROM `[0000511C,0000518C)` | Original five-row floor-glyph writer and three literals. Occupied code, with map pointer at `00005184`. |
| ROM `[0000518C,0000539E)` | Original card constructor, including embedded literals. Copies 29 columns ×9 rows of the title map, adds the floor line, or suppresses it for arena ID 26. |
| ROM `[00004B6C,00004B8E)` | Existing puzzle classifier, including embedded literal: dungeon ID 27 returns 1, ID 25 returns 2, other IDs return zero. Constructor suppresses the entire card at puzzle number 100. |
| EWRAM `[02004F8C,02004F90)`, `[02004FF0,02004FF2)` | Existing bank word and adjacent dungeon-ID/floor-number bytes. Read by the original constructor; bank's broader game semantics are not inferred here. Observation only, no writes/reservation in this PNG export. |
| EWRAM `[02000034,02000035)`, `[02005E48,02005E49)` | Existing suppression flag and card-upload flag. Constructor reads the former and sets the latter. No new owner or permanent reservation. |
| EWRAM `[02035DDC,020385DC)` | Existing 0x2800-byte arrival tile buffer: title slot `[02035DDC,020371DC)`, floor atlas `[020371DC,020385DC)`. Lifetime is native arrival display; this is not an additional project allocation. |
| EWRAM `[02034DDC,020355DC)` | Existing BG0 tilemap. The constructor's clear loop additionally touches columns 1–31 of the following row, through `0203561C`; this observed native overlap is not permission to reserve or overwrite that following region. Title occupies screen rows 1–9, floor line rows 12–16. |
| BG VRAM `[06000000,06002800)` | Native arrival upload of the combined title/floor tile buffer. Existing transient display ownership; source bytes matched the captured cave-floor transition. |

[ARRIVAL_CARDS.md](ARRIVAL_CARDS.md) records the review sheets and coverage.
[The manifest](../build/arrival-cards/manifest.json) is authoritative for the
36 per-asset ranges and 64 mappings;
[the range ledger](../build/arrival-cards/resource-ranges.json) also includes
palette, counts, pointer table and glyph indexes. Both identify the source
ROM and explicitly have no output ROM. Native instruction listings are
`build/arrival-cards/research/arrival-readers.txt` and
`arrival-conditions.txt`. Unidentified town/ending artwork remains unowned.

### External Shiren arrival-lettering reference (2026-09-12)

The user identified `../Shiren/shiren-revamp-fixes` as a lettering reference.
Its `gfx/fonts/area_title_font.2bpp` file range `[00000000,00009000)` contains
occupied SNES 2bpp bitmap data. **These are external file offsets, not Torneko
ROM offsets.** Owner is the existing Shiren area-title renderer. Source
`data/demos/demos.asm` indexes 194 nine-tile chunks; thirty records in
`code/bank_05.asm` assemble 28 nonblank English names and two blank rows.

The [reference manifest](../build/arrival-cards/references/shiren-source.json)
records source hashes and exact 144-byte bitmap spans for every used chunk.
The decoded strips establish a visual reference, not a reusable alphabet,
confirmed font identity or native GBA rendering. No external file was edited,
and no Torneko ROM/RAM/save range is allocated or approved for reuse.
See [the reference notes](ARRIVAL_CARDS.md#shiren-lettering-reference-2026-09-12).

### Arrival font reconstruction and offline audition (2026-09-12)

Owner `arrival-audition` has no GBA ROM, RAM, VRAM or save allocation. The new
`assets/fonts/arrival-candidates.json` is an external authoring asset: 43
characters cropped from the recorded Shiren strips, 51 explicitly marked
Papyrus Condensed supplements, and a space advance. Three complete installed
font comparisons are stored as raster glyphs alongside the recovered face.

Each recovered glyph records a source-PNG hash and `[left,top,right,bottom)`
crop in **bitmap pixel coordinates**, not a ROM address. Its source strip's
`references/shiren-source.json` entry links back to the exact external SNES
bitmap file spans documented above. New spacing and supplemental shapes are
draft authoring decisions; no native font table or source-space reuse follows.

The [audition build manifest](../build/arrival-cards/audition/build.json)
pins the generated HTML, font asset, renderer and gameplay backdrop images.
It identifies the pinned Japanese source and has `output_rom: null`.
[Browser validation](../build/arrival-cards/audition/verification.json) records
the exact generated artifact hashes and export checks. These sheets use the
existing title area and report tile-pattern counts for review, but do not
grant insertion ownership. Custom floor positions and glyph dimensions remain
unimplemented on the GBA. A later insertion must use the shared allocator and
the existing original-byte/overlap checks across all components.

See [ARRIVAL_AUDITION.md](ARRIVAL_AUDITION.md) for source provenance, marked
supplements, review/export instructions and the retained Japanese logo scope.
