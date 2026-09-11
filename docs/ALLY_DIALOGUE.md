# Ally dialogue and message-history reflow

Historical checkpoint. The current [complete companion-dialogue build](COMPANION_DIALOGUE.md)
adds the remaining 1,224 main-table entries and three conditional Rosa alternatives,
preserving this milestone's payloads and history fixes. The counts and hashes below
describe this earlier 400-entry build.

Completed 2026-09-11. Open
[torneko3-ally-dialogue-english.gba](../build/ally-dialogue/torneko3-ally-dialogue-english.gba)
in mGBA. This combined build adds **400 translated dialogue entries**: all eight
responses for ordinary ally species rows 1–50, from Drooling ghoul through
Batmandrill. It retains every earlier translation component and the
seven-character Adventure Log name with default **Torneko**.

It also reflows **16 earlier messages** so their full text fits message history.
Their words, catalog English and allocation addresses are unchanged. All **311
earlier core/help message templates** now pass native history stress checks.

The [dialogue catalog](../translations/ally-dialogue.json) is the insertion
authority. The [terminology review](../translations/ally-dialogue-terminology-review.tsv)
covers all 400 entries; the [history review](../translations/ally-dialogue-history-review.tsv)
records the 16 old/new layouts. The [preview](../build/ally-dialogue/preview.png)
shows controlled native screenshots. The searchable
[text catalog](../build/text-extraction/index.html) overlays this English while
preserving master drafts and notes.

## Dialogue scope and language

| Response fields | Ordinary ally context | Evidence |
|---|---|---|
| 0, 1 | Healthy | Original HP/choice selector and Japanese dialogue |
| 2, 3 | Hurt | Original HP/choice selector and Japanese dialogue |
| 4, 5 | Critically hurt | Original HP/choice selector and Japanese dialogue |
| 6, 7 | Level up | Two original callers select `random(2)+6`, then enter the shared dialogue reader |

The health selector compares current HP with `floor(maxHP*8/10)` and
`floor(maxHP*4/10)`, then picks one response in the corresponding pair. Some
monsters have special ability branches after this selection; the fixtures do
not establish every natural conversation branch.

Every species receives its complete eight-response set. Different voices,
jokes, growls, repeated words and speech quirks come from the pinned Japanese
source. All dialogue keeps its full authored wording with **no display
abbreviations**. Existing font 0 and measured wrapping fit every new English
entry on **one three-line, 208px native page**, including the wide-name profile.
`$m0` is retained throughout, as is Troll's additional `$m1` self-introduction.
Japanese `$x` indentation is replaced by measured English line breaks.

The existing **1,085-term glossary** is retained, including its evidence quality
and source URLs. Speaker species references provide context; actual `$m0` can
contain a nickname. Heal, Fullheal, Kaclang, Walking corpse and Pazuzu use their
reviewed names. Iron arrow remains an explicit project item-name choice.

Three adaptations are recorded explicitly:

- Great troll's Japanese jokes about its “King” name become boasts about being
  “Great”, retaining the reviewed modern species identity.
- She-slime retains its localized species name; the Japanese first-person
  pronoun is not treated as a separate claim about gender.
- Loathsome leek calls itself an onion monster in Japanese. The line keeps
  that meaning. Cureslime's enthusiastic healing boast also stays unquantified;
  it does not add a full-HP guarantee from the name Fullheal.

No English, font assets or descriptions are borrowed from the partial fan ROM.
There are **1,224 remaining extracted ally-dialogue entries** outside this
400-entry scope. Default nicknames are a separate table with **198 distinct
strings** and remain Japanese; this pass does not change custom-name limits.

## History correction and ownership

The previous milestone established that each 64-byte history record has only
**59 payload bytes**, even though the live message queue allows 80 bytes per
row. Sixteen older core/help templates could exceed that smaller bound with
valid synthetic narrow item names. The old ROM reproduces native truncation
for each of those 16 under that stress input. This is not a claim that those
generated names occur naturally during play.

The combined builder supplies an optional layout callback to the original
core/help components. It reflows whitespace only when the old layout exceeds
the history bound; their original components still own both allocation and
pointer patches. Each revised payload has the **same byte length** as before.
All earlier allocation addresses and original patches remain exact; the only
earlier payload revisions are these 16 documented strings. Historical builders
keep their default layout and reproduce their recorded ROMs.

