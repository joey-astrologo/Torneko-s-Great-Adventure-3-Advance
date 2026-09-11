# First label: a working translation proof

Verified on 2026-09-09. The Japanese title menu's **はじめから** label now displays
our independently written **Begin** in a separate test ROM. This is a technical
proof, not a final terminology decision. The Japanese original is the build base;
the fan translation is not an input to the build or its tests.

The patch changes **10 bytes** in the 16 MiB ROM. It uses the original game's
existing Latin glyphs and variable-width rendering. No assembly patch was needed
for this label.

## Reproduce and try it

From the project root, using the installed environment:

```bash
.venv/bin/python -m tools.build_first_label
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tools.verify_first_label
open -a /Applications/mGBA.app build/first-label/torneko3-title-begin.gba
```

The builder defaults to the Japanese filename recorded in [TOOLING.md](TOOLING.md#rom-roles-and-translation-source).
An explicit ROM path can be supplied as its first argument. It requires the
verified original SHA-256 and checks the source label, pointer, and available
space before writing output. It rejects the fan-translated ROM as a build base.

Press **Start** on the title screen to see **Begin**. Selecting it with **A** opens
the adventure-log slot menu. Both supplied source ROMs remain intact.

| Generated artifact | Purpose |
|---|---|
| `build/first-label/torneko3-title-begin.gba` | Playable proof ROM |
| `build/first-label/torneko3-title-begin.ips` | 25-byte IPS patch for the verified Japanese original |
| `build/first-label/build-report.json` | Source/output hashes, patch hash, and translation manifest |
| `build/first-label/verification.json` | Combined emulator verification results |
| `build/first-label/japanese/` | Original screenshots, raw states, battery saves, and rendering trace |
| `build/first-label/patched/` | Matching artifacts for the proof ROM |

The editable source is [title_begin.json](../translations/proof/title_begin.json).
The current visual regression fixture intentionally pins the reviewed **Begin**
proof; changing the label requires reviewing and updating that fixture.
Generated ROMs, captures, and analysis projects stay under ignored `build/`.

## Text location and encoding

Searching the Japanese ROM found the menu label as CP932/Shift-JIS-compatible
bytes. An emulator read watchpoint confirmed which occurrence is used here.
The surrounding strings are uncompressed, NUL-terminated, and referenced by a
table of little-endian GBA ROM pointers.

| Item | ROM file offset | GBA address |
|---|---|---|
| Menu text pointer table | `0x00C78280` | `0x08C78280` |
| First menu label | `0x00C782D8` | `0x08C782D8` |
| Following string begins | `0x00C782E4` | `0x08C782E4` |

The first pointer is `D8 82 C7 08`. The label occupies 12 bytes including its
terminator and alignment padding:

```text
Original: 82 CD 82 B6 82 DF 82 A9 82 E7 00 00   はじめから
Proof:    42 65 67 69 6E 00 00 00 00 00 00 00   Begin
```

The pointer stays valid because the replacement fits in the original allocation.
The builder checks the entire allocation and preserves the rest of the ROM.

The table has six entries; this fresh-save route displays entries 0 and 4:

| Index | Label address | Original Japanese |
|---|---|---|
| 0 | `0x08C782D8` | はじめから |
| 1 | `0x08C782CC` | つづきから |
| 2 | `0x08C782BC` | 冒険の書を消す |
| 3 | `0x08C782B0` | 冒険の記録 |
| 4 | `0x08C782A4` | ゲーム設定 |
| 5 | `0x08C78298` | *デバッグ |

These findings establish this menu's encoding and storage. Other resources may
use compression, different structures, or additional control codes.

## Verified rendering path

Ghidra disassembly and mGBA callbacks agree on the following path. Function names
below are our analysis labels, applied by
[AnnotateTitleText.java](../tools/ghidra_scripts/AnnotateTitleText.java).

| GBA address | Analysis label | Evidence |
|---|---|---|
| `0x08084A10` | `TitleMenuRun` | Loads the first label pointer at instruction `0x08084CD8` |
| `0x0808CBA0` | `DrawEncodedText` | Iterates decoded character codes and advances the drawing position |
| `0x0808C72C` | `ReadEncodedTextCharacter` | Reads the first label byte at `0x0808C732` |
| `0x0808C66C` | `LookupFontGlyph` | Resolves character codes to 12-byte glyph descriptors |
| `0x0808BC4C` | `DrawFontGlyph` | Draws the glyph; breakpoint `0x0808BC78` observes the resolved descriptor |

The decoder consumes two bytes for lead bytes in `0x80..0x9F` or
`0xE0..0xFE`, combining them as `(lead << 8) | trail`. Otherwise it consumes one
byte. This describes the game's observed decoder, including its broader lead-byte
checks; it is not a claim that every such byte pair is valid standard Shift-JIS.
The text loop stops on NUL and also handles control values. Full control-code
semantics are not established by this proof.

For single-byte codes, glyph lookup consults a mapping table at `0x08CA2674`.
The active font index is at `0x020398F8`; it is 0 on this route. The corresponding
glyph descriptor table is `0x08C93B4C`, obtained from the table at `0x020398EC`.
Lookup uses a binary search for ordinary character codes.

The descriptor fields verified by disassembly and runtime inspection are:

| Descriptor offset | Meaning |
|---|---|
| `+0` | 32-bit bitmap pointer |
| `+4` | 16-bit character code |
| `+6` | Signed 16-bit horizontal advance |

Other descriptor fields and the complete bitmap format still need analysis.
The original font supplies the proof's glyphs:

| Character | Code | Descriptor address | Bitmap address | Advance |
|---|---|---|---|---|
| B | `0x42` | `0x08C93CE4` | `0x08C7CA90` | 6 px |
| e | `0x65` | `0x08C93E88` | `0x08C7D468` | 5 px |
| g | `0x67` | `0x08C93EA0` | `0x08C7D4F8` | 5 px |
| i | `0x69` | `0x08C93EB8` | `0x08C7D588` | 3 px |
| n | `0x6E` | `0x08C93EF4` | `0x08C7D6F0` | 5 px |

The five original Japanese glyphs each advance 9 pixels. **Begin** advances
24 pixels in total, so this example also demonstrates the existing renderer's
variable-width support. It does not establish that every menu or dialogue path
supports the same behavior.

## Verification and fixtures

The route uses a temporary cartridge copy with no existing save and mGBA's
built-in BIOS: run 600 frames, hold Start for 3 frames, then release for 240
frames. The first label is read and rendered during frame 642. The reviewed menu
capture is at frame 843.

[verify_first_label.py](../tools/verify_first_label.py) checks both ROMs from a
fresh boot and again after restoring the title state with its battery save:

- The menu pointer and character-decoder read callbacks fire at the expected instructions.
- The glyph renderer receives the codes for our English label.
- The label crop matches the visually reviewed RGB hash in
  [title_begin.json](../tests/fixtures/title_begin.json).
- Changed screen pixels are confined to the first label: bounding rectangle
  `(29, 16, 73, 27)`, with right and bottom coordinates exclusive.
- Save-state replay reproduces identical pixels, EWRAM, IWRAM, frame count, and text trace.
- Pressing A opens the save-slot submenu. That screen matches outside the retained
  first label, which remains visible beside the submenu.
- The source ROM remains byte-identical.

The six standard-library unit tests separately check wrong-base rejection,
incorrect source/pointer rejection, string capacity and NUL handling, and an
independent application of the exported IPS record against the original ROM.

`title.state` and `menu.state` are raw Python-binding states, paired with `.sav`
battery data and the ROM hash in `capture.json`. Their compatibility with desktop
mGBA's save-state file format has not been established. Recreate these fixtures
with the verifier rather than treating them as portable GUI save states.

## Ghidra project and comparison evidence

The annotated project is `build/research/ghidra/TornekoJapanese.gpr`. Open it with
the installed Ghidra and navigate to the labels above. Targeted listings and
provisional decompiler output are in `build/research/title-text-disassembly.txt`
and `build/research/title-font-disassembly.txt`. The address-level conclusions
come from disassembly and runtime traces; provisional pseudocode contains
unresolved return/jump-table warnings and should not be treated as recovered source.

[InspectThumbFunctions.java](../tools/ghidra_scripts/InspectThumbFunctions.java)
can recreate the targeted listings in a fresh import. Its arguments are an output
text path followed by function entry addresses. Supply `0x08084A10`,
`0x0808C72C`, `0x0808CBA0`, `0x0808C66C`, and `0x0808BC4C`, then run
`AnnotateTitleText.java`. Full-ROM auto-analysis was not run for this milestone.

The read-only comparison found 30,380 differing bytes in 2,302 contiguous runs.
Both supplied ROMs are 16,777,216 bytes with matching header fields. The detailed
offset ranges are in `build/research/rom-differences.json`.

| ROM | SHA-256 |
|---|---|
| Japanese original | `35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02` |
| Fan reference | `e7108d76a0c9c3a40b3eb52dc622cfe9ac9f08e673d3f43e0996815cebf7a93f` |
| Independent Begin proof | `cef62fb4ef0ccda1fd18689072231834502b0d6dfd2b49d149ebab63ad537c7b` |

The comparison helped identify candidate changes; each finding used in the proof
was checked against the Japanese ROM. The fan translation's overall coverage is
still unverified.

The subsequent [storage audit and expansion proof](STORAGE.md) verifies relocating
a longer label into a 32 MiB ROM and checks native save-file persistence and cold
loading. The later [text-system inventory](TEXT_SYSTEMS.md) adds verified settings,
message, and event-text paths, including formatting controls and RAM output limits.
