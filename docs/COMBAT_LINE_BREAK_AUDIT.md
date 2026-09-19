# Combat line-break audit

**Historical audit, approved on 2026-09-19.** This report describes the pre-change
ROM below. The approved implementation and runtime evidence are recorded in
[COMBAT_LINES.md](COMBAT_LINES.md). The audit itself made no ROM changes.

Published ROM SHA-256: `84cc6f736f3eff1e24fbd1a9cb99f11e517298c8da831eecb7c169cb636a7344`.

## Recommendation

Use measured, conditional joining for the candidate sentence spans below. Join only after the real names, item labels and numbers have been substituted, and only if the resulting ASCII text fits **208 pixels and 59 payload bytes**. Otherwise preserve the current breaks. Keep sentence/event boundaries, pauses, indexed glyphs and dialogue pacing. Do not shorten official names or rewrite prose in this pass.

There are **303 candidate sentence spans in 303 templates**. Of these spans, **0** fit even the conservative ASCII slot-capacity bounds. The others require a runtime fit check; a short example is not a guarantee for every name.

**Recommended first pass: 268 spans that fit the stated short-name fixtures**, with fallback for longer substitutions. **Defer 35 marginal spans** whose example already exceeds the limit. They may fit unusually short substitutions, but are lower priority. Two critical/brutal continuation fragments are separately listed for dedicated validation.

Examples that fit: “Slime recovered 6 HP.” (105px), “Torneko avoided the poison.” (133px), and “Torneko is no longer confused.” (147px). These are measured examples, with the same conditional fallback required for longer actors.

Of the **379 multiline log/feedback templates**, 303 have candidate spans, 2 are continuation cases, 8 already have joining, and 66 should keep their current layout in this pass.

## Scope and evidence

This inventories every currently inserted entry in the message/queue families of the four combat/gameplay catalogs, plus tutorials and the encounter announcement to make exclusions explicit. Includes item-use, traps, status changes and dungeon feedback, not only direct attacks. Current bytes are read through every recorded pointer owner and checked against the combined build ledger; superseded translations are not used for measurements. Paged conversations, system notices, ally-order notices and the narrower Ground popup are excluded from log joining. Entity labels, item descriptions, story dialogue and menu tables are not combat log sentences. This is an audit of the known inserted inventory, not proof that no undiscovered text exists.

| Catalog | All entries | Audited family entries |
|---|---:|---:|
| core-gameplay | 262 | 205 |
| tutorial-gameplay | 285 | 179 |
| gameplay-help | 191 | 106 |
| battle-completion | 298 | 298 |
| encounter-ui | 37 | 1 |

| Classification | Templates |
|---|---:|
| no-break | 342 |
| outside-log | 68 |
| candidate | 303 |
| keep | 62 |
| already-handled | 8 |
| continuation-review | 2 |
| keep-dialogue | 2 |
| keep-controls | 2 |

Total: **789 templates**, **435 containing LF**, **496 LF boundaries (including excluded families)**.

### How to read the measurements

`↵` marks a current ROM line break. `$mN` is an actor/name slot, `$iN` an item/effect slot, `$dN` a number and `$t` the protagonist substitution. Example fixtures use Torneko, Slime, Medicinal herb, Bread and 6; these demonstrate space usage, not that each fixture can occur at every call site. Width uses font 0 from the ROM. The conservative joining guard sums max(advance, ink width) for each glyph, matching the existing hook; a few edge glyphs can therefore cost more than the exact rendered extent.

The upper bounds allow 29 ASCII bytes per actor slot, 99 per item slot, seven for the protagonist and signed 32-bit numbers. These are conservative storage bounds, not claims that normal item names reach those lengths. The builders’ nominal 120px actor/144px item budgets are not sufficient evidence to delete breaks unconditionally. Non-ASCII substitutions must fall back. No battle replay or new native runtime test was performed for this audit.

## Candidates for conditional joining

Only the spans shown are considered for joining. Other sentence boundaries in the same template remain. “Example exceeds” means this specific fixture stays wrapped; shorter real substitutions may fit. Such entries are deferred in the recommended first pass, not a promise of a one-line result.

