# Enemy-trait drafts

Current status: All 200 trait rows now have full drafts and measured display text in the combined milestone. This page preserves the earlier 80-draft research batches and their historical insertion status. See [ENEMIES_AND_ITEMS.md](ENEMIES_AND_ITEMS.md) for the current build, commands and validation.

Reviewed 2026-09-10. **80 monster-trait rows** now have independent English
translations in [master.json](../translations/master.json), recorded as batches
`enemy-traits-01` through `enemy-traits-03` in the [glossary](../translations/glossary.json). The drafts
are also in the [searchable catalog](../build/text-extraction/index.html).
**They have not been inserted into a playable ROM.**

The effect text comes exclusively from Torneko 3's pinned Japanese ROM.
[Modern species names](ENEMY_NAMES.md) supply the labels for this review.
Spell and ability names use the sourced glossary; no other game's description,
effect values, spell mechanics or monster statistics were copied. A pun in a species name does not imply that Torneko 3 uses a particular
spell or ability.

## Batch 1: first 16 rows

Rows are zero-based table indexes. Literal `<CR>` tokens below preserve the
original source control boundaries. Their runtime layout still needs tracing.
The [review JSON](../build/enemy-traits/batch-01/review.json) and
[TSV sheet](../build/enemy-traits/batch-01/review.tsv) include each complete
Japanese source, English draft, source ID, control sequence and review notes.

| Row | Species | English draft |
|---:|---|---|
| 4 | Bubble slime | `Its attacks occasionally inflict poison.` |
| 7 | Muddy hand | `Cannot walk.<CR>Burrows underground to evade special attacks.<CR>Throws nearby items.` |
| 8 | Bloody hand | `Cannot walk.<CR>Burrows underground to evade special attacks.<CR>Pulls enemy monsters closer.` |
| 21 | Slime | `No notable special abilities.` |
| 22 | She-slime | `No notable special abilities.` |
| 23 | Metal slime | `Moves quickly.<CR>Flees when it spots anyone, friend or foe.<CR>High defence, but low HP.` |
| 35 | Troll | `Builds up strength before attacking.` |
| 36 | Stout troll | `Builds up strength before attacking.` |
| 37 | Great troll | `Builds up strength before attacking.<CR>Its defence rises while it builds up strength.` |
| 64 | Magic marionette | `Creates traps or changes existing ones.` |
| 80 | Killing machine | `Deals damage to an enemy twice per attack.` |
| 81 | Hunter mech | `Deals damage to an enemy three times per attack.` |
| 87 | Living statue | `No notable special abilities.` |
| 88 | Stone guardian | `No notable special abilities.` |
| 94 | Platypunk | `No notable special abilities.` |
| 197 | Metal slime knight | `Moves quickly.` |

## Batch 2: 32 further rows

The [second review JSON](../build/enemy-traits/batch-02/review.json) and
[TSV sheet](../build/enemy-traits/batch-02/review.tsv) retain the Japanese text,
English drafts, glossary IDs and control sequences for all 32 new rows.

