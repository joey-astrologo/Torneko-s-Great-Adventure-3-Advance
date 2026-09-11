# Enemy-name drafts

Current status: All 200 character/monster name rows are now translated and inserted in the combined milestone. This page preserves the earlier 128-name research batches and their historical insertion status. See [ENEMIES_AND_ITEMS.md](ENEMIES_AND_ITEMS.md) for the current build, commands and validation.

Reviewed 2026-09-10. **128 enemy species names** are now drafted in
[master.json](../translations/master.json), with Japanese identities and sources
in [glossary.json](../translations/glossary.json), batches `enemy-names-01` through
`enemy-names-04`. There are also 80 [trait descriptions](ENEMY_TRAITS.md).
They are available in the [searchable catalog](../build/text-extraction/index.html).
**These drafts have not yet been inserted into a playable ROM.**

The name batches cover 128 of the 200 character/monster-name rows. The remaining
72 rows include characters and placeholders as well as enemies; they are not
all ordinary enemy species. Nicknames and dialogue remain outside these batches.
Official localized puns are retained after matching the Japanese identity;
literal meanings and loanwords do not determine the English label.

## Batch 1: naming evidence

Thirty names use Dragon Quest XI as the reference game. The two mole species
use the modern VIII localization; this pass did not establish XI matches for
them. Each linked DQ Wiki article is a **secondary, fan-maintained reference**
for the Japanese identity and English name. The secondary
[XI bestiary](https://wiki.etherealgames.com/dq11/bestiary/) corroborates the 30
XI English labels. These are documented official-game names, with evidence
quality explicitly recorded; the wikis themselves are not official sources.

The publisher-hosted [VIII guide sample](https://www.piggyback.com/en/wp-content/uploads/sites/7/2020/04/DQ_E_SamplePages.pdf),
PDF page 8, also supports the English labels Bodkin archer, Drackmage,
Hammerhood and Man o' war. Its text layer was inspected; screenshot retrieval
failed. Japanese identities come from the species references. No other game's
description prose or mechanics were imported.

Rows below are zero-based source-table indexes. Names use project sentence
case, and the ASCII apostrophe uses an existing font-0 glyph.

| Row | Japanese source | English draft / species reference | Reference game |
|---:|---|---|---|
| 3 | はぐれメタル | [Liquid metal slime](https://dragon-quest.org/wiki/Liquid_metal_slime) | XI |
| 4 | バブルスライム | [Bubble slime](https://dragon-quest.org/wiki/Bubble_slime) | XI |
| 11 | リリパット | [Bodkin archer](https://dragon-quest.org/wiki/Bodkin_archer) | XI |
| 12 | アローインプ | [Bodkin bowyer](https://dragon-quest.org/wiki/Bodkin_bowyer) | XI |
| 13 | どくやずきん | [Bodkin fletcher](https://dragon-quest.org/wiki/Bodkin_fletcher) | XI |
| 15 | ゴーレム | [Golem](https://dragon-quest.org/wiki/Golem) | XI |
| 16 | ストーンマン | [Stone golem](https://dragon-quest.org/wiki/Stone_golem) | XI |
| 17 | ゴールドマン | [Gold golem](https://dragon-quest.org/wiki/Gold_golem_(Recurring)) | XI |
| 18 | ホイミスライム | [Healslime](https://dragon-quest.org/wiki/Healslime) | XI |
| 19 | ベホマスライム | [Cureslime](https://dragon-quest.org/wiki/Cureslime) | XI |
| 20 | しびれくらげ | [Man o' war](https://dragon-quest.org/wiki/Man_o%27_war) | XI |
| 21 | スライム | [Slime](https://dragon-quest.org/wiki/Slime) | XI |
| 22 | スライムベス | [She-slime](https://dragon-quest.org/wiki/She-slime) | XI |
| 23 | メタルスライム | [Metal slime](https://dragon-quest.org/wiki/Metal_slime) | XI |
| 42 | ドラゴン | [Green dragon](https://dragon-quest.org/wiki/Green_dragon) | XI |
| 43 | キースドラゴン | [Blue dragon](https://dragon-quest.org/wiki/Blue_dragon) | XI |
| 44 | ダースドラゴン | [Dread dragon](https://dragon-quest.org/wiki/Dread_dragon) | XI |
| 65 | ミミック | [Mimic](https://dragon-quest.org/wiki/Mimic) | XI |
| 66 | ひとくいばこ | [Cannibox](https://dragon-quest.org/wiki/Cannibox) | XI |
| 68 | ドラキー | [Dracky](https://dragon-quest.org/wiki/Dracky) | XI |
| 69 | タホドラキー | [Drackmage](https://dragon-quest.org/wiki/Drackmage) | XI |
| 70 | ドラキーマ | [Drackyma](https://dragon-quest.org/wiki/Drackyma) | XI |
| 78 | いたずらもぐら | [Mischievous mole](https://dragon-quest.org/wiki/Mischievous_mole) | VIII |
| 79 | キラースコップ | [Mad mole](https://dragon-quest.org/wiki/Mad_mole) | VIII |
| 80 | キラーマシン | [Killing machine](https://dragon-quest.org/wiki/Killing_machine) | XI |
| 81 | メタルハンター | [Hunter mech](https://dragon-quest.org/wiki/Hunter_mech) | XI |
| 89 | ばくだん岩 | [Rockbomb](https://dragon-quest.org/wiki/Rockbomb) | XI |
| 109 | おおきづち | [Hammerhood](https://dragon-quest.org/wiki/Hammerhood) | XI |
| 110 | ブラウニー | [Brownie](https://dragon-quest.org/wiki/Brownie) | XI |
| 155 | キングスライム | [King slime](https://dragon-quest.org/wiki/King_slime) | XI |
| 196 | スライムナイト | [Slime knight](https://dragon-quest.org/wiki/Slime_knight) | XI |
| 197 | メタルライダー | [Metal slime knight](https://dragon-quest.org/wiki/Metal_slime_knight) | XI |

## Batch 2: 32 further names

This batch adds **22 XI matches**, **two XI S Tickington matches**, **three VIII
matches**, **three IX matches**, and **two Monsters: The Dark Prince matches**.
The secondary [XI bestiary](https://wiki.etherealgames.com/dq11/bestiary/)
corroborates the 22 ordinary XI labels. Bag o' laughs and Goodybag are documented
in the species references under XI, in the legacy areas included in **XI S**;
they are not inferred from an absence in that original-XI list. For the eight
fallbacks, no XI match was established in this pass. Each linked species
reference records the Japanese identity and the chosen game's English name.

| Row | Japanese source | English draft / species reference | Reference game |
|---:|---|---|---|
| 7 | マドハンド | [Muddy hand](https://dragon-quest.org/wiki/Muddy_hand) | XI |
| 8 | ブラッドハンド | [Bloody hand](https://dragon-quest.org/wiki/Bloody_hand) | XI |
| 35 | トロル | [Troll](https://dragon-quest.org/wiki/Troll) | XI |
| 36 | トロルボンバー | [Stout troll](https://dragon-quest.org/wiki/Stout_troll) | XI |
| 37 | トロルキング | [Great troll](https://dragon-quest.org/wiki/Great_troll) | IX |
| 38 | くさった死体 | [Walking corpse](https://dragon-quest.org/wiki/Walking_corpse) | VIII |
| 39 | リビングデッド | [Corpse corporal](https://dragon-quest.org/wiki/Corpse_corporal) | XI |
| 40 | グール | [Ghoul](https://dragon-quest.org/wiki/Ghoul) | XI |
| 51 | 笑いぶくろ | [Bag o' laughs](https://dragon-quest.org/w/index.php?mobileaction=toggle_view_desktop&title=Bag_o%27_laughs) | XI S |
| 52 | おどる宝石 | [Goodybag](https://dragon-quest.org/wiki/Goodybag) | XI S |
| 58 | ベビーサタン | [Imp](https://dragon-quest.org/wiki/Imp) | VIII |
| 59 | ミニデーモン | [Minidemon](https://dragon-quest.org/wiki/Minidemon) | VIII |
| 63 | どろにんぎょう | [Mud mannequin](https://dragon-quest.org/wiki/Mud_mannequin) | XI |
| 64 | パペットマン | [Magic marionette](https://dragon-quest.org/wiki/Magic_marionette) | XI |
| 87 | うごくせきぞう | [Living statue](https://dragon-quest.org/wiki/Living_statue_%28Recurring%29) | XI |
| 88 | だいまじん | [Stone guardian](https://dragon-quest.org/wiki/Stone_guardian) | XI |
| 90 | メガザルロック | [Bomboulder](https://dragon-quest.org/w/index.php?mobileaction=toggle_view_desktop&title=Bomboulder) | XI |
| 94 | ももんじゃ | [Platypunk](https://dragon-quest.org/wiki/Platypunk) | XI |
| 95 | メイジももんじゃ | [Crack-billed platypunk](https://dragon-quest.org/wiki/Crack-billed_platypunk) | XI |
| 99 | キメラ | [Chimaera](https://dragon-quest.org/wiki/Chimaera) | XI |
| 100 | スターキメラ | [Cosmic chimaera](https://dragon-quest.org/wiki/Cosmic_chimaera) | XI |
| 101 | メイジキメラ | [Hocus chimaera](https://dragon-quest.org/wiki/Hocus_chimaera) | XI |
| 102 | さまようよろい | [Restless armour](https://dragon-quest.org/wiki/Restless_armour) | XI |
| 103 | キラーアーマー | [Lethal armour](https://dragon-quest.org/wiki/Lethal_armour) | XI |
| 104 | じごくのよろい | [Infernal armour](https://dragon-quest.org/wiki/Infernal_armour) | XI |
| 105 | ギガンテス | [Gigantes](https://dragon-quest.org/wiki/Gigantes) | XI |
| 107 | アークデーモン | [Archdemon](https://dragon-quest.org/wiki/Archdemon) | The Dark Prince |
| 129 | ゴールデンスライム | [Gem slime](https://dragon-quest.org/wiki/Gem_slime) | IX |
| 130 | スライムエンペラー | [Emperor slime](https://dragon-quest.org/wiki/Emperor_slime) | The Dark Prince |
| 131 | プラチナキング | [Platinum king jewel](https://dragon-quest.org/wiki/Platinum_king_jewel) | IX |
| 156 | スライムベホマズン | [King cureslime](https://dragon-quest.org/wiki/King_cureslime) | XI |
| 157 | メタルキング | [Metal king slime](https://dragon-quest.org/wiki/Metal_king_slime) | XI |

Specific identity checks:

- **Corpse corporal**, **Goodybag**, **Bomboulder**, **Crack-billed platypunk**,
  **Magic marionette** and **Hocus chimaera** retain their localized names and
  wordplay; the Japanese names are not translated word for word.
- **Stout troll** (トロルボンバー) and **Great troll** (トロルキング) are distinct.
  The latter uses IX evidence; XI's **Boss troll** is a different Japanese species.
- **Bloody hand** links Torneko 3's ブラッドハンド spelling to XI's ブラッディハンド.
- **Living statue** uses the recurring monster reference, not the similarly
  named V miniboss or Sculpture vulture. **Infernal armour** is the monster,
  not the equipment item that shares its Japanese name.
- **Gem slime**, **Emperor slime** and **Platinum king jewel** use the established
  English labels for their separate Japanese identities. Full names remain
  intact for future layout work.

The [second batch report](../build/enemy-names/batch-02/review.json) and
[TSV review sheet](../build/enemy-names/batch-02/review.tsv) record every match,
source, measurement and hash. They are language drafts, with insertion pending.

The second [verification report](../build/enemy-names/batch-02/verification.json)
passed **87 tests** and checked all 80 master drafts at that time (64 names and
16 traits) against the regenerated HTML and TSV. The earlier 32 names and 53
family-catalog translations are preserved, all Japanese source fields and
controls remain intact, and the source and existing playable ROM hashes are
unchanged. Earlier batch hashes remain historical snapshots.

## Batch 3: 32 further names

This batch uses **12 XI**, **two XI S**, **four IV (DS/mobile)**, **four VIII**,
**three IX** and **seven Monsters: The Dark Prince** naming references. The
fallback game is recorded for each identity; a missing XI match is not a claim
that the species can never appear there.

| Row | Japanese source | English draft / species reference | Reference game |
|---:|---|---|---|
| 1 | スモールグール | [Drooling ghoul](https://dragon-quest.org/wiki/Drooling_ghoul) | IV (DS/mobile) |
| 2 | ベロベロ | [Frolicker](https://dragon-quest.org/wiki/Frolicker) | IV (DS/mobile) |
| 5 | イエティ | [Powie yowie](https://dragon-quest.org/wiki/Powie_yowie) | The Dark Prince |
| 6 | ビッグスロース | [Sasquash](https://dragon-quest.org/wiki/Sasquash) | IV (DS/mobile) |
| 27 | ようがんまじん | [Magmalice](https://dragon-quest.org/wiki/Magmalice) | IX |
| 28 | ひょうがまじん | [Firn fiend](https://dragon-quest.org/wiki/Firn_fiend) | IX |
| 33 | おおめだま | [Winky](https://dragon-quest.org/wiki/Winky) | VIII |
| 34 | スペクテット | [Peeper](https://dragon-quest.org/wiki/Peeper) | The Dark Prince |
| 41 | どくどくゾンビ | [Toxic zombie](https://dragon-quest.org/wiki/Toxic_zombie) | XI |
| 45 | がいこつけんし | [Skeleton swordsman](https://dragon-quest.org/wiki/Skeleton_swordsman_%28Dragon_Quest_IV%29) | IV (DS/mobile) |
| 46 | しりょうのきし | [Skeleton soldier](https://dragon-quest.org/wiki/Skeleton_soldier) | VIII |
| 47 | かげのきし | [Dark skeleton](https://dragon-quest.org/wiki/Dark_skeleton) | IX |
| 48 | シルバーデビル | [Silvapithecus](https://dragon-quest.org/wiki/Silvapithecus) | XI S |
| 49 | バズズ | [Pazuzu](https://dragon-quest.org/wiki/Pazuzu) | The Dark Prince |
| 50 | デビルロード | [Batmandrill](https://dragon-quest.org/wiki/Batmandrill) | XI S |
| 53 | おばけキノコ | [Funghoul](https://dragon-quest.org/wiki/Funghoul) | XI |
| 54 | マタンゴ | [Morphean mushroom](https://dragon-quest.org/wiki/Morphean_mushroom) | XI |
| 55 | マージマタンゴ | [Mushroom mage](https://dragon-quest.org/wiki/Mushroom_mage) | XI |
| 71 | シャドー | [Shadow](https://dragon-quest.org/wiki/Shadow) | XI |
| 72 | あやしいかげ | [Shade](https://dragon-quest.org/wiki/Shade) | XI |
| 97 | ミイラおとこ | [Mummy boy](https://dragon-quest.org/wiki/Mummy_boy) | VIII |
| 98 | マミー | [Mummy](https://dragon-quest.org/wiki/Mummy) | VIII |
| 106 | アトラス | [Atlas](https://dragon-quest.org/wiki/Atlas) | The Dark Prince |
| 108 | ベリアル | [Belial](https://dragon-quest.org/wiki/Belial) | The Dark Prince |
| 111 | ガニラス | [Handsome crab](https://dragon-quest.org/wiki/Handsome_crab) | XI |
| 112 | じごくのハサミ | [Crabber dabber doo](https://dragon-quest.org/wiki/Crabber_dabber_doo) | XI |
| 113 | ぐんたいガニ | [Crabid](https://dragon-quest.org/wiki/Crabid) | XI |
| 138 | ドラゴスライム | [Drake slime](https://dragon-quest.org/wiki/Drake_slime) | XI |
| 139 | スライムブレス | [Dragon slime](https://dragon-quest.org/wiki/Dragon_slime) | XI |
| 140 | ドラゴメタル | [Metal dragon slime](https://dragon-quest.org/wiki/Metal_dragon_slime) | XI |
| 171 | ドラゴンキッズ | [Small fry](https://dragon-quest.org/wiki/Small_fry) | The Dark Prince |
| 194 | フレイム | [Dancing flame](https://dragon-quest.org/wiki/Dancing_flame) | The Dark Prince |

Identity and evidence details:

- Torneko's **Skeleton swordsman** uses the IV one-sword design, according to
  the [Japanese species reference](https://wikiwiki.jp/dqdic3rd/%E3%80%90%E3%81%8C%E3%81%84%E3%81%93%E3%81%A4%E3%81%91%E3%82%93%E3%81%97%EF%BC%88DQ4%EF%BC%89%E3%80%91).
  The recurring multi-armed species shares its Japanese name; an XI match to
  that different design would not establish this Torneko identity.
- **Peeper** matches スペクテット. Its English wiki uses a mixed-kana spelling,
  スぺクテット; the [Japanese IV guide](https://cour89.com/dq4/monsters/041.php)
  corroborates the identity. **Winkster** is a different species.
- **Silvapithecus** is documented in XI S Tickington by the
  [guide search extract](https://www.neoseeker.com/dragon-quest-xi/Tickington).
  The full guide page could not be retrieved. DQ Wiki's XI section is only a
  stub; its Japanese identity and Dark Prince name provide corroboration, not
  independent proof of the XI S occurrence. This evidence limitation is in the
  glossary. **Batmandrill** has an explicit XI legacy-area entry in its species
  reference.
- **Shadow / Shade**, **Mummy boy / Mummy**, the three crab species, and
  **Drake slime / Dragon slime / Metal dragon slime** retain their distinct
  Japanese identities. Similar English words are not interchangeable names.
- **Powie yowie**, **Sasquash**, **Magmalice**, **Funghoul**, **Crabber dabber doo**
  and **Small fry** retain the localized names and wordplay. No new gameplay
  behavior is inferred from those names.

The [third batch report](../build/enemy-names/batch-03/review.json) and
[TSV sheet](../build/enemy-names/batch-03/review.tsv) contain the exact entries,
source references, measurements and review notes. The
[verification report](../build/enemy-names/batch-03/verification.json) covers
this name batch and the simultaneous 32 further trait drafts. Previous review
hashes continue to describe their original snapshots.

Batch 3 validation passed **87 tests**. All **144 drafts at that time** (96 names
and 48 traits) matched the regenerated HTML and TSV, including their control markers.
Exactly the intended 64 master entries changed; the previous 80 master drafts,
53 family-catalog English entries and 92 glossary terms are preserved. Japanese
source reconstruction and original/playable ROM hashes are unchanged. This
batch adds no ROM/RAM/save allocations or native runtime coverage.

## Batch 4: 32 further names

This batch adds **two XI matches**, **three IX matches**, **three Monsters:
The Dark Prince matches**, **one IV DS/mobile match**, **six HD-2D remake
matches**, **16 VII 3DS matches**, and **one VII Reimagined match**. Fallbacks
record a positively established modern English release; unsuccessful XI/XI S
lookups do not prove absence. The VII 3DS references are not a claim that a
complete VII Reimagined terminology audit has been performed.

Each species reference below is **secondary, fan-maintained evidence** of an
official localization. The separate [VII 3DS bestiary](https://www.woodus.com/den/games/dq73ds/monsters.php)
corroborates its English labels; missing or inconsistent Japanese cells in that
list are not used to establish species identity. No other game's description
or mechanics were copied.

| Row | Japanese source | English draft / species reference | Reference game |
|---:|---|---|---|
| 61 | ミステリドール | [Pocus poppet](https://dragon-quest.org/wiki/Pocus_poppet) | Monsters: The Dark Prince |
| 62 | いしにんぎょう | [Dirty dogu](https://dragon-quest.org/wiki/Dirty_dogu) | IV (DS/mobile) |
| 67 | バーサーカー | [Berserker](https://dragon-quest.org/wiki/Berserker) | II HD-2D Remake |
| 75 | テンツク | [Slugger](https://dragon-quest.org/wiki/Slugger) | IX |
| 76 | スーパーテンツク | [Sluggernaut](https://dragon-quest.org/wiki/Sluggernaut) | IX |
| 77 | ラストテンツク | [Sluggerslaught](https://dragon-quest.org/wiki/Sluggerslaught) | IX |
| 91 | さつじんき | [Hoodie](https://dragon-quest.org/wiki/Hoodie) | III HD-2D Remake |
| 92 | エリミネーター | [Hoodlum](https://dragon-quest.org/wiki/Hoodlum) | XI |
| 93 | デスストーカー | [Heavy hood](https://dragon-quest.org/wiki/Heavy_hood) | XI |
| 96 | おおナメクジ | [Maulusc](https://dragon-quest.org/wiki/Maulusc) | II HD-2D Remake |
| 114 | ゴースト | [Ghost](https://dragon-quest.org/wiki/Ghost) | I HD-2D Remake |
| 115 | メトロゴースト | [Fightgeist](https://dragon-quest.org/wiki/Fightgeist) | I HD-2D Remake |
| 116 | ヘルゴースト | [Spitegeist](https://dragon-quest.org/wiki/Spitegeist) | I HD-2D Remake |
| 124 | アイアンタートル | [Armoured wartoise](https://dragon-quest.org/wiki/Armoured_wartoise) | Monsters: The Dark Prince |
| 125 | ランドアーマー | [Iron tortoise](https://dragon-quest.org/wiki/Iron_tortoise) | Monsters: The Dark Prince |
| 147 | さそりかまきり | [Preying mantis](https://dragon-quest.org/wiki/Preying_mantis) | VII (3DS) |
| 148 | キラーマンティス | [Slaying mantis](https://dragon-quest.org/wiki/Slaying_mantis) | VII (3DS) |
| 149 | メダパニシックル | [Compos mantis](https://dragon-quest.org/wiki/Compos_mantis) | VII (3DS) |
| 150 | タマゴロン | [Bad egg](https://dragon-quest.org/wiki/Bad_egg) | VII (3DS) |
| 151 | ワンダーエッグ | [Rotten egg](https://dragon-quest.org/wiki/Rotten_egg) | VII (3DS) |
| 152 | スカイフロッグ | [Floating bloater](https://dragon-quest.org/wiki/Floating_bloater) | VII (3DS) |
| 153 | ファイヤーケロッグ | [Blistering bloater](https://dragon-quest.org/wiki/Blistering_bloater) | VII (3DS) |
| 154 | デーモントード | [Blighted bloater](https://www.woodus.com/den/resources/global-bestiary-all-bygame.php?pickedgame=dq7) | VII (3DS) |
| 158 | レノファイター | [Enormoose](https://dragon-quest.org/wiki/Enormoose) | VII (3DS) |
| 159 | グレイトホーン | [Ginormoose](https://dragon-quest.org/wiki/Ginormoose) | VII (3DS) |
| 160 | フライングデビル | [Dingbat](https://dragon-quest.org/wiki/Dingbat) | VII (3DS) |
| 161 | ランガー | [Div](https://dragon-quest.org/wiki/Div) | VII (3DS) |
| 162 | どぐう戦士 | [Terracotta warrior](https://dragon-quest.org/wiki/Terracotta_warrior_%28Dragon_Quest_VII%29) | VII (3DS) |
| 163 | キラープラスター | [Ceramic sergeant](https://dragon-quest.org/wiki/Ceramic_sergeant) | VII (3DS) |
| 164 | こうてつまじん | [Metal heavy](https://dragon-quest.org/wiki/Metal_heavy) | VII (3DS) |
| 165 | エビルエスターク | [Ersatz Estark](https://dragon-quest.org/wiki/Ersatz_Estark) | VII (3DS) |
| 166 | デスマシーン | [Slaughtomaton](https://dragon-quest.org/wiki/Slaughtomaton) | VII Reimagined |

Identity details to retain:

- **Terracotta warrior** uses the **VII** design. The
  [Japanese Torneko reference](https://wikiwiki.jp/dqdic3rd/%E3%80%90%E3%81%A9%E3%81%90%E3%81%86%E6%88%A6%E5%A3%AB%E3%80%91)
  explicitly distinguishes it from IV's どぐうせんし, which shares the English
  name. The broad VII 3DS list has an IV-tagged Japanese cell; use the
  VII-specific species article and this Torneko identity reference instead.
- **Armoured wartoise** is アイアンタートル; **Iron tortoise** is ランドアーマー.
  The Japanese loanwords cannot be used to swap those English names.
- **Pocus poppet / Dirty dogu**, **Hoodie / Hoodlum / Heavy hood**, and the
  three ghost, mantis and bloater variants retain separate species identities.
  **Ersatz Estark** retains the capitalized proper name and is not Estark himself.
- **Preying mantis**, **Compos mantis**, **Enormoose**, **Ginormoose**,
  **Maulusc** and **Slaughtomaton** retain localized wordplay. The species
  names do not establish particular Torneko abilities.
- **Blighted bloater** uses the linked Dragon's Den Japanese/English identity
  list plus its separate VII 3DS English list because DQ Wiki retrieval failed.
  Both supporting pages were retrieved; no unsupported fallback label was guessed.
- The **Sluggerslaught** species page has an inconsistent IX bestiary number.
  The separate [IX bestiary](https://dragon-quest.org/wiki/List_of_enemies_in_Dragon_Quest_IX)
  corroborates the English label; the inconsistent number is not an identifier
  in this catalog.

The [fourth batch report](../build/enemy-names/batch-04/review.json) and
[TSV sheet](../build/enemy-names/batch-04/review.tsv) record all source IDs,
reference games, measurements and notes. The
[verification report](../build/enemy-names/batch-04/verification.json) covers
this batch and the simultaneous third trait batch.

Validation passed **87 tests**. All **208 drafts** (128 names and 80 traits)
match the regenerated HTML and TSV. Exactly the intended 64 master entries
changed; all previous 144 master drafts, Japanese source fields, metadata,
53 family-catalog English entries and ROM hashes are preserved. Existing
133 glossary terms retain their meanings, sources and review history; one new
occurrence was appended to **sealed**. No ROM/RAM/save allocations or native
enemy runtime coverage were added.

## Batch 1 identity details to retain

- メタルハンター is **Hunter mech** in modern English. Keep it distinct from
  キラーマシン, **Killing machine**.
- リリパット / アローインプ / どくやずきん are three separate bodkin species.
  XI's additional Vicious/Malicious variants do not apply to these source names.
- ストーンマン is **Stone golem**, distinct from Living statue and Stone guardian.
  ゴールドマン uses the recurring **Gold golem**, not the separate DQ III creature.
- ドラゴン / キースドラゴン / ダースドラゴン are **Green dragon**, **Blue dragon**
  and **Dread dragon**. Do not substitute a differently named red-dragon species.
- タホドラキー is **Drackmage**, distinct from メイジドラキー (Drackolyte).
- ひとくいばこ / ミミック remain **Cannibox** / **Mimic**.
- メタルライダー is the mounted **Metal slime knight**, not Metal slime.
- ばくだん岩 and the reference spelling ばくだんいわ identify **Rockbomb**.

## Font and storage measurements

The full names are retained without abbreviations. Batch 1's widest raw font-0
advance is 87 pixels for Metal slime knight, and its 32 payloads total 368 bytes
including terminators. Batch 2's widest name is **Crack-billed platypunk at 107
pixels**, and its largest payload is **23 bytes including the terminator** for
Platinum king jewel. The 32 new names total **412 bytes** with terminators;
those first 64 name payloads total **780 bytes**. Batch 3 adds **367 bytes**,
with a widest raw advance of **94 pixels**; those 96 names total 1,147 bytes.
Batch 4 adds **388 bytes**, with a widest raw advance of **95 pixels**. All
**128 names total 1,535 payload bytes including terminators**; the overall
widest name remains 107 pixels.

Those are planning measurements, not verified enemy-window limits or a ROM
allocation. The future build may also need tables, code, alignment or repeated
representations. Actual enemy readers, fonts, buffer sizes and window widths
still need native validation. The report keeps `display_limit_px` unset and
marks every entry `not_inserted`.

## Source ownership and validation

The [memory map](MEMORY_MAP.md) already records these protected **ROM file
offsets**, using start-inclusive/end-exclusive ranges:

- Character/monster pointer table: `[0x00192568, 0x00192888)`, 200 four-byte pointers.
- Source-string envelope: `[0x00191C14, 0x00192565)`; exact strings and pointer
  candidates remain in the master catalog and extraction table report.

Each name batch changes only its selected master entries' `english` and
`notes`, and adds terminology records. The separate trait batch follows the
same source-preservation rule. Neither establishes new pointer ownership,
reserves ROM/RAM/save space, or changes source ROM bytes. Earlier English,
Japanese source fields, original metadata and existing notes are preserved.

The first [batch report](../build/enemy-names/batch-01/review.json) and
[TSV review sheet](../build/enemy-names/batch-01/review.tsv) contain the exact
IDs, source matches, widths and draft hashes. The glossary's earlier 53-entry
item/menu review remains a historical snapshot; this later batch is recorded
separately. The [verification report](../build/enemy-names/batch-01/verification.json)
records regeneration, preservation checks and test results for these drafts.

Batch 1 validation passed: **87 tests**, all 32 drafts preserved through regeneration
and present in both generated views, and all 9,272 extracted source entries
reconstructing the original Japanese ROM exactly. The earlier 53 English
entries, original glossary terms and both supplied ROMs are unchanged. Existing
item/context ROM hashes are also unchanged; this batch ran no new native enemy
checks and produced no new playable ROM.

Regenerate the searchable page and TSV after editing the master catalog:

```sh
.venv/bin/python -m tools.extract_master_text
.venv/bin/python -m unittest discover -s tests -v
```

## Continuation

Continue matching the remaining enemy species and drafting traits from
Torneko 3's Japanese, with uncertain identities explicitly flagged. Enemy
insertion is a separate implementation task with its own native checks.
Personal playtesting can wait; outstanding gameplay coverage is recorded in
[PLAYTEST_BACKLOG.md](PLAYTEST_BACKLOG.md).
