"""Summarize native discovery evidence and checked short resources; preserve inputs."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct

from tools.audit_text_coverage import OUTPUT,SourceIndex,cartridge_offset,features
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.game_text import GameTextCodec,DecodeError,rebuild
from tools.translation_pipeline import atomic_write,check,load_json

# offset, literal word, native LDR instruction, use in reader, resource role.
# These establish source use, not permission to relocate it or enlarge buffers.
RESOURCES=(
 (0xA9FE8,0x32B20,0x32B08,'080329EC -> printf at 08032B16','Actor name with level and colour'),
 (0xA9FF4,0x32C78,0x32C68,'08032B4C -> printf at 08032C6E','Actor name with colour'),
 (0xD96EC,0x45244,0x451A6,'08045088 -> printf at 080451B8, paged engine at 080451D2','Level and current/max HP'),
 (0xD9970,0x491B8,0x4919E,'08049184 -> 30-byte copy at 080491A4','Unknown-name placeholder'),
 (0x1B4475,0x6DDB8,0x6DDAC,'0806DCDC -> text helper at 0806DDE6','Conditional unknown-name placeholder'),
 (0xC3E0B4,0x717E0,0x717D4,'08071700 -> printf at 080717D8 -> draw at 08071826','Ally-row name and level'),
 (0xC3E0C0,0x71900,0x71800,'08071700 -> printf at 08071804 -> draw at 08071826','Ally-row dynamic colour, name and level'),
 (0xC3E0D0,0x71914,0x718CA,'08071700 -> printf at 080718D6 -> draw at 080718E4','Ally-list current/total counter'),
 (0xC42158,0x7B4C4,0x7B384,'0807B294 -> printf at 0807B386 -> draw at 0807B39E','Choice-row colour and text'),
 (0xC421C4,0x7B7B0,0x7B770,'0807B604 -> printf at 0807B774 -> numeric conversion loop','Eight-digit zero-filled numeric format'),
 (0xC421CC,0x7B854,0x7B7BA,'0807B604, computed two-byte lookups at 0807B7C4–0807B7DA','Full-width star/digit lookup strip'),
 (0xC4CD04,0x846AC,0x8468E,'0808467C -> name decoder 0807D228, printf at 0808469E','Stored-record name and level'),
 (0xC4CE7C,0x855A8,0x8554C,'080853E0 -> printf at 0808556C -> draw at 0808557A','Record-list composite heading'),
 (0xC4CE88,0x855B0,0x8555E,'080853E0, selected by record flag 0800 before printf','Record-list star marker'),
)


def write(path,value):atomic_write(path,(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())


def reviewed_resources(original,index):
    codec=GameTextCodec(original);entries=[]
    listings=[ROOT/'build/text-coverage/short-readers.txt',ROOT/'build/enemy-items/research/enemy-functions.txt']
    text='\n'.join(p.read_text() for p in listings)
    for at,word,instruction,reader,role in RESOURCES:
        check(index.locate(at)['kind']=='uncovered','Reviewed source already in master; refresh audit scope')
        check(struct.unpack_from('<I',original,word)[0]==0x08000000+at,'Reader literal differs')
        opcode=struct.unpack_from('<H',original,instruction)[0]
        check(opcode&0xF800==0x4800 and ((instruction+4)&~3)+(opcode&255)*4==word,'Not the expected Thumb literal load')
        check(f'{instruction+0x08000000:08x}  ldr ' in text,'Missing disassembly evidence')
        parsed=codec.parse(original,at);check(rebuild(parsed['tokens'])==original[at:parsed['end']],'Resource source differs')
        entries.append({'id':f'resource_{at:08x}','offset':f'0x{at:08X}','end_exclusive':f'0x{parsed["end"]:08X}',
            'japanese':parsed['display'],'source_hex':parsed['raw_hex'],'source_tokens':parsed['tokens'],
            'literal_word':f'0x{word:08X}','load_instruction':f'0x{instruction+0x08000000:08X}',
            'reader':reader,'role':role,'evidence':'Static native consumer and exact literal load; digit strip also has isolated native loop coverage.',
            'translation_status':'not_added_to_translation_inventory','verified_pointer_owners':[]})
    result={'source_sha256':digest(original),'entries':entries,'listing_sha256':{str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in listings},
        'scope':'Confirmed source resources omitted by the master filter. Includes formatting templates and computed glyph data, not 14 new sentences. No relocation or pointer ownership authorized.'}
    write(OUTPUT/'reviewed-resources.json',result);return result


def native_digit_strip(original):
    import mgba.log
    from tools.verify_expansion import Session
    from tools.verify_companion_dialogue import run_to
    from tools.verify_core_gameplay import write_bytes
    mgba.log.silence();cases=[];sp=0x03007C00;destination=sp+0x28
    with Session(original,OUTPUT/'digit-strip') as session:
        session.frames(5);core=session.core;backup=bytes(core.memory[sp:sp+0x100])
        try:
            for value in range(0x2F,0x3A):
                write_bytes(core,sp,b'\xA5'*0x100);write_bytes(core,sp+0xC,bytes([value])*8)
                trace=run_to(core,0x0807B7B8,0x0807B7EA,{'sp':sp,'r4':destination})
                glyph=original[0xC421CC+(value-0x2F)*2:0xC421CE+(value-0x2F)*2]
                output=bytes(core.memory[destination:destination+17])
                check(output==glyph*8+b'\0','Native digit-strip output differs')
                check(bytes(core.memory[destination-8:destination])==b'\xA5'*8 and bytes(core.memory[destination+17:destination+25])==b'\xA5'*8,'Digit loop damaged guards')
                cases.append({'input_ascii':chr(value),'index':value-0x2F,'glyph_hex':glyph.hex(),'output_hex':output.hex(),'guards_intact':True,'steps':trace['steps']})
        finally:write_bytes(core,sp,backup)
    result={'rom_sha256':digest(original),'cases':cases,'scope':'Original computed lookup loop only, eleven symbols in eight repeated positions. No interactive picker navigation or insertion claim.',
        'loop_helper_sha256':digest((ROOT/'tools/verify_companion_dialogue.py').read_bytes())}
    write(OUTPUT/'digit-strip/verification.json',result);return result


def runtime_coverage(original,index):
    routes=[];observed=set();totals=Counter();missing=[]
    for route in ('settings','creation','story'):
        path=OUTPUT/f'runtime/{route}/readers.json';data=load_json(path)
        check(data['rom_sha256']==digest(original) and data['route']==route and data['inputs'],'Stale or empty native route')
        counts=Counter();sources=set();ram=Counter();uncovered=[]
        for family,key in (('reads','address'),('draws','address'),('formats','source')):
            for event in data[family]:
                address=int(event[key],0);at=cartridge_offset(address,len(original))
                location={'kind':'RAM_or_other'} if at is None else index.locate(at)
                counts[(family,location['kind'])]+=1;totals[(family,location['kind'])]+=1
                if location.get('master_id'):sources.add(location['master_id']);observed.add(location['master_id'])
                if at is None:ram[(family,event['caller'])]+=1
                elif location['kind'] in ('uncovered','inside_character_or_control'):
                    uncovered.append({'family':family,'source_address':event[key],'caller':event['caller'],**location})
        check(data['reads'] and data['draws'] and data['formats'],'Native route missing a reader family')
        missing.extend(uncovered)
        routes.append({'route':route,'trace_sha256':digest(path.read_bytes()),'observed_master_ids':sorted(sources),'uncovered_or_invalid':uncovered,
            'counts':[{'family':f,'location':k,'events':v} for (f,k),v in sorted(counts.items())],
            'ram_or_other_callers':[{'family':f,'caller':c,'events':n} for (f,c),n in sorted(ram.items())],
            'observed_font_ids':sorted({e['font'] for e in data['glyphs']})})
    result={'rom_sha256':digest(original),'trace_harness_sha256':digest((ROOT/'tools/trace_text_systems.py').read_bytes()),
        'routes':routes,'observed_master_ids':sorted(observed),'uncovered_or_invalid_rom_events':len(missing),
        'counts':[{'family':f,'location':k,'events':v} for (f,k),v in sorted(totals.items())],
        'limits':'Boot advances 600 frames before instrumentation. Captures title/settings, new-log/name entry and opening-story routes only. ROM character reads, draw inputs and shared-formatter sources are matched by exact byte boundary. RAM strings are reported separately; their origin is not inferred from textual resemblance. Story-specific RAM producers and later gameplay remain untraced by this audit.'}
    write(OUTPUT/'runtime-coverage.json',result);return result


def font_recheck(original):
    fonts=[GameTextCodec(original,i) for i in range(3)]
    queue=load_json(OUTPUT/'review-dispositions.json')['entries'];rescued=[];count=0
    for row in queue:
        if row['disposition']!='decoder_rejected':continue
        count+=1
        for font in fonts[1:]:
            try:p=font.parse(original,int(row['offset'],0))
            except DecodeError:continue
            if p['japanese_characters']>=4:rescued.append({'offset':row['offset'],'font':font.font_id,'display':p['display'],'features':features(p)})
    result={'source_sha256':digest(original),'rejected_targets_rechecked':count,'other_fonts':[1,2],
        'japanese_decodes_at_least_four_characters':rescued,
        'code_set_outside_font_0':{str(f.font_id):len(f.code_set-fonts[0].code_set) for f in fonts[1:]},
        'indexed_order_identical_to_font_0_prefix':{str(f.font_id):f.codes==fonts[0].codes[:len(f.codes)] for f in fonts[1:]},
        'scope':'Recheck only the existing queue\'s rejected starts, using the other two known descriptor tables. Empty result does not rule out other encodings or fonts. Index order differs even though ordinary code sets are subsets.'}
    write(OUTPUT/'font-recheck.json',result);return result


def verify():
    original=ORIGINAL_ROM.read_bytes();master=load_json(ROOT/'translations/master.json')['entries'];index=SourceIndex(master)
    static=load_json(OUTPUT/'static-audit.json')
    check(static['source_sha256']==digest(original) and static['harness_sha256']==digest((ROOT/'tools/audit_text_coverage.py').read_bytes()),'Stale static audit')
    check(static['master_sha256']==digest((ROOT/'translations/master.json').read_bytes()),'Master differs from static audit')
    checks=load_json(OUTPUT/'before/hashes.json')
    for name,expected in checks.items():check(digest((ROOT/name).read_bytes())==expected,f'Input changed: {name}')
    resources=reviewed_resources(original,index);digits=native_digit_strip(original);runtime=runtime_coverage(original,index);fonts=font_recheck(original)
    check(runtime['uncovered_or_invalid_rom_events']==0,'Native route exposes a missing source; investigate it')
    queue=load_json(OUTPUT/'review-dispositions.json')['entries'];candidates=load_json(OUTPUT/'candidates.json')['entries']
    check(len(queue)==static['existing_queue_entries'] and len({e['offset'] for e in queue})==len(queue),'Incomplete/duplicate queue classification')
    check(len(candidates)==static['candidate_entries'],'Incomplete candidate report')
    codec=GameTextCodec(original)
    for e in candidates:
        at=int(e['offset'],0);p=codec.parse(original,at)
        check(p['raw_hex']==e['source_hex'] and rebuild(e['source_tokens'])==original[at:int(e['end_exclusive'],0)],'Candidate source mismatch')
        check(not e['verified_pointer_owners'],'Audit improperly grants insertion ownership')
    log=(OUTPUT/'unit-tests.log').read_text();match=re.search(r'Ran (\d+) tests',log)
    check(match and int(match[1])>=156 and log.rstrip().endswith('OK'),'Unit suite incomplete/failed')
    report={'status':'passed','source_sha256':digest(original),'master_entries':static['master_entries'],
        'translated_distinct_entries':static['translated_distinct_entries'],'remaining_entries':static['remaining_entries'],
        'preserved_input_files':len(checks),'input_hashes':checks,'unit_tests':int(match[1]),
        'all_alignment_pointer_words':sum(static['pointer_word_counts'].values()),'nul_starts_examined':static['nonempty_uncovered_nul_starts_examined'],
        'review_queue_classified':len(queue),'candidate_leads':len(candidates),'confirmed_omitted_resources':len(resources['entries']),
        'native_digit_strip_cases':len(digits['cases']),'native_routes':len(runtime['routes']),'native_unique_master_sources':len(runtime['observed_master_ids']),
        'native_uncovered_rom_events':runtime['uncovered_or_invalid_rom_events'],'other_font_rechecks':fonts['rejected_targets_rechecked']*2,
        'other_font_japanese_rescues':len(fonts['japanese_decodes_at_least_four_characters']),
        'harness_sha256':digest(Path(__file__).read_bytes()),
        'artifact_sha256':{name:digest((OUTPUT/name).read_bytes()) for name in ('static-audit.json','candidates.json','candidates.tsv','review-dispositions.json','extra-known-references.json','reviewed-resources.json','digit-strip/verification.json','runtime-coverage.json','font-recheck.json')},
        'limits':'Audit complete within its documented scan and opening-route scope. Master and ROM unchanged; candidates/resources remain separate. No complete-game extraction claim. Compressed resources, relative/computed families beyond documented readers, graphics lettering and later/RAM text provenance remain.'}
    write(OUTPUT/'acceptance.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('input_hashes','artifact_sha256')},indent=2));return report


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();verify()