| Row | Species | English draft |
|---:|---|---|
| 3 | Liquid metal slime | `Flees when it spots anyone, friend or foe.<CR>Warps when next to an enemy or when damaged.<CR>Moves quickly.` |
| 11 | Bodkin archer | `Attacks from a distance with wooden arrows.` |
| 12 | Bodkin bowyer | `Attacks from a distance with iron arrows.<CR>Keeps 2 squares away from friends and foes.` |
| 13 | Bodkin fletcher | `Attacks from a distance with poison arrows.` |
| 15 | Golem | `No notable special abilities.` |
| 16 | Stone golem | `No notable special abilities.` |
| 17 | Gold golem | `No notable special abilities.` |
| 18 | Healslime | `Uses Heal on living creatures in all 8 adjacent squares.<CR>Wanders unpredictably.<CR>Can move freely over water.` |
| 19 | Cureslime | `Uses Fullheal on living creatures in all 8 adjacent squares.<CR>Wanders unpredictably.<CR>Can move freely over water.` |
| 38 | Walking corpse | `Its rust attack lowers the attack power of the enemy in front.<CR>Throws items from underfoot at enemies.` |
| 39 | Corpse corporal | `Its rust attack lowers the attack power of the enemy in front.<CR>Throws items from underfoot at enemies.` |
| 40 | Ghoul | `Its rust attack lowers the attack power of the enemy in front.<CR>Throws items from underfoot at enemies.` |
| 42 | Green dragon | `Breathes fire to attack from a distance.` |
| 43 | Blue dragon | `Breathes fire to attack from a distance.<CR>Its flames home in on enemies anywhere in the room.` |
| 44 | Dread dragon | `Breathes fire to attack from a distance.<CR>Its flames home in on enemies anywhere on the floor.` |
| 51 | Bag o' laughs | `Ignores the hero and enemies to search for gold.<CR>When it finds gold, it warps to fetch it.` |
| 58 | Imp | `Ignores the hero and enemies to search for items.<CR>When it finds an item, it warps to fetch it.` |
| 59 | Minidemon | `Ignores the hero and enemies to search for items.<CR>When it finds an item, it warps to fetch it.` |
| 63 | Mud mannequin | `Uses Weird Dance to lower the level<CR>of the enemy monster in front by 1.` |
| 68 | Dracky | `Wanders unpredictably.<CR>Can move freely over water.` |
| 69 | Drackmage | `Wanders unpredictably.<CR>Can move freely over water.` |
| 70 | Drackyma | `Wanders unpredictably.<CR>Can move freely over water.` |
| 89 | Rockbomb | `Explodes when its HP is low.<CR>Also explodes if caught in another explosion.` |
| 90 | Bomboulder | `When an adjacent ally falls,<CR>uses Kerplunk to revive it.` |
| 99 | Chimaera | `Flies toward enemy monsters it spots.<CR>Can move freely over water.` |
| 100 | Cosmic chimaera | `Flies toward enemy monsters it spots.<CR>Can move freely over water.` |
| 101 | Hocus chimaera | `Casts Fizzle to seal the enemy in front.<CR>Flies toward enemy monsters it spots.<CR>Can move freely over water.` |
| 129 | Gem slime | `Can cast Magic Burst.<CR>Can move freely over water.` |
| 130 | Emperor slime | `Casts Multiheal<CR>to restore HP to living creatures throughout the room.<CR>Can move freely over water.` |
| 155 | King slime | `Casts Multiheal to restore HP<CR>to living creatures throughout the room.` |
| 156 | King cureslime | `Casts Omniheal to restore HP<CR>to living creatures throughout the room.` |
| 157 | Metal king slime | `Sometimes reflects enemy attacks back unchanged.<CR>Warps when next to an enemy or when damaged.<CR>Negates magic attacks.` |

The following **XI naming matches** are documented through secondary DQ Wiki
references. Only names come from those sources; the effects above come from
Torneko 3's Japanese.

