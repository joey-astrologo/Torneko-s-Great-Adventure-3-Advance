# Seven-character Adventure Log name proof

Status, 2026-09-10: **`Torneko` is the default for new Adventure Logs and can be
confirmed, saved, and loaded after a fresh start in either slot.** Both occupied
slots and existing Japanese saves pass native mGBA checks. The keyboard uses the approved font 0.
No new font assets or fan-translation text are used.

This field labels the Adventure Log; it does not rename Torneko in the story.
The implementation is a separate, reproducible proof ROM built on the 27-entry
English catalog. The ordinary `build/translation/torneko3-english.gba` milestone
still has its original four-character name path.

## Build, verify, and try it

Run from the project root with the installed Python environment and armips:

```bash
.venv/bin/python -m tools.build_name_entry
.venv/bin/python -m tools.verify_name_entry
open -a mGBA build/name-entry/torneko3-name-entry.gba
```

The builder checks the Japanese source hash, records every changed instruction
and pointer, and allocates its code/tables after the catalog's appended text.
The verifier enters names with joypad input. Its debugger observes execution;
it does not inject names, change game RAM, or force the font. Saves are native,
file-backed 65,536-byte FLASH512 files. Each load test starts a new emulator
instance. Supplied ROMs and saves are not used as output files.

Choose **New game**, select a log, and advance to the keyboard. **Torneko is
already filled in** for either slot; press R then A to accept it. To enter a
different name, press B seven times to erase the default. Use the D-pad and A
to enter letters, L to switch case, and R to select Done. Typing the seventh
character selects Done automatically. Next cannot advance beyond the
seventh position; returning to a letter at capacity replaces that position.

Artifacts under `build/name-entry/`:

- `torneko3-name-entry.gba`: the playable 32 MiB proof ROM.
- `name-entry-proof.png`: entry, confirmation, both loaded slots, and a legacy save.
- `build.json`: patch ledger, allocations, encoding IDs, font bounds, and hashes.
- `verification.json`: native test results and save hashes.
- `slot-{1,2}/{create,reload}/`: screenshots, input sequences, and passive traces.
- `two-slots/`: both occupied slots, with `Torneko` and `gyjpqQ9`.
- `legacy-{1,2}/`: original Japanese saves, acceptance of the new default
  without typing, save comparisons, and cold loads of both names.
- `keyboard-tests/verification.json`: all 62 added IDs, editing limits, and
  keyboard ink checks.
- `short/`: one-character name creation and cold loading.

The proof ROM SHA-256 is:

```text
1708353fe119e7088ceb459f03ff7b2039852ae6611b1951d1d57cb60ef0b928
```

## What changed

| Layer | Original | Name-entry proof |
|---|---|---|
| Name limit | Four compact character IDs | Seven IDs |
| New-log default | セーブ１ / セーブ２ | Torneko in either slot |
| Editor box | 48 pixels | 80 pixels; seven fixed 11-pixel cells |
| Current name in RAM | Six bytes at `02004F82` | Eight reserved bytes at `0203BB38` |
| Committed terminator | Index 5 | Index 7 |
| Save record name copy | Six bytes at record offset `0x10` | Eight bytes at `0x10..0x17` |
| Load into current name | Six-byte copy | Eight-byte copy |
| New characters | Japanese compact IDs | Existing Japanese IDs plus 52 Latin letters and 10 ASCII digits |
| Keyboard font | Font 1, ten rows | Font 0, twelve rows |
| Cartridge save size | 64 KB | 64 KB |

Names already used one byte per Japanese character. The new Latin letters also
use one compact ID each; their stored codes are not ordinary ASCII. IDs
`BF..FD`, excluding the keyboard's reserved `C9`, provide 62 new characters.
All original mappings `00..BE` are preserved. The table is extended in appended
ROM space. Legacy punctuation keys retain their original compact mappings.

`0807D228` converts terminated names and `0807D258` converts a fixed number of
editor positions. Small ARM7TDMI Thumb replacements emit one byte for ASCII
glyph codes and two for Japanese glyph codes. The original lookup at `0807D20C`
continues to select the mapping table. The editor's existing working buffer is
32 bytes; its caller's eight-byte local buffer fits seven IDs plus NUL.

The keyboard's case labels, button hints, name confirmation, and length
explanation are independently written English. `$i0` inserts the entire entered
name into the confirmation. The slot status summary otherwise remains Japanese.

The default is one shared eight-byte compact string in appended ROM space.
The pointer at ROM offset `085904` selects it, and the instruction at `0858CC`
clears the old slot-dependent offset before the existing string copy. This
changes the initial text for new logs; existing saved names are loaded normally.

