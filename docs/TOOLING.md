# Tooling decisions

Decision date: 2026-09-09. Status: selected tools installed and setup checks passed.

The project will use **Ghidra, mGBA, armips, Python, and Pillow**. This carries over
the Shiren GB/GB2 approach of documented ROM analysis, reproducible translation
builds, scripted emulator routes, memory assertions, and screenshot comparisons.

| Responsibility | Selected tool | Intended use |
|---|---|---|
| Static ROM analysis | Ghidra with pudii's GBA loader | Identify and annotate code, pointers, text decoding, fonts, and menu routines. |
| Interactive debugging and playtesting | mGBA desktop application | Observe execution and investigate behavior in the running game. |
| Emulator test automation | Upstream mGBA Python bindings with a small project adapter | Control inputs and frames, inspect memory, restore fixtures, and capture rendered output. |
| Assembly patches | armips | Assemble ARM/Thumb hooks and enforce space limits on inserted code/data. |
| Extraction, builds, and tests | Python, Pillow, and standard-library unittest | Extract and encode text, process graphics, assemble reproducible ROM changes, and verify results. |
| Distributable translation patches | Floating IPS command-line tool | Create BPS patches for the expanded 32 MiB ROM and verify that applying them reproduces the build exactly; see [BUILD.md](BUILD.md). |

