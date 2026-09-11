# Unidentified names and synthesis descriptions

Current status: The current combined milestone translates all 344 context strings. This page records the earlier ten-draft proof; its hashes, counts and commands describe that historical checkpoint. See [ENEMIES_AND_ITEMS.md](ENEMIES_AND_ITEMS.md) for the current build, commands and validation.

Status, 2026-09-10: the complete unidentified-name and synthesis-description
tables are now in the shared build, alongside the existing menus, seven-character
naming and ordinary item text. This adds **344 distinct strings through 346
pointer fields**. Six unidentified names and four synthesis descriptions have
independent English drafts; the other 334 new entries retain exact Japanese.
The fan patch supplies no text or font assets.

The 2026-09-10 [terminology review](TERMINOLOGY.md) updates the repeated
**Oaken club** and **Dragonsbane** names and adopts **Blade shield** as a
provisional Torneko 2 fallback. Effects remain faithful to the Torneko 3
Japanese. The current hash and ledger below include these corrections and the
ordinary-item spelling changes; their total cost is four additional ROM bytes.

All ranges use `[start,end)`. Source bytes and category fields remain protected;
only the declared pointer words change. This milestone adds no game-code patches,
permanent RAM reservations or save-layout changes.

## Build and edit

```bash
.venv/bin/python -m tools.build_item_contexts --language japanese
.venv/bin/python -m tools.build_item_contexts --language english
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m tools.verify_item_contexts
```

Edit `english` and `notes` in
[translations/item-contexts.json](../translations/item-contexts.json).
An existing catalog is validated without rewriting its drafts or notes. `rows`
are disguise/effect table indices, **not item IDs**. Exact source tokens,
category words, aliases, pointer owners and matching master IDs are retained.
The ordinary item drafts remain in `translations/items.json`.

| Output | Purpose |
|---|---|
| [torneko3-item-contexts-english.gba](../build/item-contexts/torneko3-item-contexts-english.gba) | Current combined 32 MiB ROM; previous English plus ten new entries |
| [torneko3-item-contexts-japanese.gba](../build/item-contexts/torneko3-item-contexts-japanese.gba) | Same previous English components; new context tables relocated in Japanese |
| [english-build.json](../build/item-contexts/english-build.json), [japanese-build.json](../build/item-contexts/japanese-build.json) | Complete shared ledgers and source/output hashes |
| [verification/report.json](../build/item-contexts/verification/report.json) | Native acceptance results and explicit fixture scope |
| [comparison.png](../build/item-contexts/verification/comparison.png) | Ten Japanese/English screen pairs |

The English build occupies **36,826 appended bytes including alignment**,
leaving **16,740,390 bytes** in the 16 MiB expansion arena. Its complete ledger
contains 1,104 allocations and 1,138 original-ROM patches. Across ordinary items
and these contexts, 1,063 distinct strings now use 1,086 table pointers. This
is a measured draft size, not a forecast for a full English translation.

English ROM SHA-256:

```text
c3694b87cd7b3a1d7c59f31b52a482d1d5a86cf232fd1616e3c544e6e3094513
```

## Located tables and readers

- ROM `[00190808,00190FB8)`: 246 eight-byte unidentified-name records. Each
  contains a four-byte item category followed by an absolute string pointer.
  The 246 distinct strings occupy the envelope `[00190FB8,00191C14)`.
  Categories observed: 3 (staff), 7 (ring), 8 (scroll), 9 (pot), 10 (herb),
  11 (bread). The category words are data to preserve, not pointer owners.
- ROM `[001B3A60,001B3BF0)`: 100 synthesis-description pointers, 98 distinct
  sources in envelope `[001B1EF1,001B3497)`. Rows 0, 98 and 99 share `なし<CR>`.
  Other rows have a heading, CR and byte `1D` before the effect description.
  Its six-pixel spacing behavior is verified below.
- Item-name formatter `08080A5C` selects unidentified pointers through the
  literals at ROM `[000810BC,000810C4)` and `[000812B4,000812BC)`: table base
  `08190808`, item-to-disguise-row mapping `0200C722`. Copies still use 100-byte
  buffers. Identification helper `0807E9BC` reads the word at RAM
  `[0200C71C,0200C720)` and the halfword mapping at
  `[0200C722,0200CA06)` (370 entries); `0FFF` is its identified sentinel.
  These are live game globals, not new reservations.
  Native loads are `0808109A` for pots and `0808113E` for the other tested
  categories. Both are exercised across their complete table rows.
- Predicate `0800033C` tests whether mode word `[02000000,02000004)` is 1
  (literal `[00000350,00000354)`). Custom-name helper `0807F9A0` uses the
  signed index table starting ROM `00C4C4FC` to select an eight-byte slot from
  RAM `0200CA06`; an empty first byte allows the unidentified table path.
  The custom-name arena's full extent is not yet established.
  The 370-entry mapping spans ROM `[00C4C4FC,00C4C7E0)` and selects slots
  0..212, reaching RAM `[0200CA06,0200D0AE)`; this is an occupied reachable
  envelope, not proof of the allocation's full extent. The controlled village
  state has `FF` in these slots, so unidentified fixtures explicitly clear the
  selected eight-byte slot before letting the normal reader use it.
  Additional inspected literals are ROM `[0007E9F8,0007E9FC)` (identification
  word), `[0007EA28,0007EA30)` (mapping base and `0FFF` sentinel), and
  `[0007F9BC,0007F9C4)` (custom-name index table and slot base). All remain
  occupied source data. The exported instruction evidence is
  [context-readers.txt](../build/item-contexts/research/context-readers.txt),
  supplemented by the earlier item reader/helper listings; provisional
  pseudocode is not treated as a complete function specification.
