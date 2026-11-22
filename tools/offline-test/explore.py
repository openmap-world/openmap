"""Places to explore (the menu's "Show places to explore"): WoW Forever's Data/Explore.lua against the
map's own pieces (Reveal.lua), and Map/Explore.lua in Lua 5.1 with Stitch.lua's pin sets stubbed: nothing
made with the option off, a zone's outlines and pins once it's in view, fewer once a place is explored,
the zones' counts further out: python -P tools/offline-test/explore.py."""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


ADDON = Path(__file__).resolve().parents[2] / "OpenMap"
DATA = ADDON / "Data" / "Forever"
B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
ELWYNN, ELWYNN_ART = 1429, 1228


def load_data(lua):
    lua.execute("ns = {}")
    for name in ("Reveal.lua", "Explore.lua"):
        fn = lua.eval("function(src, name) return assert(loadstring(src, name)) end")((DATA / name).read_text(encoding="utf-8"), name)
        fn("OpenMap", lua.eval("ns"))


def items(t):
    return list(t.items()) if t is not None else []


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lua = LuaRuntime(unpack_returned_tuples=True)
        load_data(cls.lua)
        cls.reveal = cls.lua.eval("ns.MapReveal")
        cls.explore = cls.lua.eval("ns.MapExplore")

    def test_every_piece_is_one_of_the_maps(self):
        n = 0
        for art, pieces in items(self.explore.pieces):
            self.assertIsNotNone(self.reveal[art], "art %d in Reveal.lua" % art)
            for key, _ in items(pieces):
                self.assertIsNotNone(self.reveal[art][key], "%d %s in Reveal.lua" % (art, key))
                n += 1
        self.assertEqual(n, 549)           # (the Explore achievements' overlay criteria, build 1.60.1.70245)

    def test_every_achievement_has_its_zone_and_pieces(self):
        arts = set()
        for ach, a in items(self.explore.achievements):
            self.assertGreater(a[1], 0)
            self.assertIsNotNone(self.explore.pieces[a[2]], "achievement %d's pieces" % ach)
            arts.add(a[2])
            for _, p in items(self.explore.pieces[a[2]]):
                self.assertEqual(p[1], ach)
        self.assertEqual(arts, {art for art, _ in items(self.explore.pieces)})

    def test_where_to_go_is_on_the_zone(self):
        for art, pieces in items(self.explore.pieces):
            for key, p in items(pieces):
                self.assertTrue(0 <= p[3] <= 1 and 0 <= p[4] <= 1, "%d %s: %s, %s" % (art, key, p[3], p[4]))
                self.assertGreater(len(items(p[2])), 0)

    def test_outlines_decode_near_the_zone(self):
        outlined = 0
        for art, pieces in items(self.explore.pieces):
            for key, p in items(pieces):
                if p.indoor:
                    self.assertIsNone(p[5])
                    continue
                self.assertIsNotNone(p[5], "%d %s: an outline" % (art, key))
                outlined += 1
                for loop in p[5].split():
                    self.assertEqual(len(loop) % 4, 0)
                    self.assertGreaterEqual(len(loop), 12)          # (three points at the least)
                    for i in range(0, len(loop), 2):
                        n = B64.index(loop[i]) * 64 + B64.index(loop[i + 1])
                        self.assertTrue(-0.05 <= n / 4095 * 1.25 - 0.125 <= 1.05)
        self.assertGreater(outlined, 500)

    def test_small(self):
        self.assertLess((DATA / "Explore.lua").stat().st_size, 200 * 1024)