[MEMORY_MAP.md](MEMORY_MAP.md#ally-dialogue-and-history-reflow-2026-09-11)
records the discovered ranges before insertion. The existing table is
200 records of 80 bytes at `[001A60B0,001A9F30)`. This component owns only the
first eight pointer words of rows 1–50. All other fields, source strings,
null entries and intervening padding remain occupied and preserved. New text
uses the shared append allocator; the
[combined ledger](../build/ally-dialogue/english-build.json) is authoritative.

| Combined English build | Value |
|---|---:|
| ROM size | 32 MiB |
| Total appended bytes including alignment | 106,173 |
| Added in this milestone | 22,697 |
| Appended capacity remaining | 16,671,043 |
| Allocations / checked original patch ranges | 2,859 / 3,267 |

The occupied append interval is `[01000000,01019EBD)`; this component starts
at the previous end `01014614`. There is no font, permanent RAM, actor-record
or save-layout change. The 64 KiB cartridge save remains the same size.

- English SHA-256: `e742ceb7e7f1c237f6f8825d738e03da6df7c270b3a612d3e238c1cfbe6cf0e5`
- Japanese dialogue relocation control: `d896704a9f793328846281d3f279436647b5e449f654d4634c391d1e65252fb6`
- Previous English baseline: `66c53aa470d31c73e093f5c053ea38e525ea8c47d8070266be4595626c270f24`

Both new builds apply the history reflow; only the new dialogue language
differs. The Japanese control is compared with the previous ROM's original
Japanese ally dialogue, with identical fixture state and supplied speaker names.

## Automated acceptance and limits

[acceptance.json](../build/ally-dialogue/acceptance.json) pins ROM, catalog,
harness, fixture and review hashes. It records:

- **141 passing unit tests**, deterministic English/Japanese rebuilds, collision
  checks, prior catalog preservation, and all **9,318 master sources** rebuilding
  byte-for-byte to the pinned original.
- **1,200 English dialogue cases**: normal, wide-name and narrow-name profiles
  for all 400 sources. These execute the original table selector and guarded
  formatter. Normal/wide profiles also check every native glyph, yielding
  **800 dialogue screenshots**. All 400 Japanese/baseline screen pairs match
  exactly.
- **400 native HP/choice boundary cases per variant**: each of the 50 species
  at HP 39, 40, 79 and 80 of 100, with controlled random results 0 and 99.
  Four unchanged initialized pointer tables are checked from cold boot in each
  variant and restored into the older disposable state.
- **933 earlier-message history cases**: all 311 templates in three substitution
  profiles. Every live row is retained exactly in history, with guards intact.
  The changed 16 have **32 native display screenshots** in addition to the
  before-ROM truncation reproductions. English screenshots total **832**.
- Prior-component regressions: **400 enemy-name copy guards**, both protagonist
  copies, 14 secondary menus, two normal-button ground searches, 14 item screens,
  four protagonist detail screens and **Torneko creation/save/cold-load** with a
  **65,536-byte** save.

The dialogue fixture enters the original species/response selector, then runs
the paged engine with the ally caller's `(0,1,1)` stack flags. It supplies speaker
slots and a disposable actor record, bypassing frame yields, glyph delays and
input waits. The opening-world state has no valid dungeon structure, so it
does not run the whole ally wrapper or its nickname-copy helpers. The health
fixture executes the original threshold branches but controls the random return.
Level-up caller disassembly establishes the response indices; it is not a
natural level-transition test.

History tests use the previously documented guarded disposable backing,
stopping before the unrelated scheduler. Natural recruitment, conversations,
special abilities, nickname copying, message timing/history navigation, and
ranking/save persistence remain in [PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).
Personal playtesting can stay deferred.

## Reproduce and continue

```bash
.venv/bin/python -m tools.build_ally_dialogue
.venv/bin/python -m tools.verify_ally_dialogue_all
```

Audit existing native artifacts without rerunning them:

```bash
.venv/bin/python -m tools.verify_ally_dialogue_all --summarize-only
```

Edit catalog English/notes; source and pointer fields are checked against fresh
Japanese extraction. Refresh the terminology review after language edits and
before accepting another ROM. The recorded review script is
`build/ally-dialogue/research/record-review.py` (run with `PYTHONPATH=.`).
The next dialogue milestone can cover the remaining ordinary species sets,
with special NPC records and their different response rules handled explicitly.
