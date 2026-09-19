# Menu action width audit

Audited 2026-09-19 against published ROM `0c21286fadcb`, full SHA-256
`0c21286fadcb59776b7a6639ce082a7a3180faa01621a8afc74c6d6601ebfc13`.
This records the pre-fix audit. The subsequently approved
[medal Trade fix](MEDAL_TRADE.md) is now implemented; other labels are unchanged.

## Findings for review

**One confirmed overflow was found: the Medal King's Exchange action.**
The previous fix changed the casino-specific pointer, leaving this separate
merchant label unchanged. Both use the same narrow trading popup renderer.

Widths below use font 0 with native zero spacing. Available width excludes
the label's starting inset. Required width includes cursor advance and visible
ink; this is more conservative than counting just the last painted pixel.

| Label / context | Required | Available | Result | Proposal |
|---|---:|---:|---|---|
| Exchange — medal trading | 42px | 36px | Overflows by 6px; visible ink by 5px | Change this action to **Trade** (28px), matching the casino |
| Trade — casino | 28px | 36px | Fits, 8px spare | Keep |
| Take out — narrow secondary action reader | 43px | 44px | Fits, only 1px spare | Keep; preserve the 48px window and test this longest label |
| Withdraw — narrow warehouse transfer action | 43px | 44px | Fits, only 1px spare | Keep; same geometry requirement |
| Discard — warehouse action | 35px | 44px | Fits, 9px spare | Keep |

The last two longest-label cases invoke the real secondary reader with valid
caller-supplied label pointers. They establish layout capacity, not completion
of a natural transfer transaction. The normal inventory Take out actions begin
at x=0 in a 48px window, leaving 5px; the secondary x=4 placement is tighter.

There is no reason to shorten every long verb. Several menus size themselves
appropriately or already have ample room:

| Label / context | Required | Available | Spare |
|---|---:|---:|---:|
| Withdraw — bank menu | 43px | 52px | 9px |
| Instructions — warehouse service menu | 58px | 68px | 10px |
| Unregister — ally management | 49px | 68px | 19px |
| Part ways — ally management | 50px | 68px | 18px |
| Leave Bout — ally management, four-letter context fixture | 53px | 68px | 15px |
| View next opponents — arena | 97px | 108px | 11px |
| Warp somewhere — companion menu | 77px | 84px | 7px |
| Go Your Own Way — ally orders | 84px | 124px | 40px |

Two non-verb settings rows also deserve protection against future widening:
Text speed's final Fast option ends at x=150 in a 152px region (2px spare);
Display's final Norm option ends at x=151 (1px spare). Neither overflows now.
No wording change is proposed for them.

## Coverage and limits

The [catalog inventory](../build/menu-action-audit/label-inventory.json) lists
215 entries from explicitly typed action, menu, command, choice, order and
settings families, relevant standalone service labels and frontend entries.
Control templates are not measured as literal text. Catalog wording is not
automatically current ROM wording: casino Exchange, for example, is superseded
by Trade in the published build. Runtime cases read the current ROM pointers.

The [native report](../build/menu-action-audit/native-summary.json) contains
139 controlled cases on the current ROM:

- 16 menu tables covering church, arena, warehouse/bank, companion and shop choices.
- 24 ally-management cases: all 12 groups with both context profiles.
- 14 secondary action cases across seven item categories.
- Medal/casino trading popup draws using each current caller label.
- Extra-mode, party-selection and seven-order menus.
- 37 settings callback cases, including arena variants.
- All 41 fixed action records through the inventory action reader.
- Two additional narrow secondary-reader cases for Take out and Withdraw.

Only the medal Exchange case exceeds its horizontal bounds. The audit includes
reserved action records, so the 41 cases are not 41 distinct natural commands.
Native traces and PNGs are retained next to the report. These are disposable
reader fixtures, not screenshots of natural visits to every service; some
background text comes from historical fixture states.

This does not prove every undiscovered menu or every conditional story choice
safe. Frontend entries are inventoried but not freshly replayed by this harness;
their earlier evidence remains in the frontend reports. Settings callbacks use
the established 152px drawing contract. A screenshot/state of a different
Exchange context would help identify a further caller, but is not needed to
establish the medal-trading overflow above.

## Reproduce

```sh
.venv/bin/python -m tools.audit_menu_actions
```

Requires the published ROM, native mGBA environment and existing world-state
fixtures. The harness writes reports/screenshots under `build/menu-action-audit/`
and uses temporary cartridge saves. It does not modify user saves or publish a
ROM. It reports overflows rather than treating the known bug as a failed run.

## Approved follow-up

The user approved the medal-specific change to Trade. [Implementation and
regression checks](MEDAL_TRADE.md) complete the following plan:

Patch the medal-specific label to Trade through a new checked
cumulative component. Add its actual popup to the publication regression gate,
including an assertion that the current medal caller resolves to Trade and that
the full word fits. Retain the longest-label capacity checks for Take out and
Withdraw. Do not globally replace Exchange in dialogue or widen shared windows
for this one label.

Pointer, renderer and fixture details are recorded in
[MEMORY_MAP.md](MEMORY_MAP.md#menu-action-width-audit-2026-09-19).
