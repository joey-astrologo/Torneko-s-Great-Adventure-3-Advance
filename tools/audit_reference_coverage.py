"""Find surviving Japanese references, including suffixes; candidates are not reader proof."""
import argparse
from collections import Counter
from pathlib import Path
from tools.audit_text_coverage import all_pointer_words, SourceIndex, translated_ids
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest, load_manifest
from tools.build_reference_coverage import REFERENCES
from tools.game_text import GameTextCodec, DecodeError
from tools.translation_pipeline import load_json, check
from tools.prose_review import save


def japanese(text):
    return any(0x3040<=ord(c)<=0x30ff or 0x3400<=ord(c)<=0x9fff or 0xff66<=ord(c)<=0xff9d for c in text)


def audit(rom, output):
    rom=Path(rom);output=Path(output);original=ORIGINAL_ROM.read_bytes();data=rom.read_bytes()
    check(digest(original)==load_manifest()['base_sha256'], 'Wrong Japanese original')
    check(len(data)>=len(original), 'Output ROM too small')
    master_path=ROOT/'translations/master.json';master=load_json(master_path)['entries']
    done,_=translated_ids(master)
    retained_path=ROOT/'build/completion/retained-resources.json'
    retained={e['master_id']:e for e in load_json(retained_path)['entries'] if e.get('master_id')}
    by_id={e['id']:e for e in master};index=SourceIndex(master);codec=GameTextCodec(original)
    refs,counts=all_pointer_words(original);rows=[];decode_failures=[]
    confirmed={w for w,_,_,_ in REFERENCES}
    for target,words in sorted(refs.items()):
        location=index.locate(target)
        if location['kind']=='uncovered':continue
        e=by_id[location['master_id']]
        if not japanese(e['japanese']):continue
        unchanged=[w for w in words if data[int(w['word'],0):int(w['word'],0)+4]==original[int(w['word'],0):int(w['word'],0)+4]]
        if not unchanged:continue
        try:current=codec.parse(data,target)['display']
        except DecodeError as error:
            decode_failures.append(dict(target=hex(target),location=location,words=unchanged,reason=error.reason));continue
        if not japanese(current):continue
        status='authored' if e['id'] in done else 'retained' if e['id'] in retained else 'unclassified'
        classified=[]
        for w in unchanged:
            at=int(w['word'],0)
            if at in confirmed:disposition='confirmed_missing_reference'
            elif location['kind']=='source_start' and 0xDFCC0<=at<0xDFF18:disposition='preserved_blank_scroll_matching_alias'
            elif location['kind']=='source_start' and 0xCB0620<=at<0xCB0630:disposition='superseded_keyboard_table'
            elif 0xCE0000<=at<0xCF0000:disposition='unverified_high_data_array'
            else:disposition='unverified_reference_candidate'
            classified.append(dict(**w,disposition=disposition))
        rows.append(dict(target=hex(target),**location,status=status,japanese=e['japanese'],current=current,
                         retained_record=retained.get(e['id']),words=classified))
    report=dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(original),
        output_rom=str(rom),rom_sha256=digest(data),master_sha256=digest(master_path.read_bytes()),
        retained_report_sha256=digest(retained_path.read_bytes()),harness_sha256=digest(Path(__file__).read_bytes()),
        pointer_scan_counts=counts,inventory_entries=len(master),authored_distinct_entries=len(done),
        surviving_targets=len(rows),surviving_source_ids=len({r['master_id'] for r in rows}),
        words_by_disposition=dict(Counter(w['disposition'] for r in rows for w in r['words'])),
        exact_start_sources_by_status=dict(Counter(r['status'] for r in rows if r['kind']=='source_start')),
        rows=rows,decode_failures=decode_failures,
        limits=[
            'Authored English does not prove all runtime references were redirected.',
            'All original-ROM byte alignments and GBA ROM mirrors checked against unchanged pointer words.',
            'Targets include inventoried source starts and interior token/character positions; numeric coincidences are retained as unverified.',
            'Intentional Japanese input aliases and superseded keyboard data are not untranslated displays.',
            'Retained-resource status is not a blanket runtime waiver; consult its individual record.',
            'No new discovery outside the existing inventory here: use audit_text_coverage for separate discovery leads.',
            'Computed/relative pointers, compressed text, graphics, alternate decoders and unexplored state-dependent readers need separate evidence.',
            'No claim of 100% whole-game translation or reachability.'
        ])
    save(output/'report.json',report)
    print({k:report[k] for k in ('surviving_targets','surviving_source_ids','words_by_disposition','exact_start_sources_by_status')},flush=True)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom',type=Path,default=ROOT/'build/torneko-3-english.gba')
    parser.add_argument('--output',type=Path,default=ROOT/'build/reference-coverage-audit/current')
    args=parser.parse_args();audit(args.rom,args.output)
