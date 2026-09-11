"""Build Latin-font specimens, measured English scene captures, and a local review page."""

import argparse
import base64
from collections import Counter
import html
import json
from pathlib import Path
import struct

import mgba.log
from mgba._pylib import ffi, lib
from PIL import Image, ImageChops, ImageDraw, ImageFont

from tools.build_first_label import ORIGINAL_ROM, ROOT, digest, load_manifest
from tools.build_expansion_probe import EXPANDED_SIZE
from tools.font_metrics import FONT_LAYOUTS, extract_fonts, measure_line
from tools.verify_expansion import Session
from tools.verify_first_label import require

OUTPUT = ROOT / "build/font-review"
SAMPLE_LINES = ["The quick brown fox jumps", "over the lazy dog. Il1 O0", "HP 15/15 - Gold: 9999"]
MENU_LINES = ["New game", "Settings"]
TEXT_PATCHES = [
    ("new_game", 0xC78280, 0xC782D8, MENU_LINES[0]),
    ("settings", 0xC78290, 0xC782A4, MENU_LINES[1]),
    ("message", 0x0858F4, 0xC78444, "\n".join(SAMPLE_LINES)),
    ("story", 0x91B6AC, 0x91BBB4, "\n".join("$c" + line for line in SAMPLE_LINES)),
]


def build_review_rom(original):
    require(digest(original) == load_manifest()["base_sha256"], "Expected verified Japanese original")
    result = bytearray(original)
    result.extend(b"\xFF" * (EXPANDED_SIZE - len(original)))
    cursor, patches = len(original), []
    for name, pointer, source, text in TEXT_PATCHES:
        require(struct.unpack_from("<I", original, pointer)[0] == 0x08000000 + source,
                "Unexpected review text pointer")
        raw = text.encode("ascii") + b"\0"
        cursor = (cursor + 3) & ~3
        require(cursor + len(raw) <= EXPANDED_SIZE, "Review text exceeds ROM capacity")
        result[cursor:cursor + len(raw)] = raw
        struct.pack_into("<I", result, pointer, 0x08000000 + cursor)
        patches.append({"name": name, "pointer_offset": f"0x{pointer:08X}",
                        "source_offset": f"0x{source:08X}", "destination_offset": f"0x{cursor:08X}",
                        "text": text, "bytes": len(raw)})
        cursor += len(raw)
    restored = bytearray(result[:len(original)])
    for _, pointer, _, _ in TEXT_PATCHES:
        restored[pointer:pointer + 4] = original[pointer:pointer + 4]
    require(restored == original, "Unexpected changes in original ROM region")
    return bytes(result), patches


