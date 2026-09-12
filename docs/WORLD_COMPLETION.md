# Remaining world messages

The 19-source component translates the remaining Zoom restrictions, four
item-pickup/capacity observations and two warehouse messages stored inline in
the game's initialized RAM data. All 21 pointer words have explicit owners;
[source spans](../build/completion/world-completion/source-owners.json) and
[memory-map discoveries](MEMORY_MAP.md) preceded insertion.

Zoom messages have a leading `-` or `*` protocol byte. The original caller
removes it and derives the speech flag before opening the paged window. Those
markers and all 13 selector outcomes are preserved. The two warehouse literals
now point to appended ROM text; their original RAM-backed strings and adjacent
startup data remain unchanged.

[Acceptance](../build/completion/world-completion/component-checkpoint.json)
covers 40 English cases, complete paged/world continuations, normal/wide name
substitutions and separate 99-byte item-name capacity checks, 13 native Zoom
selectors/marker handoffs, cold initialized sources and two original warehouse
literal readers. All Japanese control screenshot pairs match. The actual
paged wrapper supplies its original speech/continuation arguments; the item
observations use their own 256-byte printf and 1,024-byte world buffers.

The catalog reuses the established Zoom, Fortune-teller, Torneko, Chief and
sacred flame terms. Warehouse wording matches the earlier ally-services
translation. These controlled checks do not establish natural story gating,
actual item granting, warehouse operations or persistence.

```sh
.venv/bin/python -m tools.build_world_completion build
.venv/bin/python -m tools.verify_world_completion english
.venv/bin/python -m tools.verify_world_completion japanese
.venv/bin/python -m tools.verify_world_completion baseline
.venv/bin/python -m tools.summarize_world_completion
```

English ROM: [torneko3-world-completion-english.gba](../build/completion/world-completion/torneko3-world-completion-english.gba),
SHA256 `d15009ca598199febd4b0468638c161ad63574281abccb43f887ddd08ce25a7f`.
Japanese control SHA256:
`e0445271eab95cb749f75cb76feec6ee08cd928034a5c1fab264955c87d2acd2`.