| ID | Current span → proposed joined span | Example guard px / bytes | Result for example |
|---|---|---:|---|
| `gameplay.001b40c2` | Nothing happened to ↵ $m2. → **Nothing happened to $m2.** | 128 / 26 | Fits |
| `gameplay.001b45d0` | Unequipped ↵ $i0. → **Unequipped $i0.** | 125 / 26 | Fits |
| `gameplay.001b45e0` | $i1 won't fit ↵ inside a pot. → **$i1 won't fit inside a pot.** | 142 / 29 | Fits |
| `gameplay.001b45f4` | $i1 won't fit ↵ inside a jewel box. → **$i1 won't fit inside a jewel box.** | 172 / 35 | Fits |
| `gameplay.001b460c` | $i1 is in the ↵ water. → **$i1 is in the water.** | 110 / 22 | Fits |
| `gameplay.001b461b` | You can't pick up ↵ $i1! → **You can't pick up $i1!** | 120 / 24 | Fits |
| `gameplay.001b4628` | $i1 is stuck ↵ to the ground. → **$i1 is stuck to the ground.** | 144 / 29 | Fits |
| `gameplay.001b465f` | $i1 couldn't ↵ be put in the pot. → **$i1 couldn't be put in the pot.** | 161 / 33 | Fits |
| `gameplay.001b4677` | $i1 couldn't ↵ be put in the jewel box. → **$i1 couldn't be put in the jewel box.** | 191 / 39 | Fits |
| `gameplay.001b468f` | $i1 couldn't ↵ be stored. → **$i1 couldn't be stored.** | 123 / 25 | Fits |
| `gameplay.001b46ad` | Also put in ↵ $i1. → **Also put in $i1.** | 88 / 18 | Fits |
| `gameplay.001b46bc` | Put $i1 into ↵ $i0. → **Put $i1 into $i0.** | 147 / 30 | Fits |
| `gameplay.001b4721` | Also took out ↵ $i1. → **Also took out $i1.** | 100 / 20 | Fits |
| `gameplay.001b4730` | Took $i1 out ↵ of $i0. → **Took $i1 out of $i0.** | 165 / 33 | Fits |
| `gameplay.001b4741` | $i0 is firmly ↵ stuck to the ground. → **$i0 is firmly stuck to the ground.** | 217 / 45 | Example exceeds |
| `gameplay.001b4779` | There's $i0 ↵ here. → **There's $i0 here.** | 137 / 28 | Fits |
| `gameplay.001b4783` | You can't pick up ↵ $i0. → **You can't pick up $i0.** | 161 / 33 | Fits |
| `gameplay.001b4790` | You can't pick up ↵ $i0. → **You can't pick up $i0.** | 161 / 33 | Fits |
| `gameplay.001b479d` | You can't pick up ↵ $i0. → **You can't pick up $i0.** | 161 / 33 | Fits |
| `gameplay.001b4b65` | $m1 burrowed ↵ underground and fled. → **$m1 burrowed underground and fled.** | 179 / 36 | Fits |
| `gameplay.001b4b7d` | Stepped onto ↵ $i0. → **Stepped onto $i0.** | 137 / 28 | Fits |
| `gameplay.001b4bb0` | Put $i0 at ↵ your feet. → **Put $i0 at your feet.** | 158 / 32 | Fits |
| `gameplay.001b4be0` | $i0 filled ↵ with power! → **$i0 filled with power!** | 156 / 33 | Fits |
| `gameplay.001b4c89` | $i0 broke and ↵ can no longer be used. → **$i0 broke and can no longer be used.** | 231 / 47 | Example exceeds |
| `gameplay.001b4ca5` | $i0's sealed ↵ effects were restored. → **$i0's sealed effects were restored.** | 226 / 46 | Example exceeds |
| `gameplay.001b4d33` | $i0 was ↵ damaged! → **$i0 was damaged!** | 137 / 27 | Fits |
| `gameplay.001b4df1` | A critical hit! Dealt $d0 damage ↵ to $m1. → **A critical hit! Dealt $d0 damage to $m1.** | 194 / 40 | Fits |
| `gameplay.001b5292` | $m0's leaky belly was ↵ cured! → **$m0's leaky belly was cured!** | 157 / 32 | Fits |
| `gameplay.001b52bb` | $t's field of vision returned to ↵ normal. → **$t's field of vision returned to normal.** | 218 / 45 | Example exceeds |
| `gameplay.001b5385` | $t can see things as they really ↵ are. → **$t can see things as they really are.** | 209 / 42 | Example exceeds |
| `gameplay.001b54ed` | $t threw ↵ $i0. → **$t threw $i0.** | 145 / 29 | Fits |
| `gameplay.001b54fc` | $t fired ↵ $i0. → **$t fired $i0.** | 141 / 29 | Fits |
| `gameplay.001b550b` | $i0 fell to ↵ the ground. → **$i0 fell to the ground.** | 162 / 34 | Fits |
| `gameplay.001b5532` | $i0 fell into ↵ the water. → **$i0 fell into the water.** | 168 / 35 | Fits |
| `gameplay.001b5544` | $i0 fell to ↵ the ground or into the water. → **$i0 fell to the ground or into the water.** | 253 / 52 | Example exceeds |
| `gameplay.001b55b7` | $i0 was a ↵ Cannibox! → **$i0 was a Cannibox!** | 149 / 30 | Fits |
| `gameplay.001b55ea` | $i0 couldn't ↵ take on its monster form. → **$i0 couldn't take on its monster form.** | 241 / 49 | Example exceeds |
| `gameplay.001b561c` | $t waved ↵ $i0! → **$t waved $i0!** | 145 / 29 | Fits |
| `gameplay.001b564d` | $i0 vanished ↵ into the distance. → **$i0 vanished into the distance.** | 202 / 42 | Fits |
| `gameplay.001b566f` | $i0 hit ↵ $m0. → **$i0 hit $m0.** | 131 / 27 | Fits |
| `gameplay.001b5686` | $i0 hit ↵ $t. → **$i0 hit $t.** | 131 / 27 | Fits |
| `gameplay.001b56b9` | $i0: some ↵ burned up. → **$i0: some burned up.** | 152 / 31 | Fits |
| `gameplay.001b56d9` | $i0: some ↵ froze. → **$i0: some froze.** | 132 / 27 | Fits |
| `gameplay.001b56ed` | $i0 was buried ↵ in sand. → **$i0 was buried in sand.** | 166 / 34 | Fits |
| `gameplay.001b56fd` | $i0: some ↵ vanished into the sand. → **$i0: some vanished into the sand.** | 215 / 44 | Example exceeds |
| `gameplay.001b5712` | $i0 was lost ↵ to the wind. → **$i0 was lost to the wind.** | 177 / 36 | Fits |
| `gameplay.001b5723` | $i0: some were ↵ lost to the wind. → **$i0: some were lost to the wind.** | 212 / 43 | Example exceeds |
| `gameplay.001b574f` | $i0 was ↵ damaged. → **$i0 was damaged.** | 138 / 27 | Fits |
| `gameplay.001b5774` | $m1 didn't fall ↵ asleep. → **$m1 didn't fall asleep.** | 116 / 25 | Fits |
| `gameplay.001b5796` | $m1 is already ↵ asleep! → **$m1 is already asleep!** | 114 / 24 | Fits |
| `gameplay.001b57a9` | $t drank ↵ $i0. → **$t drank $i0.** | 144 / 29 | Fits |
| `gameplay.001b57b9` | $t tried to drink ↵ $i0! → **$t tried to drink $i0!** | 183 / 38 | Fits |
| `gameplay.001b57ca` | $t ate ↵ $i0. → **$t ate $i0.** | 134 / 27 | Fits |
| `gameplay.001b57da` | $t tried to eat ↵ $i0. → **$t tried to eat $i0.** | 177 / 36 | Fits |
| `gameplay.001b57ee` | $t used ↵ $i0! → **$t used $i0!** | 137 / 28 | Fits |
| `gameplay.001b57fe` | $t used ↵ $i0! → **$t used $i0!** | 137 / 28 | Fits |
| `gameplay.001b580e` | $t read ↵ $i0. → **$t read $i0.** | 139 / 28 | Fits |
| `gameplay.001b581e` | $t tried to read ↵ $i0! → **$t tried to read $i0!** | 181 / 37 | Fits |
| `gameplay.001b5831` | $t tried using ↵ $i0. → **$t tried using $i0.** | 169 / 35 | Fits |
| `gameplay.001b5843` | $t attempted to use ↵ $i0. → **$t attempted to use $i0.** | 201 / 40 | Fits |
| `gameplay.001b58b9` | $m0 can no longer ↵ move. → **$m0 can no longer move.** | 137 / 27 | Fits |
| `gameplay.001b58ca` | $m0 was severely ↵ paralysed! → **$m0 was severely paralysed!** | 156 / 31 | Fits |
| `gameplay.001b58e2` | $m1 is still severely ↵ paralysed. → **$m1 is still severely paralysed.** | 158 / 34 | Fits |
| `gameplay.001b58fa` | $m0 is now under ↵ ordinary paralysis. → **$m0 is now under ordinary paralysis.** | 198 / 40 | Fits |
| `gameplay.001b5913` | $m0 is no longer ↵ confused. → **$m0 is no longer confused.** | 147 / 30 | Fits |
| `gameplay.001b593e` | $m0 can see things ↵ as they really are. → **$m0 can see things as they really are.** | 209 / 42 | Example exceeds |
| `gameplay.001b595a` | $m0 is no longer ↵ frightened. → **$m0 is no longer frightened.** | 155 / 32 | Fits |
| `gameplay.001b596d` | $m0 is free from the ↵ dance. → **$m0 is free from the dance.** | 157 / 31 | Fits |
| `gameplay.001b5982` | $m0 is no longer ↵ angry. → **$m0 is no longer angry.** | 133 / 27 | Fits |
| `gameplay.001b59a8` | $m0 came to their ↵ senses. → **$m0 came to their senses.** | 147 / 29 | Fits |
| `gameplay.001b59b8` | $m0's wakefulness ↵ wore off. → **$m0's wakefulness wore off.** | 158 / 31 | Fits |
| `gameplay.001b59d3` | $m0 is no longer ↵ berserk. → **$m0 is no longer berserk.** | 142 / 29 | Fits |
| `gameplay.001b59f2` | $m0 is no longer ↵ made of iron. → **$m0 is no longer made of iron.** | 168 / 34 | Fits |
| `gameplay.001b5a09` | $m0's whiffing wore ↵ off. → **$m0's whiffing wore off.** | 140 / 28 | Fits |
| `gameplay.001b5a20` | Herbs affect $m0 ↵ normally again. → **Herbs affect $m0 normally again.** | 182 / 36 | Fits |
| `gameplay.001b5a34` | $m0 fired ↵ $i0. → **$m0 fired $i0.** | 141 / 29 | Fits |
| `gameplay.001b5a4a` | $m0 threw ↵ $i0. → **$m0 threw $i0.** | 145 / 29 | Fits |
| `gameplay.001b5a60` | $m0 spat out ↵ $i0. → **$m0 spat out $i0.** | 159 / 32 | Fits |
| `gameplay.001b5a75` | $m1 didn't become ↵ confused. → **$m1 didn't become confused.** | 142 / 29 | Fits |
| `gameplay.001b5a95` | $m1 is already ↵ confused! → **$m1 is already confused!** | 125 / 26 | Fits |
| `gameplay.001b5aa9` | $m1 became ↵ frightened! → **$m1 became frightened!** | 118 / 24 | Fits |
| `gameplay.001b5ab9` | $m1 is already ↵ frightened! → **$m1 is already frightened!** | 133 / 28 | Fits |
| `gameplay.001b5acc` | $m1 recovered ↵ $d0 HP. → **$m1 recovered $d0 HP.** | 105 / 21 | Fits |
| `gameplay.001b5ae1` | $m1's maximum HP ↵ rose by $d0. → **$m1's maximum HP rose by $d0.** | 149 / 29 | Fits |
| `gameplay.001b5af8` | $m1's HP was fully ↵ restored. → **$m1's HP was fully restored.** | 148 / 30 | Fits |
| `gameplay.001b5b0f` | $t pushed ↵ $i0! → **$t pushed $i0!** | 147 / 30 | Fits |
| `tutorial.001b50b1` | $m0 waits and ↵ watches... → **$m0 waits and watches...** | 144 / 28 | Fits |
| `tutorial.001b516f` | $i0 is no ↵ longer blessed. → **$i0 is no longer blessed.** | 170 / 36 | Fits |
| `tutorial.001b5b85` | $m0's strength was ↵ halved. → **$m0's strength was halved.** | 152 / 30 | Fits |
| `tutorial.001b5bab` | $m0's strength fell ↵ greatly! → **$m0's strength fell greatly!** | 154 / 32 | Fits |
| `tutorial.001b5ebf` | $i2 failed to ↵ work. → **$i2 failed to work.** | 135 / 28 | Fits |
| `tutorial.001b6002` | $i3 cancelled ↵ $m0's magic! → **$i3 cancelled $m0's magic!** | 189 / 39 | Fits |
| `tutorial.001b601c` | $i3 cancelled ↵ the magic affecting ↵ $m0! → **$i3 cancelled the magic affecting $m0!** | 249 / 51 | Example exceeds |
| `tutorial.001b607e` | $i3 cancelled ↵ the effect of $m0's ↵ thrown item! → **$i3 cancelled the effect of $m0's thrown item!** | 290 / 59 | Example exceeds |
| `tutorial.001b60a6` | $i3 cancelled ↵ the item effect on ↵ $m0! → **$i3 cancelled the item effect on $m0!** | 244 / 50 | Example exceeds |
| `tutorial.001b60cf` | $i3 cancelled ↵ the effect of $m0's ↵ fired item! → **$i3 cancelled the effect of $m0's fired item!** | 281 / 58 | Example exceeds |
| `tutorial.001b6674` | $i0 came ↵ flying! → **$i0 came flying!** | 129 / 27 | Fits |
| `tutorial.001b6683` | $i0 came ↵ flying! → **$i0 came flying!** | 129 / 27 | Fits |
| `tutorial.001b6704` | $i0 came ↵ flying! → **$i0 came flying!** | 129 / 27 | Fits |
| `tutorial.001b6713` | $i0 came ↵ flying! → **$i0 came flying!** | 129 / 27 | Fits |
| `tutorial.001b67a3` | $i0 came ↵ flying! → **$i0 came flying!** | 129 / 27 | Fits |
| `tutorial.001b67b2` | $i0 came ↵ flying! → **$i0 came flying!** | 129 / 27 | Fits |
| `tutorial.001b6813` | It had no effect on ↵ $i0. → **It had no effect on $i0.** | 172 / 35 | Fits |
| `tutorial.001b6875` | Some special effects of ↵ $i0 were ↵ sealed! → **Some special effects of $i0 were sealed!** | 251 / 51 | Example exceeds |
| `tutorial.001b6896` | The special effects of ↵ $i0 were ↵ sealed! → **The special effects of $i0 were sealed!** | 245 / 50 | Example exceeds |
| `tutorial.001b68c6` | $m0 performed Weird ↵ Dance! → **$m0 performed Weird Dance!** | 154 / 30 | Fits |
| `tutorial.001b6908` | The ring stopped ↵ $m1's level from ↵ falling. → **The ring stopped $m1's level from falling.** | 210 / 44 | Example exceeds |
| `tutorial.001b6965` | $m1's maximum ↵ strength fell by $d0. → **$m1's maximum strength fell by $d0.** | 173 / 35 | Fits |
| `tutorial.001b6982` | $m1's strength was ↵ halved. → **$m1's strength was halved.** | 139 / 28 | Fits |
| `tutorial.001b6995` | $m1's strength ↵ cannot fall any further! → **$m1's strength cannot fall any further!** | 200 / 41 | Fits |
| `tutorial.001b69a9` | The ring stopped ↵ $m1's strength from ↵ falling. → **The ring stopped $m1's strength from falling.** | 229 / 47 | Example exceeds |
| `tutorial.001b6a10` | $m1's maximum HP ↵ fell by $d0. → **$m1's maximum HP fell by $d0.** | 145 / 29 | Fits |
| `tutorial.001b6a4c` | $m1's HP cannot fall ↵ any further! → **$m1's HP cannot fall any further!** | 172 / 35 | Fits |
| `tutorial.001b6a85` | $m0 fired an ↵ absorption beam. → **$m0 fired an absorption beam.** | 167 / 33 | Fits |
| `tutorial.001b6a9a` | $m0 fired an ↵ absorption beam. → **$m0 fired an absorption beam.** | 167 / 33 | Fits |
| `tutorial.001b6b06` | $m0 used Harvest ↵ Moon! → **$m0 used Harvest Moon!** | 134 / 26 | Fits |
| `tutorial.001b6b42` | $m0 called for ↵ monsters! → **$m0 called for monsters!** | 139 / 28 | Fits |
| `tutorial.001b6b84` | $i0 lowered ↵ Defence! → **$i0 lowered Defence!** | 151 / 31 | Fits |
| `tutorial.001b6b98` | $i0 was ↵ knocked away. → **$i0 was knocked away.** | 163 / 32 | Fits |
| `tutorial.001b6baa` | Knocked away ↵ $i0. → **Knocked away $i0.** | 141 / 28 | Fits |
| `tutorial.001b6c19` | $m0 tried to knock ↵ equipment away! → **$m0 tried to knock equipment away!** | 192 / 38 | Fits |
| `tutorial.001b6c2b` | $m0 tried to knock ↵ items away! → **$m0 tried to knock items away!** | 172 / 34 | Fits |
| `tutorial.001b6c41` | $m0 tried to knock ↵ items away! → **$m0 tried to knock items away!** | 172 / 34 | Fits |
| `tutorial.001b6ca1` | $m1 is already ↵ invisible. → **$m1 is already invisible.** | 123 / 27 | Fits |
| `tutorial.001b6cb3` | $m1 turned invisible, ↵ but $t can still see it. → **$m1 turned invisible, but $t can still see it.** | 249 / 53 | Example exceeds |
| `tutorial.001b6cd6` | $m0 and ↵ $m1 swapped places. → **$m0 and $m1 swapped places.** | 168 / 33 | Fits |
| `tutorial.001b6cec` | $m0 cannot be ↵ swapped! → **$m0 cannot be swapped!** | 134 / 26 | Fits |
| `tutorial.001b6cff` | $m0 cannot be ↵ swapped! → **$m0 cannot be swapped!** | 134 / 26 | Fits |
| `tutorial.001b6d2b` | $m0 is asleep and ↵ cannot trip! → **$m0 is asleep and cannot trip!** | 167 / 34 | Fits |
| `tutorial.001b6d50` | The staff kept ↵ $m0 from tripping! → **The staff kept $m0 from tripping!** | 186 / 37 | Fits |
| `tutorial.001b6da9` | $m1's HP fell to a ↵ quarter! → **$m1's HP fell to a quarter!** | 141 / 29 | Fits |
| `tutorial.001b6dbd` | $m1 lost a great ↵ deal of HP! → **$m1 lost a great deal of HP!** | 148 / 30 | Fits |
| `tutorial.001b6dff` | $m0 waved a Shaman ↵ staff! → **$m0 waved a Shaman staff!** | 155 / 29 | Fits |
| `tutorial.001b6e15` | $m0 waved an ↵ Acceleratle staff! → **$m0 waved an Acceleratle staff!** | 178 / 35 | Fits |
| `tutorial.001b6e2f` | $m0 waved a ↵ Sorcerer staff! → **$m0 waved a Sorcerer staff!** | 161 / 31 | Fits |
| `tutorial.001b6e49` | $m0 waved an ↵ Acceleratle staff! → **$m0 waved an Acceleratle staff!** | 178 / 35 | Fits |
| `tutorial.001b6e63` | $m0 waved a Rage ↵ staff! → **$m0 waved a Rage staff!** | 142 / 27 | Fits |
| `tutorial.001b6e7b` | $m1 flew into a ↵ rage. → **$m1 flew into a rage.** | 113 / 23 | Fits |
| `tutorial.001b6e8b` | $m1 is sealed and ↵ cannot feel rage. → **$m1 is sealed and cannot feel rage.** | 181 / 37 | Fits |
| `tutorial.001b6ea9` | $m1 is already ↵ enraged! → **$m1 is already enraged!** | 121 / 25 | Fits |
| `tutorial.001b6ef8` | $m1 now shares ↵ $t's pain! → **$m1 now shares $t's pain!** | 160 / 32 | Fits |
| `tutorial.001b6f3c` | $m0 called for ↵ monsters! → **$m0 called for monsters!** | 139 / 28 | Fits |
| `tutorial.001b6f54` | $i0 was ↵ cursed! → **$i0 was cursed!** | 128 / 26 | Fits |
| `tutorial.001b6f60` | $m1 avoided the ↵ curse. → **$m1 avoided the curse.** | 117 / 24 | Fits |
| `tutorial.001b6fa2` | $i0 cannot be ↵ cursed. → **$i0 cannot be cursed.** | 157 / 32 | Fits |
| `tutorial.001b6fb0` | $m0 uttered strange ↵ words! → **$m0 uttered strange words!** | 153 / 30 | Fits |
| `tutorial.001b6fc8` | $i0's uses ↵ fell to 0. → **$i0's uses fell to 0.** | 151 / 32 | Fits |
| `tutorial.001b7016` | $m0 spat rotten ↵ fluid! → **$m0 spat rotten fluid!** | 127 / 26 | Fits |
| `tutorial.001b702a` | $i0 did not ↵ deteriorate. → **$i0 did not deteriorate.** | 168 / 35 | Fits |
| `tutorial.001b7062` | $i0 ↵ deteriorated. → **$i0 deteriorated.** | 135 / 28 | Fits |
| `tutorial.001b7074` | $i0 cannot ↵ deteriorate further. → **$i0 cannot deteriorate further.** | 206 / 42 | Fits |
| `tutorial.001b7083` | $i0 cannot ↵ deteriorate. → **$i0 cannot deteriorate.** | 166 / 34 | Fits |
| `tutorial.001b7720` | $i0 lost its ↵ [$i1] effect! → **$i0 lost its [$i1] effect!** | 188 / 39 | Fits |
| `tutorial.001b773f` | $i0 has no ↵ removable seals. → **$i0 has no removable seals.** | 187 / 38 | Fits |
| `tutorial.001b7761` | $m1 started acting ↵ strangely. → **$m1 started acting strangely.** | 152 / 31 | Fits |
| `tutorial.001b7771` | $m0 clamped the ↵ target's mouth shut! → **$m0 clamped the target's mouth shut!** | 203 / 40 | Fits |
| `tutorial.001b7783` | $m0 clamped the ↵ target's mouth shut! → **$m0 clamped the target's mouth shut!** | 203 / 40 | Fits |
| `tutorial.001b7793` | $m0 struck with a ↵ knockback blow! → **$m0 struck with a knockback blow!** | 187 / 37 | Fits |
| `tutorial.001b77a9` | $t's maximum fullness rose by ↵ $d0. → **$t's maximum fullness rose by $d0.** | 186 / 37 | Fits |
| `tutorial.001b77c3` | $t's maximum fullness fell by ↵ $d0. → **$t's maximum fullness fell by $d0.** | 182 / 37 | Fits |
| `tutorial.001b77de` | $m0 developed a leaky ↵ belly! → **$m0 developed a leaky belly!** | 154 / 32 | Fits |
| `tutorial.001b77f6` | $m1 returned to ↵ normal. → **$m1 returned to normal.** | 124 / 25 | Fits |
| `help.001b5b1d` | $m0 avoided the ↵ poison. → **$m0 avoided the poison.** | 133 / 27 | Fits |
| `help.001b5b32` | $m0 is immune to ↵ poison ↵ on this floor. → **$m0 is immune to poison on this floor.** | 205 / 42 | Fits |
| `help.001b5b70` | The poison had no effect on ↵ $m1. → **The poison had no effect on $m1.** | 169 / 34 | Fits |
| `help.001b5c20` | $m0 released ↵ poisonous spores! → **$m0 released poisonous spores!** | 167 / 34 | Fits |
| `help.001b5c78` | $m0 cast a strange ↵ spell! → **$m0 cast a strange spell!** | 144 / 29 | Fits |
| `help.001b5c8c` | $m1 can no longer ↵ recover HP. → **$m1 can no longer recover HP.** | 154 / 31 | Fits |
| `help.001b5cf9` | $m0 waved a Lump ↵ mage staff! → **$m0 waved a Lump mage staff!** | 171 / 32 | Fits |
| `help.001b5d1a` | $m0 waved a Lump ↵ wizard staff! → **$m0 waved a Lump wizard staff!** | 179 / 34 | Fits |
| `help.001b5d3a` | $i0 was blown ↵ away. → **$i0 was blown away.** | 153 / 30 | Fits |
| `help.001b5d5f` | $m1's speed did not ↵ change. → **$m1's speed did not change.** | 141 / 29 | Fits |
| `help.001b5d75` | $m1's speed did not ↵ change. → **$m1's speed did not change.** | 141 / 29 | Fits |
| `help.001b5db5` | $m0 slowed to half ↵ speed. → **$m0 slowed to half speed.** | 145 / 29 | Fits |
| `help.001b5dc5` | $m0 returned to ↵ normal speed. → **$m0 returned to normal speed.** | 167 / 33 | Fits |
| `help.001b5e5c` | $m1 vanished in the ↵ explosion. → **$m1 vanished in the explosion.** | 151 / 32 | Fits |
| `help.001b5eb1` | $i0 failed to ↵ explode. → **$i0 failed to explode.** | 156 / 33 | Fits |
| `help.001b5f65` | Nothing happened to ↵ $m1. → **Nothing happened to $m1.** | 128 / 26 | Fits |
| `help.001b5fdc` | $m0 used a ↵ paralysing attack! → **$m0 used a paralysing attack!** | 166 / 33 | Fits |
| `help.001b6127` | $m1 can no longer ↵ recognise items! → **$m1 can no longer recognise items!** | 174 / 36 | Fits |
| `help.001b6142` | $m0 gave a thorough ↵ licking. → **$m0 gave a thorough licking.** | 157 / 32 | Fits |
| `help.001b6167` | $m1's magic was ↵ sealed! → **$m1's magic was sealed!** | 124 / 25 | Fits |
| `help.001b617c` | $m1's magic is ↵ already sealed. → **$m1's magic is already sealed.** | 155 / 32 | Fits |
| `help.001b61a6` | $m1 is already ↵ sealed! → **$m1 is already sealed!** | 114 / 24 | Fits |
| `help.001b61ba` | $m1 already cannot ↵ use its mouth. → **$m1 already cannot use its mouth.** | 174 / 35 | Fits |
| `help.001b61cf` | $m1 can no longer ↵ use its mouth. → **$m1 can no longer use its mouth.** | 167 / 34 | Fits |
| `help.001b61f3` | Nothing changed for ↵ $m1! → **Nothing changed for $m1!** | 127 / 26 | Fits |
| `help.001b6256` | $t's maximum Fullness is now ↵ $d0. → **$t's maximum Fullness is now $d0.** | 182 / 36 | Fits |
| `help.001b6382` | $m1 recovered ↵ $d0 Strength! → **$m1 recovered $d0 Strength!** | 133 / 27 | Fits |
| `help.001b6398` | $m1's Strength was ↵ fully restored! → **$m1's Strength was fully restored!** | 176 / 36 | Fits |
| `help.001b63ab` | $m1's Strength was ↵ fully restored! → **$m1's Strength was fully restored!** | 176 / 36 | Fits |
| `help.001b63d8` | $m1's maximum ↵ Strength ↵ rose by $d0! → **$m1's maximum Strength rose by $d0!** | 177 / 35 | Fits |
| `help.001b63f6` | $m1's Attack rose by ↵ $d0! → **$m1's Attack rose by $d0!** | 123 / 25 | Fits |
| `help.001b6410` | $m0 performed a ↵ Sultry Dance! → **$m0 performed a Sultry Dance!** | 169 / 33 | Fits |
| `help.001b6424` | $m0 used a hunger ↵ attack! → **$m0 used a hunger attack!** | 148 / 29 | Fits |
| `help.001b6438` | $m1 cannot stop ↵ dancing! → **$m1 cannot stop dancing!** | 127 / 26 | Fits |
| `help.001b6455` | $m1 is already ↵ dancing! → **$m1 is already dancing!** | 119 / 25 | Fits |
| `help.001b64ac` | $m0 is building up ↵ power... → **$m0 is building up power...** | 148 / 31 | Fits |
| `help.001b64d6` | $m0 hid in its shell ↵ to defend itself! → **$m0 hid in its shell to defend itself!** | 196 / 42 | Fits |
| `help.001b6535` | $i0 was really ↵ $i1! → **$i0 was really $i1!** | 157 / 32 | Fits |
| `help.001b654a` | This is definitely ↵ $i0! → **This is definitely $i0!** | 157 / 34 | Fits |
| `help.001b655f` | $t's equipped weapon ↵ was improved by +$d0! → **$t's equipped weapon was improved by +$d0!** | 230 / 45 | Example exceeds |
| `help.001b657a` | $t's equipped shield ↵ was improved by +$d0! → **$t's equipped shield was improved by +$d0!** | 223 / 45 | Example exceeds |
| `help.001b6593` | $i0 was ↵ plated. → **$i0 was plated.** | 128 / 26 | Fits |
| `help.001b65a3` | $i0's ↵ Wearproof seal works again. → **$i0's Wearproof seal works again.** | 219 / 44 | Example exceeds |
| `help.001b65be` | $i0 can no ↵ longer break! → **$i0 can no longer break!** | 170 / 35 | Fits |
| `battle.001b7e15` | Swapped $i0 ↵ for $i1. → **Swapped $i0 for $i1.** | 167 / 33 | Fits |
| `battle.001b7e8c` | $i0 became ↵ $i1. → **$i0 became $i1.** | 141 / 28 | Fits |
| `battle.001b7e9e` | $i0 could not ↵ be turned into Bread! → **$i0 could not be turned into Bread!** | 223 / 46 | Example exceeds |
| `battle.001b7edc` | $i0 gained one ↵ charge. → **$i0 gained one charge.** | 161 / 33 | Fits |
| `battle.001b7ef0` | $i0 grew a ↵ little bigger. → **$i0 grew a little bigger.** | 171 / 36 | Fits |
| `battle.001b7fbf` | $m1 can no longer ↵ move! → **$m1 can no longer move!** | 123 / 25 | Fits |
| `battle.001b7ff1` | $m1 is already ↵ whiffing! → **$m1 is already whiffing!** | 123 / 26 | Fits |
| `battle.001b8008` | $m1 converted the ↵ effect into damage. → **$m1 converted the effect into damage.** | 195 / 39 | Fits |
| `battle.001b80a5` | $m1's maximum HP ↵ fell by $d0! → **$m1's maximum HP fell by $d0!** | 144 / 29 | Fits |
| `battle.001b80d9` | $m1's vision returned ↵ to normal! → **$m1's vision returned to normal!** | 163 / 34 | Fits |
| `battle.001b80e9` | $m1 can now see ↵ invisible things! → **$m1 can now see invisible things!** | 165 / 35 | Fits |
| `battle.001b810a` | $m1 took the form of ↵ Torneko. → **$m1 took the form of Torneko.** | 157 / 31 | Fits |
| `battle.001b8122` | $m0 stopped looking ↵ like Torneko. → **$m0 stopped looking like Torneko.** | 180 / 37 | Fits |
| `battle.001b813b` | $m1 began attacking ↵ friend and foe alike! → **$m1 began attacking friend and foe alike!** | 209 / 43 | Example exceeds |
| `battle.001b81a4` | $m0 swallowed ↵ $i0 and gained ↵ attack power! → **$m0 swallowed $i0 and gained attack power!** | 287 / 57 | Example exceeds |
| `battle.001b81c9` | $m0 swallowed ↵ $i0! → **$m0 swallowed $i0!** | 163 / 33 | Fits |
| `battle.001b81de` | $m0 tried to spit out ↵ an ally! → **$m0 tried to spit out an ally!** | 164 / 34 | Fits |
| `battle.001b820b` | $m1's equipment was ↵ damaged and weakened! → **$m1's equipment was damaged and weakened!** | 222 / 43 | Example exceeds |
| `battle.001b8228` | $m1 cannot get any ↵ weaker. → **$m1 cannot get any weaker.** | 143 / 28 | Fits |
| `battle.001b8250` | $m1 turned into ↵ Rotten bread. → **$m1 turned into Rotten bread.** | 153 / 31 | Fits |
| `battle.001b8276` | $i0 warped ↵ away. → **$i0 warped away.** | 138 / 27 | Fits |
| `battle.001b8286` | $i0 warped ↵ away and was lost. → **$i0 warped away and was lost.** | 205 / 40 | Fits |
| `battle.001b829d` | $i0's plus ↵ value temporarily fell to 0! → **$i0's plus value temporarily fell to 0!** | 236 / 50 | Example exceeds |
| `battle.001b82bf` | $i0's strength ↵ fell by 1! → **$i0's strength fell by 1!** | 170 / 36 | Fits |
| `battle.001b82d4` | $i0's plus ↵ value temporarily fell to 0! → **$i0's plus value temporarily fell to 0!** | 236 / 50 | Example exceeds |
| `battle.001b82f6` | $i0's plus ↵ value temporarily fell to 0! → **$i0's plus value temporarily fell to 0!** | 236 / 50 | Example exceeds |
| `battle.001b8318` | $i0's strength ↵ fell by 1! → **$i0's strength fell by 1!** | 170 / 36 | Fits |
| `battle.001b832d` | It had no effect on ↵ $i0. → **It had no effect on $i0.** | 172 / 35 | Fits |
| `battle.001b841d` | $m0 began a ↵ countdown to an explosion! → **$m0 began a countdown to an explosion!** | 211 / 42 | Example exceeds |
| `battle.001b8443` | $m0's self-destruct ↵ failed to go off. → **$m0's self-destruct failed to go off.** | 202 / 41 | Fits |
| `battle.001b845b` | $m0 emitted a bright ↵ light! → **$m0 emitted a bright light!** | 150 / 31 | Fits |
| `battle.001b846d` | $m0 emitted a bright ↵ light! → **$m0 emitted a bright light!** | 150 / 31 | Fits |
| `battle.001b847f` | $m1 can only see the ↵ immediate surroundings! → **$m1 can only see the immediate surroundings!** | 225 / 46 | Example exceeds |
| `battle.001b8495` | $m0 swung an axe ↵ with all its might! → **$m0 swung an axe with all its might!** | 199 / 40 | Fits |
| `battle.001b84ab` | $m0 attacked ↵ fiercely! → **$m0 attacked fiercely!** | 128 / 26 | Fits |
| `battle.001b862f` | $i0 restored ↵ health! → **$i0 restored health!** | 149 / 31 | Fits |
| `battle.001b864e` | $i0 was a ↵ Cannibox! → **$i0 was a Cannibox!** | 149 / 30 | Fits |
| `battle.001b8667` | $i0 was ↵ cursed! → **$i0 was cursed!** | 128 / 26 | Fits |
| `battle.001b8675` | $t used ↵ $i0 and ↵ revived! → **$t used $i0 and revived!** | 196 / 40 | Fits |
| `battle.001b868c` | $i0 took fire ↵ damage! → **$i0 took fire damage!** | 157 / 32 | Fits |
| `battle.001b86a4` | $m0 cast Magic ↵ Burst! → **$m0 cast Magic Burst!** | 128 / 25 | Fits |
| `battle.001b86d0` | $m0 shredded ↵ $t's $i0! → **$m0 shredded $t's $i0!** | 208 / 42 | Fits |
| `battle.001b870e` | $m0 found no items ↵ to shred! → **$m0 found no items to shred!** | 160 / 32 | Fits |
| `battle.001b872d` | $m0 waits and ↵ watches... → **$m0 waits and watches...** | 144 / 28 | Fits |
| `battle.001b8741` | $m0 extended its ↵ scythe. → **$m0 extended its scythe.** | 139 / 28 | Fits |
| `battle.001b8753` | $m0 shredded an ↵ item. → **$m0 shredded an item.** | 127 / 25 | Fits |
| `battle.001b885b` | $m1's attack power ↵ rose! → **$m1's attack power rose!** | 130 / 26 | Fits |
| `battle.001b888d` | $m0 swung a sword ↵ with all its might! → **$m0 swung a sword with all its might!** | 205 / 41 | Fits |
| `battle.001b88a3` | $m0 cast a seal on ↵ you! → **$m0 cast a seal on you!** | 136 / 27 | Fits |
| `battle.001b88ee` | $m0 made a sweeping ↵ attack! → **$m0 made a sweeping attack!** | 161 / 31 | Fits |
| `battle.001b8900` | $m0 was swept off ↵ its feet! → **$m0 was swept off its feet!** | 158 / 31 | Fits |
| `battle.001b8927` | $m0 used Blade of ↵ Ultimate Power! → **$m0 used Blade of Ultimate Power!** | 188 / 37 | Fits |
| `battle.001b8a64` | $m1 was sucked into ↵ the pot! → **$m1 was sucked into the pot!** | 148 / 30 | Fits |
| `battle.001b8a77` | $m1's presence ↵ vanished! → **$m1's presence vanished!** | 125 / 26 | Fits |
| `battle.001b8aa0` | $m1 was trapped in ↵ the pot! → **$m1 was trapped in the pot!** | 144 / 29 | Fits |
| `battle.001b8abf` | $m1 was caught in ↵ the wind! → **$m1 was caught in the wind!** | 144 / 29 | Fits |
| `battle.001b8b20` | $m0 swung its horns ↵ in a great arc! → **$m0 swung its horns in a great arc!** | 196 / 39 | Fits |
| `battle.001b8b38` | $m1 was knocked ↵ away. → **$m1 was knocked away.** | 120 / 23 | Fits |
| `battle.001b8b49` | Filled $i0 ↵ with water. → **Filled $i0 with water.** | 159 / 33 | Fits |
| `battle.001b8b6f` | $i0 is already ↵ full of water. → **$i0 is already full of water.** | 193 / 40 | Fits |
| `battle.001b8b9b` | The splash of water weakened ↵ $m1. → **The splash of water weakened $m1.** | 180 / 35 | Fits |
| `battle.001b8c38` | $m1 is already wide ↵ awake! → **$m1 is already wide awake!** | 139 / 28 | Fits |
| `battle.001b8c5b` | $i0 could not ↵ be sucked up. → **$i0 could not be sucked up.** | 184 / 38 | Fits |
| `battle.001b8cf4` | A monster became ↵ $i0. → **A monster became $i0.** | 162 / 32 | Fits |
| `battle.001b8d40` | $m0 breathed an icy ↵ blast! → **$m0 breathed an icy blast!** | 149 / 30 | Fits |
| `battle.001b8d6e` | $m0 picked up ↵ $i0 and threw ↵ it! → **$m0 picked up $i0 and threw it!** | 226 / 46 | Example exceeds |
| `battle.001b8d83` | $m0 tried to throw ↵ $i0! → **$m0 tried to throw $i0!** | 187 / 38 | Fits |
| `battle.001b8dd9` | $m1 was pulled ↵ closer! → **$m1 was pulled closer!** | 114 / 24 | Fits |
| `battle.001b8e1a` | Pulled $i0 ↵ closer! → **Pulled $i0 closer!** | 135 / 29 | Fits |
| `battle.001b8e6e` | $m0 transformed into ↵ $m1! → **$m0 transformed into $m1!** | 155 / 31 | Fits |
| `battle.001b8e80` | $m0 changed into ↵ $m1. → **$m0 changed into $m1.** | 134 / 27 | Fits |
| `battle.001b8e92` | $m0 took the form of ↵ $m1. → **$m0 took the form of $m1.** | 157 / 31 | Fits |
| `battle.001b9256` | $m0 charged its ↵ sword with power! → **$m0 charged its sword with power!** | 188 / 37 | Fits |
| `battle.001b9268` | $m0 stole ↵ $i0. → **$m0 stole $i0.** | 141 / 29 | Fits |
| `battle.001b927a` | $m0 tried to steal an ↵ item! → **$m0 tried to steal an item!** | 153 / 31 | Fits |
| `battle.001b92a6` | $m0 tried to steal an ↵ item! → **$m0 tried to steal an item!** | 153 / 31 | Fits |
| `battle.001b92cf` | $m0 stole ↵ $d0 G from ↵ $m1. → **$m0 stole $d0 G from $m1.** | 146 / 29 | Fits |
| `battle.001b92e7` | $m0 tried to steal ↵ money, but could not. → **$m0 tried to steal money, but could not.** | 217 / 44 | Example exceeds |
| `battle.001b9304` | $m0 tried to steal ↵ money, but $m1 had ↵ none. → **$m0 tried to steal money, but $m1 had none.** | 244 / 49 | Example exceeds |
| `battle.001b932e` | $m0 tried to steal ↵ money! → **$m0 tried to steal money!** | 144 / 29 | Fits |
| `battle.001b9377` | $i0 spouted ↵ flames! → **$i0 spouted flames!** | 146 / 30 | Fits |
| `battle.001b93a8` | $i0 invites ↵ you to dance! → **$i0 invites you to dance!** | 172 / 36 | Fits |
| `battle.001b93ba` | $i0 released ↵ sleeping gas! → **$i0 released sleeping gas!** | 176 / 37 | Fits |
| `battle.001b93ff` | A statue flew at ↵ $m0! → **A statue flew at $m0!** | 128 / 25 | Fits |
| `battle.001b9486` | Fired $i0 from ↵ $i1! → **Fired $i0 from $i1!** | 158 / 32 | Fits |
| `battle.001b9499` | $t rolled ↵ $i0. → **$t rolled $i0.** | 144 / 30 | Fits |
| `battle.001b94aa` | $i0 failed to ↵ go off! → **$i0 failed to go off!** | 152 / 32 | Fits |
| `battle.001b9630` | But it had no effect on ↵ $m0! → **But it had no effect on $m0!** | 160 / 32 | Fits |
| `battle.001b9891` | $m0 joined your ↵ allies! → **$m0 joined your allies!** | 128 / 27 | Fits |
| `battle.001b98a6` | $m0 left, looking ↵ lonely... → **$m0 left, looking lonely...** | 143 / 31 | Fits |
| `battle.001b9c0b` | $m0 hurled its ↵ weapon with all its might! → **$m0 hurled its weapon with all its might!** | 219 / 45 | Example exceeds |
| `battle.001b9c2b` | $m0 unleashed an evil ↵ mist! → **$m0 unleashed an evil mist!** | 151 / 31 | Fits |
| `battle.001b9ca3` | $m0 is unharmed by ↵ the flames! → **$m0 is unharmed by the flames!** | 172 / 34 | Fits |
| `battle.001b9d54` | $m0 did not swap ↵ places. → **$m0 did not swap places.** | 141 / 28 | Fits |
| `battle.001b9d7a` | $i0 froze ↵ solid! → **$i0 froze solid!** | 126 / 27 | Fits |
| `battle.001b9db0` | $m0 recovered HP on ↵ the water! → **$m0 recovered HP on the water!** | 175 / 34 | Fits |
| `battle.001b9dc8` | $i0 was a ↵ Cannibox! → **$i0 was a Cannibox!** | 149 / 30 | Fits |

