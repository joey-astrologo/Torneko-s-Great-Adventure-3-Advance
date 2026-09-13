"""Verify native title copies, palettes, fades, blink and following menus."""
from pathlib import Path
import struct
import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageDraw
from tools.audit_boot_graphics import Trace as BootTrace
from tools.build_first_label import ROOT, ORIGINAL_ROM, digest
from tools.build_title_art import OUT, ROM, BASELINE
from tools.pack_title_art import decode, APPROVAL
from tools.extract_arrival_cards import save_json
from tools.translation_pipeline import check, load_json
from tools.verify_expansion import Session


class TitleTrace(BootTrace):
    def __init__(self,core,data):
        self.selected=-1;self.guards=[];self.fades=[];self.blinks=[];self.before=None
        super().__init__(core,data)
        for at in (0x08089B74,0x08087864,0x080878B0):
            point=ffi.new('struct mBreakpoint*');point.address=at;point.segment=-1;point.type=lib.BREAKPOINT_HARDWARE
            check(self.d.platform.setBreakpoint(self.d.platform,point)>=0,'Title breakpoint unavailable')

    def hit(self,d,reason,info):
        try:
            if reason!=lib.DEBUGGER_ENTER_BREAKPOINT:return
            at=info.address;regs=[int(v)&0xffffffff for v in self.cpu.gprs]
            if at==0x0808508C:
                self.selected=regs[0]
                if self.selected==2:
                    count=struct.unpack_from('<I',self.data,0xC77BE4)[0]
                    end=0x6008000+count*32
                    check(end<=0x6010000,'Tile copy would leave BG VRAM')
                    self.before=(end,bytes(self.c.memory[0x6007FE0:0x6008000]),bytes(self.c.memory[end:0x6010000]))
            elif at==0x08085214 and self.selected==2:
                end,lo,hi=self.before
                check(bytes(self.c.memory[0x6007FE0:0x6008000])==lo,'Title overwrote preceding map bytes')
                check(bytes(self.c.memory[end:0x6010000])==hi,'Title overwrote following BG VRAM')
                self.guards.append({'frame':self.c.frame_counter,'tile_end':hex(end),'before_guard':32,'after_guard':0x6010000-end})
            elif at==0x08089B74 and self.selected==2:
                self.fades.append({'frame':self.c.frame_counter,'bank':regs[0]&65535,'value':regs[1]&65535})
            elif at in (0x08087864,0x080878B0) and self.selected==2:
                self.blinks.append(self.c.frame_counter)
            if at in (0x0808508C,0x08085214):super().hit(d,reason,info)
        except Exception as e:self.errors.append(str(e))
        finally:d.state=lib.DEBUGGER_RUNNING


def expected(data):
    source,palette,count,mode=struct.unpack_from('<4I',data,0xC77BDC)
    source-=0x8000000;palette-=0x8000000
    check(mode==1,'Title two-map mode changed')
    maps=data[source:source+4096];tiles=data[source+4096:source+4096+count*32];pal=data[palette:palette+960]
    on=decode(maps,tiles,pal)
    offmaps=bytearray(maps);offmaps[0x480:0x500]=bytes(128)
    off=decode(offmaps,tiles,pal)
    return maps,tiles,pal,on,off


def run(data,variant,initial_save):
    out=OUT/'verification'/variant
    maps,tiles,pal,on,off=expected(data)
    expected_palette=struct.pack('<240H',*[sum((((w>>(8*c))&255)>>3)<<(5*c) for c in range(3)) for w in struct.unpack('<240I',pal)])
    screens={};phases=[];cache_checks=0
    with Session(data,out,initial_save=initial_save) as session:
        trace=TitleTrace(session.core,data)
        try:
            for frame in (1,30,60,120,180,240,300,420,480,488,496,504,600):
                trace.frames(frame-session.core.frame_counter)
                screens[f'boot-{frame:04d}']=session.capture(f'boot-{frame:04d}').tobytes()
            check([r['index'] for r in trace.rows]==[1,0,9,2],'Native boot selections differ')
            check(bytes(session.core.memory[0x05000000:0x050001E0])==expected_palette,'Native full-bright palette differs')
            check(screens['boot-0600']==on.tobytes(),'Full native title pixels differ from packed decode')
            check(bytes(session.core.memory[0x0201054C:0x020105CC])==maps[0x480:0x500],'Native prompt cache differs')
            for step in range(121):
                if step:trace.frames(1)
                current=session.screen.to_pil().convert('RGB')
                raw=current.tobytes()
                check(raw in (on.tobytes(),off.tobytes()),'Unexpected title pixels during native blink')
                phase='on' if raw==on.tobytes() else 'off'
                phases.append({'frame':session.core.frame_counter,'phase':phase})
                if not (out/f'prompt-{phase}.png').exists():current.save(out/f'prompt-{phase}.png')
                check(bytes(session.core.memory[0x0201054C:0x020105CC])==maps[0x480:0x500],'Blink changed cached prompt cells')
                cache_checks+=1
            check({p['phase'] for p in phases}=={'on','off'},'Both native prompt phases were not observed')
            check(bool(trace.blinks),'Native blink reader was not reached')
            values={e['value'] for e in trace.fades if e['bank']==0}
            check(set(range(0,257,16))<=values,'Native title fade levels incomplete')
            session.press('START',240,trace);screens['menu']=session.capture('menu').tobytes()
            # Empty saves expose only New game/Settings. Existing saves add
            # Records. B returns to the illustrated menu, not the title logo.
            for _ in range(1 if initial_save is None else 3):session.press('DOWN',20,trace)
            session.press('A',120,trace);screens['submenu']=session.capture('submenu').tobytes()
            session.press('B',120,trace);screens['menu-back']=session.capture('menu-back').tobytes()
            check(not trace.errors,str(trace.errors))
            result={'rom_sha256':digest(data),'initial_save_sha256':digest(initial_save) if initial_save else None,
                'native_loads':trace.rows,'guard_checks':trace.guards,'palette_exact':True,'all_title_pixels_exact':True,
                'prompt_phases':phases,'prompt_cache_checks':cache_checks,'native_blink_iterations':len(trace.blinks),
                'fade_bank_zero_values':sorted(values),'inputs':session.frames_recorded,
                'submenu':'Settings' if initial_save is None else 'Records',
                'scope':'Natural cold boot and real buttons. Exact packed pixels, native palette, fade levels, '
                         'prompt cache/blink, Start transition, submenu and return to the illustrated main menu.'}
        finally:trace.close()
    if initial_save is not None:check(session.disk_save==initial_save,'Native title/menu route changed the disposable save')
    result['save_unchanged']=initial_save is None or session.disk_save==initial_save
    save_json(out/'native.json',result)
    return screens,result


