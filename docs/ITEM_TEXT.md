# Item text insertion

Current status: The current combined milestone translates all 719 item strings. This page records the earlier eight-item insertion proof; its hashes, counts and commands describe that historical checkpoint. See [ENEMIES_AND_ITEMS.md](ENEMIES_AND_ITEMS.md) for the current build, commands and validation.

Status, 2026-09-10: both complete item tables now relocate into expanded ROM
space in the same build as the 27 menu/message translations and seven-character
name entry. The item catalog has **369 unique names and 350 unique descriptions**
(719 strings), owning **740 pointer words** for 370 item indices. Duplicate
table targets keep their aliases. Original item text remains protected in the
[central memory map](MEMORY_MAP.md).

Eight items have independently authored English name/description drafts:
Oaken club, Copper sword, Iron axe, Dragonsbane, Wooden shield, Medicinal herb,
Bread and Big bread. The remaining 703 entries retain their exact Japanese
bytes. English descriptions omit the redundant phonetic reading in brackets;
the item name is already shown in the header. Wording and terminology remain
editable. The Japanese original is the sole source; no fan-patch text or fonts
are used.

The 2026-09-10 [terminology review](TERMINOLOGY.md) updates the two weapon
names above and uses **defence** in the shield description. Catalog notes and
Japanese metadata are preserved. The build hash below reflects those changes;
the overall ordinary-item allocation envelope stays the same, although some
individual string offsets move. Use the current ledger for exact addresses.

## Reproduce and edit

```bash
.venv/bin/python -m tools.build_items --language japanese
.venv/bin/python -m tools.build_items --language english
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tools.verify_items
```

Edit `english` and `notes` in [translations/items.json](../translations/items.json).
The catalog retains exact Japanese tokens, source offsets, all aliased item
indices, pointer owners and matching master IDs. The builder creates the file
only if absent; an existing catalog is validated without overwriting drafts or
notes. These item drafts are the insertion authority for this family; editing
`translations/master.json` alone does not change the ROM.

Use printable ASCII and explicit `\n` line breaks. Item text does not accept
the menu catalog's command syntax. The builder converts description line breaks
to the game's CR bytes and adds the final CR/NUL. Names are one line, at most
32 payload bytes and 100 pixels in font 0. Descriptions allow five lines of at
most 192 pixels each. These are conservative draft profiles for the tested
contexts; they do not assert universal engine limits. New drafts require native
coverage: extend the verifier's item fixtures when expanding the English batch.

| Output | Purpose |
|---|---|
| [torneko3-items-english.gba](../build/items/torneko3-items-english.gba) | Combined 32 MiB playable build, including all 719 item allocations and 16 English item entries |
| [torneko3-items-japanese.gba](../build/items/torneko3-items-japanese.gba) | Same menu/name components, but every relocated item string stays Japanese |
| [english-build.json](../build/items/english-build.json), [japanese-build.json](../build/items/japanese-build.json) | Source/output hashes and complete allocation/patch ledgers |
| [verification/report.json](../build/items/verification/report.json) | Native acceptance results tied to the compared ROM hashes |
| [item-comparison.png](../build/items/verification/item-comparison.png) | Eight Japanese/English information-screen pairs, visually reviewed |

The English build uses **27,951 appended bytes including alignment**, leaving
**16,749,265 bytes** in the expansion arena. The Japanese-item counterpart uses
27,943 bytes. This includes menus and name-entry assets; it is not an estimate
of the final English game's size. No original-ROM padding is reused.

English ROM SHA-256:

```text
19c287c5cbc60c262b5ac39bfa96417a3dc250e97cc34ed141dbec99883e49c4
```

## Reader discoveries

- Item-name table: ROM `[0018F16C, 0018F734)`, 370 absolute pointers. Item
  descriptions: `[001B3498, 001B3A60)`, 370 absolute pointers. Exact source
  spans/aliases are recorded in the broad extraction's `tables.json` and master.
- `08080A5C` formats an item name. The item record's signed halfword at `+0E`
  supplies the item index. Static inspection and native execution confirm:
  `08080B62` loads a name pointer, and `08080B68` calls the 100-byte copy routine.
  `0808138C` copies up to 100 bytes to the caller's output and writes a NUL at
  index 99. Prefixes, suffixes, identification and item flags affect the result;
  a 99-byte raw name is not automatically a safe formatted name.
- `0806DCDC` displays item information. `0806DE54` loads the description
  pointer using that same item index from the table selected by the literal at
  ROM `[0006DE84, 0006DE88)`. `0806DE5E` passes the description to `0808CB84`
  at local `(0, 26)`. It selects font 0 at `0806DD6E..0806DD70` and also formats
  the name into a 100-byte stack region starting at its local `sp + 4`.
- These are function entries and inspected instructions, not declarations of
  free code space or proof that all item display contexts share one limit.

