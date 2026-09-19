# Translation milestones and historical evidence

For the current build and remaining work, see [PROJECT_STATUS.md](PROJECT_STATUS.md).
`./build.sh` now publishes through `tools.build_medal_trade`, including the
completed prose review, English title, compact arrival cards, menu fixes and
approved conditional combat joining and medal Trade label. [BUILD.md](BUILD.md) describes the mandatory
publication gates and output receipt.

The sections below preserve earlier milestones and their exact ROM hashes.
References to “latest”, deferred graphics or pending prose within those dated
checkpoints describe that stage, not the current project state. The original
decision to preserve Japanese title artwork was later superseded by the approved
[English title insertion](TITLE_INSERTION.md).

## Historical checkpoint: 2026-09-13

Inventory at this checkpoint:  **8,422 authored sources + 822 retained
resources + 74 technically unclassified candidates = 9,318 inventory entries**.
The latest accepted [title insertion](TITLE_INSERTION.md) localizes the title
through its original graphics loader. Four paired boot routes, 484 prompt
frames, exact packed pixels/palette and 22 unchanged boot/menu image pairs pass.
It includes the accepted [rendering corrections](RENDERING_FIXES.md), which fix clipped
keyboard hints, the Records border, overlapping status panels and unnecessary
numeric line breaks in XP/level messages. It passes 166 paired formatter cases,
140 paired queue/history cases, 94 location cases and normal menu/input checks
using disposable copies of the user's saves. Natural combat awards remain
separate from the controlled message fixtures.
The included [Credits-adapted arrival insertion](ARRIVAL_INSERTION.md)
has all 36 arrival titles and matching floor lettering, along with the
[inventory](INVENTORY_NOTICE.md), [menu](UI_POLISH.md) and
[results-screen](RESULT_RUNTIME.md) fixes. Its 1,259 controlled arrival cases
and natural cave transition/fade/movement comparison pass.
The earlier [native save roundtrip](NATIVE_SAVE_ROUNDTRIP.md) verifies a naturally earned
defeat record, priest saving, cold records and both seven-letter Adventure Logs.
Other undiscovered graphics remain open; the already-English ending credits
are intentionally retained. The approved English title remains outside the
ordinary text-source count.
These counts describe the current inventory, not full-game discovery or
natural gameplay completion. Historical checkpoints below retain their own
ROM hashes and coverage limits.

The frozen starting point is the [early-journey build](EARLY_JOURNEY.md):
4,828 translated source entries out of 9,318, with 4,490 inventory entries
remaining. The [baseline hashes](../build/completion/before/hashes.json)
preserve its catalogs, glossary, ROM and ledger.

The [remaining-source review queue](../build/completion/remaining.json)
classifies 2,276 ordinary story leads, 29 story leads with additional controls,
1,592 other Japanese/uncertain resources and 593 internal or short candidates.
These are review categories, not approved insertion owners. Some entries are
original English diagnostics or false decodes; they must not receive invented
translations merely to make the counter reach 100%.

Work proceeds through remaining story scenes, shared services/UI and fixed
records, special formatter/name contexts, and the resource/discovery backlog.
Exact ownership is recorded before each insertion. Ordinary story drafts use
one cumulative catalog and the existing allocator; previously authored entries
are preserved as later sections are added. Native checks retain original
event parameters and compare Japanese relocation against the starting ROM.
All natural gameplay coverage continues to be stated separately.

The first preserved checkpoints passed their controlled native checks:

| Checkpoint | New source entries | Story cases | Choice menus | Japanese pixel pairs |
| --- | ---: | ---: | ---: | ---: |
| [Lighthouse](../build/completion/checkpoints/lighthouse/checkpoint.json) | 147 | 185 | 0 | 185 |
| [Castle and interview](../build/completion/checkpoints/castle/checkpoint.json) | 438 | 553 | 1 | 554 |
| [Royal scenes](../build/completion/checkpoints/royal/checkpoint.json) | 827 | 1,020 | 1 | 1,021 |
| [Coast and village states](../build/completion/checkpoints/coast/checkpoint.json) | 1,418 | 1,779 | 1 | 1,780 |
| [Complete ordinary story](../build/completion/checkpoints/story-pages/checkpoint.json) | 2,258 | 2,875 | 8 | 2,883 |

