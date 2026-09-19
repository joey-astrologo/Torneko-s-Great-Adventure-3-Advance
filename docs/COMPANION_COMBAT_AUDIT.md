# Monster-companion combat line audit

Historical audit, 2026-09-19. The subsequently approved
[implementation](COMPANION_COMBAT.md) now handles these name controls.
This audit itself made no ROM or translation changes. Tested published ROM
`e1f2babeb6b06ffdc9f52c4c190859a1f8e6712688dc7d3465736fbb55cc032e`.

## Cause

The reported XP/damage templates are already in the approved joining lists.
The missed case is the substituted actor name, not a separate untranslated
companion-message catalog.

Native ally-name formatting produces colour controls around the nickname:
`03 05 05` + `Goot1` + `03 06`. Some callers include `Lv99` inside the styled
name. The damage/XP joiner and broader combat joiner reject bytes outside
printable ASCII when measuring a prospective line. Encountering `03` therefore
keeps the original break even when the visible sentence easily fits.

Existing combat tests populated the actor slots directly with plain names,
long ASCII names or Japanese bytes. They did not pass the decorated output of
the native ally-name formatter into the joining tests. Nickname formatting had
separate coverage, but the combined path was missing. This was a test-coverage
omission in the earlier fix.

## Lines requiring the shared fix

| Message family | Desired one-line sentence when it fits | Current source IDs |
|---|---|---|
| XP gain | `<ally> gained <n> XP.` | `gameplay.001b4e23` |
| Defeat followed by XP | Keep the defeat sentence separate; join `<ally> gained <n> XP.` | `gameplay.001b4e38` |
| Level gain | `<ally> reached level <n>.` | `gameplay.001b4e7b` |
| Damage received | `<ally> took <n> damage.` | `gameplay.001b4dac`, `tutorial.001b6d7d`, `tutorial.001b6d93` |
| Ordinary damage continuation | `<ally> took <n> damage.` | `prose-review.tutorial.001b507e`, including its +1 continuation entry |
| Damage dealt | `Dealt <n> damage to <target>.` | `gameplay.001b4d95` |
| Critical damage dealt | `A critical hit! Dealt <n> damage to <target>.` | `gameplay.001b4df1` |
| Critical/brutal damage continuation | `Critical hit! <ally> took <n> damage.` / `Brutal blow! <ally> took <n> damage.` | `tutorial.001b5038`, `tutorial.001b505b` |
| Other approved feedback | HP/Strength recovery, status effects, attacks and other actor-bearing sentences | Full inventory below |

For example, Goot1 gained 6 XP. is 92px; Goot1 took 6 damage. is 104px;
Goot1 reached level 6. is 107px. Each comfortably fits 208px and the 59-byte
payload limit even with the five name-style bytes. Longer names, level suffixes,
multiple styled actors and extreme numeric values still need runtime checks.

The [complete affected-source inventory](companion-combat-affected.tsv) contains
**177 source keys representing 176 distinct templates**: eight earlier
XP/level/damage templates plus 168 templates from the broader approved combat
pass. One damage continuation has both the full source and its +1 entry key.
These are not 176 new translations or 176 messages exclusive to companions.
The same templates can refer to enemies or other actors. Their behaviour depends
on the actual substituted name.

The inventory is restricted to already approved joining spans. It does not
newly approve the earlier 35 deferred marginal spans, dialogue, event pauses,
or joining separate defeat/XP sentences together.

## Reproduction and evidence

[Native report](../build/companion-combat-audit/report.json), produced by:

```sh
.venv/bin/python -m tools.audit_companion_combat
```

The harness runs actual Slime nickname generation with suffix 1 and all three
native actor-name formatters on the current ROM. They yield two distinct forms:
coloured Goot1, and coloured Goot1Lv99. It passes each into the native message
formatter and compares against the exact same visible name without styles.

- 354 comparisons across the 177 actor-bearing approved source keys.
- 345 comparisons lose a join when styles are present; every source key has
  at least one affected comparison. The remaining nine long-form comparisons
  already retain breaks with the plain name, so are not additional failures.
- Actual queue/history calls reproduce two rows instead of one for XP, level
  gain and damage with the coloured short name. The plain-name controls join.
- Guarded output buffers remain intact. Tests use disposable emulator states
  and temporary cartridge saves; this is not a natural Tipper battle replay.

The older nickname fixture supplies viewer/actor fields solely for controlled
formatter calls. The reproduced failure does not require the user's state,
but a state just before a companion earns XP or takes damage would add natural
route coverage after the fix. Old saved history will retain old line breaks.

## Approved fix plan

1. Extend **both** existing joining paths to recognize the verified name colour
   and reset controls. Preserve them byte-for-byte and treat them as zero-width;
   count actual nickname letters and any level suffix normally.
2. Count style bytes toward the real 59-byte history payload limit. Keep the
   208px width limit, source allowlists, destination bounds, continuation rules
   and fallback for unsupported/malformed control sequences.
3. Add decorated native-name profiles to damage/XP and broad-combat build tests,
   including names with levels, multiple styled actors, exact size boundaries,
   short destinations, colour reset after the name, and queue/history output.
4. Verify ordinary, critical and brutal damage continuations and representative
   rendered rows, then publish only after the existing build checks pass.

No translation rewrites, shorter nicknames, loss of name colour, save-format
changes or global removal of line breaks are proposed. New code/table ranges
must be recorded in the memory map before insertion.
