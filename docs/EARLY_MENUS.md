# Early menus and adventure creation

Status, 2026-09-10: **21 entries added, 27 translated entries total**, using the
Japanese ROM's existing font 0. The expanded build passes Japanese round-trip
preservation, native rendering, and adventure creation/loading in both slots.
Translations are independent drafts from Japanese. The fan translation supplies
no English or font assets.

Use the commands in [TRANSLATION_PIPELINE.md](TRANSLATION_PIPELINE.md). The current
ROM is `build/translation/torneko3-english.gba`; the six-screen review image is
`build/translation/early-menus.png`.

## Added sources

All addresses below are **file offsets in the Japanese original**. The builder
checks each pointer's original value before relocating its source. Every listed
pointer and relocated source was observed on a native mGBA route.

| Entry | Source | Pointer owner | English / purpose |
|---|---|---|---|
| `title.delete_log` | `C782BC` | `C78288` | Delete log |
| `settings.display` | `C401E0` | `78634` | Display; Light / Bold / Norm |
| `settings.reset` | `C400AC` | `7856C` | Reset settings |
| `save.slot_one` | `C783AC` | `8559C` | Log 1, retaining choice attribute 1 |
| `save.slot_two` | `C783BC` | `855A0` | Log 2, retaining choice attribute 2 |
| `save.empty_log` | `C7841C` | `85870` | This Adventure Log is empty. |
| `mode.choose` | `C787D8` | `85BB0` | Choose a mode; first-time players should read Help |
| `mode.scenario_confirm` | `C7A990` | `85BD8` | Set the selected log to Story mode? |
| `save.initializing` | `C78508` | `859EC` | Preparing the selected log for a new adventure |
| `save.start_story` | `C78300` | `84EC0` | Begin from the start of the story using this log |
| `save.loading` | `09B4B0` | `01E68` | Loading the selected log |
| `save.loaded` | `C78A24` | `85DE4` | The selected log was loaded |
| `choice.yes_default` | `C420DC` | `C420B0` | Yes; initially selected for name confirmation |
| `choice.no` | `C420D4` | `C420BC` | No in the same confirmation table |
| `choice.yes` | `C42110` | `C420E4` | Yes in the mode-confirmation table |
| `choice.no_default` | `C42108` | `C420F0` | No; initially selected for mode confirmation |
| `mode.story` | `C4CDC8` | `C4CDD8` | Story mode |
| `mode.extra` | `C4CDB4` | `C4CDE4` | Extra mode |
| `mode.locked` | `C4CE20` | `C4CDF0` | ???; retain the unavailable mode's hidden label |
| `mode.help` | `C4CD90` | `C4CDFC` | Help |
| `mode.cancel` | `C4CD88` | `C4CE08` | Cancel |

The original six entries remain in the catalog. Some added strings also have
other pointer owners. This batch changes only the owners above: for example,
the separate mode table containing the revealed challenge-mode name remains
outside the verified fresh-save route. The initialization message's other
owner at `CE2304` is likewise unchanged. Identical-looking Japanese text can
therefore still appear elsewhere.

## Default choices and copied menu text

These Yes/No tables use a leading ASCII `*` to mark the initial selection. It
is consumed before drawing and must not be counted as a visible glyph. The
catalog exposes it as **`{default}`**, for example `{default}Yes`. The builder
preserves the ordered token sequence, requires this marker at the beginning
of a menu label, and rejects adding a raw leading `*` through English text.
The Japanese byte tokens retain the original marker for lossless rebuilding.

Native creation routes verify the behavior: name confirmation initially selects
Yes, while mode confirmation initially selects No. The same controller sequence
creates identical save data in the Japanese and English builds for each slot.

The generic menu routine reads the table pointers at `0807B2CA`/`0807B2E6`
while measuring labels, and at `0807B360`/`0807B3AA` when preparing draws. It
copies labels into a RAM buffer with a `03 05 xx` drawing-attribute prefix.
The trace identifies the complete wrapped payload and associates it with the
most recent observed source/pointer read. This distinguishes the two identical
English Yes labels and the two No labels. Prefix-only text matches or matches
without a source read are not accepted as evidence.

