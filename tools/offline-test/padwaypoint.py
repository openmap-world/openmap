"""The waypoint on the controller view (PadView.lua) in Lua 5.1: python -P tools/offline-test/padwaypoint.py.

The left stick pressed puts Blizzard's waypoint on its map underneath, where its own cursor is there, and
the view puts it again where the view's cursor is. Another addon's waypoint, set while the map is open,
isn't the stick's: it stays where that addon put it, whenever it comes (alone, just before or after a
press, after the stick took the waypoint off). Against a stubbed stitch and a stand-in for Blizzard's map
whose GamepadTryPlaceWaypoint does as Blizzard's (Blizzard_WorldMap.lua: set at its cursor, or taken off
when the cursor is within 0.03 of it).
(OPENMAP_PADVIEW: another PadView.lua to run these against.)
"""
import os
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"
PADVIEW = Path(os.environ.get("OPENMAP_PADVIEW") or ROOT / "Map" / "PadView.lua")

STUB = r"""
NOW, frames, events, sets, removed = 1000, {}, {}, {}, 0
waypoint, eventOnSet, ruleOff = nil, true, false
bx, by = 0.9, 0.9               -- Blizzard's cursor on its map underneath (not where the view's is)
GetTime = function() return NOW end
wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
GetPlayerFacing = function() return 0 end
PlaySound = function() end
SOUNDKIT = {}
Enum = { UIMapType = { Continent = 2, Zone = 3 }, GameRule = { WorldMapTrackingPinDisabled = 1 } }
C_GameRules = { IsGameRuleActive = function() return ruleOff end }
C_SuperTrack = { SetSuperTrackedUserWaypoint = function() end }

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
function WorldMapFrame:GetCanvas() return self.ScrollContainer.Child end
function WorldMapFrame:GetMapID() return 1429 end
function WorldMapFrame:IsCanvasGamepadFocus() return true end
function WorldMapFrame:NavigateToGamepadCursor() end
function WorldMapFrame:NavigateToParentMap() end
function WorldMapFrame:GetNormalizedGamepadCursorPosition() return bx, by end
SoftCursor = Frame()
function SoftCursor:GetRect() return 500, 300, 0, 0 end

local function Fire(event) if events[event] then events[event](nil, event) end end
local function Vector(x, y) return { x = x, y = y, GetXY = function(self) return self.x, self.y end } end
-- (as Blizzard_ObjectAPI's UiMapPoint.lua)
UiMapPoint = { CreateFromCoordinates = function(map, x, y) return { uiMapID = map, position = Vector(x, y) } end }
C_Map = {
	GetBestMapForUnit = function() end,
	GetMapInfo = function() end,
	HasUserWaypoint = function() return waypoint ~= nil end,
	GetUserWaypoint = function() return waypoint end,
	GetUserWaypointPositionForMap = function(id) if waypoint and waypoint.uiMapID == id then return waypoint.position end end,
	CanSetUserWaypointOnMap = function() return true end,
	-- (every set counted; its event comes inside the call, or (eventOnSet off) when the test fires it)
	SetUserWaypoint = function(point)
		waypoint = point
		sets[#sets + 1] = point
		if eventOnSet then Fire("USER_WAYPOINT_UPDATED") end
	end,
	ClearUserWaypoint = function()
		waypoint = nil
		removed = removed + 1
		if eventOnSet then Fire("USER_WAYPOINT_UPDATED") end
	end,
}
-- Blizzard's own, as WorldMapMixin:GamepadTryPlaceWaypoint does (Blizzard_WorldMap.lua): the waypoint where
-- its cursor is on its map, or taken off when the cursor is within 0.03 of it; nothing where a game rule
-- has map pins off
function WorldMapFrame:GamepadTryPlaceWaypoint()
	if C_GameRules.IsGameRuleActive(Enum.GameRule.WorldMapTrackingPinDisabled) then return end
	local mapID = self:GetMapID()
	local pos = C_Map.GetUserWaypointPositionForMap(mapID)
	local x, y = self:GetNormalizedGamepadCursorPosition()
	local place = true
	if pos then
		local wx, wy = pos:GetXY()
		place = math.abs(wx - x) > 0.03 or math.abs(wy - y) > 0.03
	end
	if place then
		C_Map.SetUserWaypoint(UiMapPoint.CreateFromCoordinates(mapID, x, y))
		C_SuperTrack.SetSuperTrackedUserWaypoint(false)
	else
		C_Map.ClearUserWaypoint()
		C_SuperTrack.SetSuperTrackedUserWaypoint(false)
	end
end

S = setmetatable({ WORLD = 947 }, NOOP)
local isBuilt = false
function S.IsBuilt() return isBuilt end
function S.Build() isBuilt = true end
function S.Layout() return true end
function S.Size() return 2000, 1000 end
-- (Elwynn Forest round the middle of the world, where the view opens: (0.5, 0.5) is its (0.5, 0.25))
function S.Rect(id)
	if id == 947 then return 0, 1, 0, 1 end
	if id == 1429 then return 0.4, 0.6, 0.45, 0.65 end
end
function S.ChainAt() return { 947, 1429 } end
function S.PinAt() end
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

function Updated() Fire("USER_WAYPOINT_UPDATED") end
function Tick() for _, f in ipairs(frames) do if f.shown and f.scripts.OnUpdate then f.scripts.OnUpdate(f, 0.1) end end end
-- the map opened and a frame drawn: the view built, its cursor seen
function Open()
	mod.StartPadView()
	WorldMapFrame:Show()
	Tick()
end
function Stick() WorldMapFrame:GamepadTryPlaceWaypoint() end
-- another addon's waypoint (a quest helper's, TomTom's), set on the zone Blizzard's map is on
function Other(x, y)
	local point = UiMapPoint.CreateFromCoordinates(1429, x or 0.2, y or 0.3)
	point.other = true
	C_Map.SetUserWaypoint(point)
end
function Later(seconds) NOW = NOW + seconds end
"""


class PadWaypointTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB)
        self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", PADVIEW.read_text(encoding="utf-8"))

    def ev(self, code):
        return self.lua.eval(code)

    def at_the_cursor(self):
        """the waypoint is the view's own: Elwynn's, where the view's cursor is"""
        self.assertIsNone(self.ev("waypoint.other"))
        self.assertEqual(self.ev("waypoint.uiMapID"), 1429)
        self.assertAlmostEqual(self.ev("waypoint.position.x"), 0.5)
        self.assertAlmostEqual(self.ev("waypoint.position.y"), 0.25)

    def the_other_addon_s(self, x=0.2, y=0.3):
        """the waypoint is the other addon's, where it put it"""
        self.assertTrue(self.ev("waypoint.other"))
        self.assertAlmostEqual(self.ev("waypoint.position.x"), x)
        self.assertAlmostEqual(self.ev("waypoint.position.y"), y)

    # --- the stick's waypoint

    def test_the_stick_s_waypoint_goes_where_the_view_s_cursor_is(self):
        self.lua.execute("Open() Stick()")
        self.assertEqual(self.ev("#sets"), 2)        # (Blizzard's own, then the view's)
        self.at_the_cursor()

    def test_the_same_when_the_event_comes_after_blizzard_s_call(self):
        self.lua.execute("Open() eventOnSet = false Stick()")
        self.assertEqual(self.ev("#sets"), 2)        # (the waypoint is there to see as Blizzard's call ends)
        self.lua.execute("Updated() Updated()")      # (told of both sets, late: nothing more)
        self.assertEqual(self.ev("#sets"), 2)
        self.lua.execute("Later(0.6) Updated()")     # (or later still)
        self.assertEqual(self.ev("#sets"), 2)
        self.at_the_cursor()

    def test_two_presses_close_together_both_go_where_the_view_s_cursor_is(self):
        self.lua.execute("Open() Stick() Later(0.2) Stick()")
        self.assertEqual(self.ev("#sets"), 4)
        self.at_the_cursor()

    def test_the_stick_takes_the_waypoint_off_as_blizzard_s_does(self):
        # (a waypoint under Blizzard's cursor on its map: taken off, none put again)
        self.lua.execute("Open() eventOnSet = false Other(0.9, 0.9) eventOnSet = true Later(1) Stick()")
        self.assertEqual(self.ev("removed"), 1)
        self.assertIsNone(self.ev("waypoint"))
        self.assertEqual(self.ev("#sets"), 1)

    def test_nothing_before_the_view_s_cursor_has_been_seen(self):
        self.lua.execute("mod.StartPadView() WorldMapFrame:Show() Stick()")
        self.assertEqual(self.ev("#sets"), 1)        # (left where Blizzard put it)
        self.assertAlmostEqual(self.ev("waypoint.position.x"), 0.9)

    def test_a_map_without_the_stick_s_function_has_no_stick_s_waypoint(self):
        self.lua.execute("WorldMapFrame.GamepadTryPlaceWaypoint = false Open() Other()")
        self.assertEqual(self.ev("#sets"), 1)
        self.the_other_addon_s()

    # --- another addon's waypoint

    def test_another_addon_s_waypoint_stays_where_it_was_put(self):
        self.lua.execute("Open() Other()")
        self.assertEqual(self.ev("#sets"), 1)
        self.the_other_addon_s()

    def test_another_addon_s_just_before_a_press_gives_way_to_the_stick_s(self):
        self.lua.execute("Open() Other() Later(0.1) Stick()")
        self.assertEqual(self.ev("#sets"), 3)
        self.at_the_cursor()

    def test_another_addon_s_just_after_a_press_stays(self):
        self.lua.execute("Open() Stick() Later(0.1) Other()")
        self.assertEqual(self.ev("#sets"), 3)
        self.the_other_addon_s()

    def test_another_addon_s_just_after_the_stick_took_the_waypoint_off_stays(self):
        self.lua.execute("""
            Open() eventOnSet = false Other(0.9, 0.9) eventOnSet = true Later(1)
            Stick() Later(0.1) Other()
        """)
        self.assertEqual(self.ev("removed"), 1)
        self.assertEqual(self.ev("#sets"), 2)        # (the two of the other addon's)
        self.the_other_addon_s()

    def test_another_addon_s_put_back_where_the_stick_just_took_it_off_stays(self):
        # (its waypoint under Blizzard's cursor before the map opened; the stick takes it off; the addon
        # sets it again at the same place a moment later: not the stick's, whatever the place)
        for again in ("Other(0.9, 0.9)", "Other(0.904, 0.896)"):
            with self.subTest(again=again):
                self.setUp()
                self.lua.execute("Other(0.9, 0.9) Open() Stick() Later(0.1) " + again)
                self.assertEqual(self.ev("removed"), 1)
                self.assertEqual(self.ev("#sets"), 2)
                self.assertTrue(self.ev("waypoint.other"))
                self.assertGreater(self.ev("waypoint.position.x"), 0.89)
        # (and later still)
        self.setUp()
        self.lua.execute("Other(0.9, 0.9) Open() Stick() Later(0.6) Other(0.9, 0.9)")
        self.assertEqual(self.ev("#sets"), 2)
        self.the_other_addon_s(0.9, 0.9)

    def test_another_addon_s_set_in_answer_to_the_stick_s_stays(self):
        # (an addon that sets its own waypoint as soon as it's told of a new one, inside Blizzard's call:
        # as that call ends the waypoint isn't at Blizzard's cursor, so it isn't the stick's)
        self.lua.execute("""
            Open()
            local set, answered = C_Map.SetUserWaypoint, false
            C_Map.SetUserWaypoint = function(point)
                set(point)
                if not answered then answered = true Other() end
            end
            Stick()
        """)
        self.assertEqual(self.ev("#sets"), 2)        # (Blizzard's, then the other addon's)
        self.the_other_addon_s()

    def test_another_addon_s_just_after_two_presses_stays(self):
        self.lua.execute("Open() Stick() Later(0.2) Stick() Later(0.4) Other()")
        self.assertEqual(self.ev("#sets"), 5)
        self.the_other_addon_s()

    def test_another_addon_s_later_stays_and_the_stick_s_after_it_is_the_view_s_again(self):
        self.lua.execute("Open() Stick() Later(2) Other()")
        self.assertEqual(self.ev("#sets"), 3)
        self.the_other_addon_s()
        self.lua.execute("Later(2) Stick()")
        self.assertEqual(self.ev("#sets"), 5)
        self.at_the_cursor()

    def test_another_addon_s_stays_when_a_game_rule_keeps_the_stick_from_setting_one(self):
        self.lua.execute("Open() Other() Later(0.1) ruleOff = true Stick()")
        self.assertEqual(self.ev("#sets"), 1)
        self.the_other_addon_s()
        self.lua.execute("Later(0.1) Other(0.6, 0.7)")   # (and the next one)
        self.assertEqual(self.ev("#sets"), 2)
        self.the_other_addon_s(0.6, 0.7)

    def test_another_addon_s_at_blizzard_s_cursor_stays_when_a_game_rule_keeps_the_stick_from_setting_one(self):
        # (where it is doesn't make it the stick's: Blizzard's did nothing)
        self.lua.execute("Open() Other(0.9, 0.9) Later(0.1) ruleOff = true Stick()")
        self.assertEqual(self.ev("#sets"), 1)
        self.the_other_addon_s(0.9, 0.9)
        self.lua.execute("Later(0.1) Other(0.9, 0.9)")   # (set there again just after the press: the same)
        self.assertEqual(self.ev("#sets"), 2)
        self.the_other_addon_s(0.9, 0.9)

    def test_nothing_with_the_map_closed(self):
        self.lua.execute("Open() WorldMapFrame:Hide() Other()")
        self.assertEqual(self.ev("#sets"), 1)
        self.the_other_addon_s()

if __name__ == "__main__":
    unittest.main()
