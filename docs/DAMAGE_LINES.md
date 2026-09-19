# Damage-message line joining

The 2026-09-19 fix joins ordinary `<actor> took <amount> damage.` and
`Dealt <amount> damage to <enemy>.` messages
only when their actual substituted text fits 208 pixels and the 59-byte history
payload. Long or non-ASCII cases retain their existing line breaks. Already
single-line messages need no change. Critical hit/brutal blow variants and window translucency are outside this change.

`tools.build_damage_lines` follows `build_arrival_layout` in the cumulative
build. It appends a replacement formatter wrapper, retaining the four existing
XP/level allowlisted sources and adding three ordinary received-damage sources
plus the ordinary `!` continuation source (with both entry addresses) and the
outgoing damage source. It
reuses the original formatter and existing font-width table. Only an LF is
replaced with a space; text, fonts, menu geometry and save layouts are unchanged.
Exact original-hook ownership is superseded through the shared ledger; see
[the memory map](MEMORY_MAP.md) and `build/damage-lines/allocation-plan.json`.

Reproduction:

```sh
.venv/bin/python -m tools.build_damage_lines --prepare
# Document/review any changed allocation span before insertion.
.venv/bin/python -m tools.build_damage_lines
.venv/bin/python -m tools.verify_damage_lines
./build.sh
```

Native mGBA validation passed 376 cases against each of the previous and fixed
ROMs. This includes substitution extremes, Japanese and oversized names,
short destination buffers, queue/history ring wrap and guard bytes. All selected
XP/level cases matched the previous build. Received/outgoing damage joining and fallback
were compared against measured expected output. Four ordinary damage sources
also passed native glyph rendering checks; screenshots are under
`build/damage-lines/verification/{baseline,english}/`. Acceptance hashes and
immutable user-save checks are in `build/damage-lines/acceptance.json`.

The controlled calls exercise native formatting, queue, history and rendering;
they do not claim a natural battle replay. Existing history rows stored in an
old save state retain their old breaks; newly generated messages use the fix.