| Japanese name | English label / source |
|---|---|
| ホイミ | [Heal](https://dragon-quest.org/wiki/Heal) |
| ベホマ | [Fullheal](https://dragon-quest.org/wiki/Fullheal) |
| ベホマラー | [Multiheal](https://dragon-quest.org/wiki/Multiheal) |
| ベホマズン | [Omniheal](https://dragon-quest.org/wiki/Omniheal) |
| マホトーン | [Fizzle](https://dragon-quest.org/wiki/Fizzle) |
| メガザル | [Kerplunk](https://dragon-quest.org/wiki/Kerplunk) |
| マダンテ | [Magic Burst](https://dragon-quest.org/wiki/Magic_Burst) |
| 不思議な踊り | [Weird Dance](https://dragon-quest.org/wiki/Weird_Dance) |

The wording **sealed** (verb **seal**) for 封印 is a provisional project status
term. Mainline XI provides **Fizzle** for マホトーン; some Monsters titles split
Fizzle/Kafizzle differently. This batch does not import that split or narrow
Torneko's sealing effect to spell-only silence. Wooden, iron and poison arrows
are literal ammunition descriptions in the prose, not a newly verified series
item-name glossary.

Mechanics preserved in this batch:

- Healslime and Cureslime affect **living creatures in all eight adjacent
  squares**, rather than only allies. Room-wide healing keeps the same broad
  living-creature wording. No healing amounts are added, even for a spell named
  Fullheal or Omniheal.
- **Weird Dance lowers the front enemy monster's level by 1**. Its XI MP drain
  is not used in this description.
- Blue dragon's homing reaches throughout the **room**; Dread dragon's reaches
  throughout the **floor**. The wording does not claim simultaneous area damage.
- Metal slime variants retain the source's precise warp triggers. Metal king
  slime's occasional reflection and magic-attack negation remain separate traits.
- The undead trio retains rust-based attack-power reduction and throwing
  underfoot items. Gold/item collectors retain searching and warp retrieval;
  no recipient, stealing rule or exact warp destination is invented.
- **Kerplunk** keeps the adjacent fallen-ally trigger. “Revive” interprets
  recovery of that fallen ally; the text adds no self-sacrifice cost, healing
  amount or extra target list from another game.

Batch 2 adds **2,408 hypothetical ASCII bytes including terminators**, counting
`<CR>` as `0D`. Its widest raw font-0 segment is **315 pixels**. The full prose
is retained for review and needs reflow after the real reader/layout is traced.
The [verification report](../build/enemy-traits/batch-02/verification.json)
records preservation and regeneration checks alongside the third name batch.

Batch 2 validation passed **87 tests**, verified all 144 name/trait drafts
at that time in the generated views, preserves every source control sequence, and
checks consistent English for identical translated Japanese clauses across
both trait batches. The eight sourced spell/ability names match their Japanese
occurrences. The previous drafts, original source and playable ROMs are
unchanged. These are draft checks; insertion and native layout remain pending.

## Batch 3: 32 further rows

The [third review JSON](../build/enemy-traits/batch-03/review.json) and
[TSV sheet](../build/enemy-traits/batch-03/review.tsv) contain all Japanese
sources, English drafts, control sequences and notes.

| Row | Species | English draft |
|---:|---|---|
| 1 | Drooling ghoul | `May spawn an enemy when attacked.` |
| 2 | Frolicker | `May spawn an enemy when attacked.` |
| 5 | Powie yowie | `Moves quickly.` |
| 6 | Sasquash | `Moves quickly.` |
| 27 | Magmalice | `Circles around enemy monsters.<CR>Burrows underground to evade thrown items.<CR>Destroys items and traps it overlaps.` |
| 28 | Firn fiend | `Freezes enemy monsters with its icy breath.<CR>Burrows underground to evade thrown items.<CR>Destroys items and traps it overlaps.` |
| 33 | Winky | `Confuses all enemies in the room at once.` |
| 34 | Peeper | `Talk to it to have it cast Kaclang at any time.` |
| 41 | Toxic zombie | `Its rust attack lowers the attack power of the enemy in front.<CR>Throws items from underfoot at enemies.` |
| 45 | Skeleton swordsman | `Knocks away items held by enemy monsters.<CR>Steps back 1 square when it dodges an attack.` |
| 46 | Skeleton soldier | `Knocks away items held by enemy monsters.<CR>Steps back 1 square when it dodges an attack.` |
| 47 | Dark skeleton | `Knocks away items held by enemy monsters.<CR>Steps back 1 square when it dodges an attack.` |
| 48 | Silvapithecus | `Moves quickly.` |
| 49 | Pazuzu | `Moves quickly.` |
| 50 | Batmandrill | `Moves quickly.` |
| 52 | Goodybag | `Searches for gold, then waits on top of it.<CR>Uses Sultry Dance to make the enemy monster in front dance.<CR>Has a high chance of evading all types of attacks.` |
| 53 | Funghoul | `Attacks with poisonous spores.<CR>May split when hit by a poison attack.` |
| 54 | Morphean mushroom | `Attacks with poisonous spores.<CR>May split when hit by a poison attack.` |
| 55 | Mushroom mage | `Attacks with poisonous spores.<CR>May split when hit by a poison attack.` |
| 71 | Shadow | `Its invisibility lets it act unseen by enemies.<CR>Wanders unpredictably.<CR>Can move freely over water.` |
| 72 | Shade | `Its invisibility lets it act unseen by enemies.<CR>Wanders unpredictably. Can move freely over water.<CR>Reflects wand effects.` |
| 95 | Crack-billed platypunk | `Closes the mouth of the enemy in front, leaving it sealed.` |
| 102 | Restless armour | `Keeps 1 square away from friends and foes.` |
| 103 | Lethal armour | `Keeps 1 square away from friends and foes.` |
| 104 | Infernal armour | `Keeps 1 square away from friends and foes.<CR>Sometimes reflects enemy attacks back unchanged.` |
| 105 | Gigantes | `Its attacks knock enemy monsters back.` |
| 106 | Atlas | `Builds up strength before attacking.` |
| 108 | Belial | `Builds up strength before attacking.<CR>Does not move while building up strength.` |
| 111 | Handsome crab | `Magic, arrows and thrown items become 2-damage hits.<CR>Can move freely within water.<CR>Fully restores its HP while in water.` |
| 112 | Crabber dabber doo | `Magic, arrows and thrown items become 2-damage hits.<CR>Can move freely within water.<CR>Fully restores its HP while in water.` |
| 113 | Crabid | `Magic, arrows and thrown items become 2-damage hits.<CR>Can move freely within water.<CR>Fully restores its HP while in water.` |
| 131 | Platinum king jewel | `Warps when next to an enemy or when damaged.<CR>Moves quickly and can move freely over water.<CR>Has a high chance of evading all types of attacks.` |

[**Kaclang**](https://dragon-quest.org/wiki/Kaclang) (アストロン) and
[**Sultry Dance**](https://dragon-quest.org/wiki/Sultry_Dance) (誘う踊り /
さそうおどり) use XI naming references, documented through secondary DQ Wiki
articles. Peeper's description retains casting through talking, without adding
XI's target, duration or MP cost. Goodybag retains making the enemy monster in
front dance, without another game's success rate or duration. Crack-billed
platypunk reuses the provisional **sealed** term; its new glossary occurrence
is appended without changing the prior Hocus chimaera review.

Mechanics preserved in this batch:

- The crab family converts **magic, arrows and thrown items into 2-damage hits**.
  This is not a two-point reduction or a claim about all attack types. Their
  movement is **within water**, and their Japanese explicitly states **full HP
  recovery** while in it. Other monsters' **over water** wording remains distinct.
- Skeletons knock away **held items**, without narrowing those to equipped
  weapons, and step back one square **when they dodge**. Armour spacing retains
  the stated one-square distance; the precise intervening gap and movement
  behavior still need native tracing, as do the existing archer spacing drafts.
- Drooling ghoul and Frolicker may spawn an **enemy when attacked**. The mushroom
  trio may split **when hit by a poison attack**. No probabilities or clone
  counts are added.
- Magmalice and Firn fiend retain evasion of thrown items and destruction of
  overlapping items/traps. Firn fiend's icy breath is descriptive wording;
  no named breath tier or freeze duration is inferred.
- Winky explicitly confuses **all room enemies at once**. Shade reflects
  **wand effects**; Infernal armour retains its separate occasional reflection
  of enemy attacks unchanged. The source scopes are not broadened.
- Goodybag waits on found gold, Belial stays still while building up strength,
  and Platinum king jewel retains both warp triggers and its broad evasion.

Batch 3 adds **2,320 hypothetical ASCII bytes including terminators**, counting
`<CR>` as `0D`. Its widest raw font-0 segment is **315 pixels**. All **80 trait
drafts total 5,476 hypothetical bytes**. These are prose measurements; actual
layout, wrapping, reader buffers and insertion remain pending.

The [verification report](../build/enemy-traits/batch-03/verification.json)
records **87 passing tests**, all **208 name/trait drafts** in both regenerated
views, exact source reconstruction, matching control sequences and consistent
English for identical translated Japanese clauses. Earlier drafts, source
metadata, family catalogs and original/playable ROM hashes are preserved.
This batch allocates no ROM/RAM/save space and adds no native runtime coverage.

## Batch 1 mechanics and common control rules

- Muddy hand and Bloody hand cannot **walk**. Their text retains burrowing to
  evade special attacks, then distinguishes item throwing from pulling enemies
  closer. It does not import the backup-summoning behavior of another game.
- Metal slime flees from both friends and foes; the source's high defence and
  low HP are retained. Neither speed statement receives an invented multiplier.
- Great troll's defence rises **while it builds up strength**. The source does
  not establish a tension system, numeric bonus or additional duration.
- Killing machine deals damage twice per attack; Hunter mech does so three
  times. These describe multiple damage events, not multiplied damage or turns.
- Repeated Japanese clauses use consistent English at the selected source
  addresses. Other untranslated occurrences remain pending, not automatically
  approved by a broad replacement.

Only plain text and the existing `<CR>` controls occur in the selected sources.
All control counts and their order are retained in the drafts. A future inserter
must deliberately encode those tokens; they are not literal angle-bracket text
to write into the ROM. Reflow remains a later layout task.

The report measures font-0 advance separately for each `<CR>`-delimited segment.
Batch 1's widest is **248 pixels**, so these prose drafts require layout work before
insertion. The available window width, active font, wrapping and buffer limits
have not yet been established. Hypothetical byte counts treat each `<CR>` as its
source byte `0D` and include the terminator; they are planning estimates, not
allocations or verified builder payloads.

## Protected source ranges

The [memory map](MEMORY_MAP.md) already records these **ROM file offsets** as
start-inclusive/end-exclusive ranges:

- Trait pointer table: `[0x001ACB74, 0x001ACE94)`, 200 four-byte pointers.
- Source-text envelope: `[0x001AAAC1, 0x001ACB71)`; exact selected spans and
  candidate pointers remain in the master catalog and extraction table report.

The trait batches change only `english` and `notes` in their selected existing master entries.
They reserve no ROM, RAM or save space and does not establish insertion ownership.
Japanese source bytes, other metadata and all earlier drafts are preserved.
The [verification report](../build/enemy-traits/batch-01/verification.json)
records these checks alongside the simultaneous second name batch.

Batch 1 validation passed: **87 tests**, exact Japanese-source reconstruction, all 16
trait drafts preserved through extraction and present in both generated views,
matching source/draft control sequences, and consistent English for identical
selected Japanese clauses. The earlier translations and ROM hashes are
unchanged. No native enemy-trait checks were run in this drafting pass.

## Continuation

There are 120 trait rows still without English drafts; the table also includes
character and placeholder rows. Continue matching identities and translating
Torneko 3 effects. Names, spells and named abilities need terminology evidence
before adopting their labels. Insertion and native layout checks are a separate
task; personal playtesting remains [deferred](PLAYTEST_BACKLOG.md).
