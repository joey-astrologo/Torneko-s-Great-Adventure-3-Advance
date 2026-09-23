# Item message line-break follow-up

2026-09-23 audit snapshot; no translation, patch or published build changes
were made during this audit. The subsequently approved implementation is
documented in [ITEM_LINES.md](ITEM_LINES.md).
Examined `build/torneko-3-english.gba`, SHA-256
`67a15ab8f3bc6d1d56526383278c304b382c271b6f7997468010df7b800e9582`.

| Reported text | Source ID | Finding |
| --- | --- | --- |
| Name ate / item. | `gameplay.001b57ca` | Already approved for conditional joining; native item icons and colour controls trigger the fallback. |
| Item hit / name. | `gameplay.001b566f`, `gameplay.001b5686` | Both target variants already approved; same item-format fallback. |
| Name obtained / gold. | `world-completion.0086fb1c` | Separate world observation template, outside the combat audit's catalog scope; builder inserts the break conservatively. |

## Evidence

The first three source addresses are CPU `0x0900EF50`, `0x0900EDAC`,
and `0x0900EDBC`, read through existing owned ROM pointer words `0x22E68`,
`0x1A4E0`, and `0x1A4B4`. Their source templates deliberately retain LF;
the runtime hook joins approved spans only when it can measure them safely.

Controlled native mGBA calls on the current ROM generated Bread and Wooden
arrow names using the original item formatter at `0x08080A5C`, then supplied
those bytes to the actual message formatter. Plain ASCII substitutes joined;
native substitutes retained LF in all three templates. Bread starts with icon
`874b`, colour `030507`, then its name and reset `0306`. Arrow uses icon
`8744` and the same colour/reset. The generated arrow fixture has count zero;
this is a formatter diagnostic, not a natural arrow-hit replay.
Evidence: `build/item-line-audit/native-names.json` and
`build/item-line-audit/report.json` (source ROM hash included).

The previous tests substituted plain ASCII item names. The later companion
fix recognizes actor colour `030505` and reset `0306`, but does not recognize
item colour `030507` or measure item icons. Thus these are a testing and
runtime coverage gap, not intentionally excluded sentences.

World observation pointers `0x62E80` and `0x62F34` both currently point to CPU
`0x09068158`: `$t obtained\n%s!`. The catalog authors `$t obtained %s!` on
one line. `tools/build_merchants.py:encode`, reused by world completion,
estimates `%s` as a general item substitution: the complete template estimates
233px against a 208px limit, so it wraps before `%s`. For comparison, the plain
example `Torneko obtained 123 gold!` measures 127px. This source also serves
item acquisition: removing its break based only on short gold amounts would
not validate its other uses. No natural gold-pickup replay was performed in
this audit; the exact matching template and build-time cause are confirmed.

## Proposed follow-up

Measure verified native item icons and formatting controls in the conditional
joiner, preserving colour and existing width/byte/capacity fallbacks. Cover
native item variants throughout approved messages, including companion names,
instead of testing only these three examples. Separately trace the world
observation consumer and its intermediate formatted buffer before choosing
safe conditional wrapping for obtained gold/items; it uses `%s` formatting
and must not be assumed to share the combat queue's source-address contract.

Add regression cases using real item-formatted names and acquisition payloads.
This audit establishes no new allocation or approved free space; existing
pointer ownership remains authoritative in the component ledgers linked from
[the memory map](MEMORY_MAP.md).
