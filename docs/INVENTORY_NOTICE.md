# Empty-inventory popup

The native 128px popup now displays **No items.** (45px). Its full independent
translation, “You are not carrying any items.” (157px), remains in the catalog.
The separate, larger paged-message copy retains that full wording.

Accepted cumulative ROM:
[torneko3-inventory-notice-english.gba](../build/completion/inventory-notice/torneko3-inventory-notice-english.gba),
SHA256 `8757bf5cd89e6b935c8f99c431600eb6b5367ad9e9078158a84c047cf6d6e960`.
It includes the [Records menu](UI_POLISH.md), [results animation](RESULT_RUNTIME.md)
and [Recovery pot wording](TEXT_POLISH.md) corrections.

A natural button route and passive reader watchpoints exposed that source
`001B98C2` is used by popup `08020498`; the earlier battle catalog had grouped
it with queue messages. The [new display catalog](../translations/inventory-notice.json)
corrects the reader classification. The [ledger](../build/completion/inventory-notice/english-build.json)
explicitly supersedes the existing pointer at `[00020488,0002048C)` and appends
ten bytes at `[01069FF0,01069FFA)`. Original source bytes and all prior allocations
are preserved. Total appended occupancy is 434,170 bytes, including alignment,
across 8,428 allocations and 10,110 checked original patch records. Exact source,
window and transient buffer ranges were recorded in [MEMORY_MAP.md](MEMORY_MAP.md)
before insertion. No code, font, window, RAM or save field is enlarged.

[Paired native verification](../build/completion/inventory-notice/component-checkpoint.json)
reproduces the original clipping and checks the corrected source and every
rendered glyph. The native printf format appends 36 transparent spaces; this
specific blank fill is checked separately from visible text bounds. Pixel
changes stay within the existing popup. Unrelated whole-string draws retain
their strict layout checks. The [full native save route](NATIVE_SAVE_ROUNDTRIP.md)
also passes on this ROM, with the same final save bytes as the preceding build.

```sh
.venv/bin/python -m tools.build_inventory_notice
.venv/bin/python -m tools.verify_inventory_notice
.venv/bin/python -m tools.verify_roundtrip
```

The builder and verification harnesses are frozen beside their respective
build reports. This display override adds no newly translated inventory source.
