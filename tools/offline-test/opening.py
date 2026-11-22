"""The map opening lays the icon sets out once (#293): python -P tools/offline-test/opening.py.

As the map opens Blizzard resets its view to the whole world (its ResetZoom), and OpenMap's view follows from
the reset's hook. Each scale change had OpenMap lay every set of icons out (ApplyZoom): for the whole world,
then for the view, every pin set hidden and shown again (protella's measurement: the opening 384 ms, 45 once
laid out once). Blizzard's own change now waits a frame, and is dropped when OpenMap's view follows it.
Run here: WorldMap.lua's handler and SetView's lines round it, in Lua 5.1.
"""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


WORLDMAP = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "WorldMap.lua").read_text(encoding="utf-8")


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


if __name__ == "__main__":
    unittest.main()
