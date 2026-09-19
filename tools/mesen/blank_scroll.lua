-- Torneko 3 English: blank-scroll playtest helper for Mesen 2.
-- 1. Make a separate test save state. Put expendable bread or a scroll FIRST
--    in your carried inventory. Close the menus and stand in the dungeon.
-- 2. Load/run this file in Mesen's Script Window; resume emulation.
-- 3. Press F8 (Fn+F8 if needed). The FIRST ITEM IS REPLACED, once per run.
-- 4. Open Items and read the Blank scroll. Reload your test state to undo.
--    To get another, reload the state and restart this script.
-- No ROM/patch/save-file writes. Saving in-game can persist the replaced item.
-- Learned-scroll flags are READ ONLY: unlearned names still fail normally.
-- API: https://github.com/SourMesen/Mesen2/blob/master/UI/Debugger/Documentation/LuaDocumentation.json
-- Existing documented RAM (docs/MEMORY_MAP.md, Item-reader investigation and
-- Blank-scroll English inscription compatibility): first pointer 0200C640;
-- verified first record [0200A480,0200A498), 24 bytes, flags+0, inscription+4..11,
-- item ID+0E. Write only that known record; refuse other pointer layouts.
-- Canonical blank item bytes are the existing verify_items.install_item fixture:
-- flags=81800000, ID=198, remaining fields zero. No new RAM is allocated.
-- Learned bitset [02002549,02002551), bit index=item ID-190; read only.

local GIVE_KEY = "F8" -- Change if this conflicts with your Mesen shortcuts.
local MEM = assert(emu.memType.gbaDebug, "This script requires Mesen 2 GBA support")
local function read(a) return emu.read(a, MEM, false) end
local function read32(a) return emu.read32(a, MEM, false) end
local function tell(text)
    emu.log(text)
    emu.displayMessage("Blank scroll test", text)
end
local expected = "AGB-TORNEKO3BD3J"
for i = 1, #expected do
    assert(read(0x080000A0 + i - 1) == expected:byte(i), "Load Torneko 3 Advance (JP-based English ROM) first")
end
local given, held = false, false
local function give()
    if read32(0x0200000C) == 0 then tell("Load an active adventure first."); return end
    local at = read32(0x0200C640)
    if at ~= 0x0200A480 then
        tell("Unverified first-item pointer; nothing changed. Open/close Items and retry. If it persists, send a state.")
        return
    end
    local flags = read32(at)
    local id = emu.read16(at + 14, MEM, false)
    -- Restrict replacement to ordinary scrolls and bread, never equipped gear,
    -- pots, bundled projectiles or other records with ownership dependencies.
    if flags == 0 or not ((id >= 190 and id <= 246) or (id >= 304 and id <= 309)) then
        tell("Nothing changed: put expendable bread or a scroll FIRST, then close Items and press " .. GIVE_KEY .. ".")
        return
    end
    local profile = read32(0x02034DD8)
    if profile ~= 0 then tell("Close all menus before pressing " .. GIVE_KEY .. "."); return end
    for offset = 0, 23 do emu.write(at + offset, 0, MEM) end
    emu.write32(at, 0x81800000, MEM)
    emu.write16(at + 14, 198, MEM)
    given = true
    tell("Replaced first item (ID " .. id .. ") with Blank scroll. Open Items to read it. Learned flags unchanged.")
end
emu.addEventCallback(function()
    local pressed = emu.isKeyPressed(GIVE_KEY)
    if pressed and not held and not given then give() end
    held = pressed
end, emu.eventType.endFrame)
tell("Ready: " .. GIVE_KEY .. " replaces your FIRST bread/scroll with Blank scroll. Use a test state.")
-- Exact accepted English spellings. Case is ignored; no 'scroll' suffix.
-- The following log is read-only and shows your current learned eligibility.
local spellings = {
    {192, "Bang", "Bang scroll"},
    {207, "Prayer", "Prayer scroll"},
    {191, "Peep", "Peep scroll"},
    {231, "LookBck", "Look-back scroll"},
    {241, "Blaze", "Blaze scroll"},
    {216, "Gale", "Gale scroll"},
    {196, "GrtRoom", "Great room scroll"},
    {211, "Binding", "Binding scroll"},
    {213, "IreLyre", "Lyre of Ire scroll"},
    {193, "MthSeal", "Mouthseal scroll"},
    {223, "Zing", "Zing scroll"},
    {243, "TimeBmb", "Time bomb scroll"},
    {214, "FoeSght", "Foe sight scroll"},
    {190, "Sheen", "Sheen scroll"},
    {200, "Buff", "Buff scroll"},
    {228, "Recklss", "Reckless scroll"},
    {245, "SandPlr", "Sand pillar scroll"},
    {204, "Sanctry", "Sanctuary scroll"},
    {244, "HolyCst", "Holy castle scroll"},
    {205, "ItemSgt", "Item sight scroll"},
    {237, "BigBlst", "Big blast scroll"},
    {232, "Chicken", "Chicken scroll"},
    {235, "MedRoom", "Medium room scroll"},
    {234, "PotFort", "Pot fortify scroll"},
    {215, "SafePas", "Safe Passage scroll"},
    {230, "Poof", "Poof scroll"},
    {199, "Oomphle", "Oomphle scroll"},
    {226, "DeepSlp", "Deep sleep scroll"},
    {219, "Rooting", "Rooting scroll"},
    {227, "PowerUp", "Power-up scroll"},
    {206, "Bread", "Bread scroll"},
    {220, "Pulling", "Pulling scroll"},
    {242, "Freeze", "Freeze scroll"},
    {203, "NoPick", "No-pickup scroll"},
    {238, "Dud", "Dud scroll"},
    {236, "MultiHl", "Multiheal scroll"},
    {221, "Transfm", "Transform scroll"},
    {225, "MonHast", "Monster haste scroll"},
    {217, "MonBind", "Monster bind scroll"},
    {239, "Drought", "Drought scroll"},
    {229, "Fuddle", "Fuddle scroll"},
    {201, "Plating", "Plating scroll"},
    {197, "Monster", "Monster scroll"},
    {194, "Evac", "Evac scroll"},
    {218, "Kasap", "Kasap scroll"},
    {210, "Glow", "Glow scroll"},
    {195, "Trap", "Trap scroll"},
    {233, "TrapClr", "Trap erase scroll"},
    {240, "TrapAct", "Trap trigger scroll"},
}
for _, row in ipairs(spellings) do
    local bit = row[1] - 190
    local learned = math.floor(read(0x02002549 + math.floor(bit / 8)) / 2^(bit % 8)) % 2 == 1
    emu.log(string.format("%-7s -> %-26s [%s]", row[2], row[3], learned and "learned" or "not learned"))
end