class FontTrace:
    """Force an existing font for the review scene, including width lookups."""

    def __init__(self, core, font):
        self.core, self.font = core, font
        self.cpu = ffi.cast("struct ARMCore*", core._core.cpu)
        self.glyphs, self.lookups, self.errors = [], [], []
        self.enabled = False
        self.callback = ffi.callback(
            "void(struct mDebugger*, enum mDebuggerEntryReason, struct mDebuggerEntryInfo*)", self.entered)
        self.debugger = ffi.new("struct mDebugger*")
        self.debugger.type, self.debugger.entered = lib.DEBUGGER_CUSTOM, self.callback
        lib.mDebuggerAttach(self.debugger, core._core)
        try:
            for address in (0x0808C66C, 0x0808BC78):
                point = ffi.new("struct mBreakpoint*")
                point.address, point.segment, point.type = address, -1, lib.BREAKPOINT_HARDWARE
                require(self.debugger.platform.setBreakpoint(self.debugger.platform, point) >= 0,
                        "Could not attach font breakpoint")
        except Exception:
            self.close()
            raise

    def entered(self, debugger, reason, info):
        try:
            if not self.enabled or reason != lib.DEBUGGER_ENTER_BREAKPOINT or info == ffi.NULL:
                return
            require(len(self.glyphs) < 2000, "Unexpectedly large font trace")
            if info.address == 0x0808C66C:
                self.core.memory.u32[0x020398F8] = self.font["id"]
                self.lookups.append(int(self.cpu.gprs[0]) & 0xFFFFFFFF)
            else:
                descriptor = int(self.cpu.gprs[0]) & 0xFFFFFFFF
                raw = bytes(self.core.memory[descriptor:descriptor + 12])
                bitmap, code, advance = struct.unpack_from("<IHh", raw)
                spacing = struct.unpack("<h", bytes(self.core.memory[0x020398DC:0x020398DE]))[0]
                window = int(self.cpu.gprs[4]) & 0xFFFFFFFF
                tile_x, tile_y, tiles_w = struct.unpack("<hhh", bytes(self.core.memory[window:window + 6]))
                self.glyphs.append({"code": code, "font": self.core.memory.u32[0x020398F8],
                                    "descriptor": f"0x{descriptor:08X}", "advance": advance,
                                    "spacing": spacing, "x": int(self.cpu.gprs[6]),
                                    "y": int(self.cpu.gprs[8]), "frame": self.core.frame_counter,
                                    "window_address": f"0x{window:08X}", "window_origin": [tile_x * 8, tile_y * 8],
                                    "window_width": tiles_w * 8})
        except Exception as error:
            self.errors.append(str(error))
        finally:
            debugger.state = lib.DEBUGGER_RUNNING

    def frames(self, count):
        for _ in range(count):
            lib.mDebuggerRunFrame(self.debugger)
        require(not self.errors, f"Font callback error: {self.errors[:5]}")

    def close(self):
        self.core._core.detachDebugger(self.core._core)


