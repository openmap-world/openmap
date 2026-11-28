"""Blizzard's own waypoint on the stitched map (Nav.lua's mod.ZoneWaypoint) in Lua 5.1:
python -P tools/offline-test/waypoint.py.

With "Ctrl-click drops a pin" off, Ctrl-click is Blizzard's: it sets its waypoint on the map underneath, often
a continent's, at the cursor clamped to that map's rectangle, where the game can't route to it (#19: set, never
followed). It's put where the cursor is, on the zone there, and followed; a zone's own is left as it is.
"""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


NAV = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "Nav.lua").read_text(encoding="utf-8")


class ZoneWaypointTests(unittest.TestCase):
    def setUp(self):
        m = re.search(r"\nlocal zoning = false\nfunction mod\.ZoneWaypoint\(\)\n.*?\nend\n", NAV, re.S)
        self.assertIsNotNone(m, "mod.ZoneWaypoint in Nav.lua")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(r"""
            Enum = { UIMapType = { Continent = 2, Zone = 3 } }
            fight = false
            function InCombatLockdown() return fight end
            -- the waypoint as Blizzard set it: on the continent (1415), at its own clamped point
            wp = { 1415, 0.9, 0.5 }
            set, tracked = {}, false
            function BlizzardPin() if wp then return wp[1], wp[2], wp[3] end end
            C_Map = {
                GetMapInfo = function(id) return { mapType = id == 1415 and 2 or 3 } end,
                CanSetUserWaypointOnMap = function(id) return id ~= 1415 end,
                SetUserWaypoint = function(p) set[#set + 1] = p wp = { p.id, p.x, p.y } end,
            }
            C_SuperTrack = { SetSuperTrackedUserWaypoint = function(on) tracked = on end }
            UiMapPoint = { CreateFromCoordinates = function(id, x, y) return { id = id, x = x, y = y } end }
            S = { WORLD = 947, Rect = function() return 0, 1, 0, 1 end }
            function S.ChainAt(u, v) return { 947, 1415, u < 0.5 and 1429 or 1436 } end
            mouseOver = true
            sc = { IsMouseOver = function() return mouseOver end }
            map = { IsShown = function() return true end }
            mod = {}
            function mod.IsStitched() return true end
            function mod.CursorWorld() return 0.3, 0.4 end
            function mod.ToWorld(id, x, y) return x, y end
            function mod.FromWorld(id, u, v) return (u % 0.5) * 2, v end
        """ + m.group(0))


    def test_in_a_fight_left_as_the_game_set_it(self):
        # (set from OpenMap's code in a fight, the tracker's next redraw failed: #295)
        self.lua.execute("fight = true mod.ZoneWaypoint()")
        self.assertEqual(len(list(self.lua.eval("set").values())), 0)
    def test_put_on_the_zone_under_the_cursor_and_followed(self):
        self.lua.execute("mod.ZoneWaypoint()")
        p = self.lua.eval("set[1]")
        self.assertEqual((p.id, p.x, p.y), (1429, 0.6, 0.4))
        self.assertTrue(self.lua.eval("tracked"))

    def test_a_zones_own_left_as_it_is(self):
        self.lua.execute("wp = { 1429, 0.2, 0.3 } mod.ZoneWaypoint()")
        self.assertEqual(self.lua.eval("#set"), 0)

    def test_not_off_the_stitched_map(self):
        self.lua.execute("function mod.IsStitched() return false end mod.ZoneWaypoint()")
        self.assertEqual(self.lua.eval("#set"), 0)

    def test_cursor_off_the_map_its_own_point(self):
        # (another addon set it, the cursor elsewhere: the continent point's zone)
        self.lua.execute("mouseOver = false mod.ZoneWaypoint()")
        p = self.lua.eval("set[1]")
        self.assertEqual(p.id, 1436)

    def test_once(self):
        # (its own update, as it sets the zone's: nothing more)
        self.lua.execute("mod.ZoneWaypoint() mod.ZoneWaypoint()")
        self.assertEqual(self.lua.eval("#set"), 1)


