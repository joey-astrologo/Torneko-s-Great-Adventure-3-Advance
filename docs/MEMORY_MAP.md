# Memory map and insertion ownership

Latest combined build: [early journey and place names](EARLY_JOURNEY.md), occupied append
`[01000000,01034789)`; 214,921 bytes, 4,806 allocations and 5,437 checked
original patch ranges. Exact owners are in
[its ledger](../build/early-journey/english-build.json). Historical milestone
ranges below describe their own ROM hashes, not fixed future insertion slots.

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
pins **192 Japanese sources**, their exclusive ends, **290 event operands** and
**30 place-record pointers** against original SHA
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
The latter uses the existing `$m0` substitution above. These two sources extend
this pass to **194 entries / 322 checked pointer words**. Their exact terminator
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
