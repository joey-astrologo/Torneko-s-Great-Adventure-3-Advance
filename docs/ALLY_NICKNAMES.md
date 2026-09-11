# Default ally nicknames

All **200 default-nickname table rows / 198 distinct source strings** are now
translated and inserted in the combined build. This completes the separate
nickname family after the [companion-dialogue milestone](COMPANION_DIALOGUE.md).
Species names retain their existing modern Dragon Quest terminology; personal
nicknames have their own Japanese identities and references.

Playable ROM: [torneko3-ally-nicknames-english.gba](../build/ally-nicknames/torneko3-ally-nicknames-english.gba).
SHA-256: `ae0f17d55520df86c45e10ed5b835747ce3fb698e37e34a57414b45ca906fe2f`.
The original Japanese ROM remains the build base. The supplied fan translation,
its English and its font assets are not used by this build.

## Names and the five-character limit

The ally editor has **five slots**. Both a live actor and its stored 32-byte
ally record hold **six nickname bytes: five compact character IDs plus NUL**.
The game also appends a numeric suffix when generating a default name. Its
suffix table includes full-width 0 through 9; the counter cycles 1–9 after its
initial zero. The English encoder converts that suffix to an ordinary digit.
A five-letter base therefore becomes its first four letters plus the digit.
Custom names can use all five slots without a generated suffix.

This pass retains that layout. Full names stay in the catalog and glossary;
`display` records a deliberate short base. These are project abbreviations,
not alternate official localized names. For example:

| Japanese nickname | Full reference / project name | Inserted base | Generated with suffix 1 |
|---|---|---|---|
| はぐりん | Merc | Merc | Merc1 |
| スラリン | Gootrude | Gooty | Goot1 |
| ホイミン | Healie | Healy | Heal1 |
| キラーマ | Roborg | Robby | Robb1 |
| ピエール | Goodian | Goody | Good1 |

The player's Adventure Log name remains separately capable of **seven
characters**, including **Torneko**. This pass does not shorten that name.
The nickname table also contains protagonist, NPC, boss and reserved rows;
translating them does not imply those rows are normally recruitable. Row 198
really says パウロ (**Paulo**) here, distinct from the species identity
ポポロ (**Tipper**). Rosa and Ines use fixed character names in all three tested
actor-name formatters, even if their stored nickname differs.

## Terminology evidence

The [catalog](../translations/ally-nicknames.json) and
[200-row review](../translations/ally-nickname-terminology-review.tsv) retain
Japanese source bytes, species context, full/base English, glossary identity,
source quality and abbreviation notes. The glossary adds **194 scoped nickname
identities**, reusing four existing character/placeholder identities, for
**1,283 terms** total. Earlier terminology and English are preserved.

