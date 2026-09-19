"""Audit approved combat joins with real native decorated ally names; no ROM writes."""
import json
import re
from pathlib import Path
import mgba.log
from tools import verify_ally_nicknames as nick, verify_rendering_fixes as v
from tools.build_first_label import ROOT, digest, ORIGINAL_ROM
from tools.translation_pipeline import FontZero, check, load_json
from tools.verify_expansion import Session
from tools.prose_review import save

OUT = ROOT/'build/companion-combat-audit'
ROM = ROOT/'build/torneko-3-english.gba'
STYLE = re.compile(rb'\x03\x05[\x01-\x0f]|\x03\x06')


def main():
    mgba.log.silence()
    data = ROM.read_bytes(); font = FontZero(ORIGINAL_ROM.read_bytes())
    messages = load_json(ROOT/'build/damage-lines/allocation-plan.json')['messages'] + load_json(ROOT/'translations/combat-line-joins.json')['messages']
    entries = load_json(nick.CATALOG)['entries']
    slime = next(e for e in entries if e['species_english'] == 'Slime')
    results = []; queue_examples = []
    with Session(data, OUT) as s:
        tables = nick.cold_tables(s)
        nick.restore(s, nick.STATE.read_bytes(), tables)
        generated = nick.generate(s.core, slime['row'], 1)
        decoded = nick.decode(s.core, bytes.fromhex(generated['compact_hex']))
        native_names = nick.format_names(s.core, slime['row'], decoded)
        names = list(dict.fromkeys(bytes.fromhex(f['raw_hex']) for f in native_names))
        for message in messages:
            source = message['address']; template = bytes.fromhex(message['raw_hex'])
            check(data[source-0x08000000:source-0x08000000+len(template)] == template, 'Audit source moved')
            if not any(slot in template for slot in (b'$m0',b'$m1',b'$m2')):continue
            for decorated in names:
                plain = STYLE.sub(b'',decorated)
                pair = {}
                for name, label in ((plain,'plain'),(decorated,'decorated')):
                    check(s.core.load_raw_state(v.old.STATE.read_bytes()), 'Restore formatting state')
                    v.old.slots(s.core,font,'normal');s.core.memory.u32[v.old.NUMBER] = 6
                    for i in range(3):v.old.write_bytes(s.core,v.old.ACTOR+i*30,name.ljust(30,b'\0'))
                    raw, ret = v.formatted(s, source)
                    pair[label] = dict(raw_hex=raw.hex(),return_r0=ret,visible=STYLE.sub(b'',raw).rstrip(b'\0').decode('ascii',errors='backslashreplace'))
                    if message['id'] in ('gameplay.001b4e23','gameplay.001b4dac','gameplay.001b4e7b') and len(decorated)==len(names[-1]):
                        trace = v.FixTrace(s.core)
                        try:
                            v.queue.prepare_queue(s,trace,start=15,history_start=19)
                            queued = v.queue.enqueue(s,trace,source,raw)
                            queue_examples.append(dict(id=message['id'],name_kind=label,name_hex=name.hex(),queue=queued))
                        finally:trace.close()
                missed = pair['decorated']['visible'].count('\n') > pair['plain']['visible'].count('\n')
                results.append(dict(id=message['id'],source=hex(source),template=template.rstrip(b'\0').decode('ascii'),
                    name_hex=decorated.hex(),missed_join=missed,**pair))
        report = dict(rom_sha256=digest(data),harness_sha256=digest(Path(__file__).read_bytes()),
            scope='Controlled native ally-name production, full formatter and selected real queue/history cases; not a natural battle replay',
            generated_name=generated,native_names=native_names,rows=results,queue_examples=queue_examples)
        save(OUT/'report.json',report)
    missed = {r['id'] for r in results if r['missed_join']}
    print(f'{len(results)} comparisons; {len(set(r["id"] for r in results))} actor-bearing source keys; {len(missed)} keys lose joins with native styles.')
    print('Native names:',names)


if __name__ == '__main__':main()
