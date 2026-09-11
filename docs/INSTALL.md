# Installation on macOS

Prepared on 2026-09-09 for the Apple Silicon Mac used by this project.
See [TOOLING.md](TOOLING.md) for the agreed tool choices.

**Status:** The selected tools are installed. mGBA automation, Ghidra's GBA
import/disassembly, and armips passed setup checks. See [TOOLING.md](TOOLING.md)
for exact versions and results.

## Use the installed tools

From the project root:

```bash
source .venv/bin/activate
python -c 'import mgba.core, mgba.image; from PIL import Image; print("Ready")'
/opt/homebrew/bin/ghidraRun
# In a separate terminal, or after closing Ghidra:
open /Applications/mGBA.app
.tools/bin/armips  # Prints version and usage; exits with a usage status.
```

The remaining sections describe recreating this installation. Python 3.11 is
already configured for the project; no further Python setup is needed on this Mac.
For the first actual ROM change and its emulator checks, follow
[First working label](FIRST_LABEL.md).
The later [storage and expansion proof](STORAGE.md) uses the same installed tools.

## 1. Use the native toolchain

The initial inventory, before installation, found:

| Component | Observed state |
|---|---|
| Platform | macOS 15.7.9, arm64 |
| Xcode Command Line Tools | Installed at `/Library/Developer/CommandLineTools` |
| Apple Silicon Homebrew | Available at `/opt/homebrew/bin/brew` |
| Intel Homebrew | Also present at `/usr/local/bin/brew`, currently first on PATH |
| Python | System Python 3.9.6 is first on PATH; native Homebrew Python 3.13.7 is also installed |
| Build tools | Native CMake 4.1.1 and pkgconf 2.5.1 are installed |
| Java | `/usr/libexec/java_home` could not locate a runtime |
| Selected tools | Ghidra, armips, and mGBA were not found in the checked PATH/package locations |