Fourteen exact Japanese nickname/species matches reuse modern DQ V DS default
names. Matching an ordinal between the [Japanese recruitment table](https://w.atwiki.jp/dq5mon/pages/19.html)
and the [English DS recruitment guide](https://gamefaqs.gamespot.com/ds/942423-dragon-quest-v-hand-of-the-heavenly-bride/faqs/59379)
is explicitly recorded as an inference from secondary evidence. These are not
bilingual game captures. Roborg corresponds to the **second** DQ V default,
キラーマ; merely choosing the first English name for the same species would
produce the wrong match.

Healie uses the explicit [ホイミン / Healie reference](https://dragon-quest.org/wiki/Healie)
as an editorial shared-nickname choice. DQ V's first healslime default is
different; this does not identify the Torneko recruit as the IV/VI story
character. The other nicknames are independently adapted or transliterated
from this ROM and marked as project choices. XI remains the baseline for
shared species/items/terms; no XI nickname pool is claimed here.

## ROM and storage changes

The original two-byte Japanese-to-compact encoder cannot encode the new ASCII
defaults. A checked **eight-byte hook at ROM `0007D29C`** handles only the actual
recruitment call (`LR=080292BF`) with ASCII input. Its bounded loop keeps the
output within five IDs plus NUL, retaining the suffix. Japanese inputs and
other callers resume the original encoder. Existing Latin decoder and keyboard
patches are preserved.

| Combined build resource | Result |
|---|---:|
| ROM size | 32 MiB |
| Appended bytes used, including alignment | 180,360 |
| Added by this milestone | 1,809 |
| Remaining appended capacity | 16,596,856 |
| New original-ROM patches | 200 pointer words + one encoder hook |
| Ally editor / actor / stored name capacity | 5 characters / 6 bytes / 6 bytes |
| Cartridge save size | 65,536 bytes |

The [memory map](MEMORY_MAP.md#default-ally-nicknames-2026-09-11) records each
new source/code/RAM/save discovery. The
[English ledger](../build/ally-nicknames/english-build.json) is the authority for
all allocations, padding, protected sources and checked patches. Every earlier
allocation, payload and patch remains intact. Original nickname bytes remain
protected, and the shared allocator rejects collisions.

## Automated verification

The [acceptance report](../build/ally-nicknames/acceptance.json) pins the ROMs,
catalogs, tools, terminology review and source round trip. **171 unit tests pass**.
The native mGBA checks cover:

- **2,000 English generation cases:** every row with every suffix 0–9, actual
  table-copy/concatenation/call instructions, compact decoding, guarded actor
  and record transfers, and three complete name-formatting functions.
- **600 Japanese control pairs:** relocated Japanese defaults match the prior
  build through generation, decoding, record copies and all three formatters.
  Six calls outside recruitment per variant also retain original behavior.
- **200 native editor displays:** all generated names with suffix 9 pass font 0
  glyph and window checks. Initial `Goot1` reaches the editor from the actual
  recruitment encoder. Other rows use controlled editor bytes and native
  repaint. Real joypad input covers all 62 Latin IDs, case switching, erasing,
  the five-slot limit, final-character replacement, kana shortcut and Done.
- **Actual FLASH save/cold load:** all 200 defaults, three Japanese names and
  custom names covering all 62 Latin IDs survive across two Adventure Logs.
  Each fresh emulator loads through normal buttons. Complete 130-record ally
  blocks match, and saving slot 2 preserves slot 1. The seven-character player
  name `Torneko` also survives both slots and the opening-story transition.

The save fixture changes only six nickname bytes per existing record directly
before the original serializer. It does not manufacture a valid recruited party
or prove natural recruitment, active-party eligibility, dungeon suspend saves,
rankings or later UI contexts. Those remain in the
[playtest backlog](PLAYTEST_BACKLOG.md); user playtesting is not a prerequisite
for continuing translation.

Native editor examples:
[generated Goot1](../build/ally-nicknames/verification/editor/initial-goot1.png),
[five-slot replacement](../build/ally-nicknames/verification/editor/capacity-robbx.png).
Detailed reports are under
[verification](../build/ally-nicknames/verification/).

## Reproduce and continue

```sh
.venv/bin/python -m tools.build_ally_nicknames
.venv/bin/python -m tools.verify_ally_nicknames_all
# Re-audit existing complete artifacts without rerunning emulator routes:
.venv/bin/python -m tools.verify_ally_nicknames_all --summarize-only
```

Edit `translations/ally-nicknames.json` as the insertion authority and keep its
review/glossary snapshot consistent. The draft TSV is the original preparation
input; `prepare_ally_nicknames.py` refuses to overwrite an existing catalog.

The searchable master now includes the nickname overlay while preserving all
independently authored master English and notes. Progress is **4,308 of 9,318
known source entries translated/inserted (46.23%)**, with **5,010 remaining**.
This measures the inventoried text, not complete-game discovery. The subsequent
[opening-story milestone](OPENING_STORY.md) completes that coherent event
section and is now the latest combined build, preserving this nickname work.
