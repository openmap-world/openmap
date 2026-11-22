"""The map's art fading in on the window's opening (Stitch.lua's S.Gate, from the art root's OnShow): once an
opening, the first time the art shows in it, not each time OpenMap's map is shown again within it (back from a
dungeon's map, the game's own map or the controller view: faded in again, it read as a flicker); again after the
window has closed: python -P tools/offline-test/gate.py."""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


STITCH = Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "Stitch.lua"


class GateTests(unittest.TestCase):
    def setUp(self):
        src = STITCH.read_text(encoding="utf-8")
        # (the art root's OnShow and the window's OnHide, as S.Build sets them: lifted alone, the file needs the
        # whole map to load)
        m = re.search(r'\n(\troot:SetScript\("OnShow".*?\n\t\t_G\.WorldMapFrame:HookScript\("OnHide".*?\n\tend\n)', src, re.S)
        self.assertIsNotNone(m, "the art root's OnShow in Stitch.lua")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            gates = 0
            S = { gate = {} }
            function S.Gate() gates = gates + 1 end
            local function Frame()
                local f = { scripts = {}, hooks = {} }
                function f:SetScript(what, fn) self.scripts[what] = fn end
                function f:HookScript(what, fn) self.hooks[what] = fn end
                return f
            end
            root = Frame()
            _G.WorldMapFrame = Frame()
            function Show() root.scripts.OnShow(root) end
            function CloseWindow() _G.WorldMapFrame.hooks.OnHide(_G.WorldMapFrame) end
        """)
        self.lua.execute("function Build()\n" + m.group(1) + "end\nBuild()")

    def gates(self):
        return self.lua.eval("gates")

    def test_once_an_opening(self):
        self.lua.execute("Show()")
        self.assertEqual(self.gates(), 1)
        # (OpenMap's map shown again in the same opening: back from a dungeon's map, the game's own, the controller view)
        self.lua.execute("Show() Show()")
        self.assertEqual(self.gates(), 1)

    def test_again_on_the_next_opening(self):
        self.lua.execute("Show() CloseWindow() Show()")
        self.assertEqual(self.gates(), 2)

    def test_the_window_hook_made_once(self):
        # (a rebuild of the art runs the same code again: the window's hook isn't added twice)
        self.lua.execute("local first = _G.WorldMapFrame.hooks.OnHide  Build()  hookSame = _G.WorldMapFrame.hooks.OnHide == first")
        self.assertTrue(self.lua.eval("hookSame"))


if __name__ == "__main__":
    unittest.main()