def verify_lines(glyphs, font, lines, scene):
    rows = []
    pos = 0
    for text in lines:
        row = glyphs[pos:pos + len(text)]
        pos += len(text)
        require([g["code"] for g in row] == list(text.encode("ascii")), f"Unexpected glyph sequence in {scene}")
        require(len({g["y"] for g in row}) == 1, f"Unexpected line break in {scene}")
        for previous, current in zip(row, row[1:]):
            require(current["x"] == previous["x"] + previous["advance"] + previous["spacing"],
                    "Runtime cursor advance differs from glyph metrics")
        for glyph in row:
            expected = font["glyphs"][chr(glyph["code"])]
            require(glyph["descriptor"] == expected["descriptor"] and glyph["advance"] == expected["advance"],
                    "Runtime glyph descriptor differs from extracted font")
            require(glyph["font"] == font["id"] and glyph["spacing"] == 0, "Unexpected font or extra spacing")
        measured = measure_line(font, text)
        if scene == "story":
            require(row[0]["x"] == (208 - measured["advance"]) // 2, "Unexpected story centering")
        available = row[0]["window_width"]
        require(measured["advance"] <= available and row[0]["x"] + measured["ink_right"] <= available,
                "Review sample exceeds available line width")
        rows.append({"text": text, "y": row[0]["y"], "x": row[0]["x"], **measured,
                     "available_width": available})
    require(pos == len(glyphs), "Unexpected extra glyphs in review scene")
    return rows


def capture_scene(data, font, scene, output, initial_save=None):
    with Session(data, output, initial_save) as session:
        session.frames(600)
        # Cross-check every font's ROM table, glyph count, and draw height after boot.
        for layout in FONT_LAYOUTS:
            index = layout["id"]
            require(session.core.memory.u32[0x020398EC + 4 * index] == layout["table"], "Font table mismatch")
            require(session.core.memory.u32[0x02039900 + 4 * index] == layout["count"], "Font count mismatch")
            require(session.core.memory.u32[0x02039910 + 4 * index] == layout["rows"], "Font height mismatch")
        trace = FontTrace(session.core, font)
        try:
            if scene == "menu":
                trace.enabled = True
                session.press("START", 240, trace)
            else:
                session.press("START", 240, trace)
                session.press("A", 120, trace)
                if scene == "message":
                    trace.enabled = True
                    session.press("A", 240, trace)
                else:
                    session.press("A", 120, trace)
                    trace.enabled = True
                    session.press("A", 1200, trace)
            lines = MENU_LINES if scene == "menu" else SAMPLE_LINES
            measured = verify_lines(trace.glyphs, font, lines, scene)
            image = session.capture(scene)
            # These text windows use background palette bank 15, not the scene's bank 0.
            raw_palette = bytes(session.core.memory[0x050001E0:0x05000200])
            palette = []
            for value, in struct.iter_unpack("<H", raw_palette):
                palette.append([(((value >> shift) & 31) << 3) | (((value >> shift) & 31) >> 2) for shift in (0, 5, 10)])
            if scene == "story":
                expected = Image.new("RGB", image.size, "black")
                for observed in trace.glyphs:
                    glyph_image = draw_glyph(font, chr(observed["code"]), palette)
                    origin_x, origin_y = observed["window_origin"]
                    expected.paste(glyph_image, (origin_x + observed["x"], origin_y + observed["y"]), glyph_image)
                require(ImageChops.difference(expected, image).getbbox() is None,
                        "Extracted glyph pixels do not reproduce the native story capture")
            report = {"scene": scene, "font": font["id"], "frame": session.core.frame_counter,
                      "rom_sha256": digest(data), "rgb_sha256": digest(image.tobytes()),
                      "font_selection": "Debugger forces existing font at glyph lookup only during the captured scene",
                      "bios": "mGBA built-in BIOS", "emulator": "mGBA 0.10.5", "boot_frames": 600,
                      "initial_save_sha256": digest(initial_save) if initial_save else None,
                      "inputs": session.frames_recorded, "lines": measured, "glyphs": trace.glyphs,
                      "text_palette_bank": 15, "text_palette": palette,
                      "extracted_pixels_match_native_story": scene == "story"}
            (output / "capture.json").write_text(json.dumps(report, indent=2) + "\n")
            return report
        finally:
            trace.close()


def draw_glyph(font, character, palette):
    glyph = font["glyphs"][character]
    image = Image.new("RGBA", (12, font["rows"]), (0, 0, 0, 0))
    for y, row in enumerate(glyph["pixels"]):
        for x, value in enumerate(row):
            if value:
                color = palette[value] if glyph["colored"] else (255, 255, 255)
                image.putpixel((x, y), (*color, 255))
    return image


def specimen(font, palette, output):
    atlas = Image.new("RGB", (16 * 36, 6 * 40), "#18202b")
    draw = ImageDraw.Draw(atlas)
    label_font = ImageFont.load_default()
    for index, character in enumerate(font["glyphs"]):
        x, y = (index % 16) * 36, (index // 16) * 40
        glyph = font["glyphs"][character]
        draw.rectangle((x, y, x + 35, y + 39), outline="#364153")
        image = draw_glyph(font, character, palette)
        atlas.paste(image, (x + 4, y + 4), image)
        draw.text((x + 3, y + 22), f"{ord(character):02X}:{glyph['advance']}", font=label_font, fill="#aab9cf")
    atlas.save(output / f"font-{font['id']}-atlas.png")
    return atlas


def write_review_page(fonts, captures, output):
    def png_data(path):
        return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()

    # The page embeds the extracted pixel arrays and captures, so it works offline.
    font_data = json.dumps(fonts, ensure_ascii=True)
    panels = []
    for font in fonts:
        i = font["id"]
        screenshots = "".join(f'<figure><figcaption>{scene.title()}</figcaption><img class="screen" src="{png_data(output / f"font-{i}" / scene / (scene + ".png"))}" width="240" height="160"></figure>'
                              for scene in ("menu", "message", "story"))
        panels.append(f'<section><h2>{html.escape(font["name"])}</h2><p>{font["rows"]} rendered rows · advances {min(g["advance"] for g in font["glyphs"].values())}–{max(g["advance"] for g in font["glyphs"].values())} px</p>'
                      f'<canvas id="sample-{i}" width="240" height="48"></canvas><p id="width-{i}" class="width"></p>{screenshots}'
                      f'<details><summary>All 95 printable ASCII glyphs · labels show hex code:advance</summary><img class="atlas" src="{png_data(output / f"font-{i}-atlas.png")}"></details></section>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torneko 3 — Original Latin Font Review</title><style>
*{box-sizing:border-box}body{margin:0;background:#101722;color:#e8eef7;font:16px/1.5 system-ui,sans-serif}main{max-width:1560px;margin:auto;padding:32px}h1{font-size:30px;margin:0 0 8px}h2{font-size:20px}p{max-width:920px;color:#bbcadc}label{display:inline-block;margin:10px 20px 12px 0}input,select{font:inherit;padding:8px;background:#182333;color:#fff;border:1px solid #536078;border-radius:5px}input{width:min(580px,85vw)}.panels{display:grid;grid-template-columns:repeat(3,minmax(250px,1fr));gap:20px}section{background:#182231;border:1px solid #37485f;border-radius:12px;padding:18px;overflow:auto}figure{margin:22px 0}figcaption{color:#c8d5e7;margin-bottom:8px}img,canvas{image-rendering:pixelated}canvas{background:#000;display:block}.screen{display:block}.atlas{width:576px;max-width:none}.width{min-height:48px}.note{padding:14px 18px;border-left:3px solid #74b8ee;background:#1b2b3d}.warn{color:#ffbb79}@media(max-width:940px){.panels{grid-template-columns:1fr}}summary{cursor:pointer;color:#9cceff}code{font-size:14px}
</style><main><h1>Original Latin font review</h1><p>Original Japanese ROM glyphs, with English review text rendered by mGBA. Font 0 was selected as the English baseline on 2026-09-09. Menu and dialogue captures below are real 240 × 160 game frames.</p>
<p class="note">Font 0 is the selected baseline for English text. Font 1 has identical Latin widths and top ten pixel rows, but drops the bottom two rows. Font 2 is decorative and substantially wider. Its multicolored appearance here comes from using the existing dialogue palette; its intended palette/context has not been established. Font variants 1 and 2 are forced for comparison in the emulator.</p>
<label>Try a line<br><input id="text" value="The quick brown fox jumps"></label>
<label>Width budget<br><select id="budget"><option value="76">Captured menu · 76 px from x=4</option><option value="208" selected>Story / message · 208 px</option></select></label>
<label>Display scale<br><select id="scale"><option value="1" selected>1× native pixels</option><option value="2">2× nearest neighbour</option><option value="3">3× nearest neighbour</option></select></label>
<p>Live previews use extracted ROM pixels and zero extra spacing. These budgets come from the captured windows; other layouts need their own measurements. Width checks cover literal ASCII; dollar signs and backticks need reader-specific control handling. A long sample is clipped by the preview canvas but its full width is reported.</p><div class="panels">PANELS</div>
<p>Each atlas cell shows a native-size glyph and its hexadecimal code:cursor advance. Decorative glyph colors use the captured story palette. The 10-row font is shown with its actual draw height, including the lost descenders. These are the three identified font variants, not proof that every graphical letter in the game belongs to one of them.</p>
<p>See <a href="../../docs/FONTS.md" style="color:#9cceff">docs/FONTS.md</a> for measurements, checks, and limitations.</p></main><script>
const fonts=FONTDATA;const palettes=PALETTES;
function update(){let text=document.querySelector('#text').value,budget=Number(document.querySelector('#budget').value),scale=Number(document.querySelector('#scale').value);
 document.querySelectorAll('.screen').forEach(e=>{e.style.width=240*scale+'px';e.style.height=160*scale+'px'});
 for(const f of fonts){const c=document.querySelector('#sample-'+f.id),ctx=c.getContext('2d');c.style.width=240*scale+'px';c.style.height=48*scale+'px';ctx.clearRect(0,0,240,48);ctx.fillStyle='#34536d';ctx.fillRect(budget,0,1,48);let advance=0,right=0,invalid=[];
 for(const ch of text){const g=f.glyphs[ch];if(!g||ch==='$'||ch.charCodeAt(0)===96){invalid.push(ch);continue}if(g.ink_bounds)right=Math.max(right,advance+g.ink_bounds[2]);for(let y=0;y<g.pixels.length;y++)for(let x=0;x<12;x++){let p=g.pixels[y][x];if(p){ctx.fillStyle=g.colored?'rgb('+palettes[f.id][p].join(',')+')':'white';ctx.fillRect(advance+x,8+y,1,1)}}advance+=g.advance;}
 const result=document.querySelector('#width-'+f.id);result.className='width'+((invalid.length||Math.max(advance,right)>budget)?' warn':'');result.textContent=invalid.length?'Unsupported or control-sensitive characters: '+JSON.stringify(invalid):advance+' px advance · '+right+' px ink edge · '+(Math.max(advance,right)<=budget?'fits':'OVER by '+(Math.max(advance,right)-budget)+' px')+' / '+budget+' px';}}
['text','budget','scale'].forEach(id=>document.getElementById(id).addEventListener('input',update));update();</script></html>'''
    palettes = [captures[f"{i}-story"]["text_palette"] for i in range(3)]
    page = page.replace("PANELS", "".join(panels)).replace("FONTDATA", font_data).replace("PALETTES", json.dumps(palettes))
    (output / "index.html").write_text(page)


def review(rom=ORIGINAL_ROM, output=OUTPUT):
    rom, output = Path(rom).resolve(), Path(output).resolve()
    original = rom.read_bytes()
    require(digest(original) == load_manifest()["base_sha256"], "Expected verified Japanese original")
    output.mkdir(parents=True, exist_ok=True)
    fonts = extract_fonts(original)
    data, patches = build_review_rom(original)
    (output / "torneko3-font-review.gba").write_bytes(data)
    save_path = ROOT / "build/text-inventory/relocation/original/creation/created.sav"
    require(save_path.exists(), "Run tools.verify_text_relocation first to create the reviewed story save")
    save = save_path.read_bytes()
    require(digest(save) == "95c6de6afe5d64e21de61b72c8ab3e1c67ca7649ad5a87d1c8b9db87c47feef0", "Unexpected story save fixture")
    mgba.log.silence()
    captures = {}
    for font in fonts:
        for scene in ("menu", "message", "story"):
            captures[f"{font['id']}-{scene}"] = capture_scene(
                data, font, scene, output / f"font-{font['id']}" / scene, save if scene == "story" else None)
            print(f"Font {font['id']} {scene}: metrics and glyph trace passed", flush=True)
        specimen(font, captures[f"{font['id']}-story"]["text_palette"], output)
    comparisons = []
    for text in MENU_LINES + SAMPLE_LINES + ["Start adventure", "Game settings", "Adventure log", "Torneko was a merchant."]:
        comparisons.append({"text": text, "fonts": [measure_line(f, text) for f in fonts]})
    clipped = [c for c, g in fonts[0]["glyphs"].items() if any(bytes.fromhex(g["stored_bitmap_hex"])[60:])]
    require(all(fonts[0]["glyphs"][c]["advance"] == fonts[1]["glyphs"][c]["advance"] and
                fonts[0]["glyphs"][c]["pixels"][:10] == fonts[1]["glyphs"][c]["pixels"] for c in fonts[0]["glyphs"]),
            "Small-font relationship differs from observed data")
    report = {"source_sha256": digest(original), "review_rom_sha256": digest(data), "patches": patches,
              "fonts": fonts, "sample_widths": comparisons, "font_1_loses_bottom_rows": clipped,
              "captured_scenes": 9, "runtime_checks_passed": True,
              "selection": "Existing font 0 selected by the owner as the English baseline on 2026-09-09"}
    (output / "metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    with (output / "advances.tsv").open("w") as file:
        file.write("ascii_hex\tcharacter\tfont_0_advance\tfont_1_advance\tfont_2_advance\n")
        for code in range(32, 127):
            char = chr(code)
            file.write(f"{code:02X}\t{char}\t" + "\t".join(str(f["glyphs"][char]["advance"]) for f in fonts) + "\n")
    write_review_page(fonts, captures, output)
    require(rom.read_bytes() == original, "Source ROM changed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rom", nargs="?", type=Path, default=ORIGINAL_ROM)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    review(args.rom, args.output)
