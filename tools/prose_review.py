"""Pinned bilingual review inventory and independently authored final revisions.

`show` prints original catalog indices. `mark` records an actually read range;
it does not perform a language review. Historical catalogs remain immutable.
"""
import argparse
import json
from pathlib import Path

from tools.build_first_label import ROOT, digest
from tools.translation_pipeline import atomic_write, check, load_json

REVIEW = ROOT / 'translations/prose-review/review.json'
REVISIONS = ROOT / 'translations/prose-review/revisions.json'
EXCLUDE = {'master', 'anchors', 'glossary', 'ally-nicknames', 'inscriptions',
           'item-display-overrides', 'arena-graphics', 'unowned-text-review'}


def save(path, data):
    atomic_write(path, (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode())


def initialize():
    check(not REVIEW.exists(), 'Review already exists')
    catalogs = {}
    for p in sorted((ROOT/'translations').glob('*.json')):
        if p.stem in EXCLUDE:
            continue
        es = load_json(p)['entries']
        check(isinstance(es, list), 'Unexpected catalog shape')
        # Fixed entity names stay with the terminology authority. Descriptions
        # and traits receive the bilingual prose review.
        indices = [i for i,e in enumerate(es) if e.get('family') != 'name'
                   and (p.stem != 'item-contexts' or e['family']=='synthesis')]
        catalogs[p.stem] = {'path':str(p.relative_to(ROOT)),
                           'sha256':digest(p.read_bytes()), 'indices':indices,
                           'reviewed_indices':[]}
    save(REVIEW, {'schema':1, 'status':'in_progress',
        'baseline_rom':'build/title-insertion/torneko3-title-english.gba',
        'baseline_sha256':'b80feb1177c9111f44edb1b0ffc8a63c89d94b7d4eccc9f383bc9b372d7b14a9',
        'glossary_sha256':digest((ROOT/'translations/glossary.json').read_bytes()),
        'rules':['Natural English', 'Exact sourced series terminology',
                 'Japanese meaning and voice, with natural English phrasing'],
        'scope':'Bilingual review of authored prose and adjacent UI wording. '
                'Fixed item/enemy names, nicknames, unidentified names, inscriptions and '
                'graphics remain with their existing authorities. Unowned candidates '
                'remain separate and uninserted. A recorded range means its pairs '
                'were read, not merely pattern-scanned. Runtime acceptance is separate.',
        'catalogs':catalogs})
    save(REVISIONS, {'schema':1, 'entries':[]})


def catalog(name):
    review = load_json(REVIEW); row = review['catalogs'][name]
    p = ROOT/row['path']
    check(digest(p.read_bytes())==row['sha256'], 'Pinned input changed: '+name)
    return review, row, load_json(p)['entries']


def show(name, start, end):
    _, row, _ = catalog(name)
    es = effective_catalog(name)['entries']
    for i in row['indices']:
        if start <= i < end:
            e=es[i]
            print(f'{i} {e["id"]} | '+e['japanese'].replace('\n',' / ').replace('\t',' '))
            print('  '+e['english'].replace('\n',' / '))
            if e.get('display') is not None:
                print('  Display: '+e['display'].replace('\n',' / '))


def effective_catalog(name):
    """Overlay the reviewed English while preserving immutable input catalogs."""
    _, row, _ = catalog(name)
    data = load_json(ROOT/row['path'])
    for r in load_json(REVISIONS)['entries']:
        if r['catalog'] != name: continue
        e = data['entries'][r['index']]
        check(all(e[k] == r[k] for k in ('id','japanese','source_hex')) and
              e['english'] == r['before'], 'Stale prose overlay: '+r['id'])
        e['english'] = r['english']
        if 'display' in r:
            check(e.get('display') == r['before_display'], 'Stale display overlay')
            e['display'] = r['display']
        e['prose_review_reason'] = r['reason']
    data['prose_review'] = {'pinned_catalog_sha256':row['sha256'],
                            'revisions_sha256':digest(REVISIONS.read_bytes()),
                            'authority':'translations/prose-review/revisions.json',
                            'scope':'Generated effective wording; do not edit this export.'}
    return data


def export():
    for name in load_json(REVIEW)['catalogs']:
        save(ROOT/'build/prose-review/effective'/f'{name}.json', effective_catalog(name))
    print('Exported effective catalogs to build/prose-review/effective/')


def mark(name, start, end):
    review, row, _ = catalog(name)
    selected = [i for i in row['indices'] if start<=i<end]
    check(selected, 'Empty review range')
    row['reviewed_indices'] = sorted(set(row['reviewed_indices'])|set(selected))
    save(REVIEW, review)
    print(f'{name}: {len(row["reviewed_indices"])}/{len(row["indices"])} bilingual pairs read')


def revise(name, index, english, reason, *, display=None):
    _, row, es = catalog(name)
    check(index in row['indices'], 'Revision outside review scope')
    e=es[index]
    check(english and english != e['english'] and reason, 'Empty/redundant revision')
    check(e.get('display') is None or display,
          'An existing display override needs an explicitly reviewed replacement')
    changes=load_json(REVISIONS)
    check(not any(x['catalog']==name and x['id']==e['id'] for x in changes['entries']),
          'Revision already exists')
    changes['entries'].append({'catalog':name, 'index':index, 'id':e['id'],
        'source_hex':e['source_hex'], 'japanese':e['japanese'],
        'before':e['english'], 'english':english, 'reason':reason})
    if e.get('display') is not None:
        changes['entries'][-1].update(before_display=e['display'], display=display)
    save(REVISIONS, changes)


def status():
    review = load_json(REVIEW)
    total=done=0
    for name,row in review['catalogs'].items():
        n=len(row['indices']);d=len(row['reviewed_indices']);total+=n;done+=d
        print(f'{name}: {d}/{n}')
    print(f'Total bilingual pairs read: {done}/{total}')
    print('Revisions:', len(load_json(REVISIONS)['entries']))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['init','show','mark','status','export'])
    p.add_argument('catalog', nargs='?')
    p.add_argument('start', type=int, nargs='?', default=0)
    p.add_argument('end', type=int, nargs='?', default=100000)
    a=p.parse_args()
    if a.mode=='init': initialize();status()
    elif a.mode=='status':status()
    elif a.mode=='export':export()
    elif a.mode=='show':show(a.catalog,a.start,a.end)
    else:mark(a.catalog,a.start,a.end)
