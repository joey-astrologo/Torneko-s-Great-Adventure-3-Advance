# Japanese guide leads for unresolved text

Initial source check: 2026-09-12. Japanese guides can identify mechanics and
suggest reproducible situations for the remaining candidates. They do not
establish a ROM reader, buffer capacity, pointer ownership or non-use. This
bounded check does not resolve any of the **74 open candidates** or change the
accepted ROM. It is not a complete external review of all 74.

Source identities and ranges remain in the
[review catalog](../translations/unowned-text-review.json) and
[memory map](MEMORY_MAP.md). Existing native evidence is in
[the seventeen-candidate investigation](GAMEPLAY_CANDIDATES.md).
All websites below are fan-maintained secondary sources; none supplies an
official English translation. References to the general/PS2 game must be
checked against Advance before applying their mechanics.

## Weight categories

The six sources beginning at `001B4495`, `001B449D`, `001B44A1`, `001B44A5`,
`001B44AB` and `001B44AF` describe weights from very light to very heavy.
The [Japanese casino guide](https://toruneko3.kouryaku.red/entry67.html)
lists corresponding categories in its item-weight table, next to its
weight-contest information. Five labels match exactly; the normal category
adds a weight noun to our source's short adjective.

This supports the item-weight interpretation. It does not show that the GBA
item screen reads these six addresses. The guide does not clearly establish
Advance scope, so the next checks should distinguish an active GBA display
from text retained from the PS2 system. Our existing 370-item footer test did
not output these labels. A failed search or a removed feature alone would not
prove that these bytes are unused everywhere.

## Shell emergence

Source `001B530A` says that the substituted actor came out of its shell.
The [Japanese monster list](https://game.bad-person.net/gamenote/toruneko3/t3_monsterlist.html)
assigns shell withdrawal to the snail monster あんこくつむり.
The [DQ dictionary's Torneko 3 section](https://wikiwiki.jp/dqdic3rd/【あんこくつむり】)
also describes its defensive behaviour and relates it to つのうしがい and
しびれマイマイ.

Inference: the snail family's transition out of defence is a useful test
target. These sources do not quote the candidate sentence or establish its
GBA caller. Check both natural expiry and status removal where the original
game permits them; keep the exact entity and version explicit.

## Destination-pot failure

Source `001B8A4A` describes being unable to emerge above the destination pot.
The [Japanese pot reference](https://w.atwiki.jp/toruneko3/pages/135.html)
describes ワープの壷 transporting its target to another such pot on the same
floor. An [Advance identification guide](https://peamon.net/toruneko3a/isekai/isekai-sikibetu.html)
independently lists ワープの壺 among the four push-type pots.

Inference: test transit with the destination occupied or otherwise
inaccessible, then follow the actual message selection. Neither guide
establishes the failure condition or quotes this source. The GBA-specific
listing corroborates the item's presence, not every cross-version detail.

## Limits and follow-up

Exact-phrase searches for the item-loss sentence and shell-emergence line did
not produce a verified matching gameplay transcript in this initial check.
The literal `★間` in `001B551C` remains unresolved; the searches do not justify
substituting a guessed kanji or equating it with the equipment plating marker.

Prioritize Japanese guides, player reports, screenshots and recordings for
the seventeen gameplay/frontend candidates. Record the page, platform,
observed wording, proposed trigger and remaining uncertainty. Reproduce the
strongest leads in the pinned Japanese ROM and trace their readers before
promoting drafts for insertion. Debug labels, duplicate linked resources and
the combined character map will usually need code/data investigation even
when their text is understandable.
