# Opening story and first bedroom

Completed 2026-09-11. The combined build translates the opening narration,
family voyage and birthday, both responses to Tipper's dream question, the
storm, village arrival, dawn and first bedroom conversation. It also includes
the related return/rest messages, the shared sleeping-Tipper observation, and
the event engine's separate Yes/No labels.

Playable ROM:
[torneko3-opening-story-english.gba](../build/opening-story/torneko3-opening-story-english.gba)

SHA-256: `2e05c0b030450216a47cdc76ecbb3d18195d6b0fa75bb4b3f5790e54701559e3`

The [catalog](../translations/opening-story.json) contains **46 entries**:
44 story sources and two choice labels. **45 are newly translated**. The first
narration reuses the existing `story.opening_01` wording, pointer patch and
allocation. Earlier translations, fonts, nickname support and seven-character
player-name support remain in the build.

## Language and terminology

All prose is independently translated from the Japanese original. The partial
fan translation supplies no English or font assets. Anonymous Japanese speaker
labels remain `???` until the source introduces the speaker.

Torneko and Tipper retain their existing glossary identities. **Tessie** matches
ネネ, Torneko's wife: the Japanese family relationship has
[primary Square Enix confirmation](https://www.jp.square-enix.com/tdq/character/character_detail/dq4_torneko.html),
while the modern DQ IV English/Japanese name pair uses the explicitly secondary
[Tessie Taloon reference](https://dragon-quest.org/wiki/Tessie_Taloon).
The older Neta/Nina names are not adopted. Tessie's dialogue is authored from
this game's Japanese; no other localization's dialogue or accent is copied.

**Gamlan** (ガムラン) is a documented project transliteration, without a claimed
verified official English equivalent. **Chief**, **Yes** and **No** are project
role/UI wording. These five new identities bring the glossary to **1,288 terms**.
The [46-entry review](../translations/opening-story-terminology-review.tsv)
records every source, English draft, identity reference and note. Existing
names, confidence, sources and notes are preserved.

## Layout, storage and ownership

Font 0 remains in use. Each message fits the original three-line page, within
the native **208 × 40 pixel** story window. Narration retains `$c` centering;
speech continuations retain native tabs. Intentional leading blank lines remain.
The formatter still has **1,023 payload bytes plus NUL**. This milestone changes
text and pointers, with no story code, RAM or save-layout changes.

| Combined build resource | Result |
|---|---:|
| ROM size | 32 MiB |
| Appended bytes used, including alignment | 183,315 |
| Added by this milestone | 2,955 |
| Remaining appended capacity | 16,593,901 |
| New checked original-ROM writes | 53 four-byte pointers |
| Story operands checked, including the reused narration | 52 |

The [source ownership report](../build/opening-story/source-owners.json) records
every exact source end and command/operand location. Its 44 story sources use
52 operands because the sleeping-Tipper observation has nine owners. They
share one relocation. Command headers and choice parameters remain unchanged.
The first narration retains its earlier owner; the other 51 story operands
and two Yes/No table words receive checked pointer patches.

The event Yes/No table at ROM `[0086F49C,0086F4C0)` is separate from the early
menu tables. Only its label pointers change. Yes still returns 1, No returns 0,
and the original default selection, record stride, terminator and window
geometry remain intact. Both choices render in English during the dream scene.

The [memory map](MEMORY_MAP.md#opening-story-and-first-bedroom-2026-09-11) records
these ranges before insertion. The
[English ledger](../build/opening-story/english-build.json) owns the final append
span `[01000000,0102CC13)`, including the new span `[0102C088,0102CC13)`.
Original strings remain protected. All earlier allocations, payloads, patches
and RAM reservations are checked against the preceding nickname build.

## Automated acceptance

The [acceptance report](../build/opening-story/acceptance.json) pins the ROMs,
catalog, ownership, tools and review. **179 unit tests pass.** Native mGBA checks
cover:

- **52 English event operands:** each actual ROM command is dispatched through
  its original wrapper and guarded formatter, followed by normal frame-driven
  text rendering. Glyphs, line placement, centering and window bounds pass.
- **52 Japanese pixel comparisons:** relocated original story text produces
  identical output and screenshots to the preceding build. The already-English
  first narration remains English in both controls.
- **Two natural opening routes:** fresh emulator cores load a disposable
  Japanese Adventure Log and use ordinary buttons through Yes and No. The
  routes display 36 and 37 messages, respectively; No adds Tipper's refusal
  response. All 3,198 / 3,242 native story reads are attributed to the correct
  source, with complete glyph checks and both English choice labels. No ROM,
  RAM or register redirects or skipped waits are used in these routes.
- **Both Adventure Logs:** normal joypad entry, native FLASH saving and fresh
  emulator loads preserve all seven letters of `Torneko` in each slot and into
  the opening story. Saves remain 65,536 bytes.

The natural routes cover 37 distinct story sources. The seven additional
return/rest/observation sources, and the additional shared observation operands,
have controlled display coverage. Their later natural triggers and the rest
question's branch outcomes remain in the [playtest backlog](PLAYTEST_BACKLOG.md).
These checks do not establish later village progression, endings, rankings or
complete-game text discovery. Personal playtesting can wait.

Native screenshots:
[English dream choices](../build/opening-story/verification/natural-yes/dream-choice.png),
[bedroom conversation](../build/opening-story/verification/natural-no/bedroom.png).

## Reproduce and continue

```sh
.venv/bin/python -m tools.build_opening_story
.venv/bin/python -m tools.verify_opening_story_all
# Recheck complete existing artifacts without rerunning emulator routes:
.venv/bin/python -m tools.verify_opening_story_all --summarize-only
```

Edit `translations/opening-story.json` as the insertion authority. Keep its
terminology review and glossary snapshot consistent. The preparation helper
refuses to overwrite an existing authored catalog.

The subsequent [first-village milestone](FIRST_VILLAGE.md) is now the latest
combined build and preserves this opening work. The figures below describe
the opening milestone's inventory snapshot.

The searchable master includes the opening overlay while preserving every
earlier master source, English draft and note. Progress is **4,353 of 9,318
known entries translated/inserted (46.72%)**, with **4,965 remaining**. First-village
progression and NPC conversations are covered by the subsequent milestone.
