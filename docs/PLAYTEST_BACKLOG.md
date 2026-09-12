# Deferred gameplay checks

Updated 2026-09-11. The user wants to continue translation and playtest when
time permits. **No user playtesting is required today or before the next
translation batch.** Codex can develop automated routes independently; later
personal playtesting can supplement that coverage.

The current [early-journey milestone](EARLY_JOURNEY.md),
[first-village milestone](FIRST_VILLAGE.md), the earlier
[opening-story milestone](OPENING_STORY.md), the earlier
[default-nickname milestone](ALLY_NICKNAMES.md), the earlier
[complete companion-dialogue milestone](COMPANION_DIALOGUE.md), the earlier
[ally-dialogue/history milestone](ALLY_DIALOGUE.md),
[tutorial/gameplay milestone](TUTORIAL_GAMEPLAY.md),
[ally/service milestone](ALLY_SERVICES.md),
[gameplay-help milestone](GAMEPLAY_HELP.md),
[core-gameplay milestone](CORE_GAMEPLAY.md),
[dungeon-interface milestone](DUNGEON_INTERFACE.md), the completed
[enemy/item milestone](ENEMIES_AND_ITEMS.md), and existing [item](ITEM_TEXT.md), [item-context](ITEM_CONTEXTS.md) and
[name-entry](NAME_ENTRY.md) checks remain evidence for their recorded ROM
hashes. The following gaps do not invalidate those controlled checks, but must
not be described as already tested.