def verify():
    mgba.log.silence()
    data=ROM.read_bytes();baseline=BASELINE.read_bytes();report=load_json(OUT/'english-build.json')
    check(digest(data)==report['rom_sha256'],'Built ROM differs')
    check(digest(baseline)==report['previous_rom_sha256'],'Baseline differs')
    user_files={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in (ROOT/'saves').rglob('*') if p.is_file()}
    all_results=[]
    for profile,save in (('empty',None),('user-save',(ROOT/'saves/torneko3-english.sav').read_bytes())):
        old_screens,old_report=run(baseline,'baseline-'+profile,save)
        new_screens,new_report=run(data,'english-'+profile,save)
        unchanged=[name for name in old_screens if name in ('menu','submenu','menu-back') or (name.startswith('boot-') and int(name[5:])<471)]
        for name in unchanged:check(old_screens[name]==new_screens[name],'Unrelated boot/menu screen differs: '+profile+'/'+name)
        check(old_report['prompt_phases']==new_report['prompt_phases'],'Prompt timing changed')
        all_results.append({'profile':profile,'unchanged_screen_pairs':unchanged,'prompt_timing_equal':True,
                            'baseline_report':'verification/baseline-'+profile+'/native.json',
                            'english_report':'verification/english-'+profile+'/native.json'})
        print(profile,'native title, blink, fade and menu roundtrip passed',flush=True)
    check(all(digest((ROOT/p).read_bytes())==sha for p,sha in user_files.items()),'User save/state changed')
    check(digest(ROM.read_bytes())==report['rom_sha256'] and digest(BASELINE.read_bytes())==report['previous_rom_sha256'],'A ROM changed during checks')
    save_json(OUT/'native-verification.json',{'status':'passed','source_rom':report['source_rom'],'source_sha256':report['source_sha256'],
        'output_rom':report['output_rom'],'rom_sha256':report['rom_sha256'],'baseline_sha256':report['previous_rom_sha256'],
        'profiles':all_results,'user_save_hashes':user_files,'user_files_unchanged':True,
        'harness_sha256':digest(Path(__file__).read_bytes()),
        'helper_sha256':{p:digest((ROOT/p).read_bytes()) for p in ('tools/audit_boot_graphics.py','tools/verify_expansion.py','tools/pack_title_art.py')},
        'scope':'Two paired natural boot/menu routes, 121 native blink frames per ROM/profile, '
                'palette/map/tile copies and guards. No forced CPU entry or gameplay-state edits.'})
    source=Image.open(ROOT/'assets/title-screen/approved.png').convert('RGB')
    actual=Image.open(OUT/'verification/english-user-save/boot-0600.png').convert('RGB')
    sheet=Image.new('RGB',(960,374),(16,26,35));draw=ImageDraw.Draw(sheet)
    draw.text((12,10),'Approved audition',fill='white');draw.text((492,10),'Inserted: native mGBA capture',fill='white')
    sheet.paste(source.resize((480,320),Image.Resampling.NEAREST),(0,30))
    sheet.paste(actual.resize((480,320),Image.Resampling.NEAREST),(480,30))
    draw.text((12,356),'Native tile/palette conversion; original start prompt preserved',fill='white')
    sheet.save(OUT/'approval-vs-game.png')


if __name__=='__main__':verify()