Native execution observes name-table loads at `08080B62` in all 370 item-ID
fixtures, covering 369 distinct table words. Item 127 is a special case: the
branch at `08080B48..08080B4E` selects the byte at record `+15` instead. Its
zero-filled fixture reads row 0, so row 127's placeholder (`よび127`) has static
relocation/byte coverage only. Description-table loads at `0806DE54` are traced
for the eight UI examples. Their information windows are 24 tiles /
192 pixels wide, with origin `(24,24)`. The wrapper uses 13-pixel line spacing.
The header's extra statistics start at local x=144, so formatted names must
also leave that column clear. The inventory's measured text window is 160 pixels
wide and adds a list prefix. The information panel uses a 100-byte name buffer
observed at RAM `[03007540,030075A4)` on this route; it is transient stack storage.

Assembly and provisional pseudocode are in
`build/items/research/item-readers.txt`. Ghidra's listing includes unresolved
switch branches and some literal words decoded as instructions, so native
traces are needed before treating the complete pseudocode as established.

## Controlled inventory fixtures

The world inventory head pointer is at RAM `[0200C640, 0200C644)`, selected by
the literal at ROM `[0007612C, 00076130)`. After the input-driven opening route,
it points to `0200A480`. Its first record is empty; the menu checks bit 31 of the
record's first word to decide whether an item is present. Item index is at
record `+0E`. Verification can install one known test item into the existing
24-byte slice `[0200A480, 0200A498)`, then open its menus using controller input.
These are temporary emulator fixtures, not new RAM allocations or changes to a
user's save. The full inventory/container layout is not inferred from that slice.
The fixture clears that slice, writes flags `81800000` and the item index, and
sets `+10..+12` to the signed enhancement (zero for screenshots). It then uses
`B, A, A, A` to open the world menu, inventory, actions and description. The
emulator state is restored for every case. The exact input-driven opening route
and fixture setup are implemented in [verify_items.py](../tools/verify_items.py).

Earlier isolated calls use disposable scratch RAM `[0203F000, 0203F170)` for
an item record and guarded name output, with a test stack below `03007E00`.
They discard the emulator state afterward; none of this scratch space is
approved for a permanent game allocation. A standalone information-screen call
did not reproduce the game's frame/task context, so visual verification must
use the controller-driven inventory route instead.

## Shared build ownership

[rom_build.py](../tools/rom_build.py) now supplies one `RomBuild` to menu and
name components. It owns their allocator, original-ROM patches, immutable
source spans and permanent EWRAM reservations. Cross-component duplicate asset
IDs, overlapping patches, source mismatches and reservation collisions fail.
Finalization reconstructs the entire expected image from the ledger and checks
that assets, alignment padding and unused expanded space have no unaccounted
writes. The name-only image remains byte-identical to its previous verified
build while carrying the combined ledger.

The item component then adds its 719 assets and 740 patches through that same
live build context. The final ledger contains 760 allocations and 792 patches
covering all three components. Rebuild from the pinned original; never stack
the separate proof ROMs. Finalization verifies the complete image before output
is written, including every byte that must remain unchanged.

## Verification and limits

All **87 current unit tests** pass, including whole-family Japanese byte preservation,
alias ownership, draft retention, source-metadata rejection, encoding/width
limits and cross-component collisions. Native verification uses mGBA 0.10.5
with its built-in BIOS and makes a fresh temporary Japanese save through normal
game input. Each ROM independently replays the opening to the first village
room before applying the controlled inventory fixture.

- The baseline is the previously verified menu/name ROM with original item
  pointers. All **16 inventory/information screenshots** are pixel-identical
  between that baseline and the Japanese item relocation.
- All **16 English entries** have traced table reads and native glyph checks.
  The eight names appear in both inventory and information headers; eight
  descriptions render at their expected positions, with font 0, no extra
  spacing, correct CR line breaks, and no collision with window edges/footer.
  English screenshot differences remain inside the item UI windows.
- Each of the three ROMs passes **380 guarded native name-formatter calls**:
  all 370 item IDs, plus enhancements of -99 and +99 on five weapon/shield
  examples. The 100-byte destination's guards remain intact, every call returns,
  and Japanese relocation produces identical formatted bytes. Undrafted names
  remain unchanged in English. These English cases use at most 29 bytes including
  NUL and 89 pixels including decorations, below the 144-pixel header boundary.
- The combined English ROM creates, persists and cold-loads a 65,536-byte save
  containing the full name `Torneko`, then reaches the opening story. The broader
  two-slot/keyboard/legacy-save tests belong to the unchanged name component's
  [earlier milestone](NAME_ENTRY.md).

This establishes insertion for these two tables, not every item-related text
path. The controlled fixtures cover identified items outside a dungeon, not
normal item acquisition or a full playthrough. Unidentified-item names and
synthesis descriptions have separate tables; special IDs/flags can select
alternate readers. Shop prices, containers, custom names, curses, and other
decorations need their own runtime cases before claiming those contexts.
Ranking/result-name save storage remains deferred.

The subsequent [item-context milestone](ITEM_CONTEXTS.md) now relocates both
the unidentified-name and synthesis-description tables in the same ledger.
It verifies every new table word with controlled native fixtures, identified/
custom-name regressions, and the synthesis heading/body control. This page's
ROM covers only the ordinary-item milestone, now with the terminology review
applied; the later context build includes these same corrected item drafts.