class TomTomTests(unittest.TestCase):
    """A waypoint followed sets TomTom's too, unless "TomTom waypoint too" is off (#444)"""
    def setUp(self):
        clear = re.search(r"\nlocal tomtomPoint\nlocal function ClearTomTom\(\)\n.*?\nend\n", NAV, re.S)
        track = re.search(r"\nfunction mod\.TrackPoint\(mapID, x, y, title\)\n.*?\nend\n", NAV, re.S)
        toggle = re.search(r"\nfunction mod\.SetTomTomWaypoint\(on\).*?\nend\n", NAV, re.S)
        for m in (clear, track, toggle):
            self.assertIsNotNone(m, "Nav.lua's TomTom waypoint")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(r"""
            function InCombatLockdown() return false end
            C_Map = { GetMapInfo = function(id) return { name = "Elwynn Forest" } end }
            added, removed = {}, {}
            TomTom = {
                AddWaypoint = function(self, id, x, y, opts) added[#added + 1] = { id, x, y, opts.title } return "handle" .. #added end,
                RemoveWaypoint = function(self, h) removed[#removed + 1] = h end,
            }
            function RefreshWaypoint() end
            mod = { db = {}, char = {} }
        """ + clear.group(0) + track.group(0) + toggle.group(0))

    def test_on_by_default(self):
        self.lua.execute("mod.TrackPoint(1429, 0.4, 0.6, 'Goldshire')")
        self.assertEqual(self.lua.eval("#added"), 1)
        self.assertEqual(self.lua.eval("added[1][4]"), "Goldshire")

    def test_off_no_tomtom_waypoint(self):
        self.lua.execute("mod.db.tomtom = false mod.TrackPoint(1429, 0.4, 0.6)")
        self.assertEqual(self.lua.eval("#added"), 0)
        self.assertEqual(self.lua.eval("mod.char.pin[1]"), 1429)    # (OpenMap's own waypoint still set)

    def test_turned_off_clears_the_one_set(self):
        self.lua.execute("mod.TrackPoint(1429, 0.4, 0.6) mod.SetTomTomWaypoint(false)")
        self.assertEqual(self.lua.eval("removed[1]"), "handle1")
        self.assertFalse(self.lua.eval("mod.db.tomtom"))


class WaypointMetersTests(unittest.TestCase):
    """The game's waypoint arrow's distance in meters (Nav.lua): its text written again after Blizzard's update, from a
    secure hook, nothing else of Blizzard's written; off by default, a secret distance left alone, a client without the
    method or text: nothing"""

    def setUp(self):
        block = NAV[NAV.index("local YARD = 0.9144"):NAV.index("function mod:NavOptions")]
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            secret = false
            function issecretvalue(v) return secret and type(v) == "number" end
            Safe = {}
            function Safe.Value(v) if issecretvalue(v) then return nil end return v end
            function Safe.Call(fn, ...) local ok, v = pcall(fn, ...) if ok then return Safe.Value(v) end end
            function Safe.Finite(n) return type(n) == "number" and n == n and n ~= math.huge end
            L = setmetatable({}, { __index = function(_, k) return k end })
            mod = { db = {} }
            distance = 250
            C_Navigation = { GetDistance = function() return distance end }
            function hooksecurefunc(t, name, fn)
                local was = rawget(t, name)
                rawset(t, name, function(...) was(...) fn(...) end)
            end
            -- Blizzard's frame, locked: a write to it (not its text's own) errors
            text = { shown = true }
            function text:IsShown() return self.shown end
            function text:SetText(t) self.text = t end
            function text:GetText() return self.text end
            SuperTrackedFrame = { DistanceText = text }
            function SuperTrackedFrame:UpdateDistanceText() self.DistanceText:SetText(string.format("%d yds", distance)) end
            setmetatable(SuperTrackedFrame, { __newindex = function(_, k) error("wrote Blizzard's " .. tostring(k)) end })
            IN_GAME_NAVIGATION_RANGE = "%s yds"
        """)
        self.lua.execute(block)

    def update(self):
        self.lua.execute("SuperTrackedFrame:UpdateDistanceText()")
        return self.lua.eval("text.text")

    def test_off_by_default_blizzards_yards(self):
        self.assertTrue(self.lua.eval("mod.SetupWaypointMeters()"))
        self.assertEqual(self.update(), "250 yds")

    def test_meters_and_km(self):
        self.lua.execute("mod.SetupWaypointMeters() mod.db.waypointMeters = true")
        self.assertEqual(self.update(), "229 m")                 # (250 yards)
        self.lua.execute("distance = 2000")
        self.assertEqual(self.update(), "1.8 km")
        self.assertEqual(self.lua.eval("IN_GAME_NAVIGATION_RANGE"), "%s yds")   # (the game's text untouched)

    def test_left_alone_when_secret_hidden_or_none(self):
        self.lua.execute("mod.SetupWaypointMeters() mod.db.waypointMeters = true secret = true")
        self.assertEqual(self.update(), "250 yds")
        self.lua.execute("secret = false text.shown = false")
        self.assertEqual(self.update(), "250 yds")
        self.lua.execute("text.shown = true distance = 0")
        self.assertEqual(self.update(), "0 yds")

    def test_hooked_once_and_not_without_the_frame(self):
        self.lua.execute("mod.SetupWaypointMeters() mod.SetupWaypointMeters() mod.db.waypointMeters = true")
        self.assertEqual(self.update(), "229 m")
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute("L = {} mod = { db = {} } Safe = {}")
        lua.execute(NAV[NAV.index("local YARD = 0.9144"):NAV.index("function mod:NavOptions")])
        self.assertFalse(lua.eval("mod.SetupWaypointMeters()"))
        lua.execute("SuperTrackedFrame = {}")
        self.assertFalse(lua.eval("mod.SetupWaypointMeters()"))


if __name__ == "__main__":
    unittest.main()