## Already handled in the published build

| ID | Current template | Reason |
|---|---|---|
| `gameplay.001b4d95` | Dealt $d0 damage to ↵ $m1. | Current hook conditionally joins final pair; earlier event/sentence breaks stay |
| `gameplay.001b4dac` | $m1 took $d0 ↵ damage. | Current hook conditionally joins final pair; earlier event/sentence breaks stay |
| `gameplay.001b4e23` | $m0 gained ↵ $d0 XP. | Current hook conditionally joins final pair; earlier event/sentence breaks stay |
| `gameplay.001b4e38` | $m1 was defeated. ↵ $m0 gained ↵ $d0 XP. | Current hook conditionally joins final pair; earlier event/sentence breaks stay |
| `gameplay.001b4e7b` | $m0 reached level ↵ $d0. | Current hook conditionally joins final pair; earlier event/sentence breaks stay |
| `tutorial.001b507e` | !$m1 took ↵ $d0 damage. | Current hook conditionally joins final pair; earlier event/sentence breaks stay |
| `tutorial.001b6d7d` | $m0 took $d0 ↵ damage. | Current hook conditionally joins final pair; earlier event/sentence breaks stay |
| `tutorial.001b6d93` | $m1 took $d0 ↵ damage. | Current hook conditionally joins final pair; earlier event/sentence breaks stay |