Use the Apple Silicon Homebrew explicitly. Its native prefix is `/opt/homebrew`.
The Intel installation can coexist; these instructions do not change shell startup
files. [Homebrew installation documentation](https://docs.brew.sh/Installation)

Run the following in one terminal session, stopping to resolve any failed command:

```bash
cd /Users/joey/Documents/Workplace/torneko-3-gba
export TORNEKO_ROOT="$PWD"
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
uname -m
/opt/homebrew/bin/brew --prefix
```

Expected: `arm64` and `/opt/homebrew`. The later build commands assume this project
directory and shell session. `.tools/` will hold local source/build artifacts, and
`.venv/` will hold project Python packages. Keep those generated directories out of
version control when initializing the repository.

## 2. Install dependencies and create the Python environment

The working environment uses native Homebrew Python 3.11.15 in `.venv/`.
The existing Python installations remain available. The commands below describe
recreating the environment; it already exists on this Mac.

```bash
/opt/homebrew/bin/brew update
HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1 \
  /opt/homebrew/bin/brew install python@3.11 pkgconf libpng libzip libedit lua libffi
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r docs/python-toolchain.lock.txt
python -c 'import platform, sys; print(sys.executable); print(platform.machine())'
cmake --version
mkdir -p .tools/src .tools/build
```

Expected: the project `.venv` interpreter, `arm64`, and CMake 3.31.10.
`unittest` is part of Python and needs no separate installation. `pytest-runner`
is an upstream binding build dependency, not a change to our project test framework.

The package versions are recorded in [python-toolchain.lock.txt](python-toolchain.lock.txt).
CMake 3.31.10 accepts the older minimum CMake versions in the selected releases.
The mGBA build sets `CMP0148=OLD` explicitly to retain legacy Python discovery.
CMake is installed inside the virtual environment; the existing Homebrew CMake
remains available.
[mGBA binding setup](https://github.com/mgba-emu/mgba/blob/0.10.5/src/platform/python/setup.py),
[Python discovery policy](https://cmake.org/cmake/help/latest/policy/CMP0148.html)

## 3. Install Ghidra and its GBA loader

```bash
/opt/homebrew/bin/brew install ghidra gradle
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
"$JAVA_HOME/bin/java" -version
export GHIDRA_INSTALL_DIR="$(/opt/homebrew/bin/brew --prefix ghidra)/libexec"
```

Homebrew's current Ghidra formula supplies an OpenJDK 21 dependency and launchers.
The checked formula offers Ghidra 12.1.3; installing later may select a different
version. [Ghidra formula](https://formulae.brew.sh/formula/ghidra),
[installation layout](https://github.com/Homebrew/homebrew-core/blob/master/Formula/g/ghidra.rb)

Close Ghidra before installing its extension. Build the selected loader source
against the installed Ghidra:

```bash
git clone https://github.com/pudii/gba-ghidra-loader.git .tools/src/gba-ghidra-loader
git -C .tools/src/gba-ghidra-loader checkout 9bfb2d1fe891aa78bab7093a328feb3a52318ab7
git -C .tools/src/gba-ghidra-loader rev-parse HEAD
/opt/homebrew/bin/gradle --version
cat "$GHIDRA_INSTALL_DIR/Ghidra/application.properties"
bash tools/build_gba_loader.sh
```

The selected loader source needs the checked-in
[unused-import fix](../tools/patches/README.md) for current Ghidra. The helper
applies that patch automatically and keeps Gradle build caches under
`.tools/gradle-user/`. On future upgrades, check `application.gradle.min` and
`application.gradle.max` in Ghidra's properties and use a supported Gradle
distribution. [Gradle releases](https://gradle.org/releases/)

For a fresh installation, launch `/opt/homebrew/bin/ghidraRun`. In Ghidra's
project window, choose **File > Install Extensions**, use **+** to select the
built ZIP for the installed Ghidra version under
`.tools/src/gba-ghidra-loader/dist/`, then restart Ghidra. Importing a GBA ROM
should offer **GBA Loader**. Rebuild and reinstall the extension after a Ghidra
upgrade; extension archives are tied to the Ghidra version used to build them.

On this Mac, the built extension is already extracted into
`/opt/homebrew/opt/ghidra/libexec/Ghidra/Extensions/gba-ghidra-loader/`, making it
available to both the desktop launcher and the isolated headless verification.
Ghidra 12.1.3 with this patched loader passed the import/disassembly check.

The loader currently documents testing with Ghidra 12.0.2. Building against a
newer installation requires the import/disassembly check in step 7 before we
record that pair as verified.
[Loader instructions](https://github.com/pudii/gba-ghidra-loader),
[extension build configuration](https://github.com/pudii/gba-ghidra-loader/blob/main/build.gradle)

## 4. Install the mGBA desktop application

Download the macOS modern build from the [official downloads page](https://mgba.io/downloads.html)
and install `mGBA.app` in Applications. The release checked for this guide is
[0.10.5](https://github.com/mgba-emu/mgba/releases/tag/0.10.5). Start with the same
release as the Python source build below.

Launch the app and confirm its version in About. This supplies the interactive
emulator. Its installation does not install the Python package in our virtual
environment.

## 5. Build mGBA's upstream Python bindings

The tested build uses release `0.10.5` plus the checked-in
[optional e-Reader declaration fix](../tools/patches/README.md). It builds the
library and Python bindings with the GUI frontends disabled.
Python drives the emulator directly without a window. The separate
`mgba-headless` executable in newer upstream development code is not required
by this recipe and is not assumed available in this release.

After cloning the source, the maintained build command is
`bash tools/build_mgba.sh`. It applies the patch, configures the library, compiles
the bindings, and registers them in `.venv`. The equivalent steps are below.
Lua is disabled in this library build because this release's CMake discovery
does not handle Homebrew Lua 5.5; desktop mGBA still provides Lua scripting.

From the project root with `.venv` active, for a fresh checkout:

```bash
git clone --branch 0.10.5 --depth 1 https://github.com/mgba-emu/mgba.git .tools/src/mgba
git -C .tools/src/mgba rev-parse HEAD
git -C .tools/src/mgba apply "$TORNEKO_ROOT/tools/patches/mgba-0.10.5-optional-ereader.patch"
export PKG_CONFIG_PATH="/opt/homebrew/opt/libedit/lib/pkgconfig:/opt/homebrew/opt/libffi/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export TORNEKO_PYTHON_LIBRARY="/opt/homebrew/opt/python@3.11/Frameworks/Python.framework/Versions/3.11/Python"
test -f "$TORNEKO_PYTHON_LIBRARY"
cmake -S .tools/src/mgba -B .tools/build/mgba \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DCMAKE_POLICY_DEFAULT_CMP0148=OLD \
  '-DCMAKE_PREFIX_PATH=/opt/homebrew;/opt/homebrew/opt/libedit;/opt/homebrew/opt/libffi' \
  -DCMAKE_IGNORE_PREFIX_PATH=/usr/local \
  -DBUILD_PYTHON=ON \
  -DBUILD_SHARED=ON \
  -DBUILD_QT=OFF \
  -DBUILD_SDL=OFF \
  -DBUILD_GL=OFF \
  -DUSE_FFMPEG=OFF \
  -DUSE_DISCORD_RPC=OFF \
  -DUSE_DEBUGGERS=ON \
  -DUSE_GDB_STUB=ON \
  -DENABLE_SCRIPTING=ON \
  -DUSE_LUA=OFF \
  -DUSE_PYTHON_VERSION=3.11 \
  -DPYTHON_EXECUTABLE="$TORNEKO_ROOT/.venv/bin/python" \
  -DPYTHON_INCLUDE_DIR="$(python -c 'import sysconfig; print(sysconfig.get_path("include"))')" \
  -DPYTHON_LIBRARY="$TORNEKO_PYTHON_LIBRARY"
cmake --build .tools/build/mgba --target mgba-py --parallel 4
```

If the Python library check fails, locate the framework in the installed Python
3.11 package before configuring. Inspect CMake's summary for the intended Python
version, debugger support, and PNG support. A successful compile alone is not
emulator acceptance.

The upstream `mgba-py` target builds a Python package under the build tree. Register
that directory with this virtual environment using a `.pth` file:

```bash
python - <<'PY'
from pathlib import Path
import sysconfig

build = Path('.tools/build/mgba/python').resolve()
packages = [path for path in build.glob('lib*') if (path / 'mgba' / '__init__.py').is_file()]
if len(packages) != 1:
    raise SystemExit(f'Expected one built mgba package; found {packages}')
site_packages = Path(sysconfig.get_path('purelib'))
(site_packages / 'torneko-mgba.pth').write_text(str(packages[0]) + '\n')
print(packages[0])
PY
python -c 'import mgba.core, mgba.image; print(mgba.core.__file__)'
```

Expected: an import path inside `.tools/build/mgba/python/`. Keep the source and
build tree in place: the extension links to the built mGBA library. If the project
is moved, rebuild and regenerate this path registration. A dynamic-library error
needs investigation of that library path and architecture before proceeding.

This uses the actual upstream source rather than assuming that a package named
`mgba` on a package index is the required build.
[Release build options](https://github.com/mgba-emu/mgba/blob/0.10.5/CMakeLists.txt),
[binding build targets](https://github.com/mgba-emu/mgba/blob/0.10.5/src/platform/python/CMakeLists.txt)

## 6. Build armips

The verified assembler is upstream release `v0.11.0`. Rebuild locally with the
virtual environment's CMake 3.31.10:

```bash
git clone --branch v0.11.0 --depth 1 --recurse-submodules \
  https://github.com/Kingcom/armips.git .tools/src/armips
cmake -S .tools/src/armips -B .tools/build/armips \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_OSX_ARCHITECTURES=arm64
cmake --build .tools/build/armips --target armips-bin --parallel 4
.tools/build/armips/armips
git -C .tools/src/armips rev-parse HEAD
```

Invoking the executable without an input prints usage/version information and
may return a nonzero usage status. Future project build scripts can invoke this
local executable directly. The installed shortcut is `.tools/bin/armips`.
The initial build used the existing Homebrew CMake 4.1.1 with
`-DCMAKE_POLICY_VERSION_MINIMUM=3.5`; the virtual environment's CMake 3.31.10 also
accepts this release's older CMake configuration.
[Release](https://github.com/Kingcom/armips/releases/tag/v0.11.0),
[release build targets](https://github.com/Kingcom/armips/blob/v0.11.0/CMakeLists.txt)

## 7. Validate and record the working environment

The [emulator acceptance checks](TOOLING.md#emulator-automation-decision) passed
on the Japanese Torneko ROM. To rerun the check from the project root:

```bash
.venv/bin/python tools/verify_mgba.py \
  'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan).gba'
```

It uses a temporary ROM copy, checks an execution breakpoint and 8/16/32-bit RAM
access, boots 600 frames, and replays 63 frames twice around a state restore.
The comparison covers screen pixels, EWRAM, IWRAM, and frame count. Raw core state
and battery-save data are handled separately. Reports and screenshots are under
`.tools/validation/`; the original ROM hash is checked again afterward.

armips passed a byte comparison for ARM and Thumb instructions. To verify Ghidra
with the installed GBA loader:

```bash
bash tools/verify_ghidra.sh \
  'Dragon Quest Characters - Torneko no Daibouken 3 Advance - Fushigi no Dungeon (Japan).gba'
```

The helper imports into a temporary project under `build/toolchain-validation/`,
checks the ARMv4T language and GBA memory regions, and disassembles the cartridge
entry point. It checks the success marker in `.tools/validation/ghidra-import.log`
because Ghidra may log script errors without a failing process exit code.
Ghidra settings for this check stay under `.tools/ghidra-home/`; the check uses
an extension installed in Ghidra's application directory, as on this Mac.
For a user-installed extension, run the headless command with that user's
Ghidra settings instead:

```bash
TORNEKO_GHIDRA_USER_HOME="$HOME" bash tools/verify_ghidra.sh path/to/game.gba
```

Full ROM auto-analysis is outside this setup check.

Record the exact Ghidra/loader versions, mGBA GUI version and source commit,
armips commit, Python/package versions, build flags, and any patches in TOOLING.md.
`python -m pip freeze` can capture the Python dependencies once the environment
works. Because mGBA is exposed through a `.pth` file, its source commit and build
configuration must be recorded separately from the package list.

The intended workflow is: analyze in Ghidra, extract/build with Python and armips,
then verify in mGBA. These setup checks do not establish a text encoding, a
translation build, or coverage of gameplay routes.
