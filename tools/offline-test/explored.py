"""Unexplored land hidden up close in Lua 5.1 (Stitch.lua's Shade.Hide.Rects: the rectangles a zone
hides, its unexplored pieces less its explored ones), against every pixel of random piece sets:
python -P tools/offline-test/explored.py."""
from pathlib import Path
import random
import re
import unittest

from lupa.lua51 import LuaRuntime


STITCH = Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "Stitch.lua"


class HiddenTests(unittest.TestCase):
    def setUp(self):
        # (the function alone, with the two tables it reads: Stitch.lua needs the whole map to load)
        m = re.search(r"\nfunction Shade\.Hide\.Rects\(mapID\)\n.*?\nend\n", STITCH.read_text(encoding="utf-8"), re.S)
        self.assertIsNotNone(m, "Shade.Hide.Rects in Stitch.lua")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            pieces = {}
            Shade = { Hide = { rects = {} } }
            function strsplit(sep, s)
                local out = {}
                for part in (s .. sep):gmatch("(.-)" .. sep) do out[#out + 1] = part end
                return unpack(out)
            end
        """)
        self.lua.execute(m.group(0))

    def pieces(self, specs):
        self.lua.execute("pieces[1] = {} Shade.Hide.rects = {}")
        for (w, h, x, y), un in specs:
            self.lua.execute('pieces[1]["%d:%d:%d:%d"] = { unexplored = %s }' % (w, h, x, y, "true" if un else "false"))
        rects, count = self.lua.eval("Shade.Hide.Rects")(1)
        covered = set()
        for i in range(1, len(rects) + 1 if rects else 1):
            r = rects[i]
            covered |= {(x, y) for y in range(int(r[2]), int(r[4])) for x in range(int(r[1]), int(r[3]))}
        return covered, count

    def test_random_pieces_against_every_pixel(self):
        rng = random.Random(7)
        W, H = 120, 90
        for _ in range(200):
            specs = []
            for _ in range(rng.randint(1, 9)):
                w, h = rng.randint(5, 60), rng.randint(5, 50)
                specs.append(((w, h, rng.randint(0, W - w), rng.randint(0, H - h)), rng.random() < 0.5))
            covered, count = self.pieces(specs)
            def inside(un, x, y):
                return any(u == un and px < x < px + w and py < y < py + h for (w, h, px, py), u in specs)
            want = {(x, y) for y in range(H) for x in range(W) if inside(True, x + .5, y + .5) and not inside(False, x + .5, y + .5)}
            self.assertEqual(covered, want)
            self.assertEqual(count, sum(1 for _, un in specs if un))

    def test_all_explored_hides_nothing(self):
        covered, count = self.pieces([((40, 30, 0, 0), False), ((20, 20, 10, 10), False)])
        self.assertEqual((covered, count), (set(), 0))

    def test_worked_out_again_once_explored(self):
        self.pieces([((40, 30, 0, 0), True)])
        self.lua.execute('pieces[1]["40:30:0:0"].unexplored = false')
        rects, count = self.lua.eval("Shade.Hide.Rects")(1)
        self.assertEqual(count, 0)
        self.assertIsNone(rects)


if __name__ == "__main__":
    unittest.main()