## Continuation cases requiring separate validation

| ID | Current template | Reason |
|---|---|---|
| `tutorial.001b5038` | !Critical hit! $m1 ↵ took $d0 damage. | Fits may depend on earlier attacker fragment; dedicated continuation tests required |
| `tutorial.001b505b` | !Brutal blow! $m1 ↵ took $d0 damage. | Fits may depend on earlier attacker fragment; dedicated continuation tests required |

## Keep current layout

| ID | Current template | Reason |
|---|---|---|
| `gameplay.001b459d` | $i0 is cursed! ↵ You can't remove it! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b4637` | $i1 is cursed! ↵ You can't remove it! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b46cf` | $t can't pick up items, so can't ↵ take anything out of the pot on the ↵ ground! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b4703` | Your inventory is full. You can't take ↵ anything else out of the pot. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b475d` | $i0 is firmly ↵ stuck to the ground underwater. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b47ce` | Your inventory is full. You can't pick up ↵ $i0. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b4b8c` | $i0 is cursed! ↵ You can't remove it! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b4cc5` | The sealed effects of several items were ↵ restored. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b4cef` | The Weakening trap's effect on ↵ $i0 wore off. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b4d0c` | The Weakening trap's effect on several ↵ items wore off. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b54b6` | $i0 is cursed! ↵ You can't fire it! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b54d5` | $i0 is cursed! ↵ You can't remove it! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `gameplay.001b5560` | The item was a Mimic! But for some ↵ reason, it couldn't appear. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `tutorial.001b69cc` | The bread stopped ↵ $m1's strength from ↵ falling. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `tutorial.001b69ef` | The herb stopped ↵ $m1's strength from ↵ falling. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `tutorial.001b6a5f` | The ring stopped ↵ $m1's maximum HP ↵ from falling. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `tutorial.001b6bba` | The attack missed. Nothing was knocked ↵ away. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `tutorial.001b6bd5` | The attack missed. Nothing was knocked ↵ away. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `tutorial.001b6ebe` | The monster sharing the pain took damage ↵ too! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `tutorial.001b6ede` | The ally sharing the pain took damage ↵ too! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `tutorial.001b703c` | The equipped ring kept ↵ $i0 from ↵ deteriorating. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b5b4d` | $m0 was poisoned! ↵ Strength fell by $d0. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b5bd5` | $t's poison cleared up, ↵ and Strength was restored. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b5bf5` | $m1's poison cleared ↵ up, ↵ and Attack was restored! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b5dd9` | $m0 now moves at ↵ double speed, ↵ with one attack per turn! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b5df1` | $m0 now moves at ↵ double speed, ↵ with two attacks per turn! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b5ef1` | The explosives became damp ↵ and can no longer explode! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b5f47` | $m1 can no longer ↵ see things ↵ as they really are! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b629f` | On this floor, $t can identify ↵ items just by picking them up! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b62d2` | On this floor, $t is so wide awake ↵ that nothing can put him to sleep! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b62fc` | On this floor, $t's Strength ↵ cannot be lowered! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b6322` | On this floor, $t can move quietly ↵ without waking monsters! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b6359` | On this floor, $t can move ↵ without getting hungry! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `help.001b64ed` | Lucky! The scroll identified ↵ every item you are carrying! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b4ff0` | $m0: "$t, you ↵ idiot! What have you done with my ↵ luggage?!" | Spoken/event dialogue; preserve pacing |
| `battle.001b7de0` | $i0 is cursed! ↵ You can't remove it! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b7f1d` | A monster was summoned, but could not ↵ appear! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b7f5b` | The summoning switch activated! ↵ But nothing could appear. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b7f85` | $t no longer takes damage from ↵ spiked floors! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8040` | $m1 cannot stop ↵ worrying about what's behind them! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b805e` | $m1 is very worried ↵ about what's behind them! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8175` | Herbs and seeds now have a stronger ↵ effect on $m1! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8352` | You have no items whose strength can be ↵ reduced to 0. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8370` | Your items' strength was not reduced to ↵ 0. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b83fe` | The ring tried to cause an explosion, but ↵ it fizzled! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b84d3` | \xf9\xacThe Yggdrasil leaf was blessed, so it ↵ did not turn into Weed! | Indexed glyph or control needs its existing rendering contract |
| `battle.001b84fb` | \xf9\xacThe Mystic herb prevented the Yggdrasil ↵ leaf from turning into Weed! | Indexed glyph or control needs its existing rendering contract |
| `battle.001b8526` | $m0 tried to recover, ↵ but a wall blocked the way! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8550` | $m0 tried to recover, ↵ but a creature blocked the way! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b857e` | $m0 tried to recover, ↵ but a crystal blocked the way! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b85ac` | $t tried to revive, but a wall ↵ blocked the way! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b85d7` | $t tried to revive, but a creature ↵ blocked the way! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8604` | $t tried to revive, but a wall ↵ blocked the way! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b86e8` | $m0 tried to shred ↵ an item, but the ability was blocked! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b87e3` | $m0 was about to be ↵ born, but could not appear. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8a88` | The disguised $m1 ↵ turned into a Medicinal herb! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8c84` | The planted scroll ignited! ↵ But it failed to go off. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8dc7` | $m0 is holding you! ↵ You cannot walk! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8e2a` | The effect of ↵ $i0 inside the ↵ pot spread around the area! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b8e4b` | $i0 spread an ↵ item effect throughout the room! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b91d8` | "Thief! Thief!" ↵ A thunderous shout echoed across the ↵ floor! | Spoken/event dialogue; preserve pacing |
| `battle.001b943d` | The statue caused self-destruction, but ↵ it fizzled! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b946c` | The statue tried to explode, but it ↵ fizzled! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b9c40` | $m1 was controlled ↵ and began attacking allies! | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b9c74` | The water soaked the statue, but nothing ↵ happened. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |
| `battle.001b9d3c` | But there was not enough strength to do ↵ it. | Even minimum nonempty substitutions exceed capacity, or breaks separate sentences |