Message glyphs are now associated with their specific formatter invocation,
including when several messages appear in one input phase. This allows the
initialization and completion messages, and loading and loaded notices, to be
checked separately.

## Layout observations

All translated glyphs on these routes naturally select font 0 with zero extra
spacing. No debugger memory overrides or font changes are used.

| Context | Observed English layout |
|---|---|
| Title / slot labels | 80 px windows; labels start at x=4 |
| Empty-slot status | 208 px window; x=0, one line |
| Settings | 152 px window; rows at y=0/13/26; options at x=64/96/128 |
| Mode choices | Menu contracts from 80 to 64 px; labels start at x=4 |
| Name-confirmation choices | 40 px window |
| Mode-confirmation choices | Menu contracts from 48 to 32 px |
| Save/mode/load messages | 208 px window; line positions y=2/14/26 |

The menu profiles cap the allowed window at its original width and also check
actual native width against the translated cursor end and visible ink. Automatic
contraction is expected. Screenshot comparisons permit changes within the
original menu-panel bounds, including borders that move as a panel contracts;
other regions must match. Allowed rectangles are recorded with each screenshot.

Settings retain a four-pixel minimum gap before each next fixed column. The
display choices translate 明るい / 強調 / 普通 as Light / Bold / Norm; the route
visits all three and restores Normal. Text-speed options are exercised too.
The Reset settings label is verified, but activating reset is not part of this
route. Delete log is verified on the saved title menu; the deletion flow is not
included in this batch.

## Acceptance results

- **52 unit tests pass**, including default-marker preservation, complete
  wrapped-payload matching, duplicate-label attribution, and coverage checks.
- **39 paired screenshots pass** across six routes: settings, slot-1 creation,
  slot-1 loading, the empty slot-2 prompt, slot-2 creation, and slot-2 loading.
- All **27 translated entries** have verified source/pointer reads, font-0
  glyph sequences, positions, and reader-specific bounds.
- Every supported `{slot}` substitution is checked with **both `１` and `２`**
  in native rendering and formatter output. The verifier fails if a translated
  entry or a required substitution variant lacks coverage.
- Both slots produce identical Japanese/English **65,536-byte** cartridge saves,
  persist them to disk, and cold-load into the opening story. On these fixtures,
  Continue automatically selects the populated slot. A separate slot-1 English
  save cross-load in the original ROM reaches the pinned Japanese story fixture.
- The English first story page is reconstructed from original font pixels;
  the unchanged second page matches the Japanese run. Screenshots were visually
  reviewed, including the three display palettes.
- A partial catalog with the story entry set to `null` also passes native
  verification: 26 translated entries and unchanged Japanese narration.

The normal build uses **741 payload bytes plus 44 alignment bytes = 785 bytes**
of the appended region, leaving **16,776,431 bytes**. Within the original
16 MiB, only 27 declared pointer words change. Original text/font data and both
supplied ROM files remain intact. This is measured usage for the current batch,
not a forecast of the complete translation.

Current English ROM SHA-256:

```text
0b066b5d0e61e2014ed5d47fb828bff3949a9e371620a675acf9440c77a84561
```

Slot-1 / slot-2 save SHA-256 values:

```text
95c6de6afe5d64e21de61b72c8ab3e1c67ca7649ad5a87d1c8b9db87c47feef0
6559c155858aa1093f6f73baa737bfebd1debfe70172465a23f05e34ae4b62e6
```

## Remaining early-screen work

The name-entry keyboard uses **font 1** in this 27-entry milestone. The subsequent
[seven-character name proof](NAME_ENTRY.md) supplies a Latin keyboard using font 0,
English `$i0` confirmation, bounds, and full `Torneko` save/load support in a
separate ROM.
The saved-slot status summary also remains Japanese. Help pages, other mode
branches, deletion prompts, and the separate unlocked-mode table need their own
verified sources and routes. Menu labels here are not proof that those entire
flows have been translated. Full gameplay and physical hardware remain untested.

The name proof passes both-slot and legacy-save checks. Broad Japanese text
extraction is now the next main milestone.
