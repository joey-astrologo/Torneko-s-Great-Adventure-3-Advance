# Medal-trading action label

Approved 2026-09-19 following the [menu action audit](MENU_ACTION_AUDIT.md).
The Medal King's action now reads **Trade**, matching the casino. Exchange
needed 42px in a 36px text region; Trade needs 28px, leaving 8px spare.
Other action labels and all window sizes remain unchanged.

The cumulative `tools.build_medal_trade` component appends six bytes and
supersedes only the owned medal label pointer at ROM `00063A3C`. It preserves
all earlier code/data allocations, including the old Exchange payload. See
[MEMORY_MAP.md](MEMORY_MAP.md#medal-trade-insertion-2026-09-19) and the
[allocation plan](../build/medal-trade/allocation-plan.json).

Every `./build.sh` runs four additional native mGBA checks against its candidate:

- Medal caller resolves to Trade; the native popup draws Trade and Info fully.
- Casino caller still resolves to Trade and fits the same popup.
- Take out fits the narrow secondary menu with its 4px inset.
- Withdraw fits that same secondary menu.

These execute bounded native readers in disposable states; they do not claim
natural medal transaction playback. The earlier seven gameplay menu routes and
combat/damage suites still run. The publisher records the new report and its
hash, and publishes only after all checks and the BPS roundtrip pass.

The pre-fix combat-lines ROM is rejected with `medal action is not Trade`.
A byte comparison confirms that only the four-byte pointer field and six-byte
new label allocation can differ from that baseline.

[Native report](../build/medal-trade/verification/report.json) ·
[Medal popup](../build/medal-trade/verification/medal.png)

The accepted component ROM SHA-256 is
`e1f2babeb6b06ffdc9f52c4c190859a1f8e6712688dc7d3465736fbb55cc032e`.
The latest publication receipt remains `build/torneko-3-english.json`.

```sh
.venv/bin/python -m tools.build_medal_trade --prepare
# Document changed ranges before insertion.
.venv/bin/python -m tools.build_medal_trade
.venv/bin/python -m tools.verify_medal_trade
./build.sh
```

When testing from an older state, exit and re-enter the trading conversation
so the game reloads the label pointer instead of using the cached old label.
