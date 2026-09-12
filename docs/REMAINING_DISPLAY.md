# Sound-test help and live-floor summaries

Four sound-test help lines now use English. The existing help reader selects
BGM, ME, SE or Return from its startup cache, decodes each character and draws
it with font 0 in the original 208×40 panel. Audio IDs and playback code are
unchanged. The native help state and adjacent fields pass all four selections.

The live-dungeon Adventure Log title now uses `%s %dF`, adding a separator and
Latin F to the accepted dungeon name. Native formatting and the real log
renderer pass all 64 dungeon names at both floor-byte boundaries, 0 and 255.
Both log slots use seven-letter names, with unchanged 64-byte title fields,
92-byte display records, font tables and buffer guards. Boundary values are
controlled coverage, not a claim that every dungeon reaches floor 255.

[Catalog](../translations/remaining-display.json),
[original owners](../build/completion/remaining-display/source-owners.json),
[build ledger](../build/completion/remaining-display/english-build.json), and
[132-case checkpoint](../build/completion/remaining-display/component-checkpoint.json).
All 132 Japanese relocation screenshots match the preceding build. Previous
patches and appended assets are preserved, and both complete ROM images
reconstruct from their allocation/patch ledgers.

The fixtures retain the early-world background. These checks do not establish
natural debug-menu access, audio playback, dungeon progression or new save
persistence. Those remain separate from the verified selectors and renderers.

```sh
.venv/bin/python -m tools.build_remaining_display build
.venv/bin/python -m tools.verify_remaining_display baseline
.venv/bin/python -m tools.verify_remaining_display japanese
.venv/bin/python -m tools.verify_remaining_display english
.venv/bin/python -m tools.summarize_remaining_display
```

Latest combined ROM: [torneko3-remaining-display-english.gba](../build/completion/remaining-display/torneko3-remaining-display-english.gba).
SHA256 `f0c51f1b3a4229964d23a2f0416bb854dafe1196799ce4ccea2302b211e7fb97`.
