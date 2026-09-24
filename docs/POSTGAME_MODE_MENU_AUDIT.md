# Post-game mode-menu coverage gap

Initial 2026-09-23 audit below describes the pre-fix ROM. The subsequent
[reference-coverage repair](REFERENCE_COVERAGE.md) fixes all four menu pointers
and adds mandatory expected-English checks and the cold-boot replay.

The initial audit made no ROM changes. Reproduced from a cold boot with a disposable
copy of `saves/torneko-3-english-post-game.sav`, using joypad input only.
Source save SHA-256: `98489ca7e1286b83a189ec430f25e2f8b1008560ae52fd5241a2fe01fff5d7e8`.
ROM SHA-256: `d1a1c0fde27919fc3b3ab484d6c6b7cc4995cebc51166df8489b98136da90c80`.
The source save was checked unchanged after the replay.

Evidence: `build/postgame-menu-audit/replay/report.json` records the exact
inputs, native drawn payloads and pointer mappings;
`build/postgame-menu-audit/replay/postgame-mode-menu.png` shows the result.
The reproduced flow creates Adventure Log 2; the third entry on the subsequent
mode menu is Barinabo Challenge mode. The reported Japanese menu is confirmed
regardless of the log-number wording.

## Exact cause

The earlier curated catalog already translates four labels. Its verified
pointer owners cover the fresh-save table at ROM 00C4CDD8, but omit the second
table at ROM 00C4CD40. Both tables originally reference the same Japanese
strings. The post-game table still has four original Japanese pointers:

| Label | Translated table pointer | Unpatched pointer | Original Japanese source | Existing English target (CPU) |
| --- | --- | --- | --- | --- |
| Story mode | 00C4CDD8 | 00C4CD40 | [00C4CDC8,00C4CDD7) | 090000BC |
| Extra mode | 00C4CDE4 | 00C4CD4C | [00C4CDB4,00C4CDC5) | 0900007C |
| Help | 00C4CDFC | 00C4CD64 | [00C4CD90,00C4CD95) | 09000088 |
| Cancel | 00C4CE08 | 00C4CD70 | [00C4CD88,00C4CD8F) | 09000014 |

The table is ROM [00C4CD40,00C4CD88): five 12-byte entries and a terminator
record. Its third label pointer at 00C4CD58 is already translated to Barinabo
Challenge mode. The other four pointer words have no current patch owner.
The original source strings remain occupied; this establishes no free space.

`tools/build_frontend_completion.py:extract` uses a source-range/EXTRA allowlist
that does not include these four already-curated source strings. Its TYPED set
includes the third row but not the four duplicate label owners. The completion
pass therefore did not pick up the missing references. Master extraction lists
them as pointer candidates; they are not new strings or part of the unresolved
draft-message set.

## Why tests passed

`tools/verify_frontend_completion.py:menus` actually exercises this exact table
in two flag configurations. It verifies row count, unchanged flags/return
values, and rendering bounds. However, `verify_arena_services.check_draws`
decodes whatever text it receives, then compares the glyphs to that decoded
text. Japanese text can satisfy those checks. There is no independent expected
English-label assertion. The historical English screenshot
`build/completion/frontend/verification/english/menu-00c4cd40-1.png` already
shows these four Japanese rows: both test design and review missed the issue.

Natural post-game new-game transitions were separately listed as pending in
PLAYTEST_BACKLOG.md. That does not excuse the language assertion gap in the
controlled test that already reached the menu.

## Required correction

Point these four reviewed words to the existing independently authored English
labels, preserving their flags/return values and recording intentional shared
string references. Add exact expected labels for both mode-menu tables and a
cold-boot replay with the supplied post-game fixture to the publication gate.
The check must fail on this baseline. Review analogous curated strings with
multiple menu-pointer candidates for the same omitted-reference pattern.
