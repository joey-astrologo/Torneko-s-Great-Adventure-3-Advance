# Complete companion dialogue

Historical checkpoint: the newer [default-nickname milestone](ALLY_NICKNAMES.md)
includes this entire build and completes the separate nickname family. Counts,
ROM hashes and verification limits below describe this companion checkpoint.

Completed 2026-09-11. This build adds **1,227 independently translated entries**:
the remaining **1,224 non-null main-table responses** and **three conditional
Rosa alternatives**. Combined with the previous 400 entries, all **1,624 sources
in the known 200-record ally-dialogue table** are translated and inserted.
This completes that table, not all story/event dialogue in the game.

Open [the current English ROM](../build/companion-dialogue/torneko3-companion-dialogue-english.gba)
in mGBA. It includes every previous translation component, the seven-character
name entry, and the earlier message-history reflows. Personal playtesting can
remain deferred. The separate **198 distinct default ally nicknames remain
Japanese**; the controlled dialogue fixtures supply reviewed species names.

## Catalog and language decisions

[companion-dialogue.json](../translations/companion-dialogue.json) is the new
insertion authority. It pins the Japanese bytes/tokens, exact pointer word,
row/field, full English and translation notes for every entry. The earlier
[ally-dialogue.json](../translations/ally-dialogue.json) retains its 400 entries
and ownership. Every English sentence is authored from the Japanese original;
the partial fan ROM supplies no English or font assets.

All new English fits one three-line native dialogue page with font 0. The build
wraps full wording at whole-word boundaries using a 208px budget and conservative
29-byte/120px actor substitutions. No display abbreviations are needed. `$m0`,
`$m1` and `$t` retain their source counts; Japanese `$x` indentation is replaced
by measured English layout. All 26 `$t` entries also receive a Tipper profile.

The [terminology review](../translations/companion-dialogue-terminology-review.tsv)
covers all 1,227 entries. The existing 1,085 glossary identities, confidence,
sources and notes are preserved; four scoped references bring the total to
**1,089**:

