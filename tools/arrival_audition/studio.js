'use strict';
const $=id=>document.getElementById(id);
const DEFAULTS={face:'shiren',presentation:'arrival',height:17,tracking:0,wrap:'auto',titleY:27,colour:'#fff7e5',outline:0,shadow:1,edges:'crisp',floorStyle:'matching',floor:1,floorHeight:22,floorAlign:'center',floorY:100,background:'black',dim:70,guides:false};
const PRESETS={shiren:{face:'shiren',height:17,tracking:0,titleY:27,outline:0,shadow:1,edges:'crisp'},papyrus:{face:'papyrus-condensed',height:18,tracking:0,titleY:14,outline:0,shadow:1,edges:'soft'},rounded:{face:'rounded',height:17,tracking:0,titleY:27,outline:0,shadow:1,edges:'soft'}};
let settings={...DEFAULTS},overrides={},selected=0,images={},results=[],timer;
const maskCache=new Map();
const faces=Object.fromEntries(DATA.fonts.faces.map(f=>[f.id,f]));
const numberFields=['height','tracking','titleY','outline','shadow','floor','floorHeight','floorY','dim'];
const selectFields=['face','presentation','wrap','edges','floorStyle','floorAlign','background'];
const ranges={height:[12,28],tracking:[0,3],titleY:[8,56],outline:[0,2],shadow:[0,2],floor:[1,99],floorHeight:[12,30],floorY:[80,130],dim:[0,100]};
function canvas(w=240,h=160){const c=document.createElement('canvas');c.width=w;c.height=h;return c;}
function message(text){$('toast').textContent=text;$('toast').classList.remove('hidden');clearTimeout(timer);timer=setTimeout(()=>$('toast').classList.add('hidden'),4500);}
function rgb(hex){return [1,3,5].map(n=>parseInt(hex.slice(n,n+2),16));}
function download(name,url){const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();}
function downloadJSON(name,value){const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));download(name,url);setTimeout(()=>URL.revokeObjectURL(url),1000);}
function wording(card){return overrides[card.id]??card.english_name_reference;}