- Information renderer `0806DCDC` branches to synthesis details for item types
  0, 2 or 7 when flag bit 27 is set. It takes the selected effect from record
  byte `+4+index`, masks it with `7F`, and indexes the table selected by literal
  ROM `[0006E024,0006E028)`. Effect count is byte at record `+12`; exact full
  record semantics and maximum supported count are not yet established.
  The description is wrapped using the format string selected by literal
  `[0006E028,0006E02C)` and drawn at `(0,48)`; stats remain at y=100.
  Native source load is `0806DFD8`; the observed wrapped-text buffer is at
  `030079A8` in this call. Draw routine `0808CBA0` handles `1D` at
  `0808CBD0..0808CBD8` by resetting x and advancing y by six pixels. Combined
  with the preceding CR, the effect body starts 19 pixels below its heading.
  The same destination is passed to `0806E1C0`, which clears 1024 bytes and
  terminates at index `3FF`, establishing `[030079A8,03007DA8)` for the observed
  call. The synthesis `sprintf` wrapper itself is unbounded; insertion must
  check the source plus its three style bytes and NUL against that capacity.

## Insertion profile

The new catalog/build is `translations/item-contexts.json` and
`tools.build_item_contexts`. It preserves category fields and all source bytes,
owns only the 346 pointer words, and appends 344 distinct sources (246 names,
98 synthesis strings) through the existing shared ledger. English starts with
six unidentified names, one per category, and four synthesis descriptions.
Untranslated entries retain exact Japanese bytes and controls.

Unidentified names use the existing 32-byte/100-pixel raw name reserve. Synthesis
English uses a heading on its first line and one or two effect lines below.
The builder automatically preserves the original `CR 1D` heading separator,
putting native lines at y=48,67,80; each must fit 192 pixels and end before the
statistics footer at y=100. The three shared placeholder rows have no `1D`
and retain their separate one-line profile.

## Verification and fixture scope

All **87 unit tests** pass. They include complete Japanese byte reconstruction,
all pointer owners/aliases, preserved category fields, draft retention, shared
collision rejection, deterministic allocation and the CR/1D/width/footer limits.

Native mGBA 0.10.5 verification compares the previous ordinary-item build, new
Japanese context relocation, and new English context build. Each independently
replays the opening route from a freshly created temporary Japanese save.

- **107 normal-rendering screenshots per ROM**: six unidentified-name inventory
  examples, all 100 synthesis rows, and a high-bit effect-code case that verifies
  the reader's `7F` mask. All 107 baseline/Japanese pairs are pixel-identical.
- **258 guarded native item-name calls per ROM**: all 246 unidentified rows,
  plus identified and custom-name cases in each of the six categories. Every
  table word is read by the expected instruction; 100-byte output guards stay
  intact. Japanese relocation preserves every formatted result, and the
  identified/custom paths remain unchanged in English.
  The longest formatted result among these cases is 27 bytes including NUL.
- **101 native synthesis wrappers per ROM** read the expected table targets,
  retain exact source bytes behind the style prefix, and preserve the neighbors
  of their 1024-byte stack destination. Every synthesis pointer word is covered,
  including aliases/placeholders. All ten new English entries have native glyph,
  font-0 and placement checks; body lines retain the six-pixel heading gap and
  fit above the statistics footer.
  The largest observed wrapped result is 88 bytes including NUL.
- The eight earlier English items pass their inventory/information checks on
  this combined ROM. A new `Torneko` save persists as 65,536 bytes and cold-loads
  through the opening story.

Normal English differences are confined to the corresponding item UI. In the
Passage ring synthesis case, the background sprite beneath the translucent
window also differs within `(67,37)..(89,59)`. The native text header and footer
are unchanged. A separate one-frame diagnostic with mGBA's OBJ rendering disabled
produces identical background/text-layer pixels outside the translated area.
The verifier records this exception and retains both normal and diagnostic
images; it does not claim every normal English difference is a text pixel.

Reuse the previous milestone's controlled inventory route and restore its
state after each case. All test changes to inventory records, identification
globals or scratch memory are disposable emulator state. They do not alter the
ROM's game rules, add permanent RAM allocations, modify the user's saves or
prove normal dungeon acquisition/identification/synthesis behavior.
Unidentified fixtures open the world menu first, then set the documented mode,
identification mapping and empty custom-name slot before ordinary controller
input opens the inventory. Synthesis fixtures install the effect code/count
before opening the inventory, actions and information panel. The playable ROM
does not force these test states. The game still chooses disguise names through
its own mapping during actual play.

The reader/table milestone is complete. Natural dungeon identification,
multi-effect navigation, the synthesis operation itself, shops and gameplay
save persistence of these item states remain separate verification work.
Ranking/result-name storage remains deferred.