## Excluded multiline messages

| ID | Current template | Reason |
|---|---|---|
| `gameplay.00c3ff04` | Restore the default settings? ↵ Are you sure? | System/settings message |
| `gameplay.00c3ff2c` | Entering sleep mode. ↵ Do not turn off the power. ↵ Press L+R+SELECT to return. | System/settings message |
| `tutorial.001b47ea` | Equip this to raise Attack! ↵ $wPress B to open the menu, then choose ↵ Items to equip it. | Tutorial: preserve pause and instruction structure |
| `tutorial.001b4839` | Eat this to restore fullness! ↵ $wWhen hungry, press B to open the menu ↵ and choose Eat. | Tutorial: preserve pause and instruction structure |
| `tutorial.001b4891` | Equip this to raise Attack! ↵ $wPress B to open the menu, then choose ↵ Items to equip it. | Tutorial: preserve pause and instruction structure |
| `tutorial.001b48e0` | Equip this to raise Defence! ↵ $wPress B to open the menu, then choose ↵ Items to equip it. | Tutorial: preserve pause and instruction structure |
| `tutorial.001b492f` | Choose Push to restore HP! ↵ $wWhen HP is low, press B to open the menu ↵ and use it from Items. | Tutorial: preserve pause and instruction structure |
| `tutorial.001b498d` | Drink this to breathe fire at an adjacent ↵ monster! ↵ $wFace the monster with START or the ↵ +Control Pad, then drink it. | Tutorial: preserve pause and instruction structure |
| `tutorial.001b49f5` | Throw this at a monster to put it to ↵ sleep! ↵ $wFace the monster with START or the ↵ +Control Pad, then throw it. | Tutorial: preserve pause and instruction structure |
| `tutorial.001b4a61` | Drink this to warp to another spot ↵ instantly! ↵ $wDrink it to escape when monsters surround ↵ you! | Tutorial: preserve pause and instruction structure |
| `tutorial.001b4ab5` | Drink this to restore strength lost to ↵ poison! ↵ $wUse it when your strength has fallen. | Tutorial: preserve pause and instruction structure |
| `help.001b4f0c` | $t can now order allies to ↵ [$m0]! | Ally-order notice |
| `help.00c3e334` | Ordered allied monsters to ↵ [$m0]. | Ally-order notice |
| `help.00c3e37c` | Ordered [$m0]. ↵ Controlled allies were excluded. | Ally-order notice |
| `battle.001b8efe` | Shopkeeper: "Oh, did you need something ↵ from my shop?" ↵ Shopkeeper: "Sorry, but I'm taking a ↵ break. Please come back another time." ↵ Shopkeeper: "Oh, and one more thing. Just ↵ because I'm not watching, don't think you ↵ can walk off with the goods!" | Paged shop/companion/recruitment dialogue |
| `battle.001b8feb` | Shopkeeper: "Sorry, but everything is sold ↵ out." | Paged shop/companion/recruitment dialogue |
| `battle.001b9010` | Shopkeeper: "The goods you're taking and ↵ the ones you've used come to ↵ [$d2]G." | Paged shop/companion/recruitment dialogue |
| `battle.001b9056` | Shopkeeper: "The goods you're taking ↵ come to [$d2]G altogether. Is ↵ that all right?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9099` | Shopkeeper: "That will be [$d2]G ↵ for the goods you've used." | Paged shop/companion/recruitment dialogue |
| `battle.001b90d4` | Shopkeeper: "Hmm, I see. Then how about ↵ [$d2]G?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9108` | Shopkeeper: "Hmm, I see. Then how about ↵ [$d2]G?" | Paged shop/companion/recruitment dialogue |
| `battle.001b913d` | Shopkeeper: "Hmm, I see. Then how about ↵ [$d2]G?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9172` | Shopkeeper: "I'll pay [$d0]G for ↵ the goods you've left here. Is that all ↵ right?" | Paged shop/companion/recruitment dialogue |
| `battle.001b91b3` | Shopkeeper: "Sorry, but you don't seem to ↵ have enough money." | Paged shop/companion/recruitment dialogue |
| `battle.001b94f2` | Ines: "I'm sorry, Torneko... I can't cast ↵ any more spells until I've rested." | Paged shop/companion/recruitment dialogue |
| `battle.001b955b` | Ines: "Oh, you've changed your mind? If ↵ my magic can help, please ask me any ↵ time." | Paged shop/companion/recruitment dialogue |
| `battle.001b95a5` | Ines: "Oh? But we seem to be at full ↵ health already." | Paged shop/companion/recruitment dialogue |
| `battle.001b95ec` | Ines: "Oh no! The spell didn't work. I've ↵ wasted one use." | Paged shop/companion/recruitment dialogue |
| `battle.001b964a` | Ines: "Phew... $t. I'm sorry, but I ↵ can only cast Heal once more." | Paged shop/companion/recruitment dialogue |
| `battle.001b96a6` | Ines: "Phew... $t. I'm sorry, but I ↵ can only cast Bang once more." | Paged shop/companion/recruitment dialogue |
| `battle.001b96ec` | Ines: "Oh? But neither of us seems to be ↵ poisoned." | Paged shop/companion/recruitment dialogue |
| `battle.001b9732` | Ines: "Phew... $t. I'm sorry, but I ↵ can only cast Squelch once more." | Paged shop/companion/recruitment dialogue |
| `battle.001b977c` | $m0 got up and is ↵ looking at you, eager to join you! ↵ But you cannot take any more allies along! | Paged shop/companion/recruitment dialogue |
| `battle.001b97cd` | $m0 got up and is ↵ looking at you, eager to join you! ↵ Will you let it join? | Paged shop/companion/recruitment dialogue |
| `battle.001b9831` | $m0 seems to be ↵ waiting for you to give it a name... | Paged shop/companion/recruitment dialogue |
| `battle.001b9871` | $m0 has decided to ↵ follow $t under the name ↵ $m1! | Paged shop/companion/recruitment dialogue |
| `battle.001b997c` | $m0: "Hello! Did you ↵ need something?" | Paged shop/companion/recruitment dialogue |
| `battle.001b999a` | $m0: "Great! My ↵ friends came!" | Paged shop/companion/recruitment dialogue |
| `battle.001b99bc` | $m0: "Oh, you ↵ changed your mind? Aww." | Paged shop/companion/recruitment dialogue |
| `battle.001b99d7` | $m0: "I called my ↵ friends, but nobody came..." | Paged shop/companion/recruitment dialogue |
| `battle.001b9a04` | $m0: "I called my ↵ friends, but nobody came..." | Paged shop/companion/recruitment dialogue |
| `battle.001b9a31` | $m0: "I called my ↵ friends, but nobody came..." | Paged shop/companion/recruitment dialogue |
| `battle.001b9a5e` | $m0: "Squeeze, ↵ squeeze. What do you need?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9a79` | $m0: "Oh, never ↵ mind, then. Squeeze, squeeze." | Paged shop/companion/recruitment dialogue |
| `battle.001b9a92` | $m0: "Right, I'm ↵ going underground now. Here goes!" | Paged shop/companion/recruitment dialogue |
| `battle.001b9ab4` | $m0: "Do you need ↵ something from me...?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9ad0` | $m0: "I see. You've ↵ changed your mind..." | Paged shop/companion/recruitment dialogue |
| `battle.001b9ae7` | $m0: "Underground... ↵ To where there is more blood..." | Paged shop/companion/recruitment dialogue |
| `battle.001b9b0e` | $m0: "Do you need ↵ me...?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9b29` | $m0: "What? You've ↵ changed your mind...?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9b41` | $m0: "Moving ↵ underground is my speciality. Leave it to ↵ me..." | Paged shop/companion/recruitment dialogue |
| `battle.001b9b6f` | $m0: "Do you need ↵ me...?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9b8a` | $m0: "What? You're ↵ an odd one..." | Paged shop/companion/recruitment dialogue |
| `battle.001b9ba5` | $m0: "I'm going ↵ underground... Even I don't know where ↵ I'll come up..." | Paged shop/companion/recruitment dialogue |
| `battle.001b9bdd` | $m0: "Did you need ↵ something from me?" | Paged shop/companion/recruitment dialogue |
| `battle.001b9bf6` | $m0: "Oh, you ↵ changed your mind?" | Paged shop/companion/recruitment dialogue |

