"""Audit discovery gaps without promoting candidates or authorizing ROM writes."""
import argparse
from bisect import bisect_right
from collections import Counter,defaultdict
import csv
import io
import json
from pathlib import Path
import struct

from tools.build_first_label import ORIGINAL_ROM,ROOT,digest,load_manifest
from tools.extract_master_text import MASTER,TEXT_BANKS,hx,strong_text
from tools.game_text import DecodeError,GameTextCodec,rebuild,token_boundaries
from tools.translation_pipeline import atomic_write,check,load_json

OUTPUT=ROOT/'build/text-coverage'


def cartridge_offset(address,size):
    # mGBA 0.10.5 src/gba/memory.c: cartridge windows mask SIZE_CART0-1.
    # Reject addresses outside the physical input; do not wrap by file size.
    if not 0x08000000<=address<0x0E000000:return None
    offset=address&0x01FFFFFF
    return offset if offset<size else None


class SourceIndex:
    def __init__(self,entries):
        self.entries=sorted(entries,key=lambda e:int(e['offset'],0))
        self.starts=[int(e['offset'],0) for e in self.entries]
        self.ends=[at+len(bytes.fromhex(e['source_hex'])) for at,e in zip(self.starts,self.entries)]
        check(all(self.ends[i]<=self.starts[i+1] for i in range(len(self.starts)-1)),'Overlapping source inventory')
        self.boundaries={}

    def locate(self,offset):
        i=bisect_right(self.starts,offset)-1
        if i<0 or offset>=self.ends[i]:return {'kind':'uncovered'}
        entry=self.entries[i];delta=offset-self.starts[i]
        if not delta:kind='source_start'
        else:
            if i not in self.boundaries:self.boundaries[i]=token_boundaries(entry['source_tokens'])
            kind='character_or_token_boundary' if delta in self.boundaries[i] else 'inside_character_or_control'
        return {'kind':kind,'master_id':entry['id'],'byte_delta':delta}


def all_pointer_words(data):
    refs=defaultdict(list);counts=Counter()
    for alignment in range(4):
        stop=len(data)-(len(data)-alignment)%4
        for i,(value,) in enumerate(struct.iter_unpack('<I',memoryview(data)[alignment:stop])):
            target=cartridge_offset(value,len(data))
            if target is None:continue
            word=alignment+i*4;view=(value-0x08000000)//0x02000000
            kind=('aligned' if alignment==0 else 'unaligned')+('_primary' if view==0 else '_mirror')
            counts[kind]+=1
            refs[target].append({'word':hx(word),'address':hx(value),'mode':kind})
    return refs,dict(counts)


def features(parsed):
    visible=''.join(t['text'] for t in parsed['tokens'] if t['kind']=='text')
    japanese=[c for c in visible if 0x3040<=ord(c)<=0x30ff or 0x3400<=ord(c)<=0x9fff]
    return {'japanese_characters':parsed['japanese_characters'],'distinct_japanese':len(set(japanese)),
        'indexed_characters':parsed['indexed_characters'],'visible_characters':len(visible),
        'has_printf':any(t['kind']=='printf' or 'argument_template_candidate' in t for t in parsed['tokens']),
        'unresolved_grammar':any(t.get('grammar')=='unresolved' for t in parsed['tokens']),
        'repetition_flag':len(japanese)>=8 and len(set(japanese))<=3}


