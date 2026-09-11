"""Native nickname generation, guarded actor names and party-record round trips."""
import argparse
from pathlib import Path
import json
import struct
import mgba.log
from mgba._pylib import ffi

from tools.build_ally_nicknames import OUTPUT, CATALOG, TABLE, expected_compact
from tools.build_first_label import ORIGINAL_ROM, ROOT, digest
from tools.translation_pipeline import check, load_json
from tools.verify_companion_dialogue import run_to
from tools.verify_core_gameplay import write_bytes, cstring
from tools.verify_expansion import Session
from tools.verify_items import write_json
from tools.verify_tutorial_gameplay import cold_tables, restore

STATE=ROOT/'build/companion-dialogue/verification/save/world.state'
ACTOR, DEST, RECORD, SP=0x0203F000,0x0203F200,0x0203F400,0x03007C00


def generate(core,row,suffix):
    write_bytes(core,ACTOR,b'\0'*0x150)
    core.memory.u16[ACTOR+8]=row;core.memory.u16[ACTOR+6]=0x7FFF;core.memory.u16[ACTOR+0x62]=99
    write_bytes(core,ACTOR+0x128,b'\xA5'*0x16)
    # +137 is a real name-selection flag, kept clear for nickname consumers.
    core.memory.u8[ACTOR+0x137]=0
    write_bytes(core,SP,b'\xA5'*0x80)
    pointer=core.memory.u32[0x08000000+TABLE+4*row]
    a=run_to(core,0x0802926E,0x08029288,{'sp':SP,'r7':ACTOR,'r4':0})
    source=cstring(core,pointer)
    check(cstring(core,SP+0x48)==source,'Native nickname pointer copy differs')
    b=run_to(core,0x08029288,0x080292A0,{'sp':SP,'r8':suffix})
    combined=cstring(core,SP+0x28)
    suffix_source=core.memory.u32[0x020007B8+4*suffix]
    check(combined==source[:-1]+cstring(core,suffix_source),'Native duplicate-name format differs')
    c=run_to(core,0x080292AE,0x080292BE,{'sp':SP,'r7':ACTOR})
    raw=bytes(core.memory[ACTOR+0x130:ACTOR+0x136])
    check(b'\0' in raw,'Nickname lacks terminator in six-byte actor field')
    check(bytes(core.memory[ACTOR+0x128:ACTOR+0x130])==b'\xA5'*8,'Nickname damaged preceding actor field')
    check(core.memory.u8[ACTOR+0x136]==0xA5 and core.memory.u8[ACTOR+0x137]==0,'Nickname damaged following actor field')
    return {'source':hex(pointer),'source_hex':source.hex(),'suffix_source':hex(suffix_source),'combined_hex':combined.hex(),
        'compact_hex':raw.hex(),'steps':[a['steps'],b['steps'],c['steps']],'guards_intact':True}


def decode(core,compact):
    write_bytes(core,0x0203F300,compact)
    write_bytes(core,DEST-8,b'\xA5'*46)
    trace=run_to(core,0x0807D228,0x08000000,{'r0':0,'r1':DEST,'r2':0x0203F300})
    output=cstring(core,DEST)
    check(len(output)<=30 and bytes(core.memory[DEST-8:DEST])==b'\xA5'*8 and bytes(core.memory[DEST+30:DEST+38])==b'\xA5'*8,'Compact decoder crossed guarded output')
    return output


def roundtrip(core,compact):
    write_bytes(core,RECORD-8,b'\xA5'*48)
    run_to(core,0x0804A50C,0x0804A51C,{'r5':RECORD,'r6':ACTOR,'r7':0})
    stored=bytes(core.memory[RECORD+4:RECORD+10]);expected=compact.split(b'\0',1)[0][:5].ljust(6,b'\0')
    check(stored==expected,'Party-record nickname differs')
    check(bytes(core.memory[RECORD-8:RECORD+4])==b'\xA5'*12 and bytes(core.memory[RECORD+10:RECORD+40])==b'\xA5'*30,'Nickname store changed adjacent record fields')
    write_bytes(core,ACTOR+0x130,b'\x5A'*6)
    run_to(core,0x0804A368,0x0804A378,{'r4':RECORD,'r5':ACTOR})
    check(bytes(core.memory[ACTOR+0x130:ACTOR+0x136])==stored,'Native record-to-actor copy differs')
    check(core.memory.u8[ACTOR+0x136]==0xA5,'Record restore damaged actor neighbor')
    return stored


