# Tutorials and gameplay feedback

Historical milestone. The current [ally-dialogue build](ALLY_DIALOGUE.md)
retains this component and completes the previously pending history audit:
all 311 earlier core/help messages pass, with 16 whitespace-only reflows.
The artifacts and counts below remain specific to this earlier ROM.

Completed 2026-09-11. Open
[torneko3-tutorial-gameplay-english.gba](../build/tutorial-gameplay/torneko3-tutorial-gameplay-english.gba)
in mGBA. This combined build adds **285 translated entries**, retaining the
previous ally/services build, all earlier translation components and the
seven-character Adventure Log name with default **Torneko**.

| New family | Entries | Scope |
|---|---:|---|
| Item tutorials | 9 | Equipment, food, healing, fire breath, sleep, warping and strength recovery |
| Gameplay messages | 165 | Combat, traps, stat changes, magic/item cancellation, curses, deterioration, staff use and monster abilities |
| Joined damage fragments | 5 | Attacker prefix and normal/critical/brutal damage continuations |
| Object-category labels | 8 | Items, statues, graves and their combinations |
| Equipment-effect labels | 98 | All 100 effect-name table indices, including three references to None |

These are verified sources already present in the broad extraction. This is
not a claim that every gameplay or story message in the ROM is now translated.
The [catalog](../translations/tutorial-gameplay.json) records exact source bytes,
340 pointer owners and editable English. The [review sheet](../translations/tutorial-gameplay-terminology-review.tsv)
covers every entry; the [screenshot montage](../build/tutorial-gameplay/verification/english-montage.png)
shows controlled native rendering examples.

## Language and layout

Existing exact-identity glossary choices are retained: **Fuddle, Fizzle,
Kasap, Acceleratle, Harvest Moon, Weird Dance, Mimic**, and the reviewed
Shaman/Sorcerer/Rage staff names. Project status wording includes **sealed,
whiffing** and **leaky belly**. Binding, Farsight, Wearproof and Parrying follow
their existing item/effect terminology. No new official-name claim is made.
The 98 short effect labels are registered as project wording with their
Japanese identity and source context; ambiguous labels such as 封, 印 and
黄金効果 are kept conservative instead of inventing mechanics. The glossary
now contains **1,085 terms**. All prose was independently translated from the
pinned Japanese original; no fan English or font assets were used.

Two runtime details constrain these messages:

- The live queue has 80 bytes per row, but message history stores only **59
  payload bytes** inside each 64-byte record. English wrapping checks that
  tighter limit as well as **208px** width, after substitutions. Wide-glyph
  and narrow-character profiles test different failure modes. All four
  100-byte item slots, including `$i2` and `$i3`, are exercised.
- Tutorials preserve their single **`$w`** command and the division between
  explanation and instructions. Native formatting turns it into `03 1F`;
  the renderer sets the original pause/scroll flag. Leading **`!`** in damage
  fragments is a continuation control and is consumed before display/history.

The original dungeon renderer has a **208x40px** viewport. It draws rows at
y2, y14 and y26, stages a fourth row at y38, then runs its existing scroll
callback. That staging row is intentionally below the visible area. Verification
checks every rendered glyph and horizontal boundary, the pause screen, and the
final scrolled screen; it does not treat that temporary y38 row as a new layout
bug. There is no new font, window enlargement, RAM reservation, game-logic
patch or save-layout change.

## Ownership and storage

