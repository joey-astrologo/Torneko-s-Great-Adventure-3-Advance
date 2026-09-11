# First village and northern shrine

Completed 2026-09-11. This pass adds **281 translated messages** covering the
village departure arc: the chief's meetings, Tipper's continued sleep, the
northern shrine explanation, both Ines/Rosa choices, map and food preparations,
village residents and dungeon advice. Related Torneko return conversations and
companion-switch responses are included. Later Tipper, celebration and ending
arcs remain separate.

Playable combined ROM:
[torneko3-first-village-english.gba](../build/first-village/torneko3-first-village-english.gba)

SHA-256: `0deb82fc65a1c776bb08e81d313990bc79a3833c0b2d2171968ffbcb7dc986ae`

The [catalog](../translations/first-village.json) is the insertion authority.
All prose is independently translated from the Japanese original. No English
or fonts come from the partial fan translation. All earlier catalogs, appended
payloads, patches and RAM/save reservations are preserved.

## Terminology and language

Torneko, Tipper, Tessie, Gamlan, Rosa and Ines retain their existing identities.
Bread and Teleportal reuse the established series glossary. Anonymous speakers
remain `???` until the source identifies them. Children retain a light, playful
voice; the short sailor chant is independently adapted from this game's text.

The glossary adds six explicitly **project** identities, bringing it to
**1,294 terms**:

| Japanese | English | Evidence and scope |
|---|---|---|
| バリナボ | Barinabo | Project transliteration. The [publisher's Japanese synopsis](https://www.spike-chunsoft.co.jp/pages/games/torneco3/story02.html) confirms the island and Ines's role in the journey; it supplies no official English name. |
| 神々のほこら | Shrine of the Gods | Project place translation; the dialogue also calls it the northern shrine. |
| 大地の神 | Earth God | Project lore translation, without identifying this deity as a character from another DQ game. |
| 神の道 | divine path | Project description of the route beneath the sea. Kept distinct from the existing dungeon name 神々の道 / Path of the gods. |
| 真実のトビラ | Gate of Truth | Project lore/place wording from the shrine and return conversations. |
| ヴィオラ | Viola | Project transliteration of Gamlan's daughter, mentioned in a related return conversation. |

The GBA source determines the dialogue and mechanics. The older Japanese PS2
synopsis corroborates identity only. The
[281-entry terminology review](../translations/first-village-terminology-review.tsv)
records full English, source text, identity references and notes. Earlier
glossary names, evidence quality, sources and notes remain intact.

## Layout and insertion ownership

Every message fits its original three-line page using font 0 in the native
208 × 40 pixel story window. Continuation tabs remain. The shared ancient-writing
observation retains `$t` and is checked with both Torneko and Tipper. No font,
story buffer, code or save-field expansion is needed.

| Combined build resource | Result |
|---|---:|
| ROM size | 32 MiB |
| Appended bytes used, including alignment | 203,846 |
| Added by this milestone | 20,531 |
| Remaining appended capacity | 16,573,370 |
| New distinct source allocations | 281 |
| Checked original-ROM pointer patches | 367 |

Shared strings have multiple event owners. The
[source ownership report](../build/first-village/source-owners.json) records each
exact source range and every command/operand word. All 367 owners reference
their appropriate shared allocation. Command headers, choice parameters,
following script bytes and original source text remain unchanged.

The [memory map](MEMORY_MAP.md#first-village-departure-arc-2026-09-11) records
these discoveries before insertion. The
[English ledger](../build/first-village/english-build.json) owns the combined
append span `[01000000,01031C46)`, including new data/alignment
`[0102CC13,01031C46)`. Japanese relocation is a separate control image with its
own ledger. Source-selection envelopes do not authorize reuse of their gaps.

## Automated verification

The [acceptance report](../build/first-village/acceptance.json) pins ROMs,
catalogs, tools, ownership and terminology. **186 unit tests pass.** Checks include:

- **368 English display cases:** all 367 actual event operands, with the shared
  protagonist observation tested a second time for Tipper. Native dispatch,
  wrappers, guarded 1,024-byte formatting, glyphs, line positions and window
  bounds pass. This includes all three opcode-26 messenger interruption lines
  and the opcode-2A bed prompt.
- **368 Japanese pixel pairs:** relocated Japanese text matches the previous
  combined build through native output and screenshots.
- **A fresh natural route:** ordinary buttons load a disposable Japanese
  Adventure Log, replay the opening, leave the house, follow the village escort
  and finish the first chief meeting. All **46 messages**—36 opening and ten new
  village messages—have complete glyph and source-provenance checks. All
  **3,838 native story reads** are attributed, with none unexplained. No state,
  coordinate, event-cursor, RAM or register injections are used in this replay.
- **Both Adventure Logs:** normal entry of `Torneko`, native FLASH saves, then
  cold loads of both slots from the final save preserve all seven characters
  into the opening. Saving slot two retains the first slot's name. Save size
  remains 65,536 bytes.
- **Preservation:** a deterministic rebuild checks all earlier allocations,
  payloads, patches and reservations; master source bytes, English drafts and
  notes remain unchanged, and the Japanese source round trip matches its hash.

The other 271 catalog sources have controlled display coverage. Their natural
triggers, shrine/companion-choice outcomes, repeat-advice loops, successful map
and food grants, rest transitions and later return conditions are not claimed
as naturally tested. The normal first chief meeting is a bounded route, not a
complete village playthrough. These gaps are in the
[playtest backlog](PLAYTEST_BACKLOG.md); personal playtesting can wait.

See the [native chief conversation](../build/first-village/verification/natural/chief-final.png)
and [complete route trace](../build/first-village/verification/natural/trace.json).
Exploration snapshots under `build/first-village/exploration/` are disposable
research artifacts; acceptance uses the fresh-core route above.

## Reproduce and continue

```sh
.venv/bin/python -m tools.build_first_village
.venv/bin/python -m tools.verify_first_village_all
# Recheck complete existing artifacts without rerunning emulator routes:
.venv/bin/python -m tools.verify_first_village_all --summarize-only
```

The draft TSV is the one-time preparation input. The preparation helper refuses
to overwrite an existing authored catalog. Edit `translations/first-village.json`
for subsequent revisions and keep the glossary/review snapshot consistent.

Progress is **4,634 of 9,318 known source entries translated/inserted (49.73%)**,
with **4,684 remaining**. The searchable master includes the village overlay.
This does not establish complete-game discovery. Global place labels and later
village story arcs are separate families; translating a place name in dialogue
does not by itself translate its map/menu label.

The next section is the early dungeon journey and its rest-stop conversations,
with place-label ownership reviewed alongside that work.