def format_names(core, row, expected):
    # Town fixtures have no dungeon actor context. Supply only the viewer and
    # compared entity-ID fields used by these complete formatter functions.
    write_bytes(core,0x0203F500,b'\0'*0x150)
    core.memory.u32[0x0200000C]=0x02008000
    core.memory.u16[0x0200804E]=0xFFFE
    core.memory.u32[0x02021EE4]=0x0203F500
    outputs=[]
    for function in (0x080329EC,0x08032B4C,0x08032CA4):
        write_bytes(core,DEST-8,b'\xA5'*46)
        trace=run_to(core,function,0x08000000,{'r0':ACTOR,'r1':DEST,'r2':0,'r3':0})
        raw=cstring(core,DEST)
        check(len(raw)<=30 and bytes(core.memory[DEST-8:DEST])==b'\xA5'*8 and bytes(core.memory[DEST+30:DEST+38])==b'\xA5'*8,'Actor formatter crossed name buffer')
        # All three wrappers intentionally use the fixed character names for
        # Rosa/Ines (0805ECDC), regardless of their stored nickname.
        if row not in (191,192):
            check(expected[:-1] in raw,f'Actor formatter {function:08X} lost nickname for row {row}: {raw!r}')
        else:
            check((b'Rosa' if row==191 else b'Ines') in raw,'Fixed NPC name changed')
        outputs.append({'entry':hex(function),'raw_hex':raw.hex(),'steps':trace['steps'],'guards_intact':True})
    return outputs


def verify(variant='english',limit=None):
    mgba.log.silence();catalog=load_json(CATALOG);original=ORIGINAL_ROM.read_bytes()
    rom=ROOT/'build/companion-dialogue/torneko3-companion-dialogue-english.gba' if variant=='baseline' else OUTPUT/f'torneko3-ally-nicknames-{variant}.gba'
    folder=OUTPUT/f'verification/{variant}';state=STATE.read_bytes();cases=[]
    entries=catalog['entries'][:limit] if limit else catalog['entries']
    with Session(rom.read_bytes(),folder) as session:
        tables=cold_tables(session)
        for e in entries:
            suffixes=range(10) if variant=='english' else (0,1,9)
            for suffix in suffixes:
                restore(session,state,tables);core=session.core
                result=generate(core,e['row'],suffix);raw=bytes.fromhex(result['compact_hex'])
                decoded=decode(core,raw)
                if variant=='english':
                    compact,text=expected_compact(e['display'] or e['english'],suffix)
                    check(raw.startswith(compact) and decoded==text.encode()+b'\0','English nickname/suffix was lost')
                stored=roundtrip(core,raw);check(decode(core,stored)==decoded,'Record round trip changed decoded name')
                formats=format_names(core,e['row'],decoded)
                cases.append({'id':e['id'],'row':e['row'],'suffix':suffix,**result,'decoded_hex':decoded.hex(),
                    'stored_hex':stored.hex(),'record_guards_intact':True,'formatters':formats})
            if (e['row']+1)%25==0:print(variant,e['row']+1,'nickname rows',flush=True)
        compatibility=[]
        # Calls outside recruitment must preserve the original encoder, even
        # when its input happens to begin with ASCII bytes.
        for type_id in (0,1):
            for payload in (bytes.fromhex('82a082a282a400'),b'ABCDE\0',b'\0'):
                restore(session,state,tables);core=session.core
                write_bytes(core,0x0203F300,payload+b'\0'*16);write_bytes(core,DEST,b'\xA5'*30)
                t=run_to(core,0x0807D29C,0x08000000,{'r0':type_id,'r1':DEST,'r2':0x0203F300})
                compatibility.append({'type':type_id,'source_hex':payload.hex(),'output_hex':cstring(core,DEST).hex(),'steps':t['steps']})
    report={'source_sha256':digest(original),'rom_sha256':digest(rom.read_bytes()),'catalog_sha256':digest(CATALOG.read_bytes()),
        'fixture_sha256':digest(state),'harness_sha256':digest(Path(__file__).read_bytes()),'variant':variant,'limited':bool(limit),
        'cold_initialized_tables':tables,'cases':cases,'other_encoder_callers':compatibility,
        'scope':'Original species-pointer copy and suffix-format slices, actual recruitment encoder call, compact decoder, six-byte actor/party copies and three complete name formatters. CPU entries, species, duplicate count and level are controlled. Does not by itself prove natural recruitment, renaming UI or cartridge save persistence.'}
    write_json(folder/'verification.json',report);return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--variant',choices=['english','japanese','baseline'],default='english');p.add_argument('--limit',type=int)
    args=p.parse_args();verify(args.variant,args.limit)
