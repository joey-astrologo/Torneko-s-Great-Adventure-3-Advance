# Themed monster houses and companion commands

The [catalog](../translations/encounter-ui.json) adds 36 original resources
and corrects one previously translated house announcement. The build follows
[system labels](SYSTEM_LABELS.md), uses original font 0 and the shared append
allocator, and preserves original records, menu return values and source bytes.

Twenty themed house names and the generic fallback retain the original
30-byte name field. All 20 rows in both protagonist tables, plus both fallback
cases, pass the original selector/copy instructions, field-to-actor-slot copy,
message queue/history and visible announcement: 42 native cases.

The five companion menus provide Talk, Kaclang, Call allies, Warp somewhere,
Spells, Heal, Bang, Squelch and Cancel. Four menus have three rows; the spell
menu has four. All eight combinations of the three spell-availability bytes
retain their native enabled/disabled colours and return values: 12 menu cases.

The [checkpoint](../build/completion/encounter-ui/component-checkpoint.json)
records all 54 English cases and 54 Japanese control pixel pairs, reconstructs
both complete ROMs from their ledgers and verifies preserved original data.

House categories use independent project names. Swordmaster house denotes
the sword category, Warp house denotes teleporting species, and Standoff house
denotes species that keep their distance. The [Japanese category reference](https://wikiwiki.jp/dqdic3rd/【テーマ別モンスターハウス】)
was used to cross-check those distinctions; it is fan maintained and does not
establish official English names. Pip & Conk house uses the eight exact enemy
identities already in our modern glossary, cross-checked against the
[Japanese roster](https://peamon.net/toruneko3a/monster/theme-mh.html).
Kaclang, Heal, Bang and Squelch reuse existing glossary terms.

The announcement is now "It's a $m0!", adding the missing article for the room
name. Its original source already belonged to tutorial-gameplay. This build
explicitly supersedes that one four-byte pointer patch and preserves the whole
prior ledger record and allocated text. The Japanese control retains the
previous tutorial narration so comparisons isolate the new resources.
The [memory map](MEMORY_MAP.md) records this shared ownership explicitly.

Checks use restored emulator states and isolated original instruction slices.
The early-world fixture has no active dungeon structure, so only the specific
30-byte source field is supplied in documented scratch for its reader; the
temporary base is restored immediately. These checks do not establish natural
house generation, companion effects or spell execution. Those remain in the
[playtest backlog](PLAYTEST_BACKLOG.md).

```sh
.venv/bin/python -m tools.build_encounter_ui build
.venv/bin/python -m tools.verify_encounter_ui english
.venv/bin/python -m tools.verify_encounter_ui japanese
.venv/bin/python -m tools.verify_encounter_ui baseline
.venv/bin/python -m tools.summarize_encounter_ui
```