def translated_ids(master):
    """Count authored English source IDs, independently of runtime acceptance."""
    curated=load_json(ROOT/'translations/catalog.json')['entries'];done={e['id'] for e in curated if e.get('english')}
    result={e['id'] for e in master if e.get('curated_id') in done};families={}
    for name in ('items','item-contexts','enemies','dungeon-interface','core-gameplay','gameplay-help','ally-services','tutorial-gameplay','ally-dialogue','companion-dialogue','ally-nicknames','opening-story','first-village','early-journey','story-completion','story-special','shared-story','arena-services','adventure-history','adventure-results','church-services','frontend-completion','code-owned-text','item-display','dungeon-events','battle-completion','merchants','keyboard-completion','inscriptions','world-completion','system-labels','encounter-ui','arena-final','arena-graphics','remaining-display','text-polish'):
        rows=load_json(ROOT/f'translations/{name}.json')['entries'];ids={e['master_id'] for e in rows if e.get('english') and e.get('master_id')}
        check(ids <= {e['id'] for e in master}, 'Authored catalog contains IDs outside the master inventory')
        families[name]={'entries':len(rows),'translated_source_ids':len(ids),'new_distinct_ids':len(ids-result)}
        outside=sum(bool(e.get('english')) and not e.get('master_id') for e in rows)
        if outside:families[name]['reviewed_resources_outside_inventory']=outside
        result|=ids
    return result,families