// Baseline-aligned bitmap composition; no browser fonts are used in the artwork.
function textMask(text,faceId,height,tracking,edges){
  const key=JSON.stringify([text,faceId,height,tracking,edges]);if(maskCache.has(key))return maskCache.get(key);
  const face=faces[faceId],scale=height/face.cap_height;
  let x=0,top=0,bottom=0;const placed=[],missing=[],supplements=new Set();
  for(const ch of text){const g=face.glyphs[ch];if(!g){missing.push(ch);continue;}placed.push([x,g]);if(g.height){top=Math.min(top,g.top);bottom=Math.max(bottom,g.top+g.height);}if(g.origin==='papyrus_supplement')supplements.add(ch);x+=g.advance+tracking;}
  const width=Math.max(1,Math.ceil(x-(text.length?tracking+1:0))),raw=canvas(width,Math.max(1,bottom-top)),ctx=raw.getContext('2d'),pixels=ctx.createImageData(raw.width,raw.height);
  for(const [at,g] of placed)for(let yy=0;yy<g.height;yy++)for(let xx=0;xx<g.width;xx++){const alpha=Number(g.rows[yy][xx])*85;if(!alpha)continue;const i=((g.top-top+yy)*raw.width+at+xx)*4;pixels.data[i]=255;pixels.data[i+1]=255;pixels.data[i+2]=255;pixels.data[i+3]=Math.max(pixels.data[i+3],alpha);}
  ctx.putImageData(pixels,0,0);const out=canvas(Math.max(1,Math.round(raw.width*scale)),Math.max(1,Math.round(raw.height*scale))),oc=out.getContext('2d');oc.imageSmoothingEnabled=edges==='soft';oc.drawImage(raw,0,0,out.width,out.height);
  const quant=oc.getImageData(0,0,out.width,out.height);for(let i=3;i<quant.data.length;i+=4)quant.data[i]=edges==='crisp'?(quant.data[i]>=85?255:0):Math.round(quant.data[i]/85)*85;oc.putImageData(quant,0,0);
  const result={canvas:out,missing,supplements:[...supplements]};maskCache.set(key,result);if(maskCache.size>2048)maskCache.delete(maskCache.keys().next().value);return result;
}
function linesFor(text,s){
  if(text.includes('\n'))return text.split('\n');
  const measure=t=>textMask(t,s.face,s.height,s.tracking,s.edges).canvas.width;
  const words=text.trim().split(/\s+/),limit=224-s.outline*2-s.shadow;
  if(s.wrap==='one'||words.length<2||(s.wrap==='auto'&&measure(text)<=limit))return [text];
  // A location/section separator becomes the line break when both parts fit.
  const parts=text.split(' - ');if(parts.length===2&&parts.every(p=>measure(p)<=limit))return parts;
  let best=null;for(let n=1;n<words.length;n++){const lines=[words.slice(0,n).join(' '),words.slice(n).join(' ')],widths=lines.map(measure),score=Math.max(...widths)*10+Math.abs(widths[0]-widths[1]);if(!best||score<best.score)best={lines,score};}
  return best.lines;
}
function paintText(ctx,mask,x,y,s){
  const colourCanvas=colour=>{const c=canvas(mask.width,mask.height),cx=c.getContext('2d');cx.drawImage(mask,0,0);cx.globalCompositeOperation='source-in';cx.fillStyle=colour;cx.fillRect(0,0,c.width,c.height);return c;};
  const dark=colourCanvas('#141919');if(s.shadow)ctx.drawImage(dark,x+s.shadow,y+s.shadow);
  if(s.outline)for(let dy=-s.outline;dy<=s.outline;dy++)for(let dx=-s.outline;dx<=s.outline;dx++)if(dx||dy)ctx.drawImage(dark,x+dx,y+dy);
  ctx.drawImage(colourCanvas(s.colour),x,y);
}
function background(ctx,s){ctx.fillStyle='#000';ctx.fillRect(0,0,240,160);if(s.background!=='black'){ctx.drawImage(images[s.background],0,0);ctx.fillStyle=`rgba(0,0,0,${s.dim/100})`;ctx.fillRect(0,0,240,160);}}
function originalFloor(ctx,card,number){
  if(card.sample_suffix==='none')return;let parts;
  if(card.sample_suffix==='puzzle')parts=number>=10?[[11,16],[Math.floor(number/10),19],[number%10,21]]:[[11,17],[number,20]];
  else parts=number>=10?[[Math.floor(number/10),16],[number%10,18],[10,20]]:[[number,17],[10,19]];
  for(const [glyph,x] of parts)ctx.drawImage(images['glyph'+glyph],x*8,96);
}
function inkBounds(c){const p=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let l=c.width,t=c.height,r=0,b=0;for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++)if(p[(y*c.width+x)*4+3]){l=Math.min(l,x);r=Math.max(r,x+1);t=Math.min(t,y);b=Math.max(b,y+1);}return r?[l,t,r,b]:null;}
function tileCount(layer){const d=layer.getContext('2d').getImageData(0,0,240,160).data,set=new Set(['0'.repeat(64)]);for(let ty=8;ty<80;ty+=8)for(let tx=8;tx<240;tx+=8){let key='';for(let y=0;y<8;y++)for(let x=0;x<8;x++){const i=((ty+y)*240+tx+x)*4;key+=d[i+3]?`${d[i]},${d[i+1]},${d[i+2]},${d[i+3]};`:'0';}set.add(key);}return set.size;}
function render(card,s,text=wording(card)){
  const out=canvas(),ctx=out.getContext('2d'),title=canvas(),tc=title.getContext('2d');background(ctx,s);
  const lines=linesFor(text,s),missing=new Set(),supplements=new Set();let y=s.titleY;const bounds=[];
  for(const line of lines){const m=textMask(line,s.face,s.height,s.tracking,s.edges);m.missing.forEach(x=>missing.add(x));m.supplements.forEach(x=>supplements.add(x));const x=Math.floor((240-m.canvas.width)/2);bounds.push([x-s.outline,y-s.outline,x+m.canvas.width+s.outline+s.shadow,y+m.canvas.height+s.outline+s.shadow]);paintText(tc,m.canvas,x,y,s);y+=m.canvas.height+4;}
  const titleFits=text.trim().length>0&&lines.length<=2&&bounds.every(b=>b[0]>=8&&b[2]<=232&&b[1]>=8&&b[3]<=80)&&!missing.size;
  ctx.drawImage(title,0,0);let floorBounds=null;
  if(s.presentation==='arrival'&&card.sample_suffix!=='none'){
    if(s.floorStyle==='original'){originalFloor(ctx,card,s.floor);floorBounds=[128,96,192,136];}
    else{const label=card.sample_suffix==='puzzle'?`Q${s.floor}`:`${s.floor} F`,m=textMask(label,s.face,s.floorHeight,s.tracking,s.edges);m.missing.forEach(x=>missing.add(x));m.supplements.forEach(x=>supplements.add(x));const center=s.floorAlign==='center'?120:160,x=Math.floor(center-m.canvas.width/2);paintText(ctx,m.canvas,x,s.floorY,s);floorBounds=[x-s.outline,s.floorY-s.outline,x+m.canvas.width+s.outline+s.shadow,s.floorY+m.canvas.height+s.outline+s.shadow];}
  }
  const floorFits=!floorBounds||(floorBounds[0]>=0&&floorBounds[2]<=240&&floorBounds[1]>=80&&floorBounds[3]<=160);
  if(s.guides){ctx.strokeStyle='#afcbab';ctx.setLineDash([2,2]);ctx.strokeRect(8.5,8.5,223,71);ctx.setLineDash([]);}
  return {canvas:out,title,lines,titleFits,floorFits,fit:titleFits&&floorFits&&!missing.size,missing:[...missing],supplements:[...supplements],bounds,floorBounds,titleTiles:tileCount(title)};
}
function drawOriginal(card,s){const ctx=$('original').getContext('2d');background(ctx,s);ctx.drawImage(images[card.id],0,0);if(s.presentation==='arrival')originalFloor(ctx,card,s.floor);}
function syncControls(){for(const k of [...numberFields,...selectFields,'colour'])$(k).value=settings[k];$('guides').checked=settings.guides;for(const k of ['height','tracking','titleY'])$(k+'Value').textContent=`· ${settings[k]} px`;$('dimValue').textContent=`· ${settings.dim}%`;}
function select(index){selected=(index+DATA.cards.length)%DATA.cards.length;const card=DATA.cards[selected];$('selectedName').textContent=card.english_name_reference;$('selectedJapanese').textContent=card.japanese_name_reference.replaceAll('\\u3000',' ');$('selectedIds').textContent=`${card.id} · selectors ${card.selectors.join(' / ')}`;$('wording').value=wording(card);renderAll();}
function renderAll(){
  syncControls();results=DATA.cards.map(card=>render(card,settings));const card=DATA.cards[selected],r=results[selected];for(const id of ['preview','native']){$(id).getContext('2d').clearRect(0,0,240,160);$(id).getContext('2d').drawImage(r.canvas,0,0);}drawOriginal(card,settings);$('faceLabel').textContent=faces[settings.face].name;
  $('fit').className=r.fit?'ok':'warn';$('fit').textContent=r.fit?`Fits the title area · ${r.lines.length} line${r.lines.length>1?'s':''} · ${r.titleTiles} tile patterns`:`Needs adjustment: ${!r.titleFits?'title exceeds its area, is blank, or has more than two lines. ':''}${!r.floorFits?'floor line exceeds the screen. ':''}${r.missing.length?'Unsupported: '+r.missing.join(' '):''}`;
  if(r.titleTiles>160)$('fit').textContent+=' · more than the current 160 title-tile slots';
  $('supplements').textContent=r.supplements.length?`Draft supplements in this card: ${r.supplements.join(' ')}. Their shapes need review beside the recovered letters.`:settings.face==='shiren'?'All visible letters are recovered source characters. Spacing is newly reconstructed.':'This candidate uses the installed comparison font throughout.';
  $('floorNote').textContent=card.sample_suffix==='none'?'Arena: no floor number in the original.':card.sample_suffix==='puzzle'?'Puzzle card: Q prefix follows the original convention.':'Floor lettering and position are part of this audition.';
  for(const id of ['png','png3'])$(id).disabled=!r.fit;
  const gallery=$('gallery');gallery.replaceChildren();DATA.cards.forEach((c,i)=>{const b=document.createElement('button');b.className='card'+(i===selected?' selected':'');b.type='button';b.append(results[i].canvas);const title=document.createElement('span');title.className='card-title';title.textContent=wording(c).replaceAll('\n',' / ');const meta=document.createElement('span');meta.className='card-detail'+(results[i].fit?'':' warn');meta.textContent=`${c.id} · ${results[i].fit?'fits':'adjust layout'}`;b.append(title,meta);b.onclick=()=>select(i);gallery.append(b);});
  const count=results.filter(r=>r.fit).length;$('galleryStatus').textContent=`${count}/36 fit · ${results.reduce((n,r)=>n+(r.supplements.length>0?1:0),0)} use draft supplements`;$('sheet').disabled=count!==36;renderAlphabet();
}
function renderAlphabet(){const container=$('alphabet');container.replaceChildren();for(const ch of 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789\'-.,:!?'){const g=faces[settings.face].glyphs[ch],el=document.createElement('div');el.className='glyph'+(g.origin==='papyrus_supplement'?' supplement':'');const c=canvas(48,54),cx=c.getContext('2d'),m=textMask(ch,settings.face,17,0,'crisp');paintText(cx,m.canvas,Math.floor((48-m.canvas.width)/2),Math.max(0,18+g.top+17),{colour:g.origin==='papyrus_supplement'?'#f2b862':'#ffffff',shadow:0,outline:0});const label=document.createElement('small');label.textContent=ch+' · '+(g.origin==='shiren_crop'?'source':g.origin==='papyrus_supplement'?'draft':'font');el.append(c,label);container.append(el);}}
function settingsDocument(){return {schema:1,kind:'torneko3-arrival-audition',source_rom_sha256:DATA.source_sha256,font_asset_sha256:DATA.font_asset_sha256,renderer_sha256:DATA.renderer_sha256,settings:{...settings,guides:false},wording_overrides:{...overrides},scope:'Artwork audition only. Main Japanese logo retained; no ROM patch.',cards:DATA.cards.map((c,i)=>({id:c.id,selectors:c.selectors,text:wording(c),rendered_lines:results[i].lines,fit:results[i].fit,title_tiles:results[i].titleTiles,supplements:results[i].supplements}))};}
function applyDocument(doc){
  if(doc.schema!==1||doc.kind!=='torneko3-arrival-audition'||doc.source_rom_sha256!==DATA.source_sha256||doc.font_asset_sha256!==DATA.font_asset_sha256||doc.renderer_sha256!==DATA.renderer_sha256)throw Error('This file belongs to a different audition source, font or renderer revision.');
  const s=doc.settings;if(!s||typeof s!=='object')throw Error('Missing settings.');
  for(const k of numberFields)if(!Number.isInteger(s[k])||s[k]<ranges[k][0]||s[k]>ranges[k][1])throw Error(`Invalid ${k}.`);
  for(const k of selectFields)if(![...$(k).options].some(o=>o.value===s[k]))throw Error(`Invalid ${k}.`);
  if(!/^#[0-9a-f]{6}$/i.test(s.colour)||typeof s.guides!=='boolean')throw Error('Invalid colour or guides.');
  const words=doc.wording_overrides;if(!words||typeof words!=='object'||Array.isArray(words))throw Error('Missing wording overrides.');
  for(const [key,value] of Object.entries(words))if(!DATA.cards.some(c=>c.id===key)||typeof value!=='string'||value.length>300)throw Error('Invalid card wording.');
  settings=Object.fromEntries(Object.keys(DEFAULTS).map(k=>[k,s[k]]));overrides={...words};select(selected);
}
function cardPNG(scale){const r=render(DATA.cards[selected],{...settings,guides:false});if(!r.fit)throw Error('Adjust the layout before exporting this card.');const c=canvas(240*scale,160*scale),cx=c.getContext('2d');cx.imageSmoothingEnabled=false;cx.drawImage(r.canvas,0,0,c.width,c.height);return c;}
function sheetCanvas(s=settings,force=false){const rendered=DATA.cards.map(c=>render(c,{...s,guides:false}));if(!force&&rendered.some(r=>!r.fit))throw Error('Adjust the marked layouts before exporting the full sheet.');const sheet=canvas(2048,96+9*404),ctx=sheet.getContext('2d');ctx.fillStyle='#192225';ctx.fillRect(0,0,sheet.width,sheet.height);ctx.fillStyle='#e9eee8';ctx.font='26px monospace';ctx.fillText('Torneko 3 · '+faces[s.face].name,24,38);ctx.font='19px monospace';ctx.fillStyle='#a4b1b0';ctx.fillText('English artwork audition · 36 original card identities · 2x view',24,71);ctx.imageSmoothingEnabled=false;rendered.forEach((r,i)=>{const x=i%4*512+16,y=96+Math.floor(i/4)*404;ctx.drawImage(r.canvas,x,y,480,320);ctx.fillStyle=r.fit?'#e9eee8':'#f3ae87';ctx.font='20px monospace';ctx.fillText(DATA.cards[i].id+(r.fit?'':' · ADJUST'),x,y+347);ctx.font='17px monospace';const label=wording(DATA.cards[i]).replaceAll('\n',' / ');ctx.fillStyle='#a4b1b0';ctx.fillText(label,x,y+374,480);});return sheet;}
function comparisonSheet(){const ids=[0,5,9,21],presets=['shiren','papyrus','rounded'],sheet=canvas(2048,96+presets.length*426),ctx=sheet.getContext('2d');ctx.fillStyle='#192225';ctx.fillRect(0,0,sheet.width,sheet.height);ctx.fillStyle='#e9eee8';ctx.font='26px monospace';ctx.fillText('Torneko 3 · First lettering auditions · 2x',24,40);ctx.font='19px monospace';ctx.fillText('Recovered Shiren / Papyrus Condensed / rounded comparison',24,74);ctx.imageSmoothingEnabled=false;presets.forEach((p,row)=>{const s={...DEFAULTS,...PRESETS[p]},y=96+row*426;ctx.fillStyle='#e0bb79';ctx.font='20px monospace';ctx.fillText(faces[s.face].name,16,y+23);ids.forEach((id,col)=>{const x=16+col*512,r=render(DATA.cards[id],s);ctx.drawImage(r.canvas,x,y+38,480,320);ctx.fillStyle=r.fit?'#a4b1b0':'#f3ae87';ctx.font='17px monospace';ctx.fillText(DATA.cards[id].english_name_reference+(r.fit?'':' · ADJUST'),x,y+387,480);});});return sheet;}

async function init(){
  for(const f of DATA.fonts.faces){const o=document.createElement('option');o.value=f.id;o.textContent=f.name;$('face').append(o);}
  await Promise.all(Object.entries(DATA.images).map(([id,url])=>new Promise((resolve,reject)=>{const im=new Image();im.onload=()=>{images[id]=im;resolve();};im.onerror=()=>reject(Error('Cannot decode '+id));im.src=url;})));
  for(const k of [...numberFields,...selectFields,'colour'])$(k).addEventListener('input',()=>{if(numberFields.includes(k)){const value=Number($(k).value);if(!Number.isInteger(value))return;settings[k]=Math.max(ranges[k][0],Math.min(ranges[k][1],value));}else settings[k]=$(k).value;renderAll();});
  $('guides').onchange=()=>{settings.guides=$('guides').checked;renderAll();};$('wording').oninput=()=>{overrides[DATA.cards[selected].id]=$('wording').value.slice(0,300);renderAll();};
  $('restoreText').onclick=()=>{delete overrides[DATA.cards[selected].id];select(selected);};$('previous').onclick=()=>select(selected-1);$('next').onclick=()=>select(selected+1);
  for(const b of document.querySelectorAll('[data-preset]'))b.onclick=()=>{settings={...settings,...PRESETS[b.dataset.preset]};renderAll();};
  $('reset').onclick=()=>{settings={...DEFAULTS};overrides={};select(0);};
  $('save').onclick=()=>downloadJSON('torneko3-arrival-audition.json',settingsDocument());$('load').onclick=()=>$('importFile').click();$('importFile').onchange=async e=>{try{const file=e.target.files[0];if(file.size>1000000)throw Error('Settings file is too large.');applyDocument(JSON.parse(await file.text()));message('Audition settings loaded.');}catch(error){message(error.message);}e.target.value='';};
  $('png').onclick=()=>download(DATA.cards[selected].id+'-audition.png',cardPNG(1).toDataURL());$('png3').onclick=()=>download(DATA.cards[selected].id+'-audition-3x.png',cardPNG(3).toDataURL());$('sheet').onclick=()=>download('torneko3-arrival-audition-sheet.png',sheetCanvas().toDataURL());
  select(0);window.Audition={render,settingsDocument,applyDocument,cardPNG,sheetCanvas,comparisonSheet,DATA,DEFAULTS,PRESETS,faces,get results(){return results;},get settings(){return settings;},select};
  document.documentElement.dataset.ready='true';
  if(new URLSearchParams(location.search).has('verify'))await smoke();
}
async function smoke(){
  const checks=[],assert=(ok,label)=>{if(!ok)throw Error(label);checks.push(label);};
  assert(results.length===36,'36 unique cards rendered');assert(DATA.cards.reduce((n,c)=>n+c.selectors.length,0)===64,'64 selectors retained');
  assert(results.every(r=>r.fit),'default Shiren set fits');
  for(const [name,p] of Object.entries(PRESETS))for(const floor of [1,9,10,99]){const all=DATA.cards.map(c=>render(c,{...DEFAULTS,...p,floor}));assert(all.every(r=>r.fit),`${name}: all cards fit floor ${floor}`);}
  const arena=DATA.cards.find(c=>c.sample_suffix==='none'),puzzle=DATA.cards.find(c=>c.sample_suffix==='puzzle');assert(!render(arena,DEFAULTS).floorBounds,'arena omits floor');assert(render(puzzle,{...DEFAULTS,floor:99}).supplements.includes('Q'),'puzzle Q supplement explicit');
  assert(!render(DATA.cards[0],{...DEFAULTS,wrap:'one'},'W'.repeat(90)).fit,'overflow is reported');assert(!render(DATA.cards[0],DEFAULTS,'Unsupported 龍').fit,'unsupported glyph is reported');
  assert(render(DATA.cards[0],DEFAULTS,'Mysterious\ncave').lines.length===2,'manual line break');
  assert(render(DATA.cards[5],DEFAULTS).lines[1]==='Foothills','section separator becomes a clean line break');
  for(const c of DATA.cards){const original=render(c,{...DEFAULTS,floorStyle:'original'}),title=render(c,{...DEFAULTS,presentation:'title'});assert(original.fit&&title.fit&&!title.floorBounds,`${c.id}: original-floor and title-only layouts`);}
  const exported=settingsDocument();exported.settings.background='cave';exported.settings.floor=99;exported.wording_overrides[DATA.cards[0].id]='Mysterious\ncave';applyDocument(exported);assert(settings.background==='cave'&&settings.floor===99&&wording(DATA.cards[0]).includes('\n'),'settings and wording roundtrip');
  const bad=JSON.parse(JSON.stringify(exported));bad.settings.floor=1000;let rejected=false;try{applyDocument(bad);}catch(_){rejected=true;}assert(rejected,'invalid import rejected');
  $('floor').value=10;$('floor').dispatchEvent(new Event('input'));assert(settings.floor===10,'floor input updates the preview');
  $('presentation').value='title';$('presentation').dispatchEvent(new Event('input'));assert(results.every(r=>!r.floorBounds),'title-only control removes floor lines');
  $('next').click();assert(selected===1,'gallery navigation advances selection');
  $('wording').value='Beckoning\ncavern';$('wording').dispatchEvent(new Event('input'));assert(results[1].lines.length===2&&overrides[DATA.cards[1].id].includes('\n'),'wording input preserves manual line breaks');
  $('restoreText').click();assert(!Object.hasOwn(overrides,DATA.cards[1].id),'restore name removes its override');
  document.querySelector('[data-preset="papyrus"]').click();assert(settings.face==='papyrus-condensed'&&settings.titleY===14,'preset button applies its typography and position');
  settings={...DEFAULTS};overrides={};select(0);assert(cardPNG(1).width===240&&cardPNG(3).width===720,'1x and 3x PNG sizes');
  const report={status:'passed',checks,default_cards:results.map((r,i)=>({id:DATA.cards[i].id,fit:r.fit,lines:r.lines,title_tiles:r.titleTiles,supplements:r.supplements})),settings:settingsDocument(),pngs:{'arrival-audition-shiren.png':sheetCanvas().toDataURL(),'arrival-audition-comparison.png':comparisonSheet().toDataURL(),'arrival-audition-native.png':cardPNG(1).toDataURL()}};
  const pre=document.createElement('pre');pre.id='verification-result';pre.textContent=JSON.stringify(report);document.body.replaceChildren(pre);
}
window.addEventListener('error',e=>{document.documentElement.dataset.error=e.message;});
init().catch(e=>{document.documentElement.dataset.error=e.message;message('Cannot finish audition: '+e.message);if(new URLSearchParams(location.search).has('verify')){const pre=document.createElement('pre');pre.id='verification-result';pre.textContent=JSON.stringify({status:'failed',error:e.stack});document.body.replaceChildren(pre);}});
