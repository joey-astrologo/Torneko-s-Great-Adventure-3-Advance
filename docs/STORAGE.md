# ROM storage audit and expansion proof

Verified on 2026-09-09. **The 16 MiB Japanese ROM can be expanded to 32 MiB for
the menu-text path tested here.** The game reads a relocated string from the
appended region, renders it correctly, creates an adventure-log save, and loads
that save in a fresh emulator session. The original and expanded builds produce
identical save bytes on the recorded route.

The current proof displays our own **Start adventure** label. Its 16 bytes
including NUL exceed the original label's 12-byte allocation. The original label
is preserved; only its four-byte pointer is changed in the original ROM region.
The proof uses the original font; the fan translation is not a build input.

## Budget and working storage strategy

| Region or allocation | Bytes | Treatment |
|---|---:|---|
| Original ROM, offsets `0x00000000..0x00FFFFFF` | 16,777,216 | Preserve existing contents, except explicit reviewed patches |
| Appended region, offsets `0x01000000..0x01FFFFFF` | 16,777,216 | Working budget for new project allocations |
| Current proof string, starting at `0x01000000` | 16 | Allocated |
| Remaining appended capacity in this proof | 16,777,200 | Unallocated |
| Original-ROM space approved for reuse | 0 | No old padding or zero-filled regions have been approved for allocation |

Zero approved bytes inside the original means **unverified**, not that the
original has no spare space. The appended region avoids needing to reclaim those
areas for this proof. Use it as the working approach for future relocated text,
and verify each additional text reader before applying that approach broadly.
Keep an allocation ledger as new strings, tables, or fonts are added.

The [central memory map](MEMORY_MAP.md) now indexes discovered ranges, current
build ledgers and RAM/save reservations. Record new findings there before using
them for insertion, and check all components' allocations and patches together.