def audit(output=OUTPUT):
    output=Path(output);original=ORIGINAL_ROM.read_bytes();check(digest(original)==load_manifest()['base_sha256'],'Wrong source ROM')
    master=load_json(MASTER)['entries'];index=SourceIndex(master);codec=GameTextCodec(original)
    queue=load_json(ROOT/'build/text-extraction/review-queue.json');queue_by_at={int(e['offset'],0):e for e in queue}
    refs,pointer_counts=all_pointer_words(original);print('All alignments / cartridge windows:',pointer_counts,flush=True)
    cache={};failures={}
    def parse(at):
        if at not in cache and at not in failures:
            try:cache[at]=codec.parse(original,at)
            except DecodeError as error:failures[at]={'failure_offset':hx(error.offset),'reason':error.reason}
        return cache.get(at)
    discovery=defaultdict(set);known_refs=Counter();extra_known=[]
    for at,words in refs.items():
        location=index.locate(at)
        if location['kind']!='uncovered':
            for word in words:
                known_refs[(word['mode'],location['kind'])]+=1
                if word['mode']!='aligned_primary':extra_known.append({'target':hx(at),**word,**location})
            continue
        discovery[at].add('pointer_word')
    for at in queue_by_at:discovery[at].add('existing_review_queue')
    # Visit every non-empty byte after NUL, including unaligned starts outside
    # mapped banks. Decoding success is a lead, never proof of text ownership.
    pos=original.find(b'\0');nul_starts=0
    while pos>=0 and pos+1<len(original):
        at=pos+1
        if original[at] and index.locate(at)['kind']=='uncovered':
            nul_starts+=1;p=parse(at)
            if p and strong_text(p) and p['japanese_characters']>=4:discovery[at].add('all_alignment_nul_scan')
        pos=original.find(b'\0',at)
    candidates=[];review=[]
    for at,kinds in sorted(discovery.items()):
        p=parse(at);words=refs.get(at,[]);existing=queue_by_at.get(at)
        code_refs=[w for w in words if int(w['word'],0)<0x97000 and w['mode']=='aligned_primary']
        location=index.locate(at);mapped=any(a<=at<b for a,b in TEXT_BANKS)
        if location['kind']!='uncovered':disposition='already_cataloged'
        elif p is None:disposition='decoder_rejected'
        elif not p['display']:disposition='empty_target'
        else:
            f=features(p)
            if f['unresolved_grammar']:disposition='unresolved_grammar'
            elif f['repetition_flag']:disposition='repetitive_decode_candidate'
            elif strong_text(p) and p['japanese_characters']>=4:disposition='japanese_candidate'
            elif code_refs and mapped:disposition='short_or_format_candidate'
            else:disposition='weak_decode_candidate'
        if existing:
            review.append({'offset':hx(at),'original_reason':existing['reason'],'disposition':disposition,
                'preview':p['display'][:200] if p else existing.get('decoded_prefix_before_failure',''),
                'code_region_reference_words':[w['word'] for w in code_refs],**(failures.get(at) or {})})
        if p and p['display'] and (disposition in ('japanese_candidate','short_or_format_candidate','unresolved_grammar') or 'all_alignment_nul_scan' in kinds):
            check(rebuild(p['tokens'])==original[at:p['end']],'Candidate tokens differ from source')
            candidates.append({'id':f'candidate_{at:08x}','offset':hx(at),'end_exclusive':hx(p['end']),
                'japanese':p['display'],'source_hex':p['raw_hex'],'source_tokens':p['tokens'],
                'disposition':disposition,'discovery':sorted(kinds),'mapped_bank':mapped,'nul_boundary':at>0 and original[at-1]==0,
                'features':features(p),'pointer_candidates':words,'code_region_reference_words':[w['word'] for w in code_refs],
                'verified_pointer_owners':[]})
    done,families=translated_ids(master);check(done<={e['id'] for e in master},'Unknown translated source')
    report={'source_sha256':digest(original),'source_bytes':len(original),'master_sha256':digest(MASTER.read_bytes()),
        'review_queue_sha256':digest((ROOT/'build/text-extraction/review-queue.json').read_bytes()),'harness_sha256':digest(Path(__file__).read_bytes()),
        'master_entries':len(master),'translated_distinct_entries':len(done),'remaining_entries':len(master)-len(done),
        'translated_source_bytes':sum(len(bytes.fromhex(e['source_hex'])) for e in master if e['id'] in done),
        'all_source_bytes':sum(len(bytes.fromhex(e['source_hex'])) for e in master),'families':families,
        'pointer_word_counts':pointer_counts,'distinct_normalized_pointer_targets':len(refs),
        'known_source_reference_counts':[{'mode':mode,'location':where,'words':n} for (mode,where),n in sorted(known_refs.items())],
        'nonempty_uncovered_nul_starts_examined':nul_starts,'parse_attempts':len(cache)+len(failures),
        'existing_queue_entries':len(queue),'existing_queue_dispositions':dict(Counter(e['disposition'] for e in review)),
        'candidate_entries':len(candidates),'candidate_dispositions':dict(Counter(e['disposition'] for e in candidates)),
        'candidate_overlap_warning':'Candidates may be suffixes or overlap each other and include non-text. Counts are leads, not additions to the master.',
        'limits':['Read-only audit; no candidates promoted or pointer writes authorized.',
            'Code-region pointer locations are a prioritization heuristic, not disassembly or runtime proof.',
            'All byte alignments and three 32 MiB cartridge windows scanned; addresses beyond the physical source are rejected.',
            'Whole-ROM NUL-boundary scan uses existing font-0 grammar and Japanese-character threshold; short unreferenced strings can escape it.',
            'Relative/computed references, compressed resources, alternate font contexts and graphics lettering still require specific readers.',
            'No claim of complete game-text discovery or full-game runtime coverage.']}
    def write(name,value):atomic_write(output/name,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
    write('static-audit.json',report);write('candidates.json',{'source_sha256':digest(original),'entries':candidates})
    write('review-dispositions.json',{'source_sha256':digest(original),'entries':review})
    write('extra-known-references.json',{'source_sha256':digest(original),'references':extra_known})
    sheet=io.StringIO();w=csv.writer(sheet,delimiter='\t',lineterminator='\n')
    w.writerow(['id','offset','end_exclusive','disposition','mapped_bank','code_region_references','discovery','japanese'])
    for e in candidates:w.writerow([e['id'],e['offset'],e['end_exclusive'],e['disposition'],e['mapped_bank'],','.join(e['code_region_reference_words']),','.join(e['discovery']),e['japanese'].replace('\n','<LF>')])
    atomic_write(output/'candidates.tsv',sheet.getvalue().encode())
    print(json.dumps({k:v for k,v in report.items() if k not in ('families','known_source_reference_counts','limits')},indent=2),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=OUTPUT)
    audit(p.parse_args().output)