| Japanese identity | English and evidence |
|---|---|
| ギガデイン | **Kazap**, with XI Japanese/English identity documented by the secondary [DQ Wiki reference](https://dragon-quest.org/wiki/Kazap). The Pip fighter line expresses an aspiration to master the spell. |
| アルテマソード | **Blade of Ultimate Power**, full name retained in Conkuistador's boast. Secondary [DQ Wiki reference](https://dragon-quest.org/wiki/Blade_of_Ultimate_Power) documents the identity and XI/VII 3DS usage. |
| エスターク | **Estark**, invoked by the separately identified Ersatz Estark speaker. [Square Enix's Heroes II support page](https://support.na.square-enix.com/faqarticle.php?id=16021&kid=76339&la=1&ret=main) corroborates the modern English spelling. This does not rename the imitation species or identify it as Estark himself. |
| パウロ | **Paulo**, an explicitly provisional project transliteration in eight test-style row-198 strings. The source differs from ポポロ; the protagonist remains **Tipper**. Natural use of these strings is unverified. |

Spell names provide naming evidence only. Dialogue remains Torneko 3's own
prose; another game's effects, costs and descriptions are not imported.
Existing Magic Burst, Kerplunk, Kamikazee, Multiheal, Omniheal, Fizzle, Weird
Dance and Harvest Moon choices are reused. Partial Kamikazee chants retain the
recognizable beginning of that name.

Species-name jokes are adapted to the reviewed English species: Drackmage's
name question uses its mage element, Shade's shadow joke uses “shady,”
Hocuschimaera's explanation uses hocus-pocus, and Quiller's thousand-needle boast
uses quills. Babyish speech, noises, repeated words and character voices are
independent adaptations with source notes. Robot damage percentages remain
character dialogue, not claims about the selector's exact HP thresholds.

The scope includes **48 reserved/test-style sources** in rows 0, 189, 190, 193,
198 and 199. They retain their literal/template roles without a normal-gameplay
reachability claim. Boss rows 186–188 have eight byte-identical Japanese bodies
at separate addresses; their English matches while all 24 pointer owners remain
distinct. Table completion does not imply that every row is recruitable.

## Native reader findings

The [memory map](MEMORY_MAP.md#remaining-companion-dialogue-2026-09-11) recorded
the source/table ranges and actor-field lifetimes before insertion. The exact
1,227 protected source ranges and checked pointer patches are in
[english-build.json](../build/companion-dialogue/english-build.json).
Reader disassembly is in
[special-readers.txt](../build/companion-dialogue/research/special-readers.txt).

| Reader | Confirmed behavior |
|---|---|
| `0803C3C8` | Indexes the 200-by-80-byte table using species and response. The fixture runs through Rosa's override before checking the final pointer. |
| `0803C2BC` | Ordinary rows choose between response pairs 0/1, 2/3 or 4/5 at the 80% and 40% HP thresholds. Rows 191/192 use five responses per band: 0–4, 5–9 or 10–14. |
| NPC talk counter `actor+13B` | For Rosa/Ines, a counter greater than 3 selects field 19 without a random call. The reader increments the counter. Boundary fixtures use counter values 0, 3 and 4. |
| Level-up selectors in `08025EC4` and `080377C8` | Both choose ordinary fields 6/7 or special-NPC fields 15–18. Field 19 is separate from these four level-up responses. |
| Rosa helper `0803E2E8` and flag bit 1 | After condition refresh, the flag can select the three-word table at ROM `001B4FE4`, indexed by signed `response/5` clamped to 0–2. A nonzero `actor+C4` lets the fixture retain a controlled flag without scanning an absent dungeon inventory. |
| `0807ACFC` → `0807ADA4` | Original 1,000-byte formatter and paged renderer with the dialogue caller's stack flags `(0,1,1)`. No font or renderer patch is added. |

The native selectors, formatter and page engine execute original game code.
Fixtures supply actor/name slots, control PRNG returns and Rosa's flag, and
bypass glyph delay, frame yield and input waits. The level-up checks execute
the selector slices in both callers; they do not simulate complete natural
level transitions. Two synthetic out-of-row Rosa inputs test the clamp only;
they are not asserted to occur in normal play.

Natural recruitment, nickname-copy consumers, special ability interceptions,
the inventory condition that refreshes Rosa's flag, NPC counter reset/progression
and normal conversation timing remain in the [playtest backlog](PLAYTEST_BACKLOG.md).

## Acceptance and storage

[acceptance.json](../build/companion-dialogue/acceptance.json) pins the exact
catalog, ROM, fixture and harness hashes. Results for this build:

| Check | Result |
|---|---:|
| Unit tests | 150 passed |
| New English native formatter profiles | 3,707 |
| New English native dialogue screens | 2,480 |
| Japanese relocation / baseline pixel-identical screen pairs | 1,253 |
| Native HP / talk-counter choices, each of three variants | 1,672 |
| Native choices in both level-up selectors, each variant | 808 |
| Rosa normal/alternate/clamp choices, each variant | 42 |
| Cold-initialized pointer tables, each variant | 4 |
| Earlier core/help history templates / native profiles | 311 / 933 |
| Earlier dialogue display regressions | 8 |
| Total English screens in the dialogue/history harness | 2,520 |
| Prior guarded enemy / hero copies | 400 / 2 |
| Secondary menus / natural ground-search routes | 14 / 2 |
| Item inventory-information / hero-detail screens | 14 / 4 |
| Torneko save and cold load | Passed; 65,536-byte save |

English profiles cover normal full species names, maximum-width actor names,
and synthetic narrow 29-byte actor names; the narrow profile checks formatter
capacity. Each `$t` source also tests Tipper. Earlier history checks retain the
59-byte payload limit and include synthetic 48-byte item names. The 16 previous
whitespace-only reflows are carried forward byte for byte.

The [screenshot sample](../build/companion-dialogue/companion-dialogue.png)
was visually inspected. Its background comes from a disposable world fixture;
it is evidence of native dialogue rendering, not natural access to those allies.

All previous allocation records, payload bytes, original patches, RAM/save
reservations and family catalogs are unchanged. Master extraction remains
**9,318 entries / 413,712 source bytes**, reconstructs the pinned original
exactly, and preserves independent master English/notes. The searchable browser
now overlays the new insertion catalog, including the three Rosa alternatives
that were already present in the inventory.

| Combined English storage | Amount |
|---|---:|
| ROM size | 32 MiB |
| Occupied append | `[01000000,0102B977)` |
| Used, including alignment | 178,551 bytes |
| Added in this pass | 72,378 bytes |
| Append remaining | 16,598,665 bytes (15.83 MiB) |
| Allocations / checked original patch ranges | 4,086 / 4,494 |

New strings occupy `[01019EBD,0102B977)` through the single shared allocator.
Every null field, unowned original byte and protected source remains intact.
No permanent RAM, save layout or font changes are introduced.

English SHA-256:
`50c06a6dfc6b5eb471eba234ce76c48038b1d99ce1a55935c4cb5b8e04f7cc68`

Japanese-control SHA-256:
`cb221e429fe266a3048d0d1cd7fb21984d2d48729679fe2107ba1d371a4abf73`

The control restores only this pass's 1,227 Japanese bodies while retaining
all earlier English components. Its baseline is the previous ally-dialogue ROM,
SHA-256 `e742ceb7e7f1c237f6f8825d738e03da6df7c270b3a612d3e238c1cfbe6cf0e5`.
The original and fan-reference hashes are unchanged and pinned in acceptance.

## Reproduce

From the project root:

```bash
.venv/bin/python -m tools.build_companion_dialogue
.venv/bin/python -m tools.verify_companion_dialogue_all
```

The second command rebuilds, runs all tests, all three native variants and
earlier UI/save regressions, refreshes extraction and performs acceptance.
It uses the disposable world state from the preceding ally-dialogue save check.
`--summarize-only` audits existing full-run artifacts against fresh rebuilds;
limited smoke runs cannot pass acceptance. After an intentional English edit,
review its terminology and refresh the reviewed catalog hash before acceptance.

The planned **default ally nicknames and their display, custom-name and save
consumers** are now covered by [ALLY_NICKNAMES.md](ALLY_NICKNAMES.md). Remaining
story/event text is the next translation scope. Work can continue without
requiring the user to playtest today.