[Ghidra](https://github.com/NationalSecurityAgency/ghidra) provides disassembly and
decompilation for analysis. The [GBA loader](https://github.com/pudii/gba-ghidra-loader)
sets up the cartridge entry point and memory map. Its version must be compatible
with the installed Ghidra version. Decompiled pseudocode is an analysis aid;
the translation build will apply explicit patches to the base ROM.

[armips](https://github.com/Kingcom/armips) supplies the ARM/Thumb assembler and
binary-patching facilities. Python will coordinate the build and data validation.
Game-specific encoding, compression, pointer handling, and font formats remain to
be investigated beyond the [first verified menu-text path](FIRST_LABEL.md).
That proof establishes plain CP932-compatible menu strings, direct pointers, and
existing variable-width Latin glyphs for one early menu; it does not establish
all game resource formats.

The [storage audit and expansion proof](STORAGE.md) establishes a working 32 MiB
image for the tested menu path. Use appended space as the working approach for
relocated text, while verifying each additional reader. Original-ROM padding is
not yet approved for allocation. Existing font 0 is the selected English baseline.

The [text-system inventory](TEXT_SYSTEMS.md) extends that proof to settings,
substituted messages, and an event-script text operand. Extraction must preserve
raw control bytes and placeholder syntax; reinsertion needs both ROM allocation
checks and reader-specific bounds on formatted output in RAM.

The [Latin font review](FONTS.md) measures all 95 printable ASCII entries in the
three identified variants and verifies English samples in menus, messages, and
story text. The owner selected existing font 0 as the English baseline on
2026-09-09. Use its existing glyphs and advances; shorter text contexts still
need individual layout checks.

The [translation pipeline](TRANSLATION_PIPELINE.md) implements the first reusable
catalog and builder with shared appended storage, source preservation, control
and width checks, and native verification of 27 independently translated entries.
The [early-menu milestone](EARLY_MENUS.md) adds default-choice preservation and
creation/loading checks for both Adventure Log slots.

## ROM roles and translation source

The owner clarified the purpose of the two supplied ROMs:

- **Japanese original:** `Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan).gba`.
  Use this as the authoritative Japanese text source and the base for our translation build.
- **Fan translation reference:** `Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan) [T-En by Sam Steel v0.05] [i].gba`.
  The owner believes this translation is incomplete; its coverage has not been verified.
  Use it as a technical reference only. Do not copy or reuse its English text in
  our translation or use that English as the source for translating the game.

Comparing the ROMs and corresponding emulator scenes may help locate changes to
character encoding, fonts, text rendering, pointers, and menu layout. These are
investigation targets, not findings established by the filename or the presence
of English. Verify technical conclusions against the Japanese original and
translate from its Japanese text independently.

## Emulator automation decision

Use the [upstream mGBA bindings](https://github.com/mgba-emu/mgba/tree/0.10.5/src/platform/python)
directly, with project helpers around their API. Keep emulator-specific operations
inside that adapter so route tests remain readable and a backend change is manageable.

The bindings expose frame execution, button input, raw states, video buffers, and
GBA memory access. Installing the desktop application alone does not establish a
working Python environment. The verified source-build recipe is in [INSTALL.md](INSTALL.md).

The initial setup demonstrated the following on this Mac; retain these checks
when upgrading tools before building a large test suite:

- Load the base ROM and advance exact frame counts without a window.
- Press and release buttons on a recorded frame schedule.
- Read and write memory with the intended access widths and addresses.
- Capture frames and compare relevant screen regions using Pillow.
- Restore a state, replay the same inputs, and reproduce the checked memory and pixels.
- Demonstrate the execution hooks or breakpoint callbacks needed to replace the
  Shiren projects' use of PyBoy's `hook_register()`; basic frame stepping is insufficient.

The state format needs explicit attention: the Python API's raw states are not
automatically interchangeable with GUI state files. A fixture design must account
for battery saves and other state outside a raw CPU/core snapshot. Record ROM hash,
emulator version, BIOS configuration, initial save, and input schedule with fixtures.

If the Python bindings cannot meet these requirements reliably, the fallback is
[mGBA Lua scripting](https://mgba.io/docs/scripting.html), coordinated by Python.
That route must pass the same relevant acceptance checks. Execution tracing and
unattended operation are not assumed merely because scripting is available.

## Optional and deferred tools

- **luvdis:** optional if a buildable, matching assembly reconstruction becomes useful.
  Ghidra is the primary analysis tool. [luvdis](https://github.com/aarant/luvdis)
- **PyGBA:** optional wrapper, not an initial dependency. Its installation documentation
  flags packaging problems with its mGBA dependency. [PyGBA](https://github.com/dvruette/pygba)
- **BizHawk:** an alternative to revisit if needed; its macOS limitations make it
  less suitable for this workspace. [Platform support](https://github.com/TASEmulators/BizHawk#macos-legacy-bizhawk)
- **Additional compilers, graphics editors, and compression tools:** select when
  ROM findings establish a need.

## Verified environment

Verified on 2026-09-09, macOS arm64:

| Component | Working version / source |
|---|---|
| Python | Homebrew 3.11.15, native arm64, project `.venv` |
| mGBA desktop | 0.10.5, `/Applications/mGBA.app` |
| mGBA Python library | 0.10.5, commit `26b7884bc25a5933960f3cdcd98bac1ae14d42e2`, with the [build patch](../tools/patches/README.md) |
| armips | v0.11.0, commit `156f78f6bccfc07498578ac491ce7fe2a1e807a6` |
| CMake | 3.31.10 in `.venv`; mGBA builds retain legacy Python discovery with `CMP0148=OLD` |
| Python packages | [Exact package list](python-toolchain.lock.txt) |
| Ghidra | Homebrew 12.1.3, native arm64 distribution |
| GBA loader | Commit `9bfb2d1fe891aa78bab7093a328feb3a52318ab7`, built for Ghidra 12.1.3 with the [unused-import patch](../tools/patches/README.md) |
| Java / Gradle | OpenJDK 21.0.12.1 for Ghidra and extension builds; Gradle 9.7.1 |

The emulator smoke check passed on a 16,777,216-byte ROM with SHA-256
`35bfff00dccd8de1a916b316298219c8c16a8adb0162ffe5056c481e0a8a4d02`.
It reached the title screen after 600 frames, verified input press/release and
8/16/32-bit memory access, and fired a native debugger callback at `0x080000C0`.
Restoring a 397,312-byte raw core state plus 65,536 bytes of battery-save data
reproduced identical screen pixels, EWRAM, IWRAM, and frame count after a 63-frame
input replay. The original ROM was unchanged.

The high-level `NativeDebugger.set_breakpoint()` helper in this release has an
outdated signature. [verify_mgba.py](../tools/verify_mgba.py) demonstrates the
working CFFI debugger interface instead. Future project adapters should wrap that
interface and retain the callback objects for as long as they are registered.

The assembler produced the expected bytes `0100a0e31eff2fe102207047` for an ARM
`mov`/`bx` pair followed by a Thumb `mov`/`bx` pair. Generated evidence stays under
`.tools/validation/`.

Ghidra imported the same ROM using **GBA Loader** and `ARM:LE:32:v4t`, populated
the GBA RAM, I/O, palette, VRAM, OAM, and cartridge regions, and marked the
cartridge entry point. Its disassembler decoded `0x080000C0` as `mov r0,#0x12`.
This check did not run full ROM auto-analysis. The extension is installed at
`/opt/homebrew/opt/ghidra/libexec/Ghidra/Extensions/gba-ghidra-loader/` and must be
rebuilt and reinstalled when Ghidra is upgraded.

## Version policy

The verified versions above are the starting project pins. Record exact source
commits, package versions, build flags, and local patches when changing them.
Retain those versions while
creating fixtures; revalidate affected fixtures when upgrading the emulator.
