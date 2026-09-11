# Ally management and shared services

Completed 2026-09-10. Open
[torneko3-ally-services-english.gba](../build/ally-services/torneko3-ally-services-english.gba)
in mGBA. This combined build adds **138 translated entries** and preserves
all earlier item/enemy text, gameplay help/interfaces and seven-character
Adventure Log names.

| New family | Entries | Scope |
|---|---:|---|
| Messages | 94 | Ally limits, dismissal/registration, warehouse transfers/help, discard/container/synthesis feedback, merchant sales, gold bank and casino token exchange |
| Menu choices | 16 | Ally commands, warehouse and bank choices; original default selections retained |
| Labels | 13 | Inventory/storage destinations, protagonist headings, prompts and currency units |
| Rows | 9 | Sell labels, unavailable/status placeholders, free storage count and gold/token balances |
| Bounded fields | 4 | Ally-list title and adventure/battle context labels |
| Ally stats | 2 | Attack/XP and Defence/next-level rows |

Edit [ally-services.json](../translations/ally-services.json), keeping the pinned
source and ownership metadata intact. Only `english`, optional `display`, and
`notes` are editable. The [138-row terminology review](../translations/ally-services-terminology-review.tsv)
records the Japanese, full English, display abbreviations and references.
All English is independently translated from the original Japanese ROM.

## Language and layout

- **Torneko**, **Tipper**, **Warehouse pot**, Attack and Defence retain the
  existing terminology. Generic service/ally wording is project translation.
- **Tokens** has primary modern English support in the casino section of the
  [official DQ VII 3DS manual](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/nintendo_3ds_2/dragonquest7/ElectronicManual_Nintendo3DS_DragonQuest7_EN.pdf)
  (section 27, PDF page 62). Torneko 3's own Japanese source establishes the
  casino role and **20 gold per token**; no other game's mechanics were imported.
  This evidence does not claim a directly captured XI Japanese/English pairing.
- The existing `$j2` field holds **four payload bytes plus NUL**. Full terms
  Adventure/Battle have measured displays **Trip/Bout** in Join/Leave commands.
  **Ally list** fits its original 16-byte title field.
- The quantity picker reserves one unit cell after its digits. It uses **G**
  for gold and **T** for tokens; the prompt and balance spell out tokens.
  Native testing rejected the full word in that particular picker.
- The warehouse transfer popup has 44px after its x4 origin. **Withdraw**
  (43px) and **Deposit** (34px) fit and have dedicated native caller tests.
- The XP column moves to x104 within the existing ally-details window. Both
  numeric substitutions remain intact, and signed 32-bit stress values fit
  without overlapping Attack/Defence or crossing the 188px content boundary.
- Service prose uses 208px lines, reserving the established item/actor/numeric
  substitution widths. Long messages use the game's existing three-line pages.
  Warehouse instructions occupy **six English pages / 554 bytes including NUL**.
  They retain the 200-item limit, individual counting of pot contents, access
  from different warehouses, protection on collapse and Warehouse pot rules.

## Ownership and storage

[MEMORY_MAP.md](MEMORY_MAP.md#ally-and-service-menus-2026-09-10) records the
source ranges, table strides, pointer owners and runtime fields discovered
before insertion. The complete builder uses one shared allocator, protects
original source strings, rejects collisions and preserves every earlier
allocation and patch. Unreviewed pointer hits remain excluded. The previous
enemy component keeps ownership of the ally Max HP/species format pointer.

No new font, permanent RAM reservation, game logic or save-layout patch is
introduced by this component. Changed stat columns live in the new text.

| Combined English build | Value |
|---|---:|
| ROM size | 32 MiB |
| Appended bytes including alignment | 75,729 |
| Added since gameplay help | 5,537 |
| Appended capacity remaining | 16,701,487 |
| Allocations / checked original patch ranges | 2,174 / 2,527 |

The occupied appended interval is `[01000000,010127D1)`. Exact locations are
in [english-build.json](../build/ally-services/english-build.json).
English SHA-256:
`d8e185dac51a357dc6a39640062e13d796805b12d9f98d9e5a557004f93f922e`.
Japanese-control SHA-256:
`efdf226241f51a387ae62d364c94d2d782e1f6810835da7a775da0ab7c001295`.
The control keeps earlier components English and relocates this component's
unchanged Japanese. Its comparison baseline is the prior gameplay-help ROM.

## Verification and limits

[acceptance.json](../build/ally-services/acceptance.json) pins the exact ROMs,
catalogs, native harness, terminology review and combined checks:

- **124 unit tests**, including fixed-field terminators, substitutions/printf
  arguments, stat columns, the unit-cell restriction, default markers, immutable
  source ownership and retention of previous assets/patches/RAM reservations.
- **356 English screenshots**, including normal/stress formatting of all 138
  entries, every service-message page, 12 original ally tables in both layouts,
  warehouse/bank menu readers, two transfer popups, numeric pickers and native
  balance headers.
- **211 pixel-identical Japanese/control pairs**, including service navigation.
- Three native title/context copy cases with guards, plus **400 enemy copies**,
  both protagonist copies, 14 secondary action menus, both ground-search
  protagonists, 14 item inventory/info screens and four protagonist details.
- **Torneko creation, save, cold-load and world entry**; save remains 64 KiB.
- **9,318 master entries / 413,712 source bytes**, reconstructing the Japanese
  original exactly. Earlier English/notes survive; the browser overlays the
  138 new entries. All previous glossary wording/evidence is preserved.

The paged-message fixture retains the native PC, source cursor and stack across
pages. It bypasses button waits and uses a disposable BX LR frame-yield callback,
but runs the original page redraw loop and live RAM draw callback. This matters:
skipping that redraw loop produces overlapping page text in a test screenshot.
Every final page capture uses the corrected harness. The copy fixture enters the
manager's original copy block after setup, isolating guards from legitimate
nearby writes performed during manager initialization.

A separate route enters each **real warehouse/bank handler** through one test
redirect from item information, preserving its live frame callback. Ordinary
buttons then read all six help pages, return to the warehouse menu, attempt an
empty withdrawal and cancel; the bank route opens the empty-balance menu and
cancels. Paging and input waits on these routes run normally. These are controlled
entry routes, not proof of reaching those NPCs through the story.

Generic isolated label/row fixtures do not establish every caller's surrounding
screen. Ally table fixtures draw the command popup without constructing a
natural recruited party; remaining nickname/custom scenario headings may still
be Japanese. Natural recruitment, registration/deletion, full inventories,
successful transfers/sales, deposits/withdrawals and casino transactions remain
in [PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md). Ranking/name persistence remains
deferred. Personal playtesting is not required before further translation.

Examples: [warehouse menu](../build/ally-services/verification/routes/english/warehouse-03.png),
[warehouse instructions](../build/ally-services/verification/routes/english/warehouse-09.png),
[bank menu](../build/ally-services/verification/routes/english/bank-04.png),
[ally details](../build/ally-services/verification/hero-details/ally-000.png),
[token quantity](../build/ally-services/verification/english/numeric-00c3f808.png).

## Reproduce

```bash
.venv/bin/python -m tools.build_ally_services
.venv/bin/python -m tools.verify_ally_services_all
```

The second command rebuilds, runs unit/native/regression checks, refreshes the
browser and writes acceptance. To audit existing artifacts:

```bash
.venv/bin/python -m tools.verify_ally_services_all --summarize-only
```

The next substantial translation scope is tutorials and remaining gameplay
message families. Story/ally dialogue and scenario-specific service headers
remain separate work.