| Pending coverage | What to verify | Existing evidence |
|---|---|---|
| Early journey and rest-stop outcomes | Traverse the first dungeons, reach day/night Undersea House, rest, revisit the temple and mountain stop, and check Torneko/Tipper return conditions. | All 156 new story sources have controlled native event/display checks. Natural replay on the journey ROM covers the earlier opening and first chief meeting; it does not reach these new scenes. |
| Six-topic advice interactions | Open all four elder prompts naturally, choose every topic, repeat the advice loop and leave using Never mind. | Native dispatch builds all six records for every prompt; all 24 label operands, order/ordinals, questions and menu glyphs pass. Actual loop outcomes remain separate. |
| Adventure-history achievements | Earn the listed events naturally, browse all history pages, and compare recorded floors, turns and elapsed time with the completed adventure. | 100 sources / 104 pointers pass 108 key lookups, 400 English row cases, 69 native composite contexts and 269 Japanese pixel pairs. Counter fixtures test the documented widths; they do not prove every achievement trigger or all possible stored counter maxima. |
| Arena, registered battles and entry conditions | Reach each service naturally; place and roll over bets, fight with allies, register a valid monster password, and verify the stated dungeon-entry consequences. | 108 sources pass 216 English cases, 208 Japanese pixel pairs, eight menus, 40 full rosters, 11 warning combinations, 200 bounded name/level copies and 12 popup regressions. The roster has a private wider window. Controlled display/copy checks do not perform real bets, battle outcomes, registration or item/gold/level changes. |
| Later story, postgame and shared scenes | Reach the castle, coast, shrine, lighthouse, ending/postgame and Conklave menus naturally; check story conditions, choice consequences and pacing. | Continuous completion has 2,258 translated ordinary story sources, eight complete menu prefixes and preserved intermediate native checkpoints. The completed story-pages run passes 2,875 native story cases and eight menus; 78 additional shared scripts pass 139 native story cases, one menu and 140 Japanese pixel pairs. These do not establish natural reachability. |
| Pet adoption, naming and the tree password | Adopt both pets in each applicable house state, rename them, revisit them after saving, and use the English hint to pass the tree gate naturally. | The 32-source pet/password component passes 123 native story cases and Japanese pixel pairs, 15 real-keyboard/native commit/comparison cases, and both Adventure Logs' pet-variable FLASH saves/cold loads. Seven-slot names, short-name zero fill, cancel and legacy Japanese names are covered. The exact uppercase keyword is LETMEIN. Natural adoption, gate traversal and dungeon suspend saves remain separate. |
| Place names, Zoom and map markers | Unlock destinations through normal play, navigate the complete Zoom list, confirm/cancel travel, and check location headings and map markers. | All thirty place records pass native getter/coordinate/copy/list checks, every copied name passes native confirmation display, and all coordinates remain unchanged. Administrative rows 28/29 are not claimed reachable. No natural travel or map-marker placement proof. |
| Village departure, shrine and later return outcomes | Follow the sleep/rest transitions, messenger and shrine events naturally; choose Ines/Rosa, receive the map/bread, try full inventory, repeat advice, switch companions and trigger return conditions. | FIRST_VILLAGE.md translates 281 messages and checks all 367 operands (368 English cases and Japanese pixel pairs, including both protagonists for one shared observation). The fresh natural route covers only the opening, escort and first chief meeting: 46 messages / 3,838 attributed reads, ten new village sources. Both Adventure Logs preserve Torneko through native save/cold load. Remaining scene triggers and branch outcomes are controlled-display coverage only. |
| Global place labels and later village arcs | Map the shared place-label table/consumers, then translate map/menu labels consistently with dialogue; complete later Tipper, celebration and ending conversations as coherent sections. | Barinabo and Shrine of the Gods are now documented project names in village dialogue. Their separate original location labels have not been inserted by this event-text pass. First-village source envelopes explicitly exclude the later main story arcs. |
| Later bedroom/rest triggers and first-village progression | Return to Tessie naturally, choose both rest responses, examine sleeping Tipper in later states, and continue the village story. | OPENING_STORY.md translates 44 story sources plus shared English Yes/No labels. Both natural opening routes reach the first bedroom (36/37 messages), including the dream refusal; complete glyphs and source provenance pass. All 52 story operands also pass controlled native display and Japanese pixel checks. Seven further rest/return/observation sources and extra shared observation operands have controlled coverage only. Both fresh Adventure Logs preserve seven-character Torneko through native save/cold load. |
| Extraction coverage beyond the opening | Extend story/event provenance to later areas/results/endings and other RAM producers; inspect selection-list operands, compressed resources and graphics lettering. | TEXT_COVERAGE.md scans all pointer alignments/windows and unaligned NUL starts. STORY_PROVENANCE.md additionally traces 36 original opening-story sources from event operand through RAM to 1,803 character reads, with zero unattributed story reads. Thirteen controlled dispatch branches, 135 credit pointer/position cases and one omitted punctuation line pass. The ending/credits playback, other event families and the first 600 boot frames remain outside that proof. |
| Tutorials, combat/trap feedback and effect removal | Naturally acquire each tutorial item, check pause/scroll timing and joined damage, trigger cancellation/trap variants, remove an equipment effect and review the message history. | All 285 new entries pass native queue/history formatting; two display profiles, 294 Japanese control pairs, cold initialized pointers and 108 guarded label copies are checked. Test entry, history backing, scheduler and waits are controlled; natural scenarios and history navigation remain. |
| Ally conversations and level-up dialogue | Recruit allies and trigger health/level-up responses naturally, including special ability interceptions for Malevolamp/Peeper; inspect nickname substitutions and normal text timing. | All 1,624 non-null main-table sources are translated across the two dialogue catalogs. The latest build adds 1,227 sources including three Rosa alternatives: 3,707 English profiles and 1,253 Japanese pixel pairs pass. All 200 rows have native HP choices and both level-up selector slices checked. Actor/name slots, PRNG returns and waits are controlled; full wrapper/nickname-copy and natural event coverage remain. |
| Rosa/Ines conversation conditions | Reach their conversations naturally, check the inventory-dependent Rosa condition, all HP bands, four level-up responses, repeated-talk silence and when the talk counter resets. | Native checks cover five responses per HP band, counter values 0/3/4, silence field 19, and level-up fields 15–18. Rosa's three alternatives and index clamp pass with a controlled flag and +C4 field; the inventory scan and natural counter progression are not exercised. Reserved/test-style rows have no natural-reachability claim. |
| Default ally nicknames in natural gameplay | Recruit and rename allies naturally; check repeat-name numbering, active-party rules, later UI, dungeon suspend saves and rankings. | All 200 rows / 198 nickname sources are now translated. 2,000 native English generation cases, 600 Japanese control pairs, three guarded formatters, 200 editor displays and 62 joypad IDs pass. All defaults plus legacy/custom names survive native FLASH saves and fresh-core loads across both Adventure Logs, using controlled nickname fields in existing records. This does not establish natural recruitment or valid party state. Five-character ally storage and seven-character player names are preserved; Paulo remains distinct from Tipper. |
| Earlier gameplay messages in natural history use | Navigate history after ordinary combat/item actions, check timing and actual decorated/custom names, and investigate history persistence separately. | The 59-byte audit is complete for all 311 earlier core/help message templates. Sixteen messages were reflowed without changing words or allocation addresses; all 933 normal/wide/narrow native history cases pass. The old ROM reproduces truncation in those 16 with synthetic narrow names. Natural name reachability and history navigation remain unproven. See ALLY_DIALOGUE.md. |
| Ally management and shared services | Recruit/dismiss/register allies, use both adventure/battle contexts, perform successful warehouse transfers/sales and gold/token transactions, exercise capacity limits and scenario-specific headers. | All 138 entries have native formatting/display fixtures, including 24 ally menu layouts, numeric units and balance headers. Controlled handler entry plus normal buttons covers warehouse help/empty withdrawal/cancel and empty-bank/cancel. These do not establish natural NPC access, successful transactions or every surrounding caller layout. |
| Help, ally orders and status summaries | Try all dungeon help contexts, unlock and issue each ally order, combine status effects and scroll their list, and reach the shop-specific status branches. | All ten help pages, seven orders, 64 status table rows plus four literals, and 106 additional messages have native fixtures; two world help pages also have normal button navigation. Forced rows do not establish natural state selection or ally AI. |
| Original speed-summary discrepancy | Trace the second double-speed condition and decide whether its repeated two-attack Japanese summary should be corrected to one attack. | Both source rows currently say two attacks; translated as written. The help page correctly preserves the separate one-attack and two-attack explanations. No game-logic or source-bug fix is included. |
| Core gameplay effects and message history | Naturally trigger hunger warnings, status onset/recovery, curses, throwing/using items, full inventories, item losses and ordinary combat. Check scrolling/history and message timing together. | All 205 selected templates pass native message display and guarded substitutions, including width stress. Fixtures suppress per-glyph delay and do not execute every effect/caller. |
| Full command/settings contexts | Check transformed Abilities/Skills commands, allies, dungeon/arena variants and all settings/help routes in play. Confirm trap/stair choices perform the selected action; check empty-container prompts and conditional actor reveal labels in their actual callers. | All 262 core catalog rows have controlled display coverage, four computed command variants and three stair offsets retain native strides, and natural world settings left/right changes and restores the option. The ten help bodies now have separate coverage in the help milestone. |
| Dungeon transitions and result headers | Visit ordinary and puzzle dungeons, check full/display names, transitions and result/ranking contexts. | All 64 name pointers render in the native 120-pixel header, including a `#99` puzzle-number stress case. This is not a natural dungeon traversal. |
| Object search branches | Open/search chests, barrels, pots, dressers, cupboards and shelves in both unopened/opened states, with and without items. | All 14 message sources have native story display checks for both protagonists; actual ground-search event pointer reads also pass. Object triples have static reader evidence, not every natural branch. |
| Secondary item actions | Use, discard, rename, fill/pour, transfer into/out of containers and navigate warehouse service menus during ordinary play. | All 41 fixed action records fit; 14 secondary popup fixtures cover seven item categories. Shared service labels now have their own catalog and bounded fixtures; natural transfer/transaction contexts remain pending. |
| Protagonist-name contexts | Check Torneko/Tipper in later story, arena and status/reveal contexts. | `$t`, both fixed-name copies, 400 enemy-copy regressions and four detail screens pass. Entered Adventure Log names remain separate. |
| Natural dungeon identification | Acquire an unknown item, display its disguise, identify it and show the correct actual name/description. | Controlled readers cover all 246 disguise pointers and all 246 English disguise layouts. |
| Actual synthesis operation | Perform synthesis through the normal gameplay rules and inspect the resulting item. | Controlled wrapper coverage covers all 100 synthesis-description rows. |
| Multiple synthesis effects | Navigate a multi-effect item and check spacing, headings and displayed stats together. | Individual effects and the recorded mask case have controlled checks. |
| Item-state save persistence | Save and cold-load identified/synthesized items, retaining their state and text. | Player-name save/cold-load coverage does not establish item-state coverage. |
| Shops and further item contexts | Check price, container and other decorations alongside the English text; use item naming, tracks and graves naturally. | ITEM_DISPLAY.md adds 1,197 native composition cases and 20 previews: every item normal/priced, all 246 unknown-name rows, six custom width fixtures, all 200 grave actors, three tracks contexts and two hidden properties. The 100-byte output and x=130 price column pass. Natural naming limits, transactions, acquisition and additional container modes remain. |
| Natural enemy/ally contexts | Encounter monsters, recruit allies, inspect traits and exercise nicknames/status-dependent names during ordinary play. | All 200 species and trait rows have native checks in both details layouts; two guarded copy helpers and revealed-Cannibox item formatting are checked. |
| Frontend modes and recovery | Use each mode naturally, inspect real suspended runs, and verify recovery/deletion/initialization consequences with disposable saves. | FRONTEND_COMPLETION.md records 157 English screens, 86 Japanese pixel pairs, three native menus, fourteen 92-byte summary fixtures and both seven-character Adventure Log cold loads. Controlled error-message display does not perform deletion or damaged-save recovery. |
| Church/save services | Visit the three priest variants, unattended book and disembodied voice; check EXP information, curse removal, donations and actual save/quit outcomes. | CHURCH_SERVICES.md records 124 English cases / 162 complete pages, 86 Japanese pixel pairs, all 105 table words and 14 native source selections per variant. Natural access, transaction effects and accepting save prompts remain separate. |
| Rankings and dungeon results | Finish adventures naturally with both protagonists, browse score categories/details and confirm transition/save timing. | ADVENTURE_RESULTS.md records 1,794 English cases and 1,128 Japanese pixel pairs. Native 48-byte record writes/shifts in all eight categories, original FLASH persistence, fresh-core reads and both seven-character Adventure Logs pass. Ranking readers select built-in protagonist names; no editable name field or save-size expansion is needed. |

