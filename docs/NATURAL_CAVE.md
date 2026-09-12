# Natural village and first-cave regression

The remaining-display English checkpoint passes a recorded normal-button route from
the first chief meeting through Tessie's rest choice, the second-day chief
conversation, the cave-entry narration and the first tutorial cave. Torneko
picks up and equips a Copper sword and Wooden shield, fights two Slimes, and
uses the stairs to reach floor two.

[Verification report](../build/completion/dungeon-route/verification.json)
pins the ROM, source, catalogs, helpers, replay and the earlier naturally
reached checkpoint. The 157 inputs include the original exploration detours.
No coordinates, scenario flags, registers or RAM were edited after restoring
that checkpoint. All cartridge files belong to disposable emulator sessions.

The check verifies 27 story-message producer/formatter/reader chains, exact
English output and glyph placement; two complete paged tutorials; and 88
nonempty whole-string draws, including equipment, combat and stairs text.
There are no unattributed story reads. Watchpoints on the 31 unowned Japanese
source starts did not fire on this route. This does not establish that those
sources are unused elsewhere.

The original scrolling queue stages its fourth row at y38 below a 208×40
viewport. Those rows pass exact glyph and horizontal-bound checks plus an
observed native scroll completion at `0805D63C`. Other labels pass their
static ink bounds. The replay's final screen is pixel-identical to the
exploration screen. A first version of the new replay harness failed to
release buttons correctly; that harness defect was corrected before this
acceptance. No ROM patch was needed.

Reproduce with:

```sh
.venv/bin/python -c "from tools import verify_natural_cave as v; v.BASELINE = v.ROOT/'build/completion/remaining-display/torneko3-remaining-display-english.gba'; v.verify()"
```

[Replay inputs](../build/completion/dungeon-route/replay.json),
[full checked trace](../build/completion/dungeon-route/verification/trace.json),
[floor-two screenshot](../build/completion/dungeon-route/verification/final.png)
and the final state are retained. The ROM SHA256 is
`f0c51f1b3a4229964d23a2f0416bb854dafe1196799ce4ccea2302b211e7fb97`.

Later floors, shrine access, other dungeon branches and native suspend/save
persistence remain separate checks. The user's deferred graphics phase still
includes arrival cards and possible town/ending/credit art; this route does
not investigate or alter those assets.

The newer [text-polish build](TEXT_POLISH.md) preserves every earlier byte
except the separately checked floor-two Recovery pot tutorial pointer. Its
normal pot-use route starts from this naturally reached floor-two checkpoint.
