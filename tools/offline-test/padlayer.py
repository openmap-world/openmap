"""Another addon's layer on the controller view (API.lua and PadView.lua together) in Lua 5.1:
python -P tools/offline-test/padlayer.py.

With the game's Gamepad UI the map is OpenMap's controller view: other addons are told when it's on
screen and when it goes (OpenMapAPI.Showing, "OpenMap_Showing"), a pin of a layer is entered and left by
the controller's cursor, left when its layer is cleared and entered again when the same frame comes
back, and A on it zooms into the zone under it. Against a stubbed stitch (whose pins are handed out
again, as Stitch.lua's are) and a stand-in for Blizzard's map; the layer's own arithmetic is layer.py's.
"""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"

STUB = r"""
NOW, frames, events, told, errors = 1000, {}, {}, {}, {}
GetTime = function() return NOW end
wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
tinsert, tremove = table.insert, table.remove
GetPlayerFacing = function() return 0 end
geterrorhandler = function() return function(err) errors[#errors + 1] = tostring(err) end end
securecallfunction = function(fn, ...) return fn(...) end
C_Timer = { After = function() end }
Enum = { UIMapType = { Continent = 2, Zone = 3 } }
-- (Blizzard's map is loaded: what waits for it runs at once)
EventUtil = { ContinueOnAddOnLoaded = function(_, fn) fn() end }

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
function S.GetPinSet() end
-- pin sets as Stitch.lua's: a set's pins handed out again after it's cleared (the last back first), their
-- scripts and OnClick taken off as each is handed out
local pool = {}
function S.PinSet(key, minZoom, level) return { key = key, pins = {} } end
function S.AddPin(set, u, v, look)
	local pin = table.remove(pool) or { made = true }
	pin.u, pin.v, pin.look, pin.scripts, pin.OnClick = u, v, look, {}, nil
	function pin:SetScript(k, fn) self.scripts[k] = fn end
	function pin:GetScript(k) return self.scripts[k] end
	function pin:IsVisible() return true end
	function pin:LockHighlight() end
	function pin:UnlockHighlight() end
	set.pins[#set.pins + 1] = pin
	return pin
end
function S.ClearPinSet(set)
	for _, pin in ipairs(set.pins) do pool[#pool + 1] = pin end
	wipe(set.pins)
end
function S.SetPinSetOn() end
-- (the pin under the controller's cursor: the test's)
S.PinAt = function() return underCursor end

mod = { db = { padView = true }, enabled = false }
function mod.PadUI() return true end
function mod.IsStitched() return false end      -- (OpenMap's usual map isn't set up with the Gamepad UI)
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
"""


class PadLayerTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB)
        # (as the toc loads them: the libraries, the controller view, then the API)
        for rel in ("Libs/LibStub/LibStub.lua", "Libs/CallbackHandler-1.0/CallbackHandler-1.0.lua"):
            self.lua.execute("local f = assert(loadstring(...)) f()", (ROOT / rel).read_text(encoding="utf-8"))
        for rel in ("Map/PadView.lua", "API.lua"):
            self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", (ROOT / rel).read_text(encoding="utf-8"))
        self.lua.execute("""
            OM = OpenMapAPI
            OM.RegisterCallback(told, "OpenMap_Showing", function(_, kind) told[#told + 1] = tostring(kind) end)
        """)

    def ev(self, code):
        return self.lua.eval(code)

    def told(self):
        return list(self.ev("told").values())

    # --- which map is on screen

    def test_the_controller_view_is_said_as_it_comes_on_screen_and_goes(self):
        self.assertFalse(self.ev("OM.Showing()"))
        self.assertFalse(self.ev("OM.IsStitched()"))
        self.lua.execute("Open()")
        self.assertEqual(self.ev("OM.Showing()"), "pad")
        self.assertFalse(self.ev("OM.IsStitched()"))     # (the canvas isn't stitched: the view is a frame of its own)
        self.lua.execute("WorldMapFrame:Hide()")
        self.assertFalse(self.ev("OM.Showing()"))
        self.lua.execute("WorldMapFrame:Show() Tick()")
        self.assertEqual(self.told(), ["pad", "false", "pad"])

    def test_it_isn_t_on_screen_once_the_map_is_hidden_whoever_asks_first(self):
        # (another addon's OnHide, hooked before the view's own: the view's frame isn't hidden yet)
        self.lua.execute("""
            asked = {}
            WorldMapFrame:HookScript("OnHide", function() asked[#asked + 1] = tostring(OM.Showing()) end)
            Open()
            WorldMapFrame:Hide()
        """)
        self.assertEqual(list(self.ev("asked").values()), ["false"])

    def test_the_option_turned_off_leaves_the_view_on_screen_until_the_map_closes(self):
        self.lua.execute("Open() mod.db.padView = false")
        self.assertEqual(self.ev("OM.Showing()"), "pad")
        self.lua.execute("WorldMapFrame:Hide() WorldMapFrame:Show() Tick()")
        self.assertFalse(self.ev("OM.Showing()"))
        self.assertEqual(self.told(), ["pad", "false"])

    # --- a layer on it

    def test_no_layer_before_the_map_has_opened_then_one(self):
        self.assertIsNone(self.ev('OM.Layer("Mine")'))
        self.lua.execute("Open()")
        self.assertIsNotNone(self.ev('OM.Layer("Mine")'))

    def filled(self):
        """the view up, a pin of a layer under the controller's cursor"""
        self.lua.execute("""
            Open()
            seen = {}
            layer = OM.Layer("Mine")
            pin = layer:AddPin(1429, 0.5, 0.25, { atlas = "x" },
                function(p) seen[#seen + 1] = "enter1" end, function(p) seen[#seen + 1] = "leave1" end)
            underCursor = pin
            Tick()
        """)

    def test_the_controller_s_cursor_enters_and_leaves_a_layer_s_pin(self):
        self.filled()
        self.lua.execute("underCursor = nil Tick()")
        self.assertEqual(list(self.ev("seen").values()), ["enter1", "leave1"])
        self.assertEqual(self.ev("#errors"), 0)

    def test_a_cleared_layer_s_pin_under_the_cursor_is_left_and_entered_again(self):
        # (the layer cleared and filled again while the cursor stays: the same frame comes back)
        self.filled()
        self.lua.execute("""
            layer:Clear()
            again = layer:AddPin(1429, 0.5, 0.25, { atlas = "x" },
                function(p) seen[#seen + 1] = "enter2" end, function(p) seen[#seen + 1] = "leave2" end)
            underCursor = again
            Tick()
        """)
        self.assertTrue(self.ev("again == pin"))
        self.assertEqual(list(self.ev("seen").values()), ["enter1", "leave1", "enter2"])

    def zoom_after_a(self):
        self.lua.execute("mod.ShowNow(0.5, 0.5, 1) Tick() WorldMapFrame:NavigateToGamepadCursor() for _ = 1, 10 do Tick() end")
        return self.ev("select(3, mod.ViewNow())")

    def test_a_on_a_layer_s_pin_zooms_into_the_zone_under_it(self):
        self.filled()
        self.assertAlmostEqual(self.zoom_after_a(), 5)   # (Elwynn Forest filling the view, as A beside the pin)

    def test_a_on_a_layer_s_pin_given_a_click_runs_it(self):
        self.filled()
        self.lua.execute("clicks = 0 pin.OnClick = function() clicks = clicks + 1 end")
        self.assertEqual((self.zoom_after_a(), self.ev("clicks")), (1, 1))


if __name__ == "__main__":
    unittest.main()
