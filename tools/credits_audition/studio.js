'use strict';
const $=id=>document.getElementById(id);
const DEFAULTS={headingFace:'rounded',nameFace:'rounded',headingHeight:9,nameHeight:10,titleHeight:12,tracking:0,leading:0,roleCase:'upper',align:'original',edges:'soft',headingColour:'#e0bb79',nameColour:'#fff7e5',guides:false};
const PRESETS={rounded:{headingFace:'rounded',nameFace:'rounded',headingHeight:9,nameHeight:10,titleHeight:12,edges:'soft'},mixed:{headingFace:'rounded',nameFace:'small',headingHeight:9,nameHeight:8,titleHeight:12,edges:'crisp'},papyrus:{headingFace:'papyrus-condensed',nameFace:'papyrus-condensed',headingHeight:10,nameHeight:11,titleHeight:13,edges:'soft'},shiren:{headingFace:'shiren',nameFace:'shiren',headingHeight:9,nameHeight:10,titleHeight:12,edges:'crisp'}};
const labels={rounded:'Rounded',mixed:'Rounded + small names',papyrus:'Papyrus Condensed',shiren:'Shiren + supplements'};
const ranges={headingHeight:[7,16],nameHeight:[7,16],titleHeight:[8,17],tracking:[0,2],leading:[0,4]};
const choices={headingFace:DATA.fonts.faces.map(f=>f.id),nameFace:DATA.fonts.faces.map(f=>f.id),roleCase:['upper','source'],align:['original','center'],edges:['soft','crisp']};
const faces=Object.fromEntries(DATA.fonts.faces.map(f=>[f.id,f]));
let settings={...DEFAULTS},selected=0,results=[],images={},timer;
const cache=new Map();
function canvas(w=240,h=160){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
function message(t){$('toast').textContent=t;$('toast').classList.remove('hidden');clearTimeout(timer);timer=setTimeout(()=>$('toast').classList.add('hidden'),5000);}
function download(name,url){const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();}
function downloadJSON(name,value){const u=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));download(name,u);setTimeout(()=>URL.revokeObjectURL(u),1000);}
function textMask(text,faceId,height,tracking,edges){
  const key=JSON.stringify([text,faceId,height,tracking,edges]);if(cache.has(key))return cache.get(key);
  const f=faces[faceId],scale=height/f.cap_height,placed=[],missing=[],supplements=new Set();let x=0,top=0,bottom=0,right=0;
  for(const ch of text){const g=f.glyphs[ch];if(!g){missing.push(ch);continue;}placed.push([x,g]);top=Math.min(top,g.top);bottom=Math.max(bottom,g.top+g.height);right=Math.max(right,x+g.width);x+=g.advance+tracking;if(g.origin==='papyrus_supplement')supplements.add(ch);}
  const raw=canvas(Math.max(1,right),Math.max(1,bottom-top)),ctx=raw.getContext('2d'),pixels=ctx.createImageData(raw.width,raw.height);
  for(const [at,g] of placed)for(let y=0;y<g.height;y++)for(let xx=0;xx<g.width;xx++){const a=Number(g.rows[y][xx])*85;if(!a)continue;const i=((g.top-top+y)*raw.width+at+xx)*4;pixels.data[i]=pixels.data[i+1]=pixels.data[i+2]=255;pixels.data[i+3]=Math.max(a,pixels.data[i+3]);}
  ctx.putImageData(pixels,0,0);const c=canvas(Math.max(1,Math.round(raw.width*scale)),Math.max(1,Math.round(raw.height*scale))),cx=c.getContext('2d');cx.imageSmoothingEnabled=edges==='soft';cx.drawImage(raw,0,0,c.width,c.height);
  const quant=cx.getImageData(0,0,c.width,c.height);for(let i=3;i<quant.data.length;i+=4)quant.data[i]=edges==='crisp'?(quant.data[i]>=85?255:0):Math.round(quant.data[i]/85)*85;cx.putImageData(quant,0,0);
  const result={canvas:c,top:Math.round(top*scale),missing,supplements:[...supplements]};cache.set(key,result);if(cache.size>2048)cache.delete(cache.keys().next().value);return result;
}
function paint(ctx,mask,x,y,colour){const copy=canvas(mask.width,mask.height),c=copy.getContext('2d');c.drawImage(mask,0,0);c.globalCompositeOperation='source-in';c.fillStyle=colour;c.fillRect(0,0,copy.width,copy.height);ctx.drawImage(copy,x,y);}
function render(page,s){
  const c=canvas(),ctx=c.getContext('2d');ctx.fillStyle='#000';ctx.fillRect(0,0,240,160);
  const lines=[],missing=[],supplements=new Set(),occupied=new Set();let overlap=0;
  page.lines.forEach((line,index)=>{
    const title=line.command_x<0,role=line.kind==='heading'&&!title,heading=title||role;
    const face=heading?s.headingFace:s.nameFace,height=title?s.titleHeight:role?s.headingHeight:s.nameHeight;
    const text=role&&s.roleCase==='upper'?line.text.toUpperCase():line.text;
    const m=textMask(text,face,height,s.tracking,s.edges),x=s.align==='center'||title?16+Math.floor((208-m.canvas.width)/2):16+line.x;
    const y=16+line.y+12+m.top+index*s.leading,bounds=[x,y,x+m.canvas.width,y+m.canvas.height];
    paint(ctx,m.canvas,x,y,role?s.headingColour:s.nameColour);
    const pixels=m.canvas.getContext('2d').getImageData(0,0,m.canvas.width,m.canvas.height).data;
    for(let yy=0;yy<m.canvas.height;yy++)for(let xx=0;xx<m.canvas.width;xx++){if(!pixels[(yy*m.canvas.width+xx)*4+3])continue;const key=`${x+xx},${y+yy}`;if(occupied.has(key))overlap++;occupied.add(key);}
    missing.push(...m.missing);m.supplements.forEach(ch=>supplements.add(ch));
    lines.push({text,face,height,bounds,source_offset:line.source_offset,fit:bounds[0]>=16&&bounds[1]>=16&&bounds[2]<=224&&bounds[3]<=152});
  });
  if(s.guides){ctx.strokeStyle='#bc9b60';ctx.strokeRect(15.5,15.5,209,137);}
  return {canvas:c,lines,missing,supplements:[...supplements],overlap,fit:lines.length>0&&lines.every(l=>l.fit)&&missing.length===0&&overlap===0};
}
function sync(){for(const k of Object.keys(DEFAULTS))if(k==='guides')$(k).checked=settings[k];else $(k).value=settings[k];for(const k of ['titleHeight','tracking','leading'])$(k==='titleHeight'?'titleValue':k+'Value').textContent=settings[k]+' px';}
function select(index){selected=(index+DATA.pages.length)%DATA.pages.length;renderAll();}
function renderAll(){
  sync();results=DATA.pages.map(p=>render(p,settings));const page=DATA.pages[selected],r=results[selected];$('pageName').textContent=page.label;$('pageInfo').textContent=`${page.id} · ${selected+1} of 31 · ${page.lines.length} lines`;
  $('original').getContext('2d').drawImage(images[page.id],0,0);for(const id of ['preview','native'])$(id).getContext('2d').drawImage(r.canvas,0,0);
  $('fit').className=r.fit?'ok':'warn';$('fit').textContent=r.fit?'Fits the original text area.':`Needs adjustment: ${r.lines.some(l=>!l.fit)?'text exceeds the original area. ':''}${r.overlap?'lines touch or overlap. ':''}${r.missing.length?'missing glyphs: '+r.missing.join(' '):''}`;
  $('supplements').textContent=r.supplements.length?'Shiren draft supplements on this card: '+r.supplements.join(' ')+'.':page.lines.some(l=>l.kind==='copyright')?'Copyright marks use the original ROM’s symbol in every candidate.':'Preserves original staff names and role wording.';
  $('transcript').textContent=page.lines.map(l=>l.text).join('\n');$('png').disabled=$('png3').disabled=!r.fit;
  const count=results.filter(r=>r.fit).length;$('galleryStatus').textContent=`${count}/31 fit`;$('sheet').disabled=count!==31;
  const gallery=$('gallery');gallery.replaceChildren();DATA.pages.forEach((p,i)=>{const b=document.createElement('button');b.className='card'+(i===selected?' selected':'');b.append(results[i].canvas);const label=document.createElement('span');label.className='card-title';label.textContent=p.id+' · '+p.label;const detail=document.createElement('span');detail.className='card-detail'+(results[i].fit?'':' warn');detail.textContent=results[i].fit?'Fits':'Adjust layout';b.append(label,detail);b.onclick=()=>select(i);gallery.append(b);});
}
function settingsDocument(){return {schema:1,kind:'torneko3-credits-audition',source_rom_sha256:DATA.source_sha256,font_asset_sha256:DATA.font_asset_sha256,renderer_sha256:DATA.renderer_sha256,settings:{...settings,guides:false},cards:results.map((r,i)=>({id:DATA.pages[i].id,fit:r.fit,lines:r.lines,supplements:r.supplements})),scope:'Credit typography audition only. Original text preserved; no ROM insertion.'};}
function applyDocument(doc){
  if(doc.schema!==1||doc.kind!=='torneko3-credits-audition'||doc.source_rom_sha256!==DATA.source_sha256||doc.font_asset_sha256!==DATA.font_asset_sha256||doc.renderer_sha256!==DATA.renderer_sha256)throw Error('These settings belong to a different credits source, font or renderer revision.');
  const s=doc.settings;if(!s||typeof s!=='object'||Array.isArray(s))throw Error('Missing settings.');
  for(const [k,[a,b]] of Object.entries(ranges))if(!Number.isInteger(s[k])||s[k]<a||s[k]>b)throw Error('Invalid '+k+'.');
  for(const [k,options] of Object.entries(choices))if(!options.includes(s[k]))throw Error('Invalid '+k+'.');
  for(const k of ['headingColour','nameColour'])if(typeof s[k]!=='string'||!/^#[0-9a-f]{6}$/i.test(s[k]))throw Error('Invalid colour.');
  if(typeof s.guides!=='boolean')throw Error('Invalid guides.');
  settings=Object.fromEntries(Object.keys(DEFAULTS).map(k=>[k,s[k]]));renderAll();
}
function cardPNG(scale=1){const r=render(DATA.pages[selected],{...settings,guides:false});if(!r.fit)throw Error('Adjust the layout before exporting.');const c=canvas(240*scale,160*scale),cx=c.getContext('2d');cx.imageSmoothingEnabled=false;cx.drawImage(r.canvas,0,0,c.width,c.height);return c;}
function sheetCanvas(){const all=DATA.pages.map(p=>render(p,{...settings,guides:false}));if(all.some(r=>!r.fit))throw Error('Adjust the marked cards before exporting.');const c=canvas(2016,3076),cx=c.getContext('2d');cx.fillStyle='#172328';cx.fillRect(0,0,c.width,c.height);cx.fillStyle='#eff2ec';cx.font='26px monospace';cx.fillText('Torneko 3 · Credit lettering audition',20,40);cx.font='18px monospace';cx.fillText(faces[settings.headingFace].name+' / '+faces[settings.nameFace].name,20,75);cx.imageSmoothingEnabled=false;
  all.forEach((r,i)=>{const x=i%4*504+12,y=100+Math.floor(i/4)*372;cx.drawImage(r.canvas,x,y,480,320);cx.fillStyle='#d6e1dc';cx.font='16px monospace';cx.fillText(DATA.pages[i].id+' · '+DATA.pages[i].label,x,y+345,480);});return c;
}
function comparisonSheet(){
  const pages=[0,2,10,22,30],styles=['original','rounded','mixed','papyrus','shiren'];const c=canvas(2520,1940),cx=c.getContext('2d');cx.fillStyle='#172328';cx.fillRect(0,0,c.width,c.height);cx.fillStyle='#eff2ec';cx.font='26px monospace';cx.fillText('Torneko 3 · Credits font auditions · 2× game pixels',18,37);cx.font='18px monospace';cx.fillText('Original credit text. Font choices are drafts; dense cards and copyright included.',18,70);cx.imageSmoothingEnabled=false;
  styles.forEach((style,col)=>{const x=col*504+12;cx.fillStyle='#e0bb79';cx.font='20px monospace';cx.fillText(style==='original'?'Japanese-ROM original':labels[style],x,108);pages.forEach((id,row)=>{const y=128+row*360;const r=style==='original'?{canvas:images[DATA.pages[id].id],fit:true}:render(DATA.pages[id],{...DEFAULTS,...PRESETS[style]});cx.drawImage(r.canvas,x,y,480,320);cx.fillStyle=r.fit?'#a4b1b0':'#f3ae87';cx.font='17px monospace';cx.fillText(DATA.pages[id].id+(r.fit?'':' · ADJUST'),x,y+345);});});return c;
}
async function init(){
  for(const id of ['headingFace','nameFace'])for(const f of DATA.fonts.faces){const o=document.createElement('option');o.value=f.id;o.textContent=f.name;$(id).append(o);}
  await Promise.all(Object.entries(DATA.originals).map(([id,url])=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{images[id]=im;resolve();};im.onerror=()=>reject(Error('Cannot load '+id));im.src=url;})));
  for(const k of Object.keys(DEFAULTS))$(k).addEventListener('input',()=>{if(k==='guides')settings[k]=$(k).checked;else if(k in ranges){const v=Number($(k).value);if(!Number.isInteger(v))return;settings[k]=Math.max(ranges[k][0],Math.min(ranges[k][1],v));}else settings[k]=$(k).value;renderAll();});
  for(const b of document.querySelectorAll('[data-preset]'))b.onclick=()=>{settings={...DEFAULTS,...PRESETS[b.dataset.preset]};renderAll();};
  $('reset').onclick=()=>{settings={...DEFAULTS};select(0);};$('previous').onclick=()=>select(selected-1);$('next').onclick=()=>select(selected+1);
  $('png').onclick=()=>download(DATA.pages[selected].id+'-audition.png',cardPNG().toDataURL());$('png3').onclick=()=>download(DATA.pages[selected].id+'-audition-3x.png',cardPNG(3).toDataURL());$('sheet').onclick=()=>download('credits-audition-sheet.png',sheetCanvas().toDataURL());$('compare').onclick=()=>download('credits-comparison.png',comparisonSheet().toDataURL());
  $('save').onclick=()=>downloadJSON('torneko3-credits-audition.json',settingsDocument());$('load').onclick=()=>$('importFile').click();$('importFile').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>1000000)throw Error('Settings file is too large.');applyDocument(JSON.parse(await f.text()));message('Credit settings loaded.');}catch(err){message(err.message);}e.target.value='';};
  select(0);window.Credits={DATA,DEFAULTS,PRESETS,render,select,settingsDocument,applyDocument,cardPNG,sheetCanvas,comparisonSheet,get settings(){return settings;},get results(){return results;}};document.documentElement.dataset.ready='true';
  if(new URLSearchParams(location.search).has('verify'))smoke();
}
function smoke(){
  const checks=[],assert=(ok,label)=>{if(!ok)throw Error(label);checks.push(label);};
  assert(DATA.pages.length===31&&DATA.pages.reduce((n,p)=>n+p.lines.length,0)===140,'31 cards / 140 original references');
  for(const [name,p] of Object.entries(PRESETS)){const all=DATA.pages.map(page=>render(page,{...DEFAULTS,...p}));assert(all.every(r=>r.fit),name+': all 31 cards fit');}
  for(const s of [{...DEFAULTS,align:'center'},{...DEFAULTS,roleCase:'source'}])assert(DATA.pages.every(p=>render(p,s).fit),'alternate alignment/case fits');
  assert(!render(DATA.pages[10],{...DEFAULTS,nameHeight:16,tracking:2,leading:4}).fit,'dense overflow is reported');
  assert(!render({...DATA.pages[0],lines:[{...DATA.pages[0].lines[0],text:'龍'}]},DEFAULTS).fit,'missing glyph is reported');
  assert(render(DATA.pages[30],DEFAULTS).lines.every(l=>l.text.startsWith('©')),'copyright symbol preserved');
  const collision={...DATA.pages[0],lines:[DATA.pages[0].lines[0],DATA.pages[0].lines[0]]};assert(render(collision,DEFAULTS).overlap>0,'overlapping lines are reported');
  const exported=settingsDocument();exported.settings.nameFace='small';exported.settings.nameHeight=8;applyDocument(exported);assert(settings.nameFace==='small'&&settings.nameHeight===8,'settings roundtrip');
  for(const changed of [{settings:{...exported.settings,nameHeight:999}},{font_asset_sha256:'wrong'},{renderer_sha256:'wrong'},{source_rom_sha256:'wrong'},{settings:{...exported.settings,headingColour:'oops'}}]){let rejected=false;try{applyDocument({...exported,...changed});}catch(_){rejected=true;}assert(rejected,'invalid settings rejected: '+Object.keys(changed).join(','));}
  $('next').click();assert(selected===1,'next-card button');$('previous').click();assert(selected===0,'previous-card button');
  document.querySelector('[data-preset="papyrus"]').click();assert(settings.headingFace==='papyrus-condensed','preset control');
  $('nameHeight').value=16;$('nameHeight').dispatchEvent(new Event('input'));assert(settings.nameHeight===16&&results.some(r=>!r.fit),'size control and global overflow warning');
  $('reset').click();assert(results.every(r=>r.fit)&&settings.headingFace==='rounded','reset restores Rounded draft');
  assert(cardPNG(1).width===240&&cardPNG(3).width===720,'native and enlarged PNG dimensions');
  settings.guides=true;renderAll();const clean=cardPNG().toDataURL();settings.guides=false;renderAll();assert(clean===cardPNG().toDataURL(),'guides excluded from PNG exports');
  const report={status:'passed',checks,cards:results.map((r,i)=>({id:DATA.pages[i].id,fit:r.fit,lines:r.lines,supplements:r.supplements})),settings:settingsDocument(),pngs:{'credits-audition-rounded.png':sheetCanvas().toDataURL(),'credits-comparison.png':comparisonSheet().toDataURL(),'credits-audition-native.png':cardPNG().toDataURL()}};
  const pre=document.createElement('pre');pre.id='verification-result';pre.textContent=JSON.stringify(report);document.body.replaceChildren(pre);
}
init().catch(e=>{document.documentElement.dataset.error=e.message;message('Cannot finish audition: '+e.message);if(new URLSearchParams(location.search).has('verify')){const pre=document.createElement('pre');pre.id='verification-result';pre.textContent=JSON.stringify({status:'failed',error:e.stack});document.body.replaceChildren(pre);}});
