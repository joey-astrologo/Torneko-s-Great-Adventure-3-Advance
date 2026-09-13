# Prose second pass

Completed on 2026-09-13: **7,324 bilingual catalog pairs across 36 catalogs**,
including a separate reading of **425 compact display overrides**. The pass
makes **410 editorial revisions**. Of these, 408 change inserted text; two
full-wording improvements already have suitable compact displays in the ROM.
The review follows the user's three rules: natural English, consistent sourced
series terminology, and fidelity to the Japanese meaning and character voice.

The resulting 32 MiB ROM has SHA256
`407050b263dcd3d5ad40dadd9eb70f4831085612f533288b73522e7ae0d9cc34`.
`./build.sh` now includes this pass and publishes
[the latest ROM](../build/torneko-3-english.gba) and
[BPS patch](../build/torneko-3-english.bps). The
[acceptance report](../build/prose-review/acceptance.json) links language,
insertion, native-reader and regression evidence separately.

## Scope and editing authority

[review.json](../translations/prose-review/review.json) pins all 36 input
catalogs and records the pairs actually read against Japanese. Pattern scans
and layout checks do not count as bilingual review. These are catalog pairs,
not a new count of unique ROM sources. Fixed item/enemy names, ally nicknames,
unidentified-item names, inscriptions and graphic lettering retain their
existing authorities. The 74 technically unclassified candidates remain
separate; this pass does not establish complete discovery or a full playthrough.

[revisions.json](../translations/prose-review/revisions.json) is the editable
authority for this pass. Each revision preserves the source identity, original
Japanese bytes, previous English, replacement and reason. Any compact display
change is explicit. Historical component catalogs stay pinned so earlier
builds remain reproducible. Do not regenerate them over the reviewed English
or treat their superseded wording as the current translation.

For a combined view, use the generated
[effective catalogs](../build/prose-review/effective/) or:

```sh
.venv/bin/python -m tools.prose_review show story-completion 320 330
.venv/bin/python -m tools.prose_review export
```

The export combines the original catalog with the reviewed overlay; edit the
revision authority, not the export. Earlier dedicated display fixes remain
owned by their respective build components. In particular, this pass preserves
the corrected Recovery pot “Push” tutorial, joined XP/level templates and
status-only location abbreviations.

## Changes worth calling out

- Dialogue reads more naturally while retaining character voices, monster
  cries, puns, dialect and childlike speech. Corrections include the timing of
  an engagement, shop wholesale prices, competition between traders and
  whether a route has already opened.
- Douglas's question now asks whether a merchant would let customers lose out
  for the shop's profit. The previous “Do you mind…” formulation reversed the
  question's yes/no sense. The Japanese question, neighbouring responses and
  command order were reviewed together; choice parameters remain byte-identical.
- Descriptions distinguish damage received from damage dealt. Transformed
  spell restrictions refer to casting while transformed, rather than to a
  supposed category of transformation spells. Leg-sweeping means being swept
  off one's feet, rather than removing the ground.
- Results use “XP,” matching combat and status screens. Item-specific defeat
  messages gain missing articles. Frontend save-erasure prose uses “reset”
  rather than “initialize”; its original controls and conditions are retained.
- Two project effect labels change from “Material” to “Doll-type,” matching
  the Japanese 人形系 and the existing item/synthesis descriptions. This does
  not rename official species, items or spells. The complete before/after
  glossary evidence is retained in
  [terminology-revisions.json](../translations/prose-review/terminology-revisions.json).

