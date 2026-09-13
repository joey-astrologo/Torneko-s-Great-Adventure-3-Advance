"""Append reviewed prose without rewriting pinned historical component inputs."""
import argparse
from functools import lru_cache
from importlib import import_module
from pathlib import Path
import struct

from tools import build_title_art as previous
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.prose_review import REVIEW, REVISIONS, save
from tools.translation_pipeline import check, load_json, FontZero, atomic_write
from tools.rom_build import AppendAllocator, RomBuild

OWNER = 'prose-review'
OUTPUT = ROOT/'build/prose-review'
ROM = OUTPUT/'torneko3-prose-english.gba'
PLAN = OUTPUT/'allocation-plan.json'
BASELINE = previous.ROM


@lru_cache(None)
def module(name):
    if name == 'shared-story': name = 'story-completion'
    return import_module('tools.build_'+name.replace('-', '_'))


def encode(name, entry, original, font=None):
    m = module(name)
    if name in ('items', 'item-contexts', 'enemies', 'dungeon-interface'):
        return m.encode_english(entry, font or FontZero(original))
    if name in ('core-gameplay', 'gameplay-help'):
        from tools.build_ally_dialogue import history_wrap
        return m.encode(entry, original, message_wrap=history_wrap)
    return m.encode(entry, original)


def revisions(original):
    review = load_json(REVIEW)
    check(all(r['indices'] == r['reviewed_indices'] for r in review['catalogs'].values()),
          'Bilingual review is incomplete')
    check(digest((ROOT/'translations/glossary.json').read_bytes()) ==
          review.get('current_glossary_sha256', review['glossary_sha256']), 'Glossary changed')
    catalogs = {}
    for name, row in review['catalogs'].items():
        p = ROOT/row['path']
        check(digest(p.read_bytes()) == row['sha256'], 'Pinned catalog changed: '+name)
        catalogs[name] = load_json(p)['entries']
    seen = set()
    for r in load_json(REVISIONS)['entries']:
        name = r['catalog']; e = catalogs[name][r['index']]
        check((name, e['id']) not in seen, 'Duplicate prose revision')
        seen.add((name, e['id']))
        check(all(r[k] == e[k] for k in ('id', 'source_hex', 'japanese')) and
              r['before'] == e['english'], 'Revision source/previous English changed')
        if e.get('display') is not None:
            check(r.get('before_display') == e['display'] and r.get('display'),
                  'Stale display override: '+e['id'])
        revised = e | {'english': r['english']}
        if 'display' in r: revised['display'] = r['display']
        at = int(e['offset'], 0); raw = bytes.fromhex(e['source_hex'])
        check(original[at:at+len(raw)] == raw, 'Japanese source differs')
        yield r, e, revised


def pointer_words(e):
    # Use only recorded typed owners. No scan for coincidentally matching words.
    words = [int(p['offset'], 0) for p in e.get('pointer_owners', [])]
    words += [int(p, 0) for p in e.get('pointer_offsets', [])]
    words += [int(p['pointer_offset'], 0) for p in e.get('events', [])]
    if 'pointer_offset' in e: words.append(int(e['pointer_offset'], 0))
    check(words and len(words) == len(set(words)), 'Missing/duplicate pointer owners: '+e['id'])
    return sorted(words)


def prepare():
    original = ORIGINAL_ROM.read_bytes(); baseline = BASELINE.read_bytes()
    review = load_json(REVIEW); prior = load_json(BASELINE.parent/'english-build.json')['ledger']
    check(digest(baseline) == prior['rom_sha256'] == review['baseline_sha256'], 'Baseline changed')
    by_word = {p['offset']: p for p in prior['patches']}
    by_target = {a['offset']: a for a in prior['allocations']}
    start = len(original)+prior['appended_used_with_padding']
    allocator = AppendAllocator(start); font = FontZero(original)
    rows = []; errors = []; used_words = set()
    for r, e, revised in revisions(original):
        try:
            old, _ = encode(r['catalog'], e, original, font)
            raw, metrics = encode(r['catalog'], revised, original, font)
            ident = OWNER+'.'+e['id']; owners = []
            for word in pointer_words(e):
                check(word not in used_words, 'Two revisions own one pointer')
                p = by_word[word]
                check(len(bytes.fromhex(p['after'])) == 4, 'Not an exact pointer patch')
                check(int.from_bytes(bytes.fromhex(p['before']), 'little') == 0x08000000+int(e['offset'], 0),
                      'Pointer does not own this Japanese source')
                target = int.from_bytes(bytes.fromhex(p['after']), 'little')-0x08000000
                allocation = by_target[target]
                check(baseline[word:word+4] == bytes.fromhex(p['after']), 'Stale pointer patch')
                check(baseline[target:target+allocation['bytes']] == old,
                      f'Effective baseline differs from catalog {e["id"]}: {allocation["id"]}')
                owners.append(p); used_words.add(word)
            # Some full editorial revisions already match the accepted compact display.
            changed = raw != old
            dest = allocator.allocate(ident, raw, 4) if changed else None
            if changed: allocator.allocations[-1]['owner'] = OWNER
            rows.append({'catalog':r['catalog'], 'index':r['index'], 'id':e['id'],
                'source_start':int(e['offset'],0), 'source_hex':e['source_hex'],
                'raw_hex':raw.hex(), 'old_raw_hex':old.hex(), 'metrics':metrics,
                'changed_rom_text':changed, 'allocation_id':ident, 'offset':dest,
                'previous_pointer_patches':owners})
        except (ValueError, KeyError, AttributeError) as error:
            errors.append({'catalog':r['catalog'], 'id':e['id'], 'error':str(error)})
    save(OUTPUT/'encoding-errors.json', errors)
    check(not errors, f'{len(errors)} prose encoding/ownership errors; see encoding-errors.json')
    plan = {'schema':1,'source_rom':str(ORIGINAL_ROM.relative_to(ROOT)), 'source_sha256':digest(original),
        'previous_rom':str(BASELINE.relative_to(ROOT)), 'previous_sha256':digest(baseline),
        'output_rom':str(ROM.relative_to(ROOT)), 'output_sha256':None,
        'builder_sha256':digest(Path(__file__).read_bytes()), 'review_sha256':digest(REVIEW.read_bytes()),
        'revisions_sha256':digest(REVISIONS.read_bytes()), 'start':start,'end_exclusive':allocator.cursor,
        'new_bytes_with_padding':allocator.cursor-start,'allocations':allocator.allocations,'entries':rows,
        'pointer_supersessions':sum(len(r['previous_pointer_patches']) for r in rows if r['changed_rom_text']),
        'new_ram_reservations':[], 'save_changes':[], 'code_patches':[],
        'scope':'Dry append allocation and exact existing pointer supersessions; no source byte reuse.'}
    save(PLAN, plan)
    print(f'Prepared {len(rows)} revisions, {len(allocator.allocations)} new payloads, '
          f'{plan["pointer_supersessions"]} pointer supersessions; [{start:08X},{allocator.cursor:08X}).', flush=True)


