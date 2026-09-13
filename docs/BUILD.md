# Build the latest English ROM

From the project folder, run:

```sh
./build.sh
```

The script uses the installed project Python environment automatically. The
equivalent command is `.venv/bin/python -m tools.build_english`.

| File | Purpose |
|---|---|
| [build/torneko-3-english.gba](../build/torneko-3-english.gba) | Latest successfully built English ROM; open this in mGBA. |
| [build/torneko-3-english.bps](../build/torneko-3-english.bps) | Translation patch for the pinned, unmodified Japanese original. |
| [build/torneko-3-english.json](../build/torneko-3-english.json) | Build ID, date, full source/output/patch hashes and validation results. Include this with bug reports. |
| [build/latest/english-build.json](../build/latest/english-build.json) | Detailed cumulative component report and allocation/patch ledger. |

Historical component ROMs, screenshots and verification reports remain in
their existing subfolders. The shortcut rebuilds the cumulative English image
from the Japanese original through the current component builder; it does not
select a ROM by its modification time or stack proof patches.

The current component is `tools.build_prose_review`. It includes the completed
[prose second pass](PROSE_REVIEW.md), with 410 editorial revisions, after the
accepted title and rendering work. The existing build uses
pinned prepared resources and previous component checkpoints under `build/`;
this convenience command does not yet bootstrap a completely deleted build
directory. See [prose review](PROSE_REVIEW.md), [title insertion](TITLE_INSERTION.md),
[rendering corrections](RENDERING_FIXES.md) and
[arrival insertion](ARRIVAL_INSERTION.md) for their resource preparation and
emulator checks. Future cumulative components should
update the `current` import in `tools/build_english.py`.

## Checks and patch format

Every run checks Japanese source bytes, cumulative allocations, patch ownership
and the existing component-specific encoding/layout constraints. It then creates
a BPS patch, applies it to an isolated copy of the Japanese original, and requires
the entire result to match the new English ROM byte for byte before updating
the convenient outputs. Builds are serialized with a lock; each output is
replaced atomically and the hash receipt is written last. A validation failure
leaves the previous convenient outputs in place. Cartridge saves are not opened
or modified by this command.

The ROM is 32 MiB and uses appended data beyond the ordinary IPS address range,
so its complete patch is **BPS**, with the correct `.bps` extension. BPS includes
source, target and patch checksums. [Floating IPS](https://github.com/Sir-Walrus/Flips)
creates and applies the patch using its linear BPS encoder. Its executable hash
and reported version are included in the build receipt.

This command does not run emulator routes. Its receipt distinguishes build and
patch checks from gameplay verification. When the output hash matches an
existing verified component ROM, that component's documented runtime evidence
applies to the same bytes; changes still require appropriate runtime checks.

To apply the patch locally to the Japanese original:

```sh
.tools/bin/flips --apply build/torneko-3-english.bps \
  'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan).gba' \
  /tmp/torneko-3-patched.gba
```

Do not apply it to the partial fan translation or an earlier English build.

## Patch-tool installation

The project-local Floating IPS command-line executable is `.tools/bin/flips`.
Installed source revision:
`ff216a75df0987047a67d7923567dc4482ce07ac`.
All 106 downloaded source files were checked against the upstream Git tree;
the optional profiling archives are excluded. The source-file hashes, compiler
command and installed binary hash are in
[tools/flips-toolchain.json](../tools/flips-toolchain.json).

To recreate the CLI tool on a clean installation with Xcode Command Line Tools:

```sh
git clone --depth 1 --filter=blob:none --sparse --no-checkout \
  https://github.com/Sir-Walrus/Flips.git .tools/src/flips-local
git -C .tools/src/flips-local fetch --depth 1 origin \
  ff216a75df0987047a67d7923567dc4482ce07ac
git -C .tools/src/flips-local sparse-checkout set libdivsufsort-2.0.1
git -C .tools/src/flips-local checkout --detach \
  ff216a75df0987047a67d7923567dc4482ce07ac
make -C .tools/src/flips-local TARGET=cli CFLAGS=-O2 CXX=clang++ COMMIT_COUNT=
mkdir -p .tools/bin
install -m 755 .tools/src/flips-local/flips .tools/bin/flips
```

The sparse checkout includes root source files and the bundled suffix-sort
library without downloading the large optional profiling archives. Compilation
does not require GTK or a system-wide installation. Executable hashes can
differ with the compiler/toolchain; each build receipt records the actual one.

## Current title-build acceptance (2026-09-13)

`./build.sh` reproduces the accepted English title ROM, SHA256
`b80feb1177c9111f44edb1b0ffc8a63c89d94b7d4eccc9f383bc9b372d7b14a9`.
Its 905,830-byte BPS passes the complete apply/rebuild comparison. The
[title insertion report](TITLE_INSERTION.md) records native pixels, palette,
fade, prompt blink and following-menu checks. All earlier components remain
included in the same cumulative build.

## Earlier rendering-fix acceptance (2026-09-13)

The preceding component's accepted ROM is SHA256
`fd0c0dd97ffd205bcc4ba71711c76edcc6f33dad912731d7d9d629188414ace8`.
It corrects keyboard hint clipping, Records menu geometry, town/dungeon status
panel overlap and unnecessary numeric line breaks in XP/level messages.
See [the paired screenshots and runtime coverage](RENDERING_FIXES.md).
At that checkpoint `./build.sh` reproduced those ROM bytes. Its 882,167-byte BPS passed
the complete apply/rebuild comparison, and all published receipt hashes match.

## Initial convenience-build acceptance (2026-09-13)

`./build.sh` rebuilt the accepted arrival-card ROM byte-identically:
SHA256 `08239b255025e6e2627ec0184eb829cb453dc30b0aa7a518e7e8714fc678f2c6`.
The BPS is 881,404 bytes and its complete apply/rebuild comparison passes.
An isolated incorrect-source check is rejected by Floating IPS's checksum
validation. The wrapper also resolves its project directory correctly when
invoked from another folder. Every file hash in the published receipt matches.
This is build/packaging work; the matching ROM retains the existing documented
runtime coverage.
