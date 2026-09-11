# Early dungeon journey and place names

The combined English build adds **194 independently translated source entries**:
156 story messages, six advice choices, thirty place-table labels, and the
Zoom destination heading and confirmation prompt. It retains all previous
translations, font 0 and seven-character Torneko name support.

- [Playable English ROM](../build/early-journey/torneko3-early-journey-english.gba)
- [Translation catalog](../translations/early-journey.json)
- [Terminology review](../translations/early-journey-terminology-review.tsv)
- [Acceptance report](../build/early-journey/acceptance.json)
- [Source ownership](../build/early-journey/source-owners.json)

English SHA-256:
`37414331f7866c8b4a19a5bf87d46527b91ce5dbfff67860467b05c9adcaa8c4`.
The pinned Japanese original is the only build and translation source. The fan
ROM remains unchanged and contributes no English or font assets.

## Translation scope

The story section covers the shrine's underground entrances and inscriptions,
the elder's complete dungeon advice, Undersea House, the temple passages and
the mountain rest stop. It includes the day/night and related return versions
found in those sections, including Tipper-specific lines and the siblings'
comments about Viola. These sources do not all occur during the first visit.
The Sea Dragon Lighthouse scenes are the next story section.

All four advice prompts retain their six choices in the original order:
Dungeons, Monsters, Items, Traps, Sealing traps and Never mind. Original
ordinals, event parameters and Yes/No meanings remain intact. Advice describes
Torneko 3's own mechanics; item and spell names retain the existing glossary.

All thirty place records are translated together so their shared readers have
consistent names. Records 0–27 are location labels; the final two are
administrative From the beginning and Invalid labels. Translating them does
not assert that they are normal travel destinations.

## Terminology and display limits

The glossary now has **1,327 identities**, adding 33 while preserving earlier
names, confidence, references and notes. The publisher's
[Japanese journey synopsis](https://www.spike-chunsoft.co.jp/pages/games/torneco3/story03.html)
corroborates the Japanese island, port and castle identities. Great Baleina,
Costa Libera and the other new English place/lore names are documented project
choices, not claims of official English localization.

Conklave Village applies the modern localized プチット族 group name by inference
from the [secondary Conklave reference](https://dragon-quest.org/wiki/Conklave).
Madame Gracos's bazaar retains the modern Gracos stem using
[secondary naming evidence](https://dragon-quest.org/wiki/Gracos), without
identifying that NPC as the main-series boss. The
[Medal King reference](https://dragon-quest.org/w/index.php?title=Medal_King)
supports the recurring role; another game's king's personal name is not imported.
Inatts, the monster elder, Star of the Gods and the Sea Dragon lore retain
explicit project status. Existing Slime, Zoom, item and dungeon identities are
reused. All dialogue is independently authored from the local Japanese script.

The Zoom picker revealed two separate limits:

| Context | Native limit | Result |
|---|---|---|
| Selected destination substitution | 30 bytes, including NUL | Every full place label fits; neighboring slots preserved |
| Destination list | 160px window, 4px inset | Every full place label fits the remaining 156px |
| Picker heading | 32px window | Full Destination is 53px; displayed Go to is 26px |
| Zoom confirmation | Native message window | All thirty copied destinations format and render completely |
| Story messages | Three lines in a 208 × 40px window | All messages fit, with original speech continuation tabs |

The catalog and glossary retain the full Destination term. Go to is a measured
display choice. No place-name abbreviation, font replacement, code/window
expansion or RAM/save expansion is required.

See the native [destination picker](../build/early-journey/verification/labels-english/place-15.png),
[six-topic advice menu](../build/early-journey/verification/labels-english/advice-00b85154.png)
and [Zoom confirmation](../build/early-journey/verification/labels-english/confirmation-23.png).
These images come from controlled fixtures using an earlier world snapshot.
The advice image's background dialogue is cached snapshot text; the six menu
rows are the fixture under test. Its translated question has separate native
story coverage.

## Ownership and storage

The [memory map](MEMORY_MAP.md#early-journey-and-place-records-2026-09-11) records
source ranges, readers, place records, original substitution slots and fixture
scratch before their use. **322 checked pointer words** are changed: 290 event
operands, thirty place records and two UI literals. All original source text,
command headers, choice order, coordinates and preceding allocations remain
unchanged. Selection envelopes and their gaps are not free space.

The shared allocator rebuilds every component from the original ROM. The
[English ledger](../build/early-journey/english-build.json) owns append span
`[01000000,01034789)`: **214,921 bytes**, including alignment. This pass adds
**11,075 bytes** after the first-village end `01031C46`, leaving
**16,562,295 bytes** available in the expanded half of the 32 MiB image.
The separate Japanese relocation control ends at `01034B2F`; its ledger must
not be stacked with the English build.

## Verification and remaining gameplay coverage

The acceptance report verifies a deterministic rebuild and all prior catalog,
allocation, payload, patch and RAM/save reservations. **186 unit tests pass.**

- **274 native story cases:** every non-choice event operand, with both
  protagonists for all `$t` messages. Native dispatch, wrappers, guarded
  formatting, complete glyph sequences, line positions and bounds pass.
- **64 additional native cases:** thirty place getter/coordinate/copy/draw
  fixtures, thirty corresponding Zoom confirmations, and all four six-topic
  advice menus. All 24 choice operands retain their native record ordinals.
- **338 Japanese pixel pairs:** relocated Japanese output matches the prior
  combined ROM across the story, place, confirmation and advice fixtures.
- **Natural regression:** ordinary buttons replay the opening, village escort
  and first chief meeting on this build. All 46 messages have complete source
  attribution and glyph checks, with no unexplained story-buffer reads.
- **Both Adventure Logs:** native FLASH saves and cold loads preserve all seven
  characters of Torneko. Saving the second slot preserves the first. Save size
  remains 65,536 bytes.

The natural replay covers previously translated scenes. New journey scenes,
advice selection outcomes, actual rest/shop transactions, day/night triggers,
Zoom destination outcomes and world-map marker placement still need ordinary
gameplay coverage. Controlled fixtures establish their recorded readers and
display behavior. These gaps are in the [playtest backlog](PLAYTEST_BACKLOG.md);
personal playtesting can wait.

Known-source progress is **4,828 / 9,318 entries (51.81%)**, with **4,490
remaining**. The regenerated searchable master overlays this catalog while
preserving existing master source bytes, English drafts and notes. Its source
round trip still reproduces the original. This percentage does not establish
complete-game text discovery.

## Reproduce

```sh
.venv/bin/python -m tools.build_early_journey
.venv/bin/python -m tools.verify_early_journey_all
# Validate all existing evidence without rerunning emulator routes:
.venv/bin/python -m tools.verify_early_journey_all --summarize-only
```

The draft TSV is a one-time preparation input; the helper refuses to overwrite
an authored catalog. Subsequent edits belong in `translations/early-journey.json`,
with the review and glossary snapshot kept consistent.

Next: the Sea Dragon Lighthouse story and adjoining services as one coherent
section, with all newly verified ranges recorded before insertion.