| Direct dungeon scenes and tutorials | Reach boss first/repeat encounters, free each villager group, trigger companion advice and test arena abandon consequences in disposable runs. | DUNGEON_EVENTS.md records 185 English screens / 116 Japanese pixel pairs, 31 key lookups, four boss/two abort selector slices, cold abort cache and original arena pause menu. The actual battles, travel branches and forfeits are not executed by those fixtures. |

| Remaining battle feedback and dungeon shops | Trigger wind/revival/obstruction states, recruit companions, use their actions, and complete shop/haggling transactions naturally. | BATTLE_COMPLETION.md records 843 English cases / 600 screens and 302 Japanese pixel pairs, 59-byte guarded history checks, original item symbols, complete pages, cold caches and 18 native selector slices. Actual effects, transactions, recruitment and persistence remain separate. |

| World merchants and equipment services | Visit ordinary shops and the Medal King; buy/sell, collect rewards, forge/synthesize equipment and collect player-shop proceeds, then verify persistence. | MERCHANTS.md records 282 English cases / 279 screens, 147 Japanese pixel pairs, guarded printf/world buffers, 23 native record selections and the original shop menu. Controlled pages and selectors do not execute the transactions or prove stock/save progression. |

| Shared keyboard / password workflows | Open the keyboard naturally from naming, history, password and inscription workflows; inspect the labels and exercise history selection/deletion. | KEYBOARD_COMPLETION.md records eight native layouts, exact original kana grid matches, guarded history buffers and four real joypad regressions. Natural password exchange and inscription matching remain separate. |

