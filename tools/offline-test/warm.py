"""Keep-warm in Lua 5.1: the files an opening round a zone reads first (Stitch.lua's S.WarmFiles: the
zone's own art, then the baked tiles half a zone past each side, nearest first, without repeats, at the
most `most`; a cave's map is its zone's),
and the files held as the map closes (Extras.lua's WarmCollect: shown textures, a texture still fading
in at alpha 0 among them): python -P tools/offline-test/warm.py."""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


ADDON = Path(__file__).resolve().parents[2] / "OpenMap"
STITCH = ADDON / "Map" / "Stitch.lua"
EXTRAS = ADDON / "Map" / "Extras.lua"


def chunk(path, pattern, name):
    """a function's source alone (the files need the whole map to load)"""
    m = re.search(pattern, path.read_text(encoding="utf-8"), re.S)
    assert m, name + " in " + path.name
    return m.group(0)


class WarmFilesTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        # a world of 10 x 10 baked tiles (each 0.1 of the world a side) and one zone in the middle
        self.lua.execute("""
            NONE = {}
            S = { built = true }
            rects = { [1] = { 0.4, 0.6, 0.4, 0.6 } }
            function S.Rect(mapID) local r = rects[mapID] if r then return r[1], r[2], r[3], r[4] end end
            Baked = { frame = {}, use = true, path = "Tiles\\\\", tiles = {} }
            for i = 0, 9 do
                for j = 0, 9 do
                    Baked.tiles[#Baked.tiles + 1] = { name = i .. "_" .. j,
                        u0 = i / 10, v0 = j / 10, u1 = (i + 1) / 10, v1 = (j + 1) / 10 }
                end
            end
            local function Tex(file, lazy)
                return { omFile = lazy and file or nil, GetTexture = function() return (not lazy) and file or nil end }
            end
            -- map 5: a cave in zone 1; map 6: a map of its own (no parent)
            local parents = { [5] = 1 }
            C_Map = { GetMapInfo = function(id) return { parentMapID = parents[id] or 0 } end }
            zoneTex = { [1] = { { Tex("Zone\\\\a", true) }, { Tex("Zone\\\\b", false) }, { Tex("Zone\\\\a", false) } } }
        """)
        self.lua.execute(chunk(STITCH, r"\nfunction S\.WarmFiles\(mapID, most\)\n.*?\nend\n", "S.WarmFiles"))

    def files(self, mapID=1, most=400):
        t = self.lua.eval("S.WarmFiles")(mapID, most)
        return [t[i] for i in range(1, len(t) + 1)]

    def test_the_zone_then_baked_tiles_half_a_zone_round_it_nearest_first(self):
        files = self.files()
        self.assertEqual(files[:2], ["Zone\\a", "Zone\\b"])   # (lazy or set, once each)
        # the zone is 0.4..0.6: half a zone past each side is 0.3..0.7, tiles 3..6 each way
        want = {"Tiles\\%d_%d" % (i, j) for i in range(3, 7) for j in range(3, 7)}
        self.assertEqual(set(files[2:]), want)
        self.assertEqual(len(files), 2 + len(want))
        # the four round the zone's centre first, the corners of the box last
        self.assertEqual(set(files[2:6]), {"Tiles\\4_4", "Tiles\\4_5", "Tiles\\5_4", "Tiles\\5_5"})
        self.assertEqual(set(files[-4:]), {"Tiles\\3_3", "Tiles\\3_6", "Tiles\\6_3", "Tiles\\6_6"})

    def test_a_cave_warms_its_zone(self):
        self.assertEqual(self.files(mapID=5), self.files(mapID=1))

    def test_the_zone_first_when_the_box_is_bigger_than_most(self):
        self.assertEqual(self.files(most=3)[:2], ["Zone\\a", "Zone\\b"])

    def test_at_the_most(self):
        self.assertEqual(len(self.files(most=5)), 5)

    def test_missing_tiles_left_out(self):
        self.lua.execute("for _, t in ipairs(Baked.tiles) do if t.name == '4_4' then t.missing = true end end")
        self.assertNotIn("Tiles\\4_4", self.files())

    def test_baked_tiles_not_drawn_none_of_them(self):
        self.lua.execute("Baked.use = false")
        self.assertEqual(self.files(), ["Zone\\a", "Zone\\b"])

    def test_nothing_before_the_build_or_without_a_rectangle(self):
        self.assertEqual(self.files(mapID=2), [])
        self.assertEqual(self.files(mapID=6), [])
        self.assertEqual(self.files(mapID=None), [])
        self.lua.execute("S.built = false")
        self.assertEqual(self.files(), [])


class WarmCollectTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            WARM_MOST = 1200
            function Region(file, shown, alpha, step)
                return { file = file, shown = shown, alpha = alpha, omStep = step,
                    IsObjectType = function(self, kind) return kind == "Texture" end,
                    IsShown = function(self) return self.shown end,
                    GetAlpha = function(self) return self.alpha end,
                    GetTexture = function(self) return self.file end }
            end
            function Frame(regions, children, shown, alpha)
                return { IsShown = function() return shown ~= false end, GetAlpha = function() return alpha or 1 end,
                    GetRegions = function() return unpack(regions) end,
                    GetNumRegions = function() return #regions end,
                    GetChildren = function() return unpack(children or {}) end,
                    GetNumChildren = function() return #(children or {}) end }
            end
            function Many(n)
                local list = {}
                for i = 1, n do list[i] = Region(nil, false, 0) end
                list[1] = Region("anchors' frame", true, 1)
                return list
            end
            root = Frame({ Region("shown", true, 1), Region("fading", true, 0, 0.25), Region("faded out", true, 0),
                Region("hidden", false, 1), Region("shown", true, 1) },
                { Frame({ Region("in a muted layer", true, 1) }, nil, true, 0), Frame({ Region("child", true, 1) }) })
        """)
        source = chunk(EXTRAS, r"\nlocal WARM_REGIONS.*?\nlocal function WarmCollect\(f, files, seen\)\n.*?\nend\n", "WarmCollect")
        self.lua.execute(source.replace("local function WarmCollect", "function WarmCollect", 1))

    def test_a_frame_with_thousands_of_regions_skipped_not_a_stack_overflow(self):
        # (the places to explore's anchors, thousands on the art's frame: { f:GetRegions() } overflowed the
        # stack as the map closed, #414)
        files = self.lua.eval("""(function()
            local f = {}
            WarmCollect(Frame(Many(20000), { Frame({ Region("child", true, 1) }) }), f, {})
            return f end)()""")
        self.assertEqual([files[i] for i in range(1, len(files) + 1)], ["child"])

    def test_shown_and_fading_held_once(self):
        files = self.lua.eval("(function() local f = {} WarmCollect(root, f, {}) return f end)()")
        self.assertEqual([files[i] for i in range(1, len(files) + 1)], ["shown", "fading", "child"])


if __name__ == "__main__":
    unittest.main()
