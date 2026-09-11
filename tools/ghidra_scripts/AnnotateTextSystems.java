// Apply the runtime-backed findings documented in docs/TEXT_SYSTEMS.md.
// Run after InspectThumbFunctions.java for the listed function entries.
// @category Torneko

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

public class AnnotateTextSystems extends GhidraScript {
    @Override
    protected void run() throws Exception {
        if (!"ee36c7a4cc06bf050db0b872bebb03d9".equals(currentProgram.getExecutableMD5())) {
            throw new IllegalStateException("These addresses require the verified Japanese ROM");
        }
        // Remove a provisional interior-entry probe if present in the research project.
        Function provisional = getFunctionAt(toAddr(0x0807d640L));
        if (provisional != null && provisional.getName().equals("text_probe_0807d640")) {
            removeFunction(provisional);
        }
        long[] entries = {0x0807d8ccL, 0x0807ada4L, 0x08061200L,
                          0x08061680L, 0x08061760L, 0x08064e28L, 0x0808cac4L};
        String[] names = {"FormatGameText", "RunMessageWindow", "ShowStoryText",
                          "PrepareStoryText", "UpdateStoryText", "RunEventCommands", "MeasureTextLine"};
        for (int i = 0; i < entries.length; i++) {
            Function function = getFunctionAt(toAddr(entries[i]));
            if (function == null) {
                throw new IllegalStateException("Disassemble first: " + toAddr(entries[i]));
            }
            function.setName(names[i], SourceType.USER_DEFINED);
        }
        setPlateComment(toAddr(0x0807d8ccL),
            "r0 source; r1 destination; r2 exclusive payload limit (NUL can be written at this address); " +
            "r3 low byte: stop at line break when nonzero. Expands dollar substitutions and copies " +
            "binary controls. Read source at 0x0807dbb2; output terminator at 0x0807dbca. " +
            "Observed payload limits: settings 256, message window 999, story 1023 bytes. " +
            "Relocated unchanged JP sources verified in all three paths; longer text needs bounds checks.");
        setPlateComment(toAddr(0x08064e28L),
            "Event interpreter. At 0x08064e42, LDMIA fetches two 32-bit words. " +
            "Opening story record at 0x0891b6a8 is opcode 0x27 followed by the absolute text pointer " +
            "at 0x0891b6ac. Relocating that operand to appended ROM preserves story output. " +
            "Do not assume every opcode's second word is a text pointer.");
        setPlateComment(toAddr(0x08061760L),
            "Story text state machine; decodes RAM prepared by FormatGameText. " +
            "Observed decoder BL sites 0x080618f4, 0x08061a9c and 0x08061ad2. " +
            "The $c branch measures following text and centers within 208 pixels. " +
            "Verified first two opening-story pages; not all dialogue contexts.");
        long[] data = {0x08c40100L, 0x08c78444L, 0x0891bbb4L, 0x0891b6a8L, 0x0818f16cL};
        String[] labels = {"SettingsMessageSpeedText", "NewLogExplanationText", "OpeningStoryFirstPage",
                           "OpeningStoryTextCommand", "CandidateItemNamePointers"};
        for (int i = 0; i < data.length; i++) {
            createLabel(toAddr(data[i]), labels[i], true);
        }
        setPlateComment(toAddr(0x0818f16cL),
            "Static candidate item-name table: 370 contiguous pointers through 0x0818f730. " +
            "Includes abbreviated/halfwidth Japanese and placeholders. No in-game relocation test yet.");
        println("TORNEKO_TEXT_SYSTEM_ANNOTATIONS_OK");
    }
}
