# Church and save-service dialogue

The [church component](../build/completion/church/component-checkpoint.json)
has passed its controlled native checks: 62 independently translated sources
through 70 original pointer words, 124 English cases spanning 162 pages, and
86 Japanese relocation pixel comparisons. All 105 positional table words are
checked, including the 35 unchanged internal identifiers. Fourteen original
greeting/save/oracle source-selection paths pass for each ROM variant.

The five service types cover three priest voices, the unattended Adventure Log
and a voice from nowhere. Their wording remains distinct. Existing Adventure Log
and project Earth God terminology is reused; generic references to God are not
assigned another Dragon Quest deity's identity. Full drafts and preserved
substitutions are in [the catalog](../translations/church-services.json).

The normal and stress fixtures check the existing formatter buffer and every
three-line page, including long names, signed numeric bounds, EXP information,
centered shutdown notices and page continuations. Priest choice menus remain
owned by the earlier arena component. These checks do not execute natural
church transactions, accept save prompts or establish every oracle condition.

All new prose uses the shared appended allocator. Original source bytes,
previous patches and earlier appended bytes are unchanged, and both ROM images
reconstruct exactly from their ledgers. Exact ranges and native-reader evidence
are linked in [the memory map](MEMORY_MAP.md).

Combined ROM: [torneko3-church-services-english.gba](../build/completion/church/torneko3-church-services-english.gba),
SHA256 `0ecfdac89e15a543194587cf10e18fc3ebde2f0d30cec23b92f66fe72cee124c`.

Rebuild with `.venv/bin/python -m tools.build_church_services build`.
Run `tools.verify_church_services` with `english`, `japanese` and `baseline`,
then `summarize`, using the same Python module invocation.
