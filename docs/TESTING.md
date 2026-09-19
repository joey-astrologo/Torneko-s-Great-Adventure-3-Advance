# Testing and bug reports

## Playtest the current build

Run `./build.sh` and open `build/torneko-3-english.gba` in mGBA or Mesen.
The matching JSON receipt gives the build ID. Use disposable states for unusual
or destructive gameplay experiments.

For a bug, put the matching state/battery save in `saves/` and provide:

- The build ID, emulator and version.
- A screenshot and steps from the state to reproduce it.
- Expected behavior and what happened; a state just before the action is best.

Use native GBA emulator states. A Mesen-to-PyBoy converter for GB/GBC is not an
mGBA state converter. mGBA states are directly usable by this project's existing
automation. Old states can retain old window caches/history; close/reopen menus
and generate fresh messages when checking a rendering fix.

## Automated checks

`./build.sh` runs the mandatory native menu, combat and legacy damage/XP gates
against the candidate, plus four medal/casino and narrow-action checks, then verifies the BPS roundtrip before publication.
It does not run every historical component suite. Reports and hashes are linked
in `build/torneko-3-english.json`; see [BUILD.md](BUILD.md).

For a component build already prepared on disk:

```sh
.venv/bin/python -m tools.verify_combat_lines
.venv/bin/python -m tools.verify_damage_lines
```

These standalone commands default to their own component ROMs; the publisher
explicitly supplies the complete candidate to both suites. Historical tests
and screenshots establish coverage only for their recorded ROM hashes.
Additional changed systems need their own relevant checks.

## Mesen helpers

Stop a previous helper before starting another; both currently use **F8**.
Read the script's instructions and make a separate test state first.

| Helper | Action |
|---|---|
| [blank_scroll.lua](../tools/mesen/blank_scroll.lua) | Replaces first expendable bread/scroll with a Blank scroll; learned flags stay unchanged |
| [warp_pots.lua](../tools/mesen/warp_pots.lua) | Replaces first two eligible/empty slots with Warp pot[5] and identifies that type |

[Warp-pot instructions](WARP_POT_TEST.md) · [Blank-scroll rules](INSCRIPTIONS.md)

These helpers modify live RAM. Restore the original state to undo; saving in-game
can persist the changes. They do not insert any unverified draft messages.

## Coverage priorities

Start with [PROJECT_STATUS.md](PROJECT_STATUS.md) for current priorities and
[PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md) for detailed evidence. Later story,
postgame, dungeon suspend/resume and full ending playback remain valuable
coverage. Report discoveries with the exact build and context; successful
controlled displays do not establish every natural trigger or save outcome.