def build_rom(original, *, build=None):
    plan = load_json(PLAN)
    check(plan['source_sha256'] == digest(original), 'Wrong Japanese base')
    for path, key in [(Path(__file__),'builder_sha256'),(REVIEW,'review_sha256'),(REVISIONS,'revisions_sha256')]:
        check(digest(path.read_bytes()) == plan[key], 'Regenerate changed prose plan: '+str(path))
    # Revalidate pinned catalogs and revised encodings, not just the generated plan.
    effective = {(r['catalog'],e['id']): revised for r,e,revised in revisions(original)}
    marker = f'`[{plan["start"]:08X},{plan["end_exclusive"]:08X})`'
    check(marker in (ROOT/'docs/MEMORY_MAP.md').read_text(), 'Document prose ranges before insertion')
    b = RomBuild(original) if build is None else build
    baseline, prior = previous.build_rom(original, build=b)
    check(baseline == BASELINE.read_bytes() and digest(baseline) == plan['previous_sha256'], 'Earlier build changed')
    check(b.allocator.cursor == plan['start'], 'Prose allocator start changed')
    font = FontZero(original); supersessions = []
    for row in plan['entries']:
        raw, metrics = encode(row['catalog'], effective[(row['catalog'],row['id'])], original, font)
        check(raw.hex() == row['raw_hex'] and metrics == row['metrics'], 'Prepared prose encoding differs')
        if not row['changed_rom_text']: continue
        source = bytes.fromhex(row['source_hex']); at = row['source_start']
        b.protect_source(row['allocation_id'], at, at+len(source), OWNER)
        dest = b.allocate(row['allocation_id'], raw, OWNER, alignment=4)
        check(dest == row['offset'], 'Prose allocation differs')
        for old in row['previous_pointer_patches']:
            check(next(p for p in b.patches if p['offset']==old['offset']) == old, 'Previous ownership changed')
            supersessions.append(b.supersede_patch(row['allocation_id']+f'.{old["offset"]:08x}',
                old['id'], old['owner'], bytes.fromhex(old['after']), struct.pack('<I',dest+0x08000000),
                OWNER, 'Independently reviewed prose; preserve original source, reader and substitutions'))
    data, ledger = b.finish()
    check(ledger['allocations'][-len(plan['allocations']):] == plan['allocations'], 'Prose allocation ledger differs')
    check(ledger['allocations'][:-len(plan['allocations'])] == prior['ledger']['allocations'], 'Earlier allocations changed')
    check(ledger['memory_reservations'] == prior['ledger']['memory_reservations'], 'Unexpected RAM change')
    return data, {'source_rom':plan['source_rom'],'source_sha256':digest(original),
        'output_rom':str(ROM.relative_to(ROOT)), 'rom_sha256':digest(data),
        'previous_rom_sha256':digest(baseline),'allocation_plan_sha256':digest(PLAN.read_bytes()),
        'review_sha256':plan['review_sha256'],'revisions_sha256':plan['revisions_sha256'],
        'prose_review':{'revisions':len(plan['entries']),'inserted_payloads':len(plan['allocations']),
            'pointer_supersessions':len(supersessions),'bytes_with_padding':plan['new_bytes_with_padding']},
        'ledger':ledger}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--prepare',action='store_true')
    if p.parse_args().prepare: prepare()
    else:
        data, report = build_rom(ORIGINAL_ROM.read_bytes())
        atomic_write(ROM,data);save(OUTPUT/'english-build.json',report)
        print('Built',report['rom_sha256'],flush=True)