| Blank-scroll inscription gameplay | Naturally obtain/read a blank scroll, enter a learned English spelling, test an unknown/unlearned spelling, consume the result and save/reload the inventory. | INSCRIPTIONS.md records 549 English matcher cases, 255 legacy regressions, 51 learned-list selectors, all 49 list rows and four real joypad conversions through the original item caller. Effect consumption and persistent save consequences are not established by these fixtures. |

| Zoom restrictions / world items / inline warehouse messages | Attempt Zoom during the documented story restrictions; collect world items with free/full inventory and money; visit full warehouse and exit. | WORLD_COMPLETION.md records 40 English cases, actual paged-wrapper flags, 13 Zoom marker/selector handoffs, native world scrolling, guarded printf and two inline warehouse readers. Story progression, actual item grants and warehouse persistence remain separate. |

| Remaining system labels | Use Extra Mode, choose each character/companion, retry and suspend; inspect equipment/synthesis and growth types, object names and Adventure Log titles. | SYSTEM_LABELS.md records 549 native cases and 549 Japanese pixel pairs. Natural mode availability, confirmation responses, actual synthesis and full dungeon transitions remain separate. |

| Themed houses / companion commands | Enter themed monster houses as both protagonists; use talk, Kaclang, call-allies, warp and all three companion spells. | ENCOUNTER_UI.md records 42 native house-copy/handoff/queue cases and 12 menu/availability cases. Natural generation, companion effects and spell execution remain separate. |

