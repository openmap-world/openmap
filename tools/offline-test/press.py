"""A left press that wandered isn't a click (#37, #64), and a Ctrl-click with OpenMap's pins off is
another addon's (#19): python -P tools/offline-test/press.py."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


SOURCE = (Path(__file__).resolve().parents[2] / 'OpenMap/Map/WorldMap.lua').read_text(encoding='utf-8')


class PressTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            cx, cy = 100, 100
            sc = { mouseButtonInfo = { LeftButton = { down = false } } }
            function sc:GetCursorPosition() return cx, cy end
            function Down() sc.mouseButtonInfo.LeftButton.down = true PressDown(nil, 'LeftButton') end
            function MoveTo(x, y) cx, cy = x, y PressTrack() end
        """)
        helpers = SOURCE[SOURCE.index('local press = {'):SOURCE.index('local function OnCanvasClick(')]
        self.lua.execute(helpers + '\n_G.PressDown, _G.PressTrack, _G.WasDrag = PressDown, PressTrack, WasDrag\n')

    def check(self, code):
        self.lua.execute(code)

    def test_still_press_is_a_click(self):
        self.check("Down() MoveTo(101, 102) assert(not WasDrag())")

    def test_drag_out_and_back_is_not_a_click(self):
        self.check("Down() MoveTo(160, 100) MoveTo(101, 100) assert(WasDrag(), 'a drag back to the start counted as a click')")

    def test_next_press_starts_fresh(self):
        self.check("Down() MoveTo(160, 100) sc.mouseButtonInfo.LeftButton.down = false Down() assert(not WasDrag())")

    def test_right_button_leaves_left_press_alone(self):
        self.check("Down() MoveTo(160, 100) PressDown(nil, 'RightButton') assert(WasDrag())")

    def test_no_tracking_after_release(self):
        self.check("Down() sc.mouseButtonInfo.LeftButton.down = false MoveTo(300, 300) assert(not WasDrag())")


class CtrlClickTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            ctrl, shift = false, false
            function IsControlKeyDown() return ctrl end
            function IsShiftKeyDown() return shift end
            active, dropped, glided = true, 0, 0
            own = { on = false }     -- (OwnView.lua's view in a fight: off)
            mod = { db = {}, DropWaypoint = function() dropped = dropped + 1 end,
                CursorWorld = function() return 0.5, 0.5 end }
            sc = { mouseButtonInfo = { LeftButton = { down = false } } }
            function sc:GetCursorPosition() return 0, 0 end
            WORLD = 947
            S = { ChainAt = function() return { WORLD, 1 } end, Rect = function() return 0, 1, 0, 1 end }
            function View() return 0, 0, 1 end
            function Stitchable() return true end
            function FitZoom() return 2 end
            function GlideTo() glided = glided + 1 end
            ns, tinsert = {}, table.insert
        """)
        chunk = SOURCE[SOURCE.index("-- Blizzard's map-pin button (#324)"):SOURCE.index('-- our icons: a press')]
        self.lua.execute(chunk + '\n_G.OnCanvasClick = OnCanvasClick\n_G.DisarmBlizzardPin = pinBtn.Disarm\n')

    def check(self, code):
        self.lua.execute(code)

    def test_ctrl_click_drops_a_pin_by_default(self):
        self.check("ctrl = true assert(OnCanvasClick(true, 'LeftButton') == true) assert(dropped == 1 and glided == 0)")

    def test_ctrl_click_passes_on_when_turned_off(self):
        self.check("ctrl = true mod.db.ctrlClickPin = false "
                   "assert(OnCanvasClick(true, 'LeftButton') == false, 'the Ctrl-click was kept from other addons') "
                   "assert(dropped == 0 and glided == 0)")

    def test_ctrl_click_in_a_fight_sets_blizzards_waypoint(self):
        # (the own view: Blizzard's canvas under it never gets the click, the waypoint is set from OpenMap's code)
        self.check("ctrl = true mod.db.ctrlClickPin = false own.on = true set = 0 "
                   "mod.OwnViewWaypoint = function() set = set + 1 return true end "
                   "assert(OnCanvasClick(true, 'LeftButton') == true) assert(set == 1 and dropped == 0 and glided == 0)")

    def test_plain_click_still_zooms_when_turned_off(self):
        self.check("mod.db.ctrlClickPin = false assert(OnCanvasClick(true, 'LeftButton') == true) assert(glided == 1)")

    def test_right_click_zooms_out_by_default(self):
        self.check("assert(OnCanvasClick(true, 'RightButton') == true) assert(glided == 1)")

    def test_right_click_passes_on_when_turned_off(self):
        # (#117: Questie's objectives take right-clicks)
        self.check("mod.db.rightClickOut = false "
                   "assert(OnCanvasClick(true, 'RightButton') == false, 'the right-click was kept from other addons') "
                   "assert(glided == 0)")

    def test_controller_b_still_steps_out_when_turned_off(self):
        self.check("mod.db.rightClickOut = false assert(OnCanvasClick(nil, 'RightButton') == true) assert(glided == 1)")
    def test_blizzard_pin_button_drops_and_disarms(self):
        self.check("""
            local armed = true
            local pinBtn = {
                ActiveTexture = { IsShown = function() return armed end },
                SetActive = function(_, on) armed = on and true or false end,
            }
            map = { overlayFrames = { pinBtn } }
            assert(OnCanvasClick(true, 'LeftButton') == true)
            assert(dropped == 1 and glided == 0 and armed == false)
        """)

    def test_blizzard_pin_button_defers_disarm_in_combat(self):
        self.check("""
            local combat = true
            function InCombatLockdown() return combat end
            local armed, setCalls = true, 0
            local pinBtn = {
                ActiveTexture = { IsShown = function() return armed end },
                SetActive = function(_, on) setCalls = setCalls + 1; armed = on and true or false end,
            }
            map = { overlayFrames = { pinBtn } }
            assert(OnCanvasClick(true, 'LeftButton') == true)
            assert(dropped == 1 and setCalls == 0 and armed == true)
            combat = false
            DisarmBlizzardPin()
            assert(setCalls == 1 and armed == false)
        """)

    def test_blizzard_pin_button_respects_game_rule(self):
        self.check("""
            Enum = { GameRule = { WorldMapTrackingPinDisabled = 42 } }
            C_GameRules = { IsGameRuleActive = function(r) return r == 42 end }
            local armed = true
            local pinBtn = {
                ActiveTexture = { IsShown = function() return armed end },
                SetActive = function(_, on) armed = on and true or false end,
            }
            map = { overlayFrames = { pinBtn } }
            assert(OnCanvasClick(true, 'LeftButton') == true)
            assert(dropped == 0 and glided == 1 and armed == true)
        """)


if __name__ == '__main__':
    unittest.main()