Standard GBA cartridge ROM addressing covers 32 MiB at `0x08000000..0x09FFFFFF`.
This expansion stays within that range and needs no GB/GBC-style MBC conversion.
The other cartridge views mirror the same ROM at different wait-state settings;
they do not provide additional capacity.
[GBATEK memory map](https://rust-console.github.io/gbatek-gbaonly/#gba-memory-map)

This budget does not yet estimate the complete English script: full text
extraction, compression analysis, and other pointer formats remain future work.

## Existing-ROM findings

[audit_rom_storage.py](../tools/audit_rom_storage.py) records byte-pattern runs,
256 KiB block statistics, known code/text/font locations, save-library markers,
and pointer-like words. It does not label an entire unidentified region as free.

| Candidate region | Size | Evidence and interpretation |
|---|---:|---|
| `0x00FD7AF4..0x00FFFFFF` | 165,132 bytes (about 161 KiB) | Contiguous trailing `FF`; promising padding candidate, not approved for reuse |
| `0x00CF3B44..0x00CFFFFF` | 50,364 bytes | Contiguous `FF` before the next MiB boundary; also unverified |
| Five smaller `FF` runs | 2,169 bytes total | Inside content-bearing regions; not counted as free |
| Zero runs of at least 256 bytes | 419,027 bytes total | Not counted as free; some contain targets of structured tables |

All seven `FF` runs of at least 256 bytes total 217,665 bytes. These figures
describe patterns, not a verified free-space total. In particular, the
zero-filled region `0x00CB1B64..0x00CB4E9B` contains addresses referenced by
12-byte, glyph-descriptor-shaped records starting at `0x00CC1B94`. The first
record points to `0x08CB1BA0`. Other large zero runs are similarly referenced by
pointer tables. Overwriting every run of zero bytes would therefore be an
unsound allocation strategy.

The broad pointer scan also finds graphics/compressed-data values that resemble
addresses. Its candidate counts are not confirmed references, and absence from
that scan would not rule out computed or relative references. The JSON report
keeps that distinction explicit.

The original includes `FLASH512_V131` markers at offsets `0x00CAF678`,
`0x00CE0C9C`, and `0x00CEDFF0`. Runtime inspection confirms mGBA's FLASH512 mode
and a 65,536-byte cartridge save.

## Expansion and relocation checks

The builder extends the image with `FF` bytes and changes the pointer at ROM
offset `0x00C78280` from `0x08C782D8` to `0x09000000`.

| Test variant | ROM size | Text address | Result |
|---|---:|---|---|
| Original Japanese baseline | 16 MiB | `0x08C782D8` | Baseline |
| Unchanged Japanese label relocated | 32 MiB | `0x09000000` | Menu pixels identical to baseline |
| Longer English proof label | 32 MiB | `0x09000000` | Correct glyphs; changes confined to the label |
| Same English label near the ROM limit | 32 MiB | `0x09FFFFC0` | Menu pixels identical to the other English variant |

The last location is 64 bytes below the 32 MiB boundary. Both expanded locations
were observed through the game's character decoder at instruction `0x0808C732`,
not only by reading memory from Python. Glyph callbacks verify the actual
character sequence. Direct reads additionally verify all three cartridge views.
The original `はじめから` bytes at `0x00C782D8` remain intact in the expanded ROM.

Each variant also repeats the title-to-menu route after restoring a raw core
state plus battery data. Pixels, EWRAM, IWRAM, frame count, and rendering traces
match within that variant. This establishes a representative relocation path;
it does not prove that every resource loader accepts all expanded addresses.

## Actual cartridge saving and cold loading

The verifier opens a native `.sav` file in a temporary cartridge directory.
It uses normal controller input to create slot 1, accept the default **セーブ1**
name, choose scenario mode, and confirm creation. The game changes 25,411 bytes
relative to its pre-creation save. After destroying the emulator core, the save
file on disk matches the captured FLASH contents exactly.

The same route on the original and expanded English builds produces the same
65,536 bytes, with SHA-256:

```text
95c6de6afe5d64e21de61b72c8ab3e1c67ca7649ad5a87d1c8b9db87c47feef0
```

A new emulator instance then boots each ROM with that `.sav` file, selects
Continue and slot 1, acknowledges the load notification, and reaches the opening
story. The final pixels match the visually reviewed fixture. The expanded
build's save also loads in the original ROM. The relocation proof therefore
includes actual game save-file persistence and cold loading, separately from
the emulator save-state replay check.

Generated `creation.json` and `reload.json` files record the exact input timing.
The new-adventure write completes before the capture at frame 2436; the
cold-load story capture is at frame 2292 of the new session.

## Reproduce and inspect

From the project root:

```bash
.venv/bin/python -m tools.audit_rom_storage
.venv/bin/python -m tools.build_expansion_probe
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tools.verify_expansion
open -a /Applications/mGBA.app build/storage-audit/torneko3-expansion-32m.gba
```

All tools default to the known Japanese filename and require its pinned hash.
They accept an explicit source ROM as the first argument and `--output` for the
generated directory. Both supplied source ROMs remain intact.

| Artifact under `build/storage-audit/` | Contents |
|---|---|
| `torneko3-expansion-32m.gba` | Playable 32 MiB proof; press Start to see the label |
| `storage-audit.json`, `uniform-regions.json` | Layout checkpoints, byte-pattern candidates, and statistics |
| `expansion-build.json` | Allocation and source/output hashes |
| `expansion-verification.json` | Combined pass results and tested scope |
| `original/`, `expanded-japanese/`, `expanded-english/`, `expanded-limit/` | Screenshots and title read/glyph traces |
| `original/created.sav`, `expanded-english/created.sav` | Real adventure-log saves created by the game |
| `original/cold-reload/`, `expanded-english/cold-reload/` | Cold-boot loading evidence |
| `cross-load-original/` | Original ROM loading the expanded build's save |

The expanded ROM SHA-256 is:

```text
ba60e807aadfe9b903dadd70decf1e6671a26c538096e5edf1eb3251470e1cc1
```

The 14 unit tests cover both proofs, including wrong-base rejection, preservation
of existing data, exact-end placement, overflow rejection, alignment, and
uniform-run boundaries. Emulator checks are run by the verifier separately.
The earlier first-label verifier also passed again after its trace helper was
extended to accept relocated addresses.

This milestone generates a ROM through the reproducible builder. The older
first-label IPS file still applies only to that older, in-place proof.

## Coverage and next work

Verified with the installed mGBA 0.10.5 build and built-in BIOS. No physical
cartridge/flashcart test or complete game playthrough was performed. Dungeon
progress saving, later dialogue, other fonts and text formats, compressed
resources, and unusual computed pointers need separate checks.

The immediate storage question has a positive result: appended ROM space works
for the tested text and save/load route. The subsequent
[text-system inventory](TEXT_SYSTEMS.md) verifies three more relocated sources
through settings, message, and event readers, and records their RAM output limits.
The subsequent [font review](FONTS.md) established existing font 0 as the chosen
English baseline. Complete text coverage remains future work.

The [translation pipeline](TRANSLATION_PIPELINE.md) now owns a shared allocator
for the 27-entry [early-menu batch](EARLY_MENUS.md). It uses 785 appended bytes
including alignment, leaving 16,776,431 bytes. Its Japanese round trip, native
English rendering, creation/loading in both slots, and slot-1 cross-loading pass;
this is a measured small batch,
not an estimate of the eventual full translation size.

The [broad extraction](TEXT_EXTRACTION.md) now measures 413,278 source bytes
across 9,272 entries and candidates. A planning scenario with four times those
bytes plus three alignment bytes per entry would occupy 1,680,928 appended
bytes (1.60 MiB), leaving 15,096,288 bytes (14.40 MiB) from the extra 16 MiB.
This excludes other code/assets and allocations in the existing proof builds;
it is not a finished-English estimate or proof of complete extraction. It does
provide substantial storage headroom for the text found so far. Reader RAM and
screen-width budgets remain separate constraints.