These are cumulative additions to the 4,828-source starting build. They do not
establish natural reachability of every scene. The castle checkpoint includes
both shopkeeper interview branches and all four Samson question choices. Its
earlier appended bytes are preserved exactly. Each checkpoint freezes its
catalog, ROMs, ledgers and verification harness before further drafting.

The cumulative working catalog currently has **2,258 translated sources / 2,810
owned pointer operands**, through the ordinary ending/postgame/rest-stop prose,
with eight complete native choice menus. All drafts pass source reconstruction,
control preservation and font/page validation. The frozen `story-pages`
checkpoint has passed its complete native run: 2,875 story cases, eight menus
and 2,883 Japanese pixel comparisons. Natural later-scene reachability remains
separate from these controlled checks. These counts do not include
the 29 pet-name story sources, two password hints, or other resource families.
Sixteen short binary-data decoding leads are explicitly excluded from prose
insertion, not counted as translated Japanese.

The royal checkpoint additionally passed the natural 46-message opening/chief
regression and native saves/cold loads of seven-character Torneko in both
Adventure Logs. These checks do not establish natural reachability of the new
later scenes. The existing save file remains 65,536 bytes.

Terminology additions remain explicit about their evidence. Puff-Puff matches
Japanese ぱふぱふ using the [secondary series reference](https://dragon-quest.org/wiki/Puff-Puff),
which documents XI/XI S usage; this is not a primary-source verification claim.
The GBA's own story remains the translation source. An [independent Japanese
reference](https://wikiwiki.jp/dqdic3rd/%E3%80%90%E3%83%98%E3%83%AB%E3%82%B8%E3%83%A3%E3%82%B9%E3%83%86%E3%82%A3%E3%82%B9%E3%80%91)
was used only to cross-check the ambiguous sealing clause at `009D8A98`:
Hell Justice was sealed by the god. It supplies neither English dialogue nor
imported mechanics. The unnamed Demon King remains unnamed; the local script
does not establish a specific other Dragon Quest villain's identity.

The [pet/password component](../build/completion/special/component-checkpoint.json)
adds **32 sources / 33 operands**. It passed 123 native story cases and 123
Japanese pixel comparisons, 15 real-keyboard input/commit/comparison cases,
and native pet-variable FLASH saves and cold loads in both Adventure Logs.
The seven-character password is `LETMEIN`; both hints and the comparison
keyword agree. Existing seven-slot pet storage needs no expansion. Tests include
short-name zero filling, cancellation and legacy Japanese pet names. This is
component acceptance; the larger story baseline has now also passed its
separate full verification.

The long `story-pages` native processes were terminated with signal 9 / exit
137 before completion; the cause was not established. Their partial evidence is
preserved under `verification-interrupted` and excluded from acceptance. The
replacement [chunk runner](../tools/verify_story_chunks.py) uses one short-lived
worker at a time and accepts an aggregate only when exact ranges, all case/menu
keys and all input/harness hashes match. The completed three-variant aggregate has passed; no partial run is counted.

A further **78 shared sources / 105 operands** have passed component checks in
[shared-story.json](../translations/shared-story.json): object searching,
synthesis services, transition narration and bonus-cave events. Nine exact
Japanese duplicates reuse our earlier independently authored wording. The
source's ソンビキラー spelling lacks the dakuten; the undead-effective weapon
example identifies the existing Zombiesbane glossary entry. Original source
bytes remain unchanged, and the typo is recorded rather than treated as a new
item identity. The [component report](../build/completion/shared-story/component-checkpoint.json)
records 139 native story cases, one choice menu and 140 Japanese pixel pairs.

The refreshed inventory contains **7,784 English-authored sources / 9,318**,
with **1,534 entries without English**. This is authored coverage, independent
of cumulative runtime acceptance. The remainder includes internal dictionaries
and binary decoding leads; discovery outside this inventory remains open. See
the [current progress report](../build/completion/progress.json).

The [arena component](../build/completion/arena/component-checkpoint.json) adds
**108 sources / 128 pointer words**: betting/allied/registered-monster service
prose, church choices, dungeon-entry conditions and save notices. All 216
English cases and 208 Japanese pixel comparisons pass, with eight native
menus, 40 full roster fixtures, 11 entry-warning combinations, 200 guarded
name/level copies and 12 detail-popup regressions. The list needed a private
208px window and a 160px odds column; full names, original betting logic and
previously owned popup patches are preserved. Exact ownership and the rejected
overlap attempt are recorded in [the memory map](MEMORY_MAP.md).

English component build: `build/completion/arena/torneko3-arena-services-english.gba`,
SHA256 `d4301abcf6aac837f2d0000f5643128bfc80a3812e2066a42a0758d73e1f0e07`.
The native component checks do not establish natural arena access, password
registration, battle outcomes or dungeon-entry inventory/save consequences.

The [adventure-history component](../build/completion/history/table-checkpoint.json)
adds **100 sources / 104 value pointers**. All 108 original key lookups,
400 English row cases, 69 native composite contexts and 269 Japanese pixel
pairs pass. Full wording remains in the catalog beside measured display forms.
The original reader establishes that the clear-record `$i0` field is elapsed
time; the initial draft assumption was corrected before acceptance.
All 64 Barinabo/dungeon-name variants and five turn/time records use their
original composition code. Natural achievements and actual maximum stored
counters remain separate from the stated numeric fixtures.

Previous combined component ROM: [torneko3-adventure-history-english.gba](../build/completion/history/torneko3-adventure-history-english.gba),
SHA256 `f9f9668257865acbc548a2f6d110a3c36f5c7ee3ad7e1829c3a59a97cd5979a2`.
Rebuild with `.venv/bin/python -m tools.build_adventure_history build`.

The [adventure-results component](ADVENTURE_RESULTS.md) adds **185 resources /
284 text pointers**, including **181 inventory sources** and four explicitly
reviewed short/empty resources outside that inventory. Its 1,558 English
result/list/detail cases, 236 ending/category cases and 1,128 Japanese pixel
comparisons pass. All 200 species and 370 items are checked with their widest
result partner. A private 216px detail window and eight result-only item display
forms fit the existing memory without changing full names or save records.

Native score creation/row shifting passes in all eight categories, followed by
original checksum/FLASH writes, identical fresh-core profile reads and both
seven-character Torneko Adventure Logs cold-loading. The 65,536-byte save needs
no ranking-name expansion: those records select the built-in protagonist name.
Natural dungeon outcomes and save timing remain in the playtest backlog.

Previous combined component ROM: [torneko3-adventure-results-english.gba](../build/completion/results/torneko3-adventure-results-english.gba),
SHA256 `6db4a44bb2f06ff976cae82bedb18224c35b6bc8c302d2257169240a6cb2bbff`.
Rebuild with `.venv/bin/python -m tools.build_adventure_results build`.

The [church-services component](CHURCH_SERVICES.md) adds **62 sources /
70 pointer words**. All 124 English cases / 162 pages and 86 Japanese pixel
pairs pass, together with all 105 positional table words and 14 original
greeting/save/oracle source-selection paths per variant. The five service
voices remain distinct, and 35 internal identifier words stay unchanged.

Previous combined component ROM: [torneko3-church-services-english.gba](../build/completion/church/torneko3-church-services-english.gba),
SHA256 `0ecfdac89e15a543194587cf10e18fc3ebde2f0d30cec23b92f66fe72cee124c`.
Rebuild with `.venv/bin/python -m tools.build_church_services build`.

The [remaining frontend component](FRONTEND_COMPLETION.md) adds **48 sources /
48 pointer words**, including complete mode help, save/recovery warnings and
Adventure Log summaries. Its 96 English source cases, three native menus and
14 summary-reader fixtures pass (157 screens), with 86 Japanese pixel pairs.
Both Adventure Logs cold-load seven-character Torneko into the opening.
No summary-window or save-layout changes were needed.

Previous combined component ROM: [torneko3-frontend-completion-english.gba](../build/completion/frontend/torneko3-frontend-completion-english.gba),
SHA256 `2d2bd38acc79fa6d7f2752ad1b89415967ec07dcd5941bc632a06b3e65fd805c`.
Rebuild with `.venv/bin/python -m tools.build_frontend_completion build`.

The [code-text reconciliation](../build/completion/code-text-reconciliation.json)
links six already-authored code-owned resources to their master IDs: puzzle
format, ally HP/species row, three keyboard hints and name confirmation. This
adds no ROM writes or new runtime-coverage claim. The original compact name
map/default and indirect keyboard resources are not counted as newly translated
prose.

The [composed item-label component](ITEM_DISPLAY.md) adds **20 sources /
21 pointer words**. Its 1,197 native item-format cases and 20 resource previews
pass, with 1,217 Japanese pixel pairs. Full identified/unknown names, quantities,
custom-name width fixtures, graves, tracks and hidden-name contexts fit the
existing 100-byte output and price column. All earlier writes are preserved.

Previous combined component ROM: [torneko3-item-display-english.gba](../build/completion/item-display/torneko3-item-display-english.gba),
SHA256 `1e9540ec1448916fa6c23e07307f24bc9f8e5191f8a983714860cf2d9d52294e`.
Rebuild with `.venv/bin/python -m tools.build_item_display build`.

The [direct dungeon-event component](DUNGEON_EVENTS.md) adds **63 sources /
82 pointers** from boss/rescue scenes, companion tutorials and arena pause
prompts. All 126 English source cases / 185 screens, 116 Japanese pixel pairs,
31 native tutorial lookups, six text selector cases and the original arena menu
pass. No layout, code, RAM or save change was needed.

Previous combined component ROM: [torneko3-dungeon-events-english.gba](../build/completion/dungeon-events/torneko3-dungeon-events-english.gba),
SHA256 `8c082e005b119c5385c80f2a814adbb505e4eae5e866fe76e7ecff791d019160`.
Rebuild with `.venv/bin/python -m tools.build_dungeon_events build`.

The [remaining battle component](BATTLE_COMPLETION.md) adds **298 sources /
382 pointers**: 247 scrolling feedback messages and 51 paged shop, companion
and recruitment prompts. All 843 English cases / 600 screens, 302 Japanese
pixel pairs, both cold caches and 18 original table selections pass. Normal,
wide and narrow substitution fixtures preserve exact history payloads within
59 bytes. Two original item symbols are retained; no font, layout, code,
RAM or save change was needed.

Previous combined component ROM: [torneko3-battle-completion-english.gba](../build/completion/battle/torneko3-battle-completion-english.gba),
SHA256 `5591e461e494946a56464327842cf8ef4a691a716a2ae14932ed451c945d2f04`.
Rebuild with `.venv/bin/python -m tools.build_battle_completion build`.

The [world merchant component](MERCHANTS.md) adds **132 sources / 453 pointers**
for ordinary shops, the Medal King, player shops, blacksmith and synthesis.
All 282 English cases / 279 screens and 147 Japanese pixel pairs pass, with
23 native record selections and the original three-row menu. The separate
256-byte printf and 1,024-byte world buffers pass normal/wide and byte-capacity
fixtures. Cash, stock, transaction logic and all earlier patches remain intact.

Previous combined component ROM: [torneko3-merchants-english.gba](../build/completion/merchants/torneko3-merchants-english.gba),
SHA256 `9d735a15224915e4436cc8e21b1ff426f598f72ab226c638e68cb2421d6e4904`.
Rebuild with `.venv/bin/python -m tools.build_merchants build`.

The [shared keyboard completion](KEYBOARD_COMPLETION.md) corrects six resources,
restores the caller-controlled History label, and uses original font 1 only for
preserved kana grids. All eight contexts, 16 history rows, guarded buffers,
four real joypad comparisons and 11 Japanese pixel pairs pass. Two existing
pointer patches are superseded explicitly, retaining their ledger history.

Previous combined component ROM: [torneko3-keyboard-completion-english.gba](../build/completion/keyboard/torneko3-keyboard-completion-english.gba),
SHA256 `8a6eb7fed361493b10383d792bd7a64e4fe4964a410f21c6551cc5aa8d3c178d`.
Rebuild with `.venv/bin/python -m tools.build_keyboard_completion build`.

The [blank-scroll inscription component](INSCRIPTIONS.md) adds English
seven-slot spellings for 49 scroll identities / 98 original kana sources.
The learned-scroll list shows these spellings. English matching ignores case,
requires the original learned flag and retains the original kana fallback.
All 549 English cases, 255 legacy regressions, 51 learned-list selections,
49 displayed rows, seven control pixel pairs and four real joypad inscriptions
pass. Item fields and save layouts retain their existing sizes.

Previous combined component ROM: [torneko3-inscriptions-english.gba](../build/completion/inscriptions/torneko3-inscriptions-english.gba),
SHA256 `577f519029f96c714ba1f1a53c68bdee0007d15e9bd67ca65f88217e455848f1`.
Rebuild with `.venv/bin/python -m tools.build_inscriptions build`.

[Retained-resource review](RETAINED_RESOURCES.md) now confirms 165 original
name-filter terms and one language-neutral history format. They remain intact
and are not counted as authored English. At the inscription checkpoint, that
leaves 835 inventory entries needing further classification/translation, in
addition to discovery and gameplay coverage outside this counter.

The [remaining world-message component](WORLD_COMPLETION.md) adds 19 sources /
21 pointer words: Zoom restrictions, item pickup/capacity observations and two
warehouse messages copied inline to RAM at startup. It passes 40 English cases,
13 Zoom selectors/marker handoffs, two warehouse readers, and all control pixel
pairs. Original initialized string storage and game logic remain unchanged.

Previous combined component ROM: [torneko3-world-completion-english.gba](../build/completion/world-completion/torneko3-world-completion-english.gba),
SHA256 `d15009ca598199febd4b0468638c161ad63574281abccb43f887ddd08ce25a7f`.
Rebuild with `.venv/bin/python -m tools.build_world_completion build`.

The retained-resource review now also confirms 139 history/tutorial lookup keys
(138 within the inventory). At the world-message checkpoint, inventory accounting was **8,336 authored
English + 304 retained + 678 still unclassified/untranslated = 9,318**.
The additional outside-inventory key is recorded separately. Native discovery
and gameplay coverage are still open.

The [remaining system labels](SYSTEM_LABELS.md) add 42 sources / 42 pointer
words, with 549 English cases and 549 Japanese control pixel pairs. Native checks cover
both menus, all 64 dungeon-entry summary titles and the fixed 23-byte copy,
12 growth labels, object names, all 370 item-statistic rows, 75 cap values,
three four-byte context fields and the remaining confirmations/details.
The original Adventure → Trip abbreviation is reused in bounded contexts;
record sizes, game logic, prior patches and source data remain intact.

Previous combined component ROM: [torneko3-system-labels-english.gba](../build/completion/system-labels/torneko3-system-labels-english.gba),
SHA256 `e57a95e98f74f5cbf4ea745b4f192096d38a05331ede5daf780b40b27d7ccdf1`.
Rebuild with `.venv/bin/python -m tools.build_system_labels build`.

Before result-key classification: **8,378 authored English + 304 retained + 636
still unclassified/untranslated = 9,318**. Discovery outside the inventory and
natural gameplay coverage remain open.

The retained audit additionally confirms 101 result lookup keys. Current
accounting at that checkpoint was **8,378 authored English + 405 retained + 535 still
unclassified/untranslated = 9,318**; no new English is claimed for keys.

The [encounter UI](ENCOUNTER_UI.md) adds 36 sources and corrects one existing
house announcement. Both protagonist tables, all themed houses and fallback,
five companion menus and all eight spell-availability combinations pass:
54 English cases / 54 Japanese control pixel pairs. The existing narration
pointer is explicitly superseded with its complete prior ownership preserved.

Previous combined component ROM: [torneko3-encounter-ui-english.gba](../build/completion/encounter-ui/torneko3-encounter-ui-english.gba),
SHA256 `263c9ac4b2321967a30cafc7fdb59c078629969aa373e51109ce840b4d5dc878`.
Rebuild with `.venv/bin/python -m tools.build_encounter_ui build`.

Accounting at that checkpoint: **8,414 authored English + 405 retained + 499
still unclassified/untranslated = 9,318**. Discovery and natural gameplay
coverage remain open; the corrected existing narration is counted once.

The [remaining arena outcome text](ARENA_RESULTS_TEXT.md) adds three resources.
All 200 actor names, full eight-row boards and both result labels pass 205
English cases / 205 Japanese control pixel pairs. The separate indexed graphic
heading is still Japanese and is tracked for the next investigation.

Previous combined component ROM: [torneko3-arena-final-english.gba](../build/completion/arena-final/torneko3-arena-final-english.gba),
SHA256 `f71bc1e8151508385d92fd287ea8e16ed5206571b79892cc001a738a55720fdf`.
Rebuild with `.venv/bin/python -m tools.build_arena_final build`.

Current accounting: **8,417 authored English + 405 retained + 496 still
unclassified/untranslated = 9,318**. Graphic resources outside the text
inventory, discovery and natural gameplay coverage remain open.

The [indexed arena graphics](ARENA_GRAPHICS.md) add six translated resources
outside the ordinary-string inventory: winning monsters, battle results,
Tipper's allies and all three outcomes. Five native presentations and five
Japanese pixel pairs pass, with exact whole-window tile-buffer comparisons.
The previously identified Japanese arena graphic heading is now translated.

Previous combined component ROM: [torneko3-arena-graphics-english.gba](../build/completion/arena-graphics/torneko3-arena-graphics-english.gba),
SHA256 `a3f1088e83d01bf2692806e67fe80c5a842fd3eedb6d9d2f1beb86f97ee2e79d`.
Rebuild with `.venv/bin/python -m tools.build_arena_graphics build`.
The ordinary inventory remains **8,417 authored + 405 retained + 496 open**;
the six graphic phrases are tracked separately. Other discovery and natural
gameplay coverage remain open.

The [scene-resource audit](SCENE_RESOURCE_AUDIT.md) identifies 205 event command
prefixes through native scene readers and dispatch. Together with original
ASCII placeholders, character-input assets, a cash field and one naturally
observed command, retained accounting is now **635 ordinary entries**.
Current ordinary inventory: **8,417 authored + 635 retained + 266 open = 9,318**.
The six translated arena graphic phrases remain outside that count. The
latest playable ROM is unchanged by this classification work.

The [background graphics audit](SCENE_GRAPHICS_AUDIT.md) confirms another 71
extraction candidates as native tile pixels or metatile indexes. Eight more
candidates are contained within already verified command operands. Current
ordinary inventory: **8,417 authored + 714 retained + 187 open = 9,318**.
All retained source bytes remain unchanged in the accepted arena-graphics ROM.

The [auxiliary and neutral audit](AUXILIARY_RESOURCES.md) classifies another
22 typed numeric/input resources and 64 unchanged formats/original English
diagnostics. Current inventory: **8,417 authored + 800 retained + 101 open =
9,318**. No ROM allocation or source bytes change in this classification pass.

The [remaining display component](REMAINING_DISPLAY.md) translates the four
sound-test help lines and the live-dungeon floor suffix. All four native help
selectors and all 64 dungeon names at floor-byte bounds 0/255 pass, using both
Adventure Log slots and seven-letter names: 132 English cases and 132 Japanese
control pixel pairs. Complete ROM images reconstruct from the collision ledger.

Latest combined component ROM: [torneko3-remaining-display-english.gba](../build/completion/remaining-display/torneko3-remaining-display-english.gba),
SHA256 `f0c51f1b3a4229964d23a2f0416bb854dafe1196799ce4ccea2302b211e7fb97`.
Rebuild with `.venv/bin/python -m tools.build_remaining_display build`.
Current ordinary inventory: **8,422 authored + 800 retained + 96 open = 9,318**.
Resources outside the inventory and natural gameplay coverage remain open.

A separate [unowned-language review](UNOWNED_TEXT_REVIEW.md) now preserves 30
English drafts and one unresolved phrase. These have not been inserted and do
not advance the 8,422-source combined-ROM count or close their technical reader
investigations. Other translation and discovery work continues.

A further [native field audit](../build/completion/remaining-field-audit/native-verification.json)
confirms four numeric fields, two event commands and eleven original ASCII startup values. The
later consumers of those ASCII values remain unconfirmed. Current inventory:
**8,422 authored build-catalog sources + 817 retained + 79 open = 9,318**.
The separate 30 uninserted drafts remain part of the open technical queue.

The [cold-boot graphics audit](BOOT_GRAPHICS.md) now covers the first 600
frames with native copies and nine Japanese/English pixel pairs. It confirms
a Japanese illustrated title logo outside the ordinary text inventory. The user chose to preserve the original Japanese title artwork; it is an
intentional retained graphic, not an unfinished English title insertion.

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

The [natural first-cave regression](NATURAL_CAVE.md) now extends that checkpoint
through Tessie/rest, the second chief meeting, cave entry, sword/shield
equipment, Slime combat and the stairs to floor two. Its 27 story messages,
two paged tutorials and 88 nonempty whole-string draws pass; native scrolling
completes and the final screen matches the recorded exploration. The 31
unowned Japanese source watchpoints do not fire on this route. This adds
natural gameplay evidence, not new translations or an unused-source verdict.

The subsequent [gameplay wording correction](TEXT_POLISH.md) fixes the Recovery
pot tutorial's “Press”/“Push” mismatch. The newest combined ROM is
[torneko3-text-polish-english.gba](../build/completion/text-polish/torneko3-text-polish-english.gba),
SHA256 `09bb26e91250a7a958783f12fed53ca3e687cab1387c93448deea48afc8c1a2b`.
All 46 observed draws per variant pass a normal pickup/menu/pot-use route;
the final result is identical and only the intended message wording changes.
All earlier allocations and unrelated patches remain byte-identical.
The retained-resource audits pass on this ROM. Counts remain 8,422 authored,
817 retained and 79 unclassified; graphics work remains deferred.

The later [results animation correction](RESULT_RUNTIME.md) and [Records menu
label](UI_POLISH.md) retain their own paired native evidence. The current ROM
also fixes the 128px [empty-inventory popup](INVENTORY_NOTICE.md), using the
display form “No items.” while preserving full English in the catalog and the
larger paged message. Cumulative ROM:
[torneko3-inventory-notice-english.gba](../build/completion/inventory-notice/torneko3-inventory-notice-english.gba),
SHA256 `8757bf5cd89e6b935c8f99c431600eb6b5367ad9e9078158a84c047cf6d6e960`.

The [native save roundtrip](NATIVE_SAVE_ROUNDTRIP.md) starts with fresh seven-letter
logs and follows the normal opening, first-floor defeat, village return and
priest save. A fresh core reads the earned ranking/history and loads Log 1
in the village; an independent cold load confirms Log 2 remains intact.
The native saved profile and complete save file match. This is a defeat/save
route, not a cave clear or dungeon-suspend test. No new inventory source is
added by the popup display override; unclassified-source research continues.

The [resource-boundary audit](RESOURCE_BOUNDARIES.md) confirms five more
candidates as native metatile/animated-tile data or RGB color fields, including
one apparent string that crosses an asset boundary. The ROM stays unchanged.
Current accounting is 8,422 authored + 822 retained + 74 open; the remaining
queue has 31 Japanese review sources, 42 original ASCII sources and one combined
character-map candidate. None of those unverified sources is treated as free
space or granted insertion ownership.

The [seventeen-candidate gameplay pass](GAMEPLAY_CANDIDATES.md) checks adjacent
landing, dungeon-name, item-footer, frontend and status-prefix readers in the
Japanese and current English ROMs. All controlled cases pass; no new reader
ownership follows. The literal-star loss sentence remains unresolved, with
the user's plating lead preserved. Accounting and the accepted ROM are
unchanged. A separate normal-button route is being extended beyond floor two
toward a successful clear and subsequent native save/reload.

That [successful cave-clear roundtrip](CAVE_CLEAR.md) now passes on the same
ROM: 435 uninterrupted inputs from the accepted opening through all three
Mysterious cave floors, the Shrine of the Gods meeting, Ines joining, the map
handover and priest save. It verifies 83 story messages, 11 paged messages,
220 whole-string draws and all 17 result-animation steps. A fresh core checks
40 further draws, all 2,205 white result pixels, the earned 4,002-point clear
record, the progressed Log 1 and unchanged Log 2. All native name copies retain
Torneko. No new source or patch is added; the 74 technical candidates, later
gameplay, suspend/resume and deferred graphics remain separate work.
