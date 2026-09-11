// Apply the title-menu findings documented in docs/FIRST_LABEL.md.
// Run after InspectThumbFunctions.java on the verified Japanese ROM.
// @category Torneko

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

public class AnnotateTitleText extends GhidraScript {
    @Override
    protected void run() throws Exception {
        if (!"ee36c7a4cc06bf050db0b872bebb03d9".equals(currentProgram.getExecutableMD5())) {
            throw new IllegalStateException("These addresses require the verified Japanese ROM");
        }
        long[] entries = {0x08084a10L, 0x0808c72cL, 0x0808cba0L, 0x0808c66cL, 0x0808bc4cL};
        String[] names = {"TitleMenuRun", "ReadEncodedTextCharacter", "DrawEncodedText",
                          "LookupFontGlyph", "DrawFontGlyph"};
        for (int i = 0; i < entries.length; i++) {
            Function function = getFunctionAt(toAddr(entries[i]));
            if (function == null) {
                throw new IllegalStateException("Disassemble the function first: " + toAddr(entries[i]));
            }
            function.setName(names[i], SourceType.USER_DEFINED);
        }
        createLabel(toAddr(0x08c78280L), "TitleMenuTextPointers", true);
        createLabel(toAddr(0x08c782d8L), "TitleMenuBeginLabel", true);
        createLabel(toAddr(0x08c93b4cL), "MenuFontGlyphDescriptors", true);
        createLabel(toAddr(0x08ca2674L), "SingleByteGlyphCodeMap", true);
        createLabel(toAddr(0x020398f8L), "ActiveFontIndex", true);
        setPlateComment(toAddr(0x08c782d8L),
            "Verified title label: はじめから (CP932), NUL terminated, 12-byte allocation. " +
            "Pointer at 0x08c78280. The independent Begin proof patches this string only.");
        setPlateComment(toAddr(0x0808c72cL),
            "r0: text cursor; r1: output code address. Returns advanced cursor in r0. " +
            "Combines lead bytes 0x80..0x9f or 0xe0..0xfe with the following byte; " +
            "otherwise emits a single-byte code. Verified via read watchpoint at 0x0808c732.");
        setPlateComment(toAddr(0x08c93b4cL),
            "Font 0 table observed in the title menu. 12-byte records: +0 bitmap pointer, " +
            "+4 u16 character code, +6 s16 horizontal advance. Other fields need further analysis.");
        println("TORNEKO_TITLE_ANNOTATIONS_OK");
    }
}