| Arena winner presentation | Finish matches with no winners, ordinary winners and more than eight displayed winners; check payout. | ARENA_RESULTS_TEXT.md verifies native row formatting and controls. ARENA_GRAPHICS.md adds native indexed-heading and draw/defeat/victory proofs. Natural outcomes and payouts remain separate. |

For each completed route, record the exact ROM hash, fixture/steps, expected
and actual behavior, and screenshots or an automated report. Use disposable
fixtures for automation. Document any newly discovered ranges in
[MEMORY_MAP.md](MEMORY_MAP.md) before using them for insertion or RAM/save changes.

Language research and drafting can proceed meanwhile. Each new insertion
family still needs its own native checks; enemy-name limits must not be
inferred from item-name tests.

The remaining-display component covers sound-test help through controlled
native selectors/character loops and the live-floor log title through all
dungeon names at byte bounds. Natural diagnostic-menu entry/audio playback
and saved-log displays after actual dungeon progression remain separate.

Cold boot through the initial title now has separate natural automated coverage
in [BOOT_GRAPHICS.md](BOOT_GRAPHICS.md). Its nine pixel comparisons preserve the
original logo; the user explicitly chose to keep the Japanese title artwork.

User scope update: graphics work is deferred to a later phase. The user
reports dungeon-floor/arrival title cards and possible town/ending/credit
graphics; these require a separate discovery and translation pass. Do not
infer that the eleven boot/menu assets cover those families. Continue
ordinary text-source research and insertion checks now. The original Japanese
title artwork remains intentionally preserved.

The [latest combined-build regression](../build/completion/current-text-regression/verification.json)
passes the normal opening/escort/first-chief route with 46 messages and zero
unattributed reads. Fresh normal-button entry saves seven-letter Torneko in
both Adventure Logs, then cold-loads both from the final 65,536-byte save.
Slot one survives the slot-two write. The exact current ROM is pinned in that
report. These checks do not establish later gameplay or dungeon suspend.
Reproduce with `.venv/bin/python -m tools.verify_current_text_pass`.

[Natural first-cave coverage](NATURAL_CAVE.md) now includes Tessie's rest
choice, the second chief meeting, first cave entry, Copper sword/Wooden shield
pickup and equipment, two Slime battles and stairs to floor two. Both floor
tutorials and observed scrolling messages pass. Later floors, shrine access,
other branches and native dungeon suspend/save persistence remain pending.

The [text-polish route](TEXT_POLISH.md) additionally covers normal floor-two
Recovery pot pickup, tutorial scrolling, Look/Push menus and actual HP
restoration on the latest corrected ROM. The tutorial now matches the Push
action label. This does not establish cartridge save persistence.
