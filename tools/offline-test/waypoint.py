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


if __name__ == "__main__":
    unittest.main()
