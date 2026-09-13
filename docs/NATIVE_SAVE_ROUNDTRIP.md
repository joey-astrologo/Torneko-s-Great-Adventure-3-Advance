# Natural dungeon result, save and cold reload

The later [successful cave-clear roundtrip](CAVE_CLEAR.md) supplements this
defeat route with all three floors, the following shrine/party story, native
saving and cold loading of the earned clear record on the same ROM.

The inventory-notice ROM passes a full **first-floor defeat → village priest
save → fresh emulator → earned records → saved village** route. Both Adventure
Logs retain the seven-letter name Torneko. This adds real persistence evidence
to the earlier controlled ranking and name tests.

[Acceptance report](../build/completion/roundtrip/component-checkpoint.json),
ROM SHA256 `8757bf5cd89e6b935c8f99c431600eb6b5367ad9e9078158a84c047cf6d6e960`.
The harness creates both logs through the native keyboard, follows the normal
46-message opening, and records its own chief-meeting checkpoint. From there,
184 recorded button inputs reach a first-floor She-slime defeat, return to
Barinabo Village, select Pray/save, stop playing and return to the title.
No HP, inventory, coordinates, event flags, names or score records are injected.

Fresh named logs produce a different dungeon layout from the earlier Japanese-log
[first-cave fixture](NATURAL_CAVE.md). Replaying historical exploration inputs
therefore does **not** establish a cave clear or a floor-two visit on this route.
The actual earned result is Mysterious cave 1F, defeated by She-slime, score 1.

The natural result animation passes all 17 steps and 459 map cells per step.
The adventure trace verifies 28 story messages, 13 paged messages and 89 distinct
whole-string draws. Native name-copy and profile-write observers confirm the
save writes the complete name and the naturally earned record. Closing the
emulator produces the exact native 65,536-byte cartridge save.

The cold test starts a new core from that save, navigates Records, the score
list/detail and Adventure history, then loads Log 1 back into the saved village.
Its 37 whole-string draws include the full name, village summary and earned
result. The 8,108-byte profile matches the saved bytes; all 459 detail-map cells
and 2,135 white text pixels match the actual screen. An independent cold load
of untouched Log 2 still reaches the opening with Torneko intact. Merely viewing
these records and loading either log does not modify the cartridge save.

Initial save SHA256:
`b5759e17e26e938785ad527086f186dc20e781b1b9fa3bbe50d2813944eadbbd`.
Final save SHA256:
`a1f72b38a89ea47ab466a31fdf0048468a20c0480d98dc79d6b0a53452b2f8f1`.
The popup correction preserves the preceding build's complete final save.
Disposable saves, traces, screenshots and final states are in
`build/completion/roundtrip/verification/`; the report pins the trace hashes.

```sh
.venv/bin/python -m tools.verify_roundtrip
```

The frozen harness is `build/completion/roundtrip/verify_roundtrip.py`.
The replay is pinned by hash in the adventure trace. Thirty-one unresolved
Japanese source watchpoints have no hits on this adventure; this does not prove
those sources unused. Dungeon clearing, suspend/resume, later outcomes,
alternate branches and broader discovery remain in [PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).
Graphics work remains deferred and the original Japanese title artwork stays.
