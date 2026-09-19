# Current project status

Updated 2026-09-19. This page summarizes the current state; component reports
retain the hashes and evidence for their historical checkpoints.

## Implemented

- Verified text catalogs: story, gameplay feedback, menus, items, enemies,
  services, results, name entry and other documented text families.
- Prose second pass: 7,324 bilingual pairs and 425 compact displays reviewed,
  with 410 revisions. See [PROSE_REVIEW.md](PROSE_REVIEW.md).
- Approved English title, Credits-adapted arrival cards for 36 identities / 64
  selectors, and the more compact vertical arrival layout.
- Reported menu, keyboard, Records, warehouse and casino rendering fixes.
- Conditional joining for 268 additional combat sentence spans and two
  critical/brutal continuations, retaining existing damage/XP joining and
  fallback when actual substitutions exceed 208px or 59 history bytes.
- Convenient ROM/BPS outputs and mandatory native menu/combat publication gates.

The current accepted build is `e1f2babeb6b0`, full SHA-256
`e1f2babeb6b06ffdc9f52c4c190859a1f8e6712688dc7d3465736fbb55cc032e`.
For subsequent builds, [the receipt](../build/torneko-3-english.json) is the
artifact authority. The current component is `tools.build_medal_trade`.

## Remaining text and research

Ordinary inventory accounting remains **8,422 authored sources + 822 retained
resources + 74 technically unclassified candidates = 9,318 entries**. This is
inventory accounting, not a percentage of the game proven complete.

The 74 candidates consist of:

- 31 Japanese sources: 30 English drafts and one unresolved phrase, all
  uninserted pending reader/context/ownership evidence.
- 42 original ASCII candidates and one character-map candidate. These need
  classification; they are not automatically untranslated player-facing text.

See [unowned review](UNOWNED_TEXT_REVIEW.md), [resource boundaries](RESOURCE_BOUNDARIES.md)
and [Japanese guide leads](JAPANESE_GUIDE_LEADS.md). Unreferenced strings are not
proven unused, and extraction gaps are not free ROM space.

The user tested an enemy occupying a Warp pot's destination and reported an
already-English generic no-effect message. This does not reproduce the draft
at `001B8A4A` or prove it unused. See [the test helper](WARP_POT_TEST.md).
The user also tested the Blank scroll's learned-name restriction and chose to
leave the manual-input aliases unchanged, using the learned list in normal play.

## Remaining verification

The [menu action audit](MENU_ACTION_AUDIT.md) led to the approved
[medal Trade fix](MEDAL_TRADE.md). The other tested action labels fit and
remain unchanged, including Take out and Withdraw.

1. Later story, postgame, uncommon interactions and long contextual names during
   ordinary play. Controlled text displays do not prove every event outcome.
2. Dungeon suspend/resume and broader item/ally/progression save persistence.
   Earlier defeat and successful first-cave clear routes already have native
   save/cold-load evidence; those checks are not full-game coverage.
3. Full ending playback, including illustrations, transitions and fades.
   All 31 examined credit text cards are already English in the Japanese ROM;
   their isolated text-layer checks do not establish the complete ending.
4. Additional graphics discovery. The known title/arrival work is inserted;
   separate town-card families and some small scene/sprite details remain
   unconfirmed. See [GRAPHICS_REVIEW.md](GRAPHICS_REVIEW.md).

No known large verified text catalog is waiting for an initial translation.
Natural playtesting and concrete bug fixes are the main next steps; technical
research can continue independently. [PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md)
records detailed route coverage and limitations.

## Build coverage and reproducibility

The current publication gate checks seven menu routes, four trading/narrow-action cases, every approved combat
source across six substitution profiles, queue/history behavior, size boundaries,
critical/brutal continuations, and 376 existing damage/XP cases per ROM. It then
requires a byte-identical BPS roundtrip. Reports are pinned in the build receipt.
See [COMBAT_LINES.md](COMBAT_LINES.md), [MENU_FIXES.md](MENU_FIXES.md) and
[BUILD.md](BUILD.md).

The convenience build still depends on prepared artifacts and historical
checkpoints under `build/`, plus local emulator fixtures. A clean-checkout
bootstrap is a future tooling improvement, not an existing supported command.
