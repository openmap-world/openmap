"""Friends and guild with the controller view, and A on an icon with nothing to press (PadView.lua) in
Lua 5.1: python -P tools/offline-test/padfriends.py.

The controller view sets friends and guild up as it starts (Friends.lua's own behaviour is friends.py's),
whatever that setup does. The controller's A presses the icon under its cursor, or zooms into the zone
there: an icon marked as having nothing to press lets A through to the zoom. And an icon under the cursor
is left, then entered again, when its file hands its frames out again (PadViewForget). Against a stubbed
stitch and a stand-in for Blizzard's map.
(OPENMAP_PADVIEW: another PadView.lua to run these against.)
"""
import os
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"
PADVIEW = Path(os.environ.get("OPENMAP_PADVIEW") or ROOT / "Map" / "PadView.lua")

STUB = r"""
NOW, frames, events = 1000, {}, {}
GetTime = function() return NOW end
wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
GetPlayerFacing = function() return 0 end
Enum = { UIMapType = { Continent = 2, Zone = 3 } }

NOOP = { __index = function() return function() end end }
local function Region() return setmetatable({}, NOOP) end
local function Frame(parent)
	local f = { scripts = {}, hooks = {}, shown = true, parent = parent }
	function f:SetScript(k, fn) self.scripts[k] = fn end
	function f:GetScript(k) return self.scripts[k] end
	function f:HookScript(k, fn) self.hooks[k] = self.hooks[k] or {} table.insert(self.hooks[k], fn) end
	function f:Run(k, ...) for _, fn in ipairs(self.hooks[k] or {}) do fn(self, ...) end end
	function f:Show() if not self.shown then self.shown = true self:Run("OnShow") end end
	function f:Hide() if self.shown then self.shown = false self:Run("OnHide") end end
	function f:IsShown() return self.shown end
	function f:IsVisible() return self.shown end
	function f:GetParent() return self.parent end
	function f:GetFrameLevel() return 1 end
	function f:GetWidth() return 1000 end
	function f:GetHeight() return 600 end
	function f:GetRect() return 0, 0, 1000, 600 end
	function f:GetEffectiveScale() return 1 end
	function f:CreateTexture() return Region() end
	function f:CreateFontString() return Region() end
	frames[#frames + 1] = f
	return setmetatable(f, NOOP)
end
CreateFrame = function(_, _, parent) return Frame(parent) end
-- (as the game's: the hook after the function, each time)
hooksecurefunc = function(t, name, post)
	local fn = t[name]
	t[name] = function(...) local a, b, c = fn(...) post(...) return a, b, c end
end

-- Blizzard's map, on Elwynn Forest, and its controller cursor in the middle of the view
WorldMapFrame = Frame()
WorldMapFrame.shown = false
WorldMapFrame.ScrollContainer = Frame(WorldMapFrame)
WorldMapFrame.ScrollContainer.Child = Frame(WorldMapFrame.ScrollContainer)
WorldMapFrame.ScrollContainer.gamepadScrollSpeed = false   -- (the cursor away from the view's edges)
WorldMapFrame.GamepadTryPlaceWaypoint = false
function WorldMapFrame:GetCanvas() return self.ScrollContainer.Child end
function WorldMapFrame:GetMapID() return 1429 end
function WorldMapFrame:IsCanvasGamepadFocus() return true end
function WorldMapFrame:NavigateToGamepadCursor() end
function WorldMapFrame:NavigateToParentMap() end
SoftCursor = Frame()
function SoftCursor:GetRect() return 500, 300, 0, 0 end

C_Map = {
	GetBestMapForUnit = function() end,
	GetMapInfo = function(id) if id == 1429 then return { mapType = 3 } end end,   -- (Elwynn Forest: a zone)
}

S = setmetatable({ WORLD = 947 }, NOOP)
local isBuilt = false
function S.IsBuilt() return isBuilt end
function S.Build() isBuilt = true end
function S.Layout() return true end
function S.Size() return 2000, 1000 end
-- (Elwynn Forest round the middle of the world, where the view opens)
function S.Rect(id)
	if id == 947 then return 0, 1, 0, 1 end
	if id == 1429 then return 0.4, 0.6, 0.45, 0.65 end
end
function S.ChainAt() return { 947, 1429 } end
function S.ArtSize() return 400, 200 end
function S.Stitched() return 1 end
S.PinAt = function() return underCursor end   -- (the test's: the pin under the controller's cursor)
function S.GetPinSet() end

mod = { db = { padView = true }, enabled = false }
function mod.PadUI() return true end
function mod.Refresh() end
function mod.Unexplored() return "show" end
ns = { MapStitch = S, L = setmetatable({}, { __index = function(_, k) return k end }) }
function ns:GetModule() return mod end
function ns:Print() end
function ns.RegisterEvent(_, event, fn) events[event] = fn end
ns.Safe = { IsSecret = function() return false end,
	XY = function(p) if type(p) ~= "table" then return end if p.GetXY then return p:GetXY() end return p.x, p.y end,
	Call = function(fn, ...) local ok, v = pcall(fn, ...) if ok then return v end end }

function Tick() for _, f in ipairs(frames) do if f.shown and f.scripts.OnUpdate then f.scripts.OnUpdate(f, 0.1) end end end
-- the map opened and a frame drawn: the view built, its cursor seen
function Open()
	mod.StartPadView()
	WorldMapFrame:Show()
	Tick()
end
-- a pin as Stitch.lua's: only the fields its set's code gave it
function Pin()
	return { IsVisible = function() return true end, GetScript = function(self, k) return self.scripts and self.scripts[k] end,
		SetScript = function(self, k, fn) self.scripts = self.scripts or {} self.scripts[k] = fn end,
		LockHighlight = function() end, UnlockHighlight = function() end }
end
"""


class PadFriendsTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB)
        self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", PADVIEW.read_text(encoding="utf-8"))

    def ev(self, code):
        return self.lua.eval(code)

    # --- friends and guild (Friends.lua), set up with the view

    def test_friends_and_guild_are_set_up_with_the_view_before_the_map_ever_opens(self):
        self.lua.execute("""
            calls = {}
            function mod.SetupFriends(self, worldMap) calls[#calls + 1] = (self == mod and worldMap == WorldMapFrame) end
            mod.StartPadView()
        """)
        self.assertEqual(list(self.ev("calls").values()), [True])
        self.lua.execute("mod.StartPadView() WorldMapFrame:Show() Tick() WorldMapFrame:Hide() WorldMapFrame:Show()")
        self.assertEqual(self.ev("#calls"), 1)       # (once, however often the view starts or the map opens)

    def test_an_error_setting_friends_up_doesn_t_keep_the_view_from_opening(self):
        self.lua.execute('function mod.SetupFriends() error("friends broke") end Open()')
        self.assertTrue(self.ev("mod.PadViewOn()"))
        self.assertEqual(self.ev("select(3, mod.ViewNow())"), 1)     # (built, its view its own: the whole world)

    # --- A on a pin (the icon under the cursor pressed, or the zone under it zoomed into)

    def press_a_on(self, fields):
        """the whole world in view, a pin under the cursor, A, and the glide run: the zoom, and the pin's clicks"""
        self.lua.execute("""
            Open()
            mod.ShowNow(0.5, 0.5, 1)
            Tick()
            clicks = 0
            pin = Pin()
            %s
            underCursor = pin
            Tick()
            WorldMapFrame:NavigateToGamepadCursor()
            for _ = 1, 10 do Tick() end
        """ % fields)
        return self.ev("select(3, mod.ViewNow())"), self.ev("clicks")

    def test_a_beside_any_pin_zooms_into_the_zone_under_the_cursor(self):
        zoom, clicks = self.press_a_on("pin = nil")
        self.assertAlmostEqual(zoom, 5)              # (Elwynn Forest filling the view)

    def test_a_on_a_pin_with_a_click_presses_it(self):
        zoom, clicks = self.press_a_on("pin.OnClick = function() clicks = clicks + 1 end")
        self.assertEqual((zoom, clicks), (1, 1))

    def test_a_on_a_pin_not_marked_stays_on_it_as_before(self):
        zoom, clicks = self.press_a_on("")
        self.assertEqual((zoom, clicks), (1, 0))

    def test_a_on_a_pin_marked_as_having_nothing_to_press_zooms_in_under_it(self):
        zoom, clicks = self.press_a_on("pin.openmapNoPress = true")
        self.assertAlmostEqual(zoom, 5)

    def test_a_on_a_marked_pin_given_a_click_presses_it(self):
        zoom, clicks = self.press_a_on("pin.openmapNoPress = true pin.OnClick = function() clicks = clicks + 1 end")
        self.assertEqual((zoom, clicks), (1, 1))

    # --- a pin under the cursor as its set is redrawn (the same frames handed out again)

    def test_a_pin_under_the_cursor_is_left_and_entered_again_when_its_set_is_redrawn(self):
        self.lua.execute("""
            Open()
            seen = {}
            pin = Pin()
            pin:SetScript("OnEnter", function() seen[#seen + 1] = "enter1" end)
            pin:SetScript("OnLeave", function() seen[#seen + 1] = "leave1" end)
            underCursor = pin
            Tick()
            -- (the set cleared and filled again: the same frame handed back, with the new scripts)
            mod.PadViewForget({ Pin(), pin })
            pin:SetScript("OnEnter", function() seen[#seen + 1] = "enter2" end)
            pin:SetScript("OnLeave", function() seen[#seen + 1] = "leave2" end)
            Tick()
            -- (another set's pins redrawn: this one stays entered)
            mod.PadViewForget({ Pin() })
            Tick()
        """)
        self.assertEqual(list(self.ev("seen").values()), ["enter1", "leave1", "enter2"])


if __name__ == "__main__":
    unittest.main()
