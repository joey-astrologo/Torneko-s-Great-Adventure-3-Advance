# Corrections found during normal gameplay

The Recovery pot tutorial now says **“Choose Push to restore HP!”**, matching
the native action menu. Its earlier English draft said “Press”. The original
Japanese names the same 押す action; the remaining instructions and `$w`
pause are preserved. No fan-translation wording is used.

Latest combined ROM:
[torneko3-text-polish-english.gba](../build/completion/text-polish/torneko3-text-polish-english.gba),
SHA256 `09bb26e91250a7a958783f12fed53ca3e687cab1387c93448deea48afc8c1a2b`.

[The build ledger](../build/completion/text-polish/english-build.json) explicitly
supersedes the existing tutorial pointer at `001B4B08`. The earlier English
allocation stays intact. The corrected 93-byte payload is appended at
`01069F88`; the occupied append ends at `01069FE5` (434,149 bytes including
padding). The complete image reconstructs from its ledger. All bytes outside
that pointer and new payload match the preceding combined ROM exactly.
No font, code, graphics, RAM or save fields change.

[Native verification](../build/completion/text-polish/component-checkpoint.json)
replays 20 normal inputs from the accepted floor-two checkpoint on both ROMs.
It covers pot pickup, the tutorial pause and native scroll, the Look list,
the Push action and actual HP restoration. All 46 nonempty draws per variant
pass glyph and layout checks. Only the expected tutorial wording changes in
the eight formatted message rows. Nineteen screen pairs are identical; the
other two differ only within the message viewport. The final gameplay screen
matches the original exploration. No item, HP, coordinate or scenario values
were injected.

The 818-resource retained audit was revalidated against this ROM, including
817 entries within the master inventory. The 31 unowned Japanese source
watchpoints did not fire during the pot route. They remain unresolved outside
this limited gameplay coverage.

This corrects an existing source, so inventory accounting remains **8,422
authored + 817 retained + 79 technically unclassified = 9,318**. The earlier
tutorial catalog records its historical wording; the later
[text-polish catalog](../translations/text-polish.json) is the explicit
insertion override shown by the extraction browser. Native cartridge save
persistence and other dungeon branches remain separate checks.

```sh
.venv/bin/python -m tools.build_text_polish
.venv/bin/python -m tools.verify_text_polish
```
