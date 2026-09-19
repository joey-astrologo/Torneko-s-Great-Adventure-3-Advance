-- Torneko 3 Advance / English: two Warp pots for Mesen 2.
-- Make a separate test state. The FIRST TWO inventory slots must be empty or
-- contain expendable bread/scrolls. Close all menus; press F8 (Fn+F8 on Mac).
-- Both slots become identified Warp pot[5], ONCE per script run.
-- Put one pot on the ground, walk away, then Push the carried pot.
-- Reload your original test state to undo. Stop the blank_scroll.lua helper
-- first: it also uses F8. No ROM/save-file writes; saving in-game persists items.
-- Layout/evidence: docs/MEMORY_MAP.md, "Mesen Warp-pot playtest helper".
local KEY = "F8"
local MEM = assert(emu.memType.gbaDebug, "Mesen 2 GBA support required")
local function read(a) return emu.read(a, MEM, false) end
local function read32(a) return emu.read32(a, MEM, false) end
local function tell(text)
    emu.log(text)
    emu.displayMessage("Warp pot test", text)
end
local expected = "AGB-TORNEKO3BD3J"
for i = 1, #expected do
    assert(read(0x080000A0+i-1)==expected:byte(i), "Load Torneko 3 Advance first")
end
local given, held = false, false
local function give()
    if read32(0x0200000C)==0 then tell("Load an active adventure first."); return end
    if read32(0x0200C640)~=0x0200A480 then
        tell("Unsupported inventory bank; nothing changed. Use Torneko's inventory."); return
    end
    if read32(0x02034DD8)~=0 then tell("Close all menus, then press "..KEY.." again."); return end
    local records = {0x0200A480, 0x0200A558}
    -- Validate BOTH before changing either. Never replace equipment or a pot.
    for slot, at in ipairs(records) do
        local flags = read32(at)
        local id = emu.read16(at+14, MEM, false)
        if flags~=0 and not ((id>=190 and id<=246) or (id>=304 and id<=309)) then
            tell("Nothing changed: inventory slot "..slot.." must be empty or expendable bread/scroll. Move those items to the top first.")
            return
        end
    end
    for _, at in ipairs(records) do
        for offset=0,23 do emu.write(at+offset, 0, MEM) end
        emu.write32(at, 0x81800000, MEM)
        emu.write16(at+14, 267, MEM)
        emu.write16(at+16, 5, MEM)
    end
    -- Existing per-type identification sentinel: only Warp pot is identified.
    emu.write16(0x0200C938, 0x0FFF, MEM)
    given = true
    tell("First two slots are now Warp pot[5]. Put one on the ground, walk away, then Push the other. Restore your test state to undo.")
end
emu.addEventCallback(function()
    local pressed = emu.isKeyPressed(KEY)
    if pressed and not held and not given then give() end
    held = pressed
end, emu.eventType.endFrame)
tell("Ready: "..KEY.." replaces FIRST TWO empty/bread/scroll slots with Warp pot[5]. Make a test state first.")
