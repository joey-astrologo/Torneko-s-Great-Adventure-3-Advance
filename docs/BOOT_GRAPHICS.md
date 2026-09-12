# Boot graphics and title-logo coverage

The current English build still displays the Japanese illustrated title logo.
The user explicitly chose to preserve that original artwork. It is an
intentional retained graphic outside the ordinary text inventory, not an
authored English translation. Its lettering is embedded in the stone-scroll
artwork. No title-art replacement is planned.

[Original title, captured from the English build](../build/completion/boot-graphics/research/english/boot-0600.png)
and [decoded foreground tiles](../build/completion/boot-graphics/research/asset-02-map-0.png)
show the actual resource. The ocean layer has holes behind the foreground;
removing the logo would not reveal a complete background.

The lettering reads Dragon Quest, Dragon Quest Characters, Torneko's Great
Adventure 3, Advance and Mystery Dungeon. Those are proposed independent English
renderings, not a claim that this game received an official English title.
The existing `PUSH START BUTTON` prompt is already English and blinks through
two rows of the same foreground map.

## Evidence and scope

[The audit harness](../tools/audit_boot_graphics.py) cold-boots the pinned Japanese
ROM and current combined English ROM with disposable saves and mGBA's built-in
BIOS. It supplies no buttons, forced function entry or RAM writes. Both runs
select the same four graphics and pass exact native map/tile copy checks:

| First selection frame | Record | Graphic |
| --- | --- | --- |
| 8 | 1 | Square Enix |
| 163 | 0 | Chunsoft |
| 317 | 9 | Copyright notice |
| 471 | 2 | Title and start prompt |

[Japanese provenance](../build/completion/boot-graphics/research/japanese/provenance.json)
and [English provenance](../build/completion/boot-graphics/research/english/provenance.json)
pin ROM/harness/helper hashes. Nine frame-matched screenshots agree exactly
between variants. Separate cold traces from frame zero through frame 600 see
no shared character decoder, string draw, glyph draw or message formatter calls.
This closes the earlier **first-600-frame gap for this natural boot route**;
it does not cover alternate boot/save-error conditions or every graphics reader.

The shared loader uses eleven contiguous 16-byte records. The remaining decoded
assets are five illustrated menu backgrounds (records 3–7) and blue/green gradient
backgrounds (8 and 10). Visual inspection found no additional Japanese lettering
in those seven assets. Their natural callers were not exercised by the boot
route, and other graphic families remain outside this finding.

The [range manifest](../build/completion/boot-graphics/research/resource-ranges.json)
and [central memory map](MEMORY_MAP.md#cold-boot-and-title-graphics-new-coverage)
record the exact occupied maps, tiles, palettes, table, native readers and
existing RAM/VRAM buffers. No range is released for reuse and no ROM changes
are made by this audit. It does not change the ordinary text-inventory counts.

```bash
.venv/bin/python -m tools.audit_boot_graphics
```

The exported asset PNGs are structural decodes of original tile indices and RGB
palette words. The emulator captures are the authority for actual display
colours, timing and composition.

User scope update: graphics work is deferred to a later phase. The user
reports dungeon-floor/arrival title cards and possible town/ending/credit
graphics; these require a separate discovery and translation pass. Do not
infer that the eleven boot/menu assets cover those families. Continue
ordinary text-source research and insertion checks now. The original Japanese
title artwork remains intentionally preserved.
