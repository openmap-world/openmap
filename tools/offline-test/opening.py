"""The map opening lays the icon sets out once (#293), and the session's first opening makes only the baked
tiles near its view: python -P tools/offline-test/opening.py.

As the map opens Blizzard resets its view to the whole world (its ResetZoom), and OpenMap's view follows from
the reset's hook. Each scale change had OpenMap lay every set of icons out (ApplyZoom): for the whole world,
then for the view, every pin set hidden and shown again (protella's measurement: the opening 384 ms, 45 once
laid out once). Blizzard's own change now waits a frame, and is dropped when OpenMap's view follows it.
Run here: WorldMap.lua's handler and SetView's lines round it, in Lua 5.1.

The first opening of a session has no view culled yet: S.SetZoom brought the baked tiles in before the view
update culled the view, and Stitch.lua's Baked.Cull took every tile as near, all of the world's made and their
files set at once (#433: a first opening of 800 ms). Run here: Baked.Cull, and ApplyZoom's cull of the view.
"""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


WORLDMAP = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "WorldMap.lua").read_text(encoding="utf-8")
STITCH = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "Stitch.lua").read_text(encoding="utf-8")


def chunk(text, pattern, name):
    """a function's source alone (the files need the whole map to load)"""
    m = re.search(pattern, text, re.S)
    assert m, name
    return m.group(0)


