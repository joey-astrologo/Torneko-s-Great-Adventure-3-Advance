"""Decode every scene-table background into source-linked review PNGs."""
from collections import defaultdict
from pathlib import Path
import struct

from PIL import Image, ImageDraw

from tools.build_first_label import ROOT, ORIGINAL_ROM, digest, load_manifest
from tools.extract_arrival_cards import save_json, label_font, rgb
from tools.translation_pipeline import check

OUT=ROOT/'build/graphics-review'
CACHE=(0xCB02F4,0xCB048C)
ENDING_SCENES=(9,56,83,31,101)


def unpack_map(rom,start,width,height):
    """Native 080672A2: paired 12-bit values, RLE and XOR against prior row."""
    at=start;planes=[]
    for layer in range(2):
        rows=[]
        for y in range(height):
            row=[]
            while len(row)<width:
                tag=rom[at];at+=1
                count=tag-191 if tag>=192 else tag-127 if tag>=128 else tag+1
                pairs=[]
                for _ in range(count if tag>=192 else 1 if tag>=128 else 0):
                    check(at+3<=len(rom),'Map packet leaves ROM')
                    value=int.from_bytes(rom[at:at+3],'little');at+=3
                    pairs.append((value&4095,value>>12))
                if tag<128:pairs=[(0,0)]*count
                elif tag<192:pairs*=count
                for pair in pairs:row.extend(pair)
                check(len(row)<=((width+1)//2)*2,'Map packet exceeds padded row width')
            if y:row=[value^rows[-1][x] for x,value in enumerate(row)]
            rows.append(row)
        planes.append(rows)
    return planes,at


def scene(rom,number):
    u32=lambda at:struct.unpack_from('<I',rom,at)[0]
    desc=u32(CACHE[0]+4*number)-0x8000000
    fields=struct.unpack_from('<9I',rom,desc)
    header,mapping=fields[0]-0x8000000,fields[1]-0x8000000
    h=struct.unpack_from('<6H3I',rom,header)
    check(h[0] in (0x0202,0x0303) and 1<=h[1]+h[2]<=1024,'Unsupported scene graphic header')
    side=h[0]&255
    width,height=rom[mapping+4:mapping+6]
    check(0<width<=128 and 0<height<=94,'Unsupported scene map size')
    stream=u32(mapping+8)-0x8000000
    planes,end=unpack_map(rom,stream,width,height)
    pal=fields[3]-0x8000000;banks=fields[2]&65535
    check(0<banks<=15,'Invalid scene palette count')
    words=[]
    for bank in range(banks):words += [0]+list(struct.unpack_from('<15I',rom,pal+bank*60))
    words += [0]*(256-len(words))
    tiles_at,meta_at=h[6]-0x8000000,h[7]-0x8000000
    tiles=bytes(32)+rom[tiles_at:tiles_at+(h[1]-1)*32]
    definitions=[tuple([0]*(side*side))]+list(struct.iter_unpack('<'+str(side*side)+'H',rom[meta_at:meta_at+(h[3]-1)*side*side*2]))
    frames=[]
    if h[2]:
        table=h[8]-0x8000000
        for i in range(h[4]):
            period,source,indices=struct.unpack_from('<3I',rom,table+i*12)
            check(source and indices and period>0,'Invalid animated frame')
            frames.append(dict(frame=i,record=table+i*12,period=period,tiles=source-0x8000000,
                               tiles_end_exclusive=source-0x8000000+h[2]*32,
                               attributes=indices-0x8000000,attributes_end_exclusive=indices-0x8000000+h[2]*2))
        check(u32(table+h[4]*12+4)==0,'Missing animation table sentinel')
        tiles += rom[frames[0]['tiles']:frames[0]['tiles_end_exclusive']]
    check(len(tiles)==(h[1]+h[2])*32,'Scene tiles truncated')
    check(all((cell&1023)<len(definitions) for plane in planes for row in plane for cell in row[:width]),'Map metatile index leaves header count')
    check(all((cell&1023)<h[1]+h[2] and cell>>12<banks for mt in definitions for cell in mt),'Tile index/palette leaves recorded sources')
    row=dict(scene=number,descriptor=desc,header=header,map_header=mapping,format=f'{h[0]:04x}',
        map_size=[width,height],image_size=[rom[mapping]*8,rom[mapping+1]*8],metatile_side=side,
        palette=pal,palette_banks=banks,palette_words=words,tiles=tiles_at,static_tile_count=h[1],
        animated_tile_count=h[2],metatiles=meta_at,metatile_count=h[3],map_stream=stream,
        map_end_exclusive=end,animation_frames=frames,planes=planes,
        source_ranges=[dict(start=a,end_exclusive=b,purpose=purpose,sha256=digest(rom[a:b])) for a,b,purpose in
                       [(CACHE[0]+4*number,CACHE[0]+4*number+4,'scene table word'),
                        (desc,desc+36,'scene descriptor'),(header,header+24,'graphic header'),
                        (mapping,mapping+20,'map header'),(pal,pal+banks*60,'base RGB palettes'),
                        (tiles_at,tiles_at+(h[1]-1)*32,'stored static tiles; blank tile implicit'),
                        (meta_at,meta_at+(h[3]-1)*side*side*2,'stored metatiles; blank metatile implicit'),
                        (stream,end,'two-layer compressed map; excludes alignment padding')]],
        scope='Static background composition with first tile-animation frame and base palettes. Actors, objects, palette/time-of-day effects and camera are separate.')
    if frames:
        row['source_ranges'].append(dict(start=table,end_exclusive=table+(h[4]+1)*12,
            purpose='tile-animation records including sentinel',sha256=digest(rom[table:table+(h[4]+1)*12])))
        for frame in frames:
            for key in ('tiles','attributes'):
                a,b=frame[key],frame[key+'_end_exclusive']
                row['source_ranges'].append(dict(start=a,end_exclusive=b,purpose=f"animation frame {frame['frame']} {key}",sha256=digest(rom[a:b])))
    return row,tiles,definitions


def tile_image(tiles,entry,colours):
    im=Image.new('RGBA',(8,8))
    for y in range(8):
        for x in range(8):
            px=7-x if entry&1024 else x;py=7-y if entry&2048 else y
            raw=tiles[(entry&1023)*32+py*4+px//2];index=(raw>>(4*(px%2)))&15
            if index:im.putpixel((x,y),(*colours[(entry>>12)*16+index],255))
    return im


def pictures(row,tiles,definitions):
    side=row['metatile_side'];colours=[rgb(w) for w in row['palette_words']]
    tile_cache={};metas=[]
    for entries in definitions:
        im=Image.new('RGBA',(side*8,side*8))
        for i,entry in enumerate(entries):
            if entry not in tile_cache:tile_cache[entry]=tile_image(tiles,entry,colours)
            im.paste(tile_cache[entry],(i%side*8,i//side*8))
        metas.append(im)
    width,height=row['map_size'];layers=[]
    for plane in row['planes']:
        im=Image.new('RGBA',(width*side*8,height*side*8))
        for y,line in enumerate(plane):
            for x,cell in enumerate(line[:width]):
                mt=metas[cell&1023]
                if cell&1024:mt=mt.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                if cell&2048:mt=mt.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                im.paste(mt,(x*side*8,y*side*8))
        layers.append(im)
    composite=Image.new('RGBA',layers[0].size,(0,0,0,255))
    for im in layers:composite.alpha_composite(im)
    return composite.convert('RGB').crop((0,0,*row['image_size'])),layers,metas


def sheet(images,path,title,cell=(320,260),columns=4):
    out=Image.new('RGB',(cell[0]*columns,70+cell[1]*((len(images)+columns-1)//columns)),'#192225')
    d=ImageDraw.Draw(out);d.text((16,15),title,font=label_font(22),fill='white')
    for i,(label,im) in enumerate(images):
        x,y=i%columns*cell[0],70+i//columns*cell[1]
        preview=im.copy();preview.thumbnail((cell[0]-12,cell[1]-35),Image.Resampling.NEAREST)
        out.paste(preview,(x+(cell[0]-preview.width)//2,y))
        d.text((x+6,y+cell[1]-28),label,font=label_font(13),fill='white')
    out.save(path)


def animation_review(rom,row,definitions):
    """All frames of all metatiles that refer to the animated tile slot."""
    nt=row['static_tile_count'];side=row['metatile_side'];colours=[rgb(w) for w in row['palette_words']]
    selected=[i for i,mt in enumerate(definitions) if any((v&1023)>=nt for v in mt)]
    reports=[];images=[]
    for frame in row['animation_frames']:
        tiles=bytes(32)+rom[row['tiles']:row['tiles']+(nt-1)*32]+rom[frame['tiles']:frame['tiles_end_exclusive']]
        attributes=struct.unpack_from('<'+str(row['animated_tile_count'])+'H',rom,frame['attributes'])
        atlas=Image.new('RGBA',(8*side*8,((len(selected)+7)//8)*side*8))
        for position,index in enumerate(selected):
            for k,entry in enumerate(definitions[index]):
                if (entry&1023)>=nt:entry=(entry&4095)|attributes[(entry&1023)-nt]
                check((entry&1023)<len(tiles)//32,'Animated index leaves recorded frame')
                im=tile_image(tiles,entry,colours)
                atlas.paste(im,(position%8*side*8+k%side*8,position//8*side*8+k//side*8))
        path=OUT/'animations'/f"scene-{row['scene']:03d}-frame-{frame['frame']:03d}.png"
        atlas.save(path)
        reports.append(dict(scene=row['scene'],frame=frame['frame'],metatile_indexes=selected,
                            png=str(path.relative_to(ROOT)),png_sha256=digest(path.read_bytes())))
        images.append((f"S{row['scene']:03d} frame {frame['frame']:03d}",atlas))
    return reports,images


def extract():
    rom=ORIGINAL_ROM.read_bytes();check(digest(rom)==load_manifest()['base_sha256'],'Unpinned Japanese source')
    (OUT/'scenes').mkdir(parents=True,exist_ok=True);(OUT/'animations').mkdir(exist_ok=True)
    entries=[];images=[];headers={};ending=[];animations=[];animation_images=[]
    for n in range((CACHE[1]-CACHE[0])//4):
        row,tiles,defs=scene(rom,n);im,layers,metas=pictures(row,tiles,defs)
        path=OUT/'scenes'/f'scene-{n:03d}.png';im.save(path)
        row.update(png=str(path.relative_to(ROOT)),png_sha256=digest(path.read_bytes()))
        for i,layer in enumerate(layers):layer.save(OUT/'scenes'/f'scene-{n:03d}-layer-{i}.png')
        entries.append(row);images.append((f"Scene {n:03d} / {im.width}x{im.height}",im))
        if n in ENDING_SCENES:ending.append((f'Scene {n:03d}',im))
        if row['header'] not in headers:
            atlas=Image.new('RGBA',(16*row['metatile_side']*8,((len(metas)+15)//16)*row['metatile_side']*8))
            for i,mt in enumerate(metas):atlas.paste(mt,(i%16*mt.width,i//16*mt.height))
            atlas.save(OUT/'scenes'/f'metatiles-{n:03d}.png');headers[row['header']]=n
            if row['animation_frames']:
                records,frames=animation_review(rom,row,defs);animations.extend(records);animation_images.extend(frames)
    for start in range(0,len(images),24):sheet(images[start:start+24],OUT/f'scenes-page-{start//24+1}.png',f'Original scene backgrounds / {start:03d}-{min(start+23,101):03d}')
    sheet(ending,OUT/'ending-backgrounds.png','Backgrounds referenced around the credits',cell=(480,370),columns=3)
    for start in range(0,len(animation_images),32):
        sheet(animation_images[start:start+32],OUT/f'animations-page-{start//32+1}.png',
              f'All animated metatile frames / {start:03d}-{min(start+31,len(animations)-1):03d}',cell=(240,225),columns=4)
    report=dict(source_rom=str(ORIGINAL_ROM.relative_to(ROOT)),source_sha256=digest(rom),output_rom=None,
        generator_sha256=digest(Path(__file__).read_bytes()),entries=entries,scenes=len(entries),
        unique_graphics_headers=len(headers),animations=animations,scene_table=dict(start=CACHE[0],end_exclusive=CACHE[1]),
        scope='Complete 102-entry scene background table, static composed source art. Decoding requires separate native verification. No ROM writes or insertion-space approval. Not a complete inventory of object/sprite art or all graphics loaders.')
    save_json(OUT/'scene-manifest.json',report)
    print('Decoded',len(entries),'scene backgrounds and',len(headers),'metatile atlases',flush=True)


if __name__=='__main__':extract()