## Approval scope and later validation

Proposed implementation: the candidate spans marked Fits, plus the two critical/brutal continuation variants after explicit attacker-prefix validation. This requires extending the guarded joining mechanism to the approved spans, including three-line spans; merely adding every source to the current final-pair allowlist would not implement this audit correctly. Do not merge independent messages or remove every LF globally.

Before publishing any implementation, run native formatter/live-queue/history tests for every approved span, short and longest practical names, item suffixes, numeric extremes, non-ASCII fallback, buffer guards, ring wrap and sentence-boundary preservation. Include exact 208/209px and 59/60-byte boundary cases, and combined attacker/critical/damage sequences. Preserve existing XP/damage tests and menu publication checks. A passing static measurement is not runtime acceptance.

The machine-readable inventory includes every entry, including those without breaks, original Japanese, current ROM target, pointer owners, exact bytes, per-span measurements and decisions: [audit.json](../build/combat-line-audit/audit.json). The original command was `.venv/bin/python -m tools.audit_combat_lines`; it validates the pre-change hook and is not a live audit of the newer joined build. The approved source selection is frozen in `translations/combat-line-joins.json`. Existing renderer/history evidence: [tutorial gameplay](TUTORIAL_GAMEPLAY.md), [battle feedback](BATTLE_COMPLETION.md), [current damage joining](DAMAGE_LINES.md).