### RAM reservation and saved records

The old name is followed immediately by a live 32-bit gameplay field at
`02004F88`. Expanding it in place would overwrite that field. Instead, the five
literal references to the current name are redirected to a new eight-byte BSS
reservation at `0203BB38..0203BB3F`. Startup's BSS end at ROM offset `087A04`
changes from `0203BB38` to `0203BB40`, so startup clears the new buffer too.
The game heap is separately initialized by `08087E00` at `02010A90`, size
`0x24000`, ending at `02034A90`; this reservation does not overlap it.

The Adventure Log record has a six-byte name at `0x10..0x15`, followed by two
alignment bytes, then flags at `0x18`. The proof uses those alignment bytes for
the extended name. Flags and subsequent fields retain their offsets. The native
record checksum covers both name words; the game updates it normally.

The slot-summary reader at `08085314` already copies `0x5C` bytes starting at
record offset `0x10` (`08085346`), including both former alignment bytes. Its
terminated-name conversion at `08085548` therefore receives the full name
without needing a larger summary record. The cold-load copy at `080022FC` and
record creation copy at `080027C2` are widened from six to eight bytes.

Paired native saves compare the original Japanese defaults with acceptance of
the prefilled `Torneko`. Only the eight-byte name region and the native checksum
may differ; all other save bytes match. Both default names cold-load correctly
in either slot. The earlier proof, while retaining the Japanese defaults, also
established that widening the copy alone changed only the former `FF FF`
alignment bytes to `00 00` and the checksum. Older names terminate before those
padding bytes, and both original Japanese fixtures retain their names.

### Verified behavior

- New logs display `Torneko` immediately in both slots. Accepting it without
  entering any letters saves the full name, which survives a cold load.
- `Torneko` entered through the keyboard, confirmed with `$i0`, saved, displayed
  in the slot menu, and loaded through the opening-story transition in each slot.
- Both slots occupied: creating `gyjpqQ9` in slot 2 leaves the entire first
  slot's `0x7000`-byte save region unchanged; both names cold-load correctly.
- Original Japanese saves for both slots load correctly in the new ROM.
- Every new Latin letter and digit can be entered and decoded by the native
  renderer. Case switching and erasure pass throughout the alphabet.
- One-character names save/load correctly. At seven characters, Next clamps
  the cursor and further typing replaces the last character safely. The original
  Start shortcut for kana variants leaves the tested Latin name unchanged.
- The relocated name commit leaves neighboring globals unchanged, and the
  capacity test leaves the editor buffer's bytes after the name untouched.
- Both keyboard pages use font 0. Their visible glyph ink stays inside the
  keyboard area, with no overlap between glyphs. Static bounds put the widest
  seventh-position ink edge at x=75 in an 80-pixel box, and the maximum
  confirmation line advance at 137 pixels in its 208-pixel window.

The existing 52 unit tests passed for the name-entry implementation. This proof
occupies **2,528 appended ROM bytes including the English catalog, code, tables,
and padding**, leaving
16,774,688 bytes in the appended region. The appended executable code occupies
108 bytes. No installation changes are needed.

## Scope and next milestone

This completes the bounded Adventure Log name proof. It does not establish
long-name compatibility for every later naming screen, password, result, or
gameplay route. The generic editor's other uses still need their own coverage;
the encoded-output routine at `0807D480`, for example, still consumes only the
first four name IDs. Full gameplay and physical hardware remain untested.

**Broad Japanese text extraction is the next main task.** Carry the new name
assets and patch ledger into the shared build as the master catalog develops;
finishing every early menu is not a prerequisite for extraction.

### Deferred: dungeon results and ranking names

Joey raised the possibility that dungeon results or rankings may store their own
copy of a player name, as some Shiren games do. Whether Torneko 3 has such records,
which name they use, and their storage layout have not been established here.
If present, check their name buffers, copy limits, display width, and save
serialization before treating longer-name support as complete across the game.
Changes to saved record fields may be necessary; this does not by itself imply
that the overall save file must grow. This investigation remains deferred.

## Earlier capacity-only investigation

The original audit remains reproducible with:

```bash
.venv/bin/python -m tools.audit_name_field
```

Its artifacts remain in `build/name-field/`, including `audit.json`,
`name-field-comparison.png`, original-route traces, and the temporary seven-slot
layout probe. That earlier probe changed only the editor limit and did not save
a longer name. The `build/name-entry/` artifacts above supersede it for working
Latin entry and persistence.