The stone descriptions now specify targets **two squares away** and **three
squares away** respectively. Their Japanese counts one/two intervening squares;
a GBA-specific [Japanese throwing-item guide](https://peamon.net/toruneko3a/item/touteki.html)
corroborates the target distances. Related enemy spacing descriptions explicitly
say “a one/two-square gap,” avoiding confusion with adjacency. This secondary
guide is an independent mechanics reference, not official English localization
evidence. Dedicated in-game throw/range tests remain useful playtest coverage.

The Doll-type identity distinction is also supported by the fan-maintained
[Japanese Doll crusher reference](https://wikiwiki.jp/dqdic3rd/%E3%80%90%E3%83%89%E3%83%BC%E3%83%AB%E3%82%AF%E3%83%A9%E3%83%83%E3%82%B7%E3%83%A3%E3%83%BC%E3%80%91).
It is not treated as an official English source. Existing modern Dragon Quest
name evidence remains in the glossary; no fan-patch English was used.

The connected chief speeches `completion.009d8928` then
`completion.009d88f0` were checked in actual event order, rather than ascending
text-address order. Their dream/prophecy wording continues across two messages.
Natural conversation pacing and all branch outcomes remain separate coverage.

## Insertion and validation

The base is the accepted title ROM
`b80feb1177c9111f44edb1b0ffc8a63c89d94b7d4eccc9f383bc9b372d7b14a9`.
[MEMORY_MAP.md](MEMORY_MAP.md) recorded the ownership before insertion:
408 appended payloads occupy `[0111B490,0112242F)`, **28,575 bytes including
alignment**, with 491 exact four-byte pointer supersessions. Original Japanese
strings and all earlier allocations remain occupied and byte-identical.
There are no code, graphics, font, RAM or save-layout changes. The whole new
ROM reconstructs exactly from the accepted baseline plus these owned changes.

All revised entries pass their established native readers and applicable
substitution, buffer, page, queue/history, glyph and layout checks:

| Native verification phase | Revised entries |
| --- | ---: |
| Ordinary story | 203 |
| Pet/special story | 5 |
| Ally/companion dialogue | 34 |
| Item descriptions, enemy traits, synthesis and dungeon searches | 58 |
| Shops, services, events and frontend prose | 44 |
| Combat, help, tutorials and effect labels | 60 |
| Results prose/statistics | 6 |

The effect-label regression additionally checks 108 original bounded copies
and 77 indexed selections, including removal feedback. Controlled reader
fixtures do not establish every natural trigger or mechanic.

Regression checks on this exact ROM pass:

- Cold title boot with empty/existing saves: exact title pixels, palette,
  fade, 242 observed prompt frames and 32 unchanged boot/menu captures.
- Name-entry hints and Records/status navigation; all 94 controlled location
  headings; 166 formatter cases and 140 native queue/history cases retain the
  accepted rendering fixes. Three fresh history examples remain single lines.
- A normal-button floor-two combat defeat, complete results animation and
  return to town. All 17 animation steps pass, with **2,492 actual white text
  pixels checked and zero mismatches**. The original live-results reader uses
  the revised XP statistics. The cartridge save remains unchanged.
- All supplied user saves/states remain byte-identical. Emulator sessions use
  disposable copies. Old saved history still contains its original line breaks.

The natural defeat replay is recorded in
[prose-result-replay.json](../tools/prose-result-replay.json). Its trace recognises
the previously accepted XP lookahead hook. It performs no gameplay RAM/CPU
injection after restoring the naturally reached checkpoint.

The tested allocation plan is retained beside the native evidence. Final
glossary status/evidence metadata changes the review hash, but the acceptance
checker requires every payload, pointer and allocation in the final plan to
match the tested plan exactly. The rebuilt ROM hash is unchanged.

To reproduce preparation and validation with the existing fixtures/resources:

```sh
.venv/bin/python -m tools.build_prose_review --prepare
# Document any changed ranges before insertion.
.venv/bin/python -m tools.build_prose_review
.venv/bin/python -m tools.prose_review export
# Run each phase: story special dialogue items services messages results
.venv/bin/python -m tools.verify_prose_review story
# Run each regression: render title result
.venv/bin/python -m tools.verify_prose_regressions result
./build.sh
.venv/bin/python -m tools.accept_prose_review --published
```

The preserved acceptance belongs to the recorded inputs. Further wording edits
need a new tested plan and appropriate fresh phase evidence. Future language
polish from real scene context, later story/choice outcomes, dedicated mechanic
checks, suspend/resume and full ending playback remain in
[PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).
