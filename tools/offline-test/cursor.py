"""The cursor's place on a map OpenMap doesn't stitch (a battleground's, a dungeon's): off the map's own art,
over the frame round a map smaller than the window, no place ("--"), not Blizzard's position clamped to the
map's edge ("57.6, 0.0" in Alterac Valley): python -P tools/offline-test/cursor.py.
Run here: Extras.lua's PlaceAt in Lua 5.1, with the map stubbed."""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


EXTRAS = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "Extras.lua").read_text(encoding="utf-8")


class CursorTests(unittest.TestCase):
    def setUp(self):
        m = re.search(r"\nlocal lastU, lastV, lastId\nlocal function PlaceAt\(\)\n.*?\nend\n", EXTRAS, re.S)
        self.assertIsNotNone(m, "PlaceAt")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            over, cx, cy = true, 0.576, 0.0
            mod = { IsStitched = function() return false end, PadCursor = function() return false end }
            canvas = { IsMouseOver = function() return over end }
            map = { GetMapID = function() return 1459 end, GetCanvas = function() return canvas end,
                GetNormalizedCursorPosition = function() return cx, cy end }
            C_Map = { GetMapInfoAtPosition = function() return nil end }
        """ + m.group(0).replace("local function PlaceAt", "function PlaceAt", 1))

    def test_over_the_map_its_place(self):
        self.lua.execute("over, cx, cy = true, 0.3, 0.4")
        self.assertEqual(tuple(self.lua.eval("{ PlaceAt() }").values()), (1459, 0.3, 0.4, 0.3, 0.4))

    def test_off_the_maps_art_no_place(self):
        self.lua.execute("over = false")
        _, x, y, hx, hy = tuple(self.lua.eval("{ PlaceAt() }").values())
        self.assertTrue(x < 0 and y < 0 and hx < 0 and hy < 0)     # (Coord shows "--" off 0..1)


if __name__ == "__main__":
    unittest.main()