[MEMORY_MAP.md](MEMORY_MAP.md#tutorials-gameplay-feedback-and-history-2026-09-11)
records the source/table ranges, initialized RAM pointers, queue/history fields
and fixture scratch before insertion. Object, strength-loss, cancellation and
trap pointers live in a ROM image copied into EWRAM at startup. They must be
patched in that initializer and tested from a cold boot. All four identified
table ranges are covered; null fields and table shape are preserved.

One allocator composes this component after every prior component. All original
source bytes and earlier allocations/patches remain exact. New destinations are
owned by the combined ledger; no old text, gap or padding is reused.

| Combined English build | Value |
|---|---:|
| ROM size | 32 MiB |
| Total appended bytes including alignment | 83,476 |
| Added in this milestone | 7,747 |
| Appended capacity remaining | 16,693,740 |
| Allocations / checked original patch ranges | 2,459 / 2,867 |

The occupied appended interval is `[01000000,01014614)`. The previous build
ended at `010127D1`. Exact destinations and source hashes are in
[english-build.json](../build/tutorial-gameplay/english-build.json).

- English SHA-256: `66c53aa470d31c73e093f5c053ea38e525ea8c47d8070266be4595626c270f24`
- Japanese relocation control: `59ba7fbb9d260b47777561a194ef8411f3df1ac5b57f4394fe52d78cbd198a1e`
- Previous English baseline: `d8e185dac51a357dc6a39640062e13d796805b12d9f98d9e5a557004f93f922e`

## Automated verification and its limits

[acceptance.json](../build/tutorial-gameplay/acceptance.json) ties the following
to the exact ROM, catalogs, fixture state, harness and terminology review:

- **131 unit tests**, a byte-identical fresh rebuild, shared allocation checks,
  all earlier catalog bytes and master English/notes preserved, and all **9,318
  extracted sources** round-tripping exactly.
- **855 English native cases**: normal, wide-glyph and narrow-character profiles
  for all 285 entries. Each executes the original formatter and live queue/history
  writer. The two display profiles produce **580 screenshots** including the
  separate joined-message sequences and pause screens.
- **294 Japanese/baseline screenshot pairs**, all pixel-identical. Japanese and
  baseline cases use the same native paths as English.
- Per ROM variant: **four cold-boot initializer checks**, **100 guarded effect
  copies**, those **100 copied labels in removal feedback**, **eight guarded
  object-label copies**, and original selection slices for **nine tutorials,
  three strength messages, 25 cancellation entries and 40 trap/context entries**.
- Four joined-damage sequences per variant, including native queue and history
  index wrapping. Continuation flags and full history payloads are checked.
- Prior-component regression: **400 enemy-name copy guards**, both protagonist
  copies, 14 secondary menus, two normal-button ground searches, 14 item
  inventory/information screens, four protagonist detail screens, and **Torneko
  creation/save/cold-load**, retaining the **65,536-byte** cartridge save.

These are controlled fixtures. The opening-world state has no dungeon history
structure, so tests provide a guarded disposable history backing and stop the
queue function before its unrelated scheduler call. Rendering retains native
instructions and scrolling but bypasses frame-yield calls and button waits.
Native table-selection slices stop before unrelated combat/effect mutations.
Older raw states have their four static pointer-table slices refreshed from
independently verified cold-boot values; this does not simulate startup by
arbitrarily patching expected English pointers into the state.

Natural tutorial pickups, full combat/trap sequences, effect-removal gameplay,
message-history navigation and timing still belong in
[PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md). The history record is a runtime
structure offset; its save persistence and ranking/name storage are not proven
by these tests. Personal playtesting can remain deferred.

## Reproduce and continue

```bash
.venv/bin/python -m tools.build_tutorial_gameplay
.venv/bin/python -m tools.verify_tutorial_gameplay_all
```

To audit the existing artifacts without rerunning native fixtures:

```bash
.venv/bin/python -m tools.verify_tutorial_gameplay_all --summarize-only
```

Edit only catalog English/display/notes. Source and pointer metadata are checked
against fresh extraction. New translations or wording changes require an updated
terminology review and native evidence before acceptance. The master browser
uses this catalog as an overlay and preserves independent full drafts.

The next broad translation area is narrative and ally dialogue, with further
scenario-specific text and unreviewed pointer owners tracked separately. The new
history limit should also be audited against earlier gameplay catalogs before
claiming complete message-history coverage for the combined translation.

The initial static audit of unchanged core/help templates flags **16 lines**
under maximum narrow-name assumptions; the exact catalog/ROM hashes and lines
are in [earlier-history-audit.json](../build/tutorial-gameplay/research/earlier-history-audit.json).
That is a bound to investigate, not evidence of 16 naturally reachable errors.
