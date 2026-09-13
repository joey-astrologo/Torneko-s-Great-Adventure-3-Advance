# Resources intentionally retained

Some extracted strings are program data or language-neutral formatting. They
must be reviewed and preserved rather than assigned invented English text.
This review remains distinct from both translation progress and uncertain
extraction candidates.

The [retained-resource report](../build/completion/retained-resources.json)
currently records 823 resources (822 within the master inventory) with positive
reader evidence:

- 165 original compact-name filter terms, read by `0807D1A0`. They are compared
  internally and are not displayed dialogue. Their original policy is retained.
- The history-row printf format, which contains a row number, positioning,
  separator and a substituted name. Native Latin and kana display checks pass.
- 108 adventure-history lookup keys (107 within the master inventory). The
  separate displayed values have already been translated and verified.
- 31 tutorial lookup keys, likewise retained separately from displayed values.
- 101 result-cause lookup keys; all keys and both protagonist contexts were
  exercised by the accepted result/list component.
- 17 original ASCII church placeholders in the typed service table. These
  are positional values, not dictionary keys or newly authored English.
- Four original kana input grids and two compact character maps retained for
  Japanese name/password compatibility alongside the appended Latin input.
- The player-shop initial-cash field: the apparent `Pて` text is integer 50,000.
- 205 [native scene script command prefixes](SCENE_RESOURCE_AUDIT.md), plus
  one additional command prefix observed in the original opening route.
- Eight candidates contained wholly within those verified command operands.
- Four more numeric fields: item-format argument 200, ally command ID 100,
  keyboard X offset 170 and world-label Y coordinate 33.
- One trigger event command reached through native trigger indirection and
  bounded event activation/dispatch.
- One following event command, A7 at `00B9F024`, through a bounded native
  continuation after the preceding opcode-45 callback. The callback itself
  and natural temple event are not executed by that check.
- Eleven original ASCII startup values. Their initialized pointers are verified;
  later diagnostic/identifier consumers remain unconfirmed.
- 22 [auxiliary resources](AUXILIARY_RESOURCES.md): global commands and an
  operand, actor IDs, flag parameters, nickname digits and kana/default assets.
- 64 [neutral formats and original English diagnostics](AUXILIARY_RESOURCES.md),
  with reviewed native consumers and literal-resolution checks.
- 71 [background graphics candidates](SCENE_GRAPHICS_AUDIT.md), confirmed
  through native scene/header selection and guarded tile/index copies.
- Five [animation-resource candidates](RESOURCE_BOUNDARIES.md): three RGB
  values, one tile-pixel fragment and one decode crossing from metatiles into
  the following animated tile asset, all checked through native consumers.

All source bytes and the filter's pointer words match the original in the
accepted inventory-notice ROM. Exact source spans, reader evidence and the tested
ROM hash are recorded in the report and [memory map](MEMORY_MAP.md).

At this checkpoint, the 9,318-entry inventory has 8,422 authored English
entries, 822 confirmed retained entries and 74 entries still requiring
classification or translation. The final category includes more internal keys
and binary candidates; this report does not yet resolve them. Resources beyond
the extracted inventory and natural gameplay coverage remain separate.

Reproduce with `.venv/bin/python -m tools.audit_retained_resources`.