class OpeningTests(unittest.TestCase):
    def setUp(self):
        handler = re.search(r'(dp\.OnCanvasScaleChanged = Ours\("scale changed", function\(\)\n.*?\n\tend\))', WORLDMAP, re.S)
        self.assertIsNotNone(handler, "the scale handler")
        sv = re.search(r"\nlocal function SetView\(scale, x, y\)\n(.*?)\nend\n", WORLDMAP, re.S).group(1)
        self.assertIn("viewSetting = true\n\tmap:OnCanvasScaleChanged()\n\tviewSetting, scaleWaiting = false, false", sv)
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            laid, fight, active = 0, false, true
            viewSetting, scaleWaiting = false, false
            timers = {}
            C_Timer = { After = function(_, fn) timers[#timers + 1] = fn end }
            function RunTimers() local t = timers timers = {} for _, fn in ipairs(t) do fn() end end
            function InCombatLockdown() return fight end
            function ApplyZoom() laid = laid + 1 end
            function Ours(_, fn) return fn end
            dp = {}
            map = { OnCanvasScaleChanged = function() dp.OnCanvasScaleChanged() end }
            -- (SetView's lines round Blizzard's call, as WorldMap.lua has them)
            function SetView()
                viewSetting = true
                map:OnCanvasScaleChanged()
                viewSetting, scaleWaiting = false, false
            end
        """ + handler.group(1))

    def test_an_opening_lays_out_once(self):
        # (Blizzard's reset to the whole world, OpenMap's view from its hook, then the next frame)
        self.lua.execute("map:OnCanvasScaleChanged() SetView() RunTimers()")
        self.assertEqual(self.lua.eval("laid"), 1)

    def test_blizzards_change_alone_laid_out_a_frame_later(self):
        self.lua.execute("map:OnCanvasScaleChanged()")
        self.assertEqual(self.lua.eval("laid"), 0)
        self.lua.execute("map:OnCanvasScaleChanged() RunTimers()")
        self.assertEqual(self.lua.eval("laid"), 1)

    def test_in_combat_at_once(self):
        self.lua.execute("fight = true map:OnCanvasScaleChanged()")
        self.assertEqual(self.lua.eval("laid"), 1)


class BakedCullTests(unittest.TestCase):
    """Stitch.lua's Baked.Cull: each baked tile made (its file set) the first time it's near the culled view,
    and shown near it; none before a view is culled."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        # a world of 10 x 10 baked tiles, each 0.1 a side; the frame they're on shown (the zones' detail in)
        self.lua.execute("""
            S = {}
            cullBox = nil
            SET, MISSING = {}, {}
            function Record() end
            local function Tex()
                return { shown = true,
                    SetTexture = function(self, file) SET[#SET + 1] = file return not MISSING[file] end,
                    SetTexCoord = function() end, SetDesaturation = function() end,
                    Hide = function(self) self.shown = false end, SetShown = function(self, on) self.shown = on end }
            end
            Baked = { path = "Tiles\\\\", inset = 0, desat = 0, tiles = {},
                frame = { IsShown = function() return true end, CreateTexture = function() return Tex() end } }
            for i = 0, 9 do
                for j = 0, 9 do
                    Baked.tiles[#Baked.tiles + 1] = { name = i .. "_" .. j, x = i, y = j, size = 1,
                        u0 = i / 10, v0 = j / 10, u1 = (i + 1) / 10, v1 = (j + 1) / 10 }
                end
            end
            function Counts()
                local made, shown = 0, 0
                for _, t in ipairs(Baked.tiles) do
                    if t.tex then made = made + 1 if t.tex.shown then shown = shown + 1 end end
                end
                return made, shown
            end
        """)
        self.lua.execute(chunk(STITCH, r"\nfunction Baked\.Cull\(\)\n.*?\nend\n", "Baked.Cull"))

    def cull(self):
        """the tiles made, and those shown"""
        self.lua.execute("Baked.Cull()")
        return self.lua.eval("Counts()")

    def test_no_view_culled_yet_none_made(self):
        # (it was all 100: the whole world's tiles made and their files set in the first opening's first frame)
        self.assertEqual(self.cull(), (0, 0))
        self.assertEqual(self.lua.eval("#SET"), 0)

    def test_the_tiles_near_the_view(self):
        # (0.3..0.7 each way: tiles 3..6)
        self.lua.execute("cullBox = { 0.31, 0.31, 0.69, 0.69 }")
        self.assertEqual(self.cull(), (16, 16))

    def test_the_view_moved_its_tiles_made_the_others_hidden(self):
        self.lua.execute("cullBox = { 0.31, 0.31, 0.69, 0.69 }")
        self.cull()
        self.lua.execute("cullBox = { 0.01, 0.01, 0.19, 0.19 }")
        self.assertEqual(self.cull(), (16 + 4, 4))
        self.assertEqual(self.lua.eval("#SET"), 20)   # (each tile's file set once)

    def test_no_box_again_the_tiles_left_as_they_are(self):
        # (the bench's S.ResetShown forgets the box: ApplyZoom culls the view again at once)
        self.lua.execute("cullBox = { 0.31, 0.31, 0.69, 0.69 }")
        self.cull()
        self.lua.execute("cullBox = nil")
        self.assertEqual(self.cull(), (16, 16))

    def test_a_tile_the_game_cant_find_left_hidden(self):
        # (it draws as a solid green square: #349, #353)
        self.lua.execute('MISSING["Tiles\\\\4_4"] = true cullBox = { 0.31, 0.31, 0.69, 0.69 }')
        self.assertEqual(self.cull(), (16, 15))
        self.assertEqual(self.lua.eval("Baked.missing"), 1)

    def test_a_frame_not_shown_makes_none(self):
        self.lua.execute("cullBox = { 0, 0, 1, 1 } Baked.frame.IsShown = function() return false end")
        self.assertEqual(self.cull(), (0, 0))


class FirstCullTests(unittest.TestCase):
    """WorldMap.lua's ApplyZoom: with no view culled yet (the session's first opening, or after the bench), the
    view's own box culled in the same call, right after S.SetZoom, not a frame on in the view update."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            CALLS = {}
            local function Log(what) CALLS[#CALLS + 1] = what end
            active, culled, shown = true, false, true
            view = { 0.5, 0.4, 8 }
            function Before() end
            function Clock() end
            function After() end
            function Clocked() end
            function ApplyView() Log("view update") end
            function ZoomFor() return 8 end
            function CanvasScale() return 1 end
            function DetailK() return 1 end
            function View() return view[1], view[2], view[3] end
            function PerPx(zoom) return 0.001, 0.002 end
            map = { GetMapID = function() return 1429 end, IsShown = function() return shown end }
            sc = { GetWidth = function() return 100 end, GetHeight = function() return 50 end }
            ns = { Safe = { Finite = function(...)
                for i = 1, select("#", ...) do
                    local n = select(i, ...)
                    if type(n) ~= "number" or n ~= n or n == math.huge or n == -math.huge then return false end
                end
                return true
            end } }
            S = { SetZoom = function() Log("zoom") end, Culled = function() return culled end,
                Cull = function(u0, v0, u1, v1) Log(("cull %.2f %.2f %.2f %.2f"):format(u0, v0, u1, v1)) end }
        """)
        self.lua.execute(chunk(WORLDMAP, r"\nApplyZoom = function\(\)\n.*?\nend\n", "ApplyZoom"))

    def calls(self):
        self.lua.execute("CALLS = {} ApplyZoom()")
        t = self.lua.eval("CALLS")
        return [t[i] for i in range(1, len(t) + 1)]

    def test_the_first_opening_culls_its_view_after_the_zoom(self):
        # (half extents: 100 / 2 * 0.001 and 50 / 2 * 0.002, round 0.5, 0.4)
        self.assertEqual(self.calls(), ["zoom", "cull 0.45 0.35 0.55 0.45", "view update"])

    def test_later_ones_leave_it_to_the_view_update(self):
        self.lua.execute("culled = true")
        self.assertEqual(self.calls(), ["zoom", "view update"])

    def test_not_while_the_map_is_closed(self):
        # (the build's refresh runs ApplyZoom with the map closed: its canvas has no view of the opening's)
        self.lua.execute("shown = false")
        self.assertEqual(self.calls(), ["zoom", "view update"])

    def test_not_a_view_that_isnt_one(self):
        # (a map 0 px across divides by zero: NaN, #260 #261)
        self.lua.execute("view = { 0 / 0, 0.4, 8 }")
        self.assertEqual(self.calls(), ["zoom", "view update"])


if __name__ == "__main__":
    unittest.main()
