# Indexed arena headings and outcomes

Six phrases outside the ordinary text inventory now have English graphic
assets, generated from the pinned Japanese ROM's font 0. The original game
still draws them as indexed 16×16 cells; there is no new renderer or font.

| Original indexed graphic | English |
| --- | --- |
| 今回の勝利モンスター | Winning monsters |
| 今回の対戦結果 | Battle results |
| ポポロの仲間 | Tipper's allies |
| <<<勝利>>> | <<< Victory >>> |
| <<<敗北>>> | <<< Defeat >>> |
| <<<引分け>>> | <<< Draw >>> |

The first phrase names the **winners**, confirmed by the same 勝利 tile IDs
used in the victory banner. Tipper follows the accepted `enemy_tipper`
glossary identity. These translations are independent of the partial patch.

[The catalog](../translations/arena-graphics.json) preserves manual source
transcriptions, original index bytes, exact literal owners and editable
English. [The memory map](MEMORY_MAP.md) records the original atlas, palette,
six index sequences, eight patched pointer words and native window buffers.
The new atlas and sequences use the shared expansion allocator. Original
assets, source strings, code, palette and save layouts remain intact.

[The checkpoint](../build/completion/arena-graphics/component-checkpoint.json)
covers five native presentations: a full winner board, no winners, draw,
defeat and victory. Checks include the original palette loader, every index
and tile blit, exact whole-window buffer contents, original result-status
writes and five Japanese relocation/control pixel pairs. Earlier accepted
text is also rendered in the winner/no-winner boards. Both complete ROMs
reconstruct from their ledgers with all earlier patches/allocations preserved.

The actual window is 208×136 pixels. Each English phrase is centered inside
its original field, using unchanged glyph pixels and advances. All six fit.
The controlled fixture uses an early-world background; it does not prove
natural arena entry, palette fades during battle, outcomes or payouts.

These six translated resources are tracked **outside** the 9,318-entry
ordinary-string inventory. Finding and translating them improves discovery
coverage without inflating the ordinary-text completion percentage.

```sh
.venv/bin/python -m tools.build_arena_graphics build
.venv/bin/python -m tools.verify_arena_graphics english
.venv/bin/python -m tools.verify_arena_graphics japanese
.venv/bin/python -m tools.verify_arena_graphics baseline
.venv/bin/python -m tools.summarize_arena_graphics
```
