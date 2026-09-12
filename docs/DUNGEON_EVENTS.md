# Direct dungeon dialogue and tutorials

This component has passed its controlled native checks. Its combined image is
linked in [COMPLETION.md](COMPLETION.md); translation work continues.

The [catalog](../translations/dungeon-events.json) contains 63 independently
translated sources through 82 reviewed pointers: arena pause/abandon prompts,
Hell Justice encounters, four groups of rescued Conklave villagers, companion
warnings/tutorials and the Earth God's concluding message. These messages are
called by dungeon code outside the ordinary story-event operand table.

The [source report](../build/completion/dungeon-events/source-owners.json) and
[memory map](MEMORY_MAP.md) record the exact sources and native readers before
insertion. The 31-key tutorial dictionary retains its internal identifiers;
the arena menu retains its return values and default marker. Two abort prompts
use the original initialized RAM cache. High data-array references remain
unreviewed and excluded.

Existing Hell Justice, Joe, Talos, Rosa, Ines, Earth God, Barinabo and people of
the earth terms are reused. Conklave folk extends the existing project village
name to its inhabitants. **Squelch** matches キアリー using the
[secondary XI naming reference](https://dragon-quest.org/wiki/Squelch), not a
primary-source verification claim. The Japanese [Ines reference](https://wikiwiki.jp/dqdic3rd/%E3%80%90%E3%82%A4%E3%83%8D%E3%82%B9%E3%80%91)
corroborates the people-of-the-earth passage's later reveal; the translation
keeps that collective expression and does not add names early.

The [acceptance report](../build/completion/dungeon-events/component-checkpoint.json)
records 126 English source cases / 185 screens and 116 Japanese pixel pairs.
All 31 native tutorial key lookups, the original arena menu, four boss/two abort
selector cases and cold abort-cache initialization also pass. Both complete
images reconstruct from the shared ledgers, preserving earlier patches and
appended bytes. No layout/code/RAM/save changes were needed; appended usage is
404,842 bytes. Catalog and harness are frozen beside the component reports.

Those controlled fixtures do not execute natural boss battles, rescue travel,
arena forfeit consequences or tutorial activation.

Build with `.venv/bin/python -m tools.build_dungeon_events build`.
Verify `english`, `japanese` and `baseline` with
`.venv/bin/python -m tools.verify_dungeon_events VARIANT`, then run
`.venv/bin/python -m tools.summarize_dungeon_events`.
