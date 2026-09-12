# Arena outcome text

The three remaining result labels are independently translated: `No winner`,
`... others` and the positioned winner/odds row. The native colour and position
controls, original row order and 200-byte formatting buffer are preserved.

[The checkpoint](../build/completion/arena-final/component-checkpoint.json)
accepts 205 English cases and 205 Japanese relocation/control pixel pairs:
every one of the 200 accepted actor names, four complete eight-row boards
covering both colours and odds limits, and the no-winner case. The boards use
seven wide characters as a custom-name stress case. Actual glyph ink stays
inside the window without overlap; actor slots and output guards are preserved.
Both complete ROM images reconstruct from their allocation/patch ledgers,
with all earlier patches and appended bytes unchanged.

The original odds generator clamps to 9,999 tenths, displayed as `999.9x`.
The row divides/modulos the stored value in its native instruction sequence;
the proof supplies accepted actor names at the original actor slot. It does
not exercise natural monster generation, battles or payout decisions.

Source ranges and literal owners are recorded in
[the memory map](MEMORY_MAP.md) and
[source ownership](../build/completion/arena-final/source-owners.json).
No save layout, permanent RAM or original graphic assets change.

Screenshot review also exposed a separate Japanese graphic heading. It is
drawn by `0805D070` from one-byte tile indexes at `000DC838`, rather than by
the string renderer. This component deliberately claims only the three text
resources; the indexed headings are now translated in [the following component](ARENA_GRAPHICS.md).

Rebuild and verify:

```sh
.venv/bin/python -m tools.build_arena_final build
.venv/bin/python -m tools.verify_arena_final english
.venv/bin/python -m tools.verify_arena_final japanese
.venv/bin/python -m tools.verify_arena_final baseline
.venv/bin/python -m tools.summarize_arena_final
```
