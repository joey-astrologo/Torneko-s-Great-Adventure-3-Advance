"""Read-only cold-boot graphics provenance; no forced entry or RAM writes."""
import json, struct
from pathlib import Path
import mgba.log
from mgba._pylib import ffi,lib
from tools.verify_expansion import Session
from tools.audit_scene_resources import BASELINE
from tools.build_first_label import ORIGINAL_ROM,ROOT,digest
from tools.translation_pipeline import check
from tools.trace_text_systems import ReaderTrace
OUT=ROOT/'build/completion/boot-graphics/research'

class Trace:
    def __init__(self,c,data):
        self.c,self.data=c,data;self.rows=[];self.errors=[];self.active=None
        self.cpu=ffi.cast('struct ARMCore*',c._core.cpu)
        self.callback=ffi.callback('void(struct mDebugger*, enum mDebuggerEntryReason, struct mDebuggerEntryInfo*)',self.hit)
        self.d=ffi.new('struct mDebugger*');self.d.type=lib.DEBUGGER_CUSTOM;self.d.entered=self.callback
        lib.mDebuggerAttach(self.d,c._core)
        for at in (0x0808508C,0x08085214):
            p=ffi.new('struct mBreakpoint*');p.address=at;p.segment=-1;p.type=lib.BREAKPOINT_HARDWARE
            check(self.d.platform.setBreakpoint(self.d.platform,p)>=0,'Breakpoint unavailable')
    def hit(self,d,reason,info):
        try:
            if reason!=lib.DEBUGGER_ENTER_BREAKPOINT:return
            r=[int(v)&0xffffffff for v in self.cpu.gprs]
            if info.address==0x0808508C:
                index=r[0];at=0xC77BBC+index*16
                check(0<=index<=10,'Unmapped graphic index')
                source,palette,count,mode=struct.unpack_from('<4I',self.data,at)
                maps=0x1000 if mode else 0x800
                self.active={'index':index,'frame':self.c.frame_counter,'caller':hex((r[14]&~1)-4),'record':hex(at),'source':hex(source),'palette':hex(palette),'tile_count':count,'two_maps':bool(mode),'maps_bytes':maps}
            else:
                a=self.active;check(a is not None,'Copy without selection')
                src=int(a['source'],0);n=a['tile_count']*32;off=src-0x08000000+a['maps_bytes']
                raw=bytes(self.c.memory[0x06008000:0x06008000+n])
                check(raw==self.data[off:off+n],'Native tile copy differs')
                pointers=[int(self.c.memory.u32[x]) for x in (0x020105D4,0x020105D8)]
                copied=[bytes(self.c.memory[p:p+0x800]) for p in pointers]
                source=self.data[src-0x08000000:src-0x08000000+a['maps_bytes']]
                check(copied==([source[:0x800],source[0x800:]] if a['two_maps'] else [bytes(0x800),source]),'Native maps differ')
                a.update({'tile_copy_sha256':digest(raw),'native_maps_match':True,'map_heap_pointers':list(map(hex,pointers)),'copy_frame':self.c.frame_counter})
                self.rows.append(a);self.active=None
        except Exception as e:self.errors.append(str(e))
        finally:d.state=lib.DEBUGGER_RUNNING
    def frames(self,n):
        for _ in range(n):lib.mDebuggerRunFrame(self.d)
        check(not self.errors,str(self.errors))
    def close(self):self.c._core.detachDebugger(self.c._core)

if __name__=='__main__':
    mgba.log.silence()
    for variant,path in [('japanese',ORIGINAL_ROM),('english',BASELINE)]:
        data=path.read_bytes();out=OUT/variant
        with Session(data,out) as s:
            t=Trace(s.core,data)
            try:
                for n in (1,30,60,120,180,240,300,420,600):
                    t.frames(n-s.core.frame_counter);s.capture(f'boot-{n:04d}')
                for name,at,n in [('vram',0x06000000,0x18000),('palette',0x05000000,0x400),('io',0x04000000,0x60)]:
                    (out/f'{name}.bin').write_bytes(bytes(s.core.memory[at:at+n]))
                result={'rom':str(path),'rom_sha256':digest(data),'harness_sha256':digest(Path(__file__).read_bytes()),'frames':600,'inputs':[],'cases':t.rows,'scope':'Natural cold boot, original loader selection and exact tile/map copies. No input, forced function entry or RAM writes.'}
                check([e['index'] for e in t.rows]==[1,0,9,2],'Boot graphic selection changed')
                result['helper_sha256']={Path(m).name:digest(Path(m).read_bytes()) for m in (__import__('tools.verify_expansion',fromlist=['']).__file__,__import__('tools.trace_text_systems',fromlist=['']).__file__)}
                (out/'provenance.json').write_text(json.dumps(result,indent=2)+'\n')
            finally:t.close()
        with Session(data,out/'text-trace') as s:
            t=ReaderTrace(s.core)
            try:
                t.frames(600);result=t.report()
                check(all(not v for v in result.values()),'Boot now reaches a shared text reader; review required')
                result.update({'rom_sha256':digest(data),'harness_sha256':digest(Path(__file__).read_bytes()),'frames':600,'scope':'Natural cold boot, built-in mGBA BIOS, no input; shared readers observed from frame zero.'})
                (out/'text-readers.json').write_text(json.dumps(result,indent=2)+'\n')
            finally:t.close()
        print(variant,'four native boot graphics and first 600 frames checked',flush=True)
    from PIL import Image
    for n in (1,30,60,120,180,240,300,420,600):
        check(Image.open(OUT/'japanese'/f'boot-{n:04d}.png').tobytes()==Image.open(OUT/'english'/f'boot-{n:04d}.png').tobytes(),'Preserved boot pixels differ')
    print('Nine Japanese/English boot pixel comparisons passed',flush=True)