STUB = """
local made = {}
unexplored = {}                 -- key -> true: Elwynn's pieces still to explore (all of them at first)
S = { viewHooks = {}, exploredHooks = {}, built = true }
function S.IsBuilt() return S.built end
function S.Rect(mapID) if mapID == 1429 then return 0.4, 0.5, 0.6, 0.7 end return 0.1, 0.2, 0.1, 0.2 end
stale = false                   -- the map's pieces as built at login: everything unexplored, whatever the game says
function S.Pieces(mapID)
    if mapID ~= 1429 then return nil end
    local list = {}
    for key in pairs(ns.MapExplore.pieces[1228]) do list[key] = { key = key, unexplored = stale or unexplored[key] ~= false } end
    return list
end
function S.PinSet(key, minZoom, level)
    if not made[key] then made[key] = { key = key, on = true, minZoom = minZoom, pins = {}, lines = {} } end
    return made[key]
end
function S.ClearPinSet(set) set.pins = {} set.lines = {} set.cleared = (set.cleared or 0) + 1 end
function S.SetPinSetOn(set, on) set.on = on and true or false end
local Pin = {}
Pin.__index = Pin
function Pin:SetScript() end
function Pin:CreateFontString() return setmetatable({}, { __index = function() return function() end end }) end
function S.AddPin(set, u, v, look, data)
    local pin = setmetatable({ u = u, v = v }, Pin)
    set.pins[#set.pins + 1] = pin
    return pin
end
function S.AddPath(set, pts) for _ = 1, #pts / 2 - 1 do set.lines[#set.lines + 1] = true end end
ns.MapStitch = S
ns.L = setmetatable({}, { __index = function(_, k) return k end })
mod = { defaults = {}, db = {} }
function ns:GetModule() return mod end
-- the game's own list of what's explored: Elwynn's pieces marked explored in `unexplored`
C_MapExplorationInfo = { GetExploredMapTextures = function(mapID)
    local out = {}
    if mapID ~= 1429 then return out end
    for key, un in pairs(unexplored) do
        if un == false then
            local w, h, x, y = key:match("^(%d+):(%d+):(%d+):(%d+)$")
            out[#out + 1] = { textureWidth = tonumber(w), textureHeight = tonumber(h), offsetX = tonumber(x), offsetY = tonumber(y) }
        end
    end
    return out
end }
events = {}
function ns.RegisterEvent(owner, event, fn) events[event] = fn end
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
C_Timer = { After = function(_, fn) fn() end }
mapShown = false
WorldMapFrame = { IsShown = function() return mapShown end, HookScript = function(self, _, fn) self.onShow = fn end }
C_Map = { GetAreaInfo = function() return "?" end, GetMapInfo = function() return { name = "?" } end }
function GetAchievementInfo(id) return id, "Explore" end
function tinsert(t, v) t[#t + 1] = v end
GameTooltip_Hide = function() end
function View(u, v, hu, hv, zoom) for _, fn in ipairs(S.viewHooks) do fn(u, v, hu, hv, zoom) end end
function Explored() for _, fn in ipairs(S.exploredHooks) do fn() end end
function Made() return made end
"""


class ModuleTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        load_data(self.lua)
        self.lua.execute(STUB)
        fn = self.lua.eval("function(src) return assert(loadstring(src, 'Explore.lua')) end")(
            (ADDON / "Map" / "Explore.lua").read_text(encoding="utf-8"))
        fn("OpenMap", self.lua.eval("ns"))
        self.mod = self.lua.eval("mod")
        self.made = self.lua.eval("Made()")
        self.pieces = len(items(self.lua.eval("ns.MapExplore.pieces[%d]" % ELWYNN_ART)))

    def view(self, zoom):
        self.lua.eval("View")(0.45, 0.65, 0.02, 0.02, zoom)

    def test_off_by_default_and_nothing_made(self):
        self.assertIs(self.mod.defaults.explore, False)
        self.mod.db.explore = False
        self.view(8)
        self.mod.RefreshExplore()
        self.assertEqual(len(items(self.made)), 0)

    def test_on_a_zone_in_view(self):
        self.mod.db.explore = True
        self.view(8)
        elwynn = self.made["explore%d" % ELWYNN]
        self.assertIsNotNone(elwynn)
        self.assertTrue(elwynn.on)
        self.assertEqual(len(items(elwynn.pins)), self.pieces)
        self.assertGreater(len(items(elwynn.lines)), self.pieces * 3)
        # (a zone out of view: nothing made for it)
        self.assertIsNone(self.made["explore1426"])
        # the counts, further out: one a zone with places left
        counts = self.made["exploreCount"]
        self.assertGreater(len(items(counts.pins)), 30)

    def test_fewer_once_explored(self):
        self.mod.db.explore = True
        self.view(8)
        key = sorted(k for k, _ in items(self.lua.eval("ns.MapExplore.pieces[%d]" % ELWYNN_ART)))[0]
        self.lua.eval("unexplored")[key] = False
        self.lua.eval("Explored")()
        self.view(8)
        self.assertEqual(len(items(self.made["explore%d" % ELWYNN].pins)), self.pieces - 1)

    def test_far_out_only_the_counts(self):
        self.mod.db.explore = True
        self.view(1)
        self.assertIsNone(self.made["explore%d" % ELWYNN])
        self.assertTrue(self.made["exploreCount"].on)

    def test_turned_off(self):
        self.mod.db.explore = True
        self.view(8)
        self.mod.db.explore = False
        self.mod.RefreshExplore()
        self.view(8)
        self.assertFalse(self.made["explore%d" % ELWYNN].on)
        self.assertFalse(self.made["exploreCount"].on)

    def test_nothing_before_the_map_is_built(self):
        self.lua.execute("S.built = false")
        self.mod.db.explore = True
        self.mod.RefreshExplore()
        self.assertEqual(len(items(self.made)), 0)

    def test_the_games_exploring_not_the_maps_pieces(self):
        # (the map's pieces built at login before the game sent what's explored: all unexplored there, while the
        # game says one is explored. The game's word counts: the Barrens showed 3/25 explored, #417 #418)
        self.lua.execute("stale = true")
        key = sorted(k for k, _ in items(self.lua.eval("ns.MapExplore.pieces[%d]" % ELWYNN_ART)))[0]
        self.lua.eval("unexplored")[key] = False
        self.mod.db.explore = True
        self.view(8)
        self.assertEqual(len(items(self.made["explore%d" % ELWYNN].pins)), self.pieces - 1)

    def test_made_again_when_the_game_says_something_was_explored(self):
        self.mod.db.explore = True
        self.lua.execute("mapShown = true")
        self.view(8)
        key = sorted(k for k, _ in items(self.lua.eval("ns.MapExplore.pieces[%d]" % ELWYNN_ART)))[0]
        self.lua.eval("unexplored")[key] = False
        self.lua.eval("events.MAP_EXPLORATION_UPDATED")()
        self.view(8)
        self.assertEqual(len(items(self.made["explore%d" % ELWYNN].pins)), self.pieces - 1)

    def test_closed_made_again_as_the_map_opens(self):
        self.mod.db.explore = True
        self.view(8)
        key = sorted(k for k, _ in items(self.lua.eval("ns.MapExplore.pieces[%d]" % ELWYNN_ART)))[0]
        self.lua.eval("unexplored")[key] = False
        self.lua.eval("events.MAP_EXPLORATION_UPDATED")()
        self.lua.execute("mapShown = true WorldMapFrame.onShow()")
        self.view(8)
        self.assertEqual(len(items(self.made["explore%d" % ELWYNN].pins)), self.pieces - 1)

    def load(self, keep):
        """Explore.lua again, with KEEP_LINES set to `keep`"""
        src = (ADDON / "Map" / "Explore.lua").read_text(encoding="utf-8")
        src, n = re.subn(r"\nlocal KEEP_LINES = \d+\n", "\nlocal KEEP_LINES = %d\n" % keep, src)
        self.assertEqual(n, 1, "KEEP_LINES")
        self.setUp()
        self.lua.execute("for k in pairs(Made()) do Made()[k] = nil end S.viewHooks = {} S.exploredHooks = {}")
        fn = self.lua.eval("function(src) return assert(loadstring(src, 'Explore.lua')) end")(src)
        fn("OpenMap", self.lua.eval("ns"))
        self.mod.db.explore = True

    def test_out_of_view_let_go_past_the_budget(self):
        # (every zone toured kept its outlines: thousands of lines laid out again on each zoom frame, #411 #413
        # #419, and their anchors overflowed the stack reading the art frame's regions, #414)
        self.load(0)
        self.view(8)
        elwynn = self.made["explore%d" % ELWYNN]
        n = len(items(elwynn.lines))
        self.assertGreater(n, 0)
        self.lua.eval("View")(0.15, 0.15, 0.02, 0.02, 8)         # (elsewhere: Elwynn out of view)
        self.assertFalse(elwynn.on)
        self.assertEqual(len(items(elwynn.lines)), 0)
        self.view(8)                                             # (back: made again)
        self.assertTrue(elwynn.on)
        self.assertEqual(len(items(elwynn.lines)), n)

    def test_within_the_budget_kept(self):
        self.load(100000)
        self.view(8)
        elwynn = self.made["explore%d" % ELWYNN]
        n, cleared = len(items(elwynn.lines)), elwynn.cleared
        self.lua.eval("View")(0.15, 0.15, 0.02, 0.02, 8)
        self.assertFalse(elwynn.on)
        self.view(8)
        self.assertEqual(len(items(elwynn.lines)), n)
        self.assertEqual(elwynn.cleared, cleared)          # (not made again)

    def test_turned_off_let_go(self):
        self.mod.db.explore = True
        self.view(8)
        self.mod.db.explore = False
        self.mod.RefreshExplore()
        self.assertEqual(len(items(self.made["explore%d" % ELWYNN].lines)), 0)

    def test_nothing_new_nothing_made_again(self):
        # (a new subzone with the map open, or an opening after one: nothing explored since, nothing made again.
        # All of it made each time was a hitch at every opening)
        self.mod.db.explore = True
        self.lua.execute("mapShown = true")
        self.view(8)
        elwynn, counts = self.made["explore%d" % ELWYNN], self.made["exploreCount"]
        cleared, countsCleared = elwynn.cleared, counts.cleared
        self.lua.eval("events.ZONE_CHANGED")()
        self.view(8)
        self.assertEqual((elwynn.cleared, counts.cleared), (cleared, countsCleared))
        # (one explored: that zone and the counts made again)
        key = sorted(k for k, _ in items(self.lua.eval("ns.MapExplore.pieces[%d]" % ELWYNN_ART)))[0]
        self.lua.eval("unexplored")[key] = False
        self.lua.eval("events.ZONE_CHANGED")()
        self.view(8)
        self.assertGreater(elwynn.cleared, cleared)
        self.assertGreater(counts.cleared, countsCleared)
        self.assertEqual(len(items(elwynn.pins)), self.pieces - 1)


if __name__ == "__main__":
    unittest.main()
