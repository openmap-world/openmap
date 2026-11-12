"""Another addon's layer on the map (API.lua's OpenMapAPI.Layer, Showing and "OpenMap_Showing") in
Lua 5.1: python -P tools/offline-test/layer.py.

Against a stubbed stitch: where a pin and a line of a uiMap land in the world, what comes back off the
stitched world, the scripts the controller's cursor runs, and when other addons are told which of
OpenMap's maps is on screen.
"""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"

STUB = r"""
NOW, errors, added, lines, cleared, shown, told, order = 1000, {}, {}, {}, 0, {}, {}, {}
built, stitched, padShown, mapShown, mapHooks = false, false, false, false, {}
-- Blizzard's map: open or closed, and what's hooked to that (API.lua's own)
WorldMapFrame = { IsShown = function() return mapShown end,
	HookScript = function(_, k, fn) mapHooks[k] = mapHooks[k] or {} table.insert(mapHooks[k], fn) end }
function MapShown(on) mapShown = on for _, fn in ipairs(mapHooks[on and "OnShow" or "OnHide"] or {}) do fn(WorldMapFrame) end end
EventUtil = { ContinueOnAddOnLoaded = function(name, fn) loadedFor = name fn() end }
GetTime = function() return NOW end
geterrorhandler = function() return function(err) errors[#errors + 1] = tostring(err) end end
securecallfunction = function(fn, ...) return fn(...) end
tremove, tinsert = table.remove, table.insert
C_Timer = { After = function() end }

S = { WORLD = 947 }
-- (Elwynn Forest: a tenth of the world each way, from (0.4, 0.6))
function S.Rect(id) if id == 1429 then return 0.4, 0.5, 0.6, 0.7 end end
function S.IsBuilt() return built end
function S.PinSet(key, minZoom, level) return { key = key, minZoom = minZoom, level = level, pins = {} } end
function S.ClearPinSet(set) cleared = cleared + 1 order[#order + 1] = "clear" end
function S.SetPinSetOn(set, on) shown[#shown + 1] = on end
function S.AddPin(set, u, v, look)
	local pin = { set = set, u = u, v = v, look = look, scripts = {} }
	function pin:SetScript(k, fn) self.scripts[k] = fn end
	function pin:GetScript(k) return self.scripts[k] end
	added[#added + 1] = pin
	set.pins[#set.pins + 1] = pin
	return pin
end
function S.AddLine(set, u1, v1, u2, v2, thickness, r, g, b, a)
	local line = { set = set, u1 = u1, v1 = v1, u2 = u2, v2 = v2, thickness = thickness, r = r, g = g, b = b, a = a }
	lines[#lines + 1] = line
	return line
end
function S.ChainAt() return {} end

mod = {}
function mod.IsStitched() return stitched end
function mod.PadViewShown() return padShown end
-- (PadView.lua's: the pin under the controller's cursor left, if it's one of these)
function mod.PadViewForget(pins) forgot = pins order[#order + 1] = "forget" end
ns = { MapStitch = S, L = setmetatable({}, { __index = function(_, k) return k end }) }
function ns:GetModule() return mod end
ns.Safe = { IsSecret = function() return false end }
"""


class LayerTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB)
        for rel in ("Libs/LibStub/LibStub.lua", "Libs/CallbackHandler-1.0/CallbackHandler-1.0.lua"):
            self.lua.execute("local f = assert(loadstring(...)) f()", (ROOT / rel).read_text(encoding="utf-8"))
        src = (ROOT / "API.lua").read_text(encoding="utf-8")
        self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", src)
        self.lua.execute("""
            OM = OpenMapAPI
            OM.RegisterCallback(told, "OpenMap_Showing", function(_, kind) told[#told + 1] = tostring(kind) end)
        """)

    def ev(self, code):
        return self.lua.eval(code)

    def test_no_layer_until_the_art_is_built(self):
        self.assertIsNone(self.ev('OM.Layer("Mine")'))
        self.lua.execute("built = true")
        self.assertIsNotNone(self.ev('OM.Layer("Mine")'))
        # (one layer an owner, the same handed back; over OpenMap's own icons by default)
        self.assertTrue(self.ev('OM.Layer("Mine") == OM.Layer("Mine")'))
        self.assertFalse(self.ev('OM.Layer("Mine") == OM.Layer("Other")'))
        self.assertEqual(self.ev('OM.Layer("Mine").set.key'), "ext.Mine")
        self.assertEqual(self.ev('OM.Layer("Mine").set.level'), 6)
        self.assertEqual(self.ev('OM.Layer("High", 99).set.level'), 20)
        self.assertEqual(self.ev('OM.Layer("Low", -3).set.level'), 1)

    def test_an_owner_is_a_name(self):
        self.assertFalse(self.ev("(pcall(OM.Layer, 12))"))

    def test_a_pin_lands_where_its_map_point_is_in_the_world(self):
        self.lua.execute("built = true")
        self.lua.execute('pin = OM.Layer("Mine"):AddPin(1429, 0.25, 0.5, { atlas = "x", size = 20 })')
        self.assertEqual(self.ev("#added"), 1)
        self.assertAlmostEqual(self.ev("added[1].u"), 0.425)
        self.assertAlmostEqual(self.ev("added[1].v"), 0.65)
        self.assertEqual(self.ev("added[1].look.size"), 20)
        self.assertTrue(self.ev("pin == added[1]"))
        self.assertEqual(self.ev("added[1].set.key"), "ext.Mine")
        # (PadView.lua: nothing of its own to press, so the controller's A zooms in under it)
        self.assertTrue(self.ev("pin.openmapNoPress"))

    def test_nothing_off_the_stitched_world_or_from_bad_values(self):
        self.lua.execute("built = true")
        for call in ('AddPin(9999, 0.5, 0.5, { atlas = "x" })', 'AddPin(1429, "a", 0.5, { atlas = "x" })',
                     "AddPin(1429, 0.5, 0.5)", "AddPin(nil, 0.5, 0.5, {})", "AddLine(9999, 0, 0, 1, 1)",
                     'AddLine(1429, 0, 0, 1, "b")'):
            self.assertIsNone(self.ev('OM.Layer("Mine"):' + call), call)
        self.assertEqual(self.ev("#added"), 0)
        self.assertEqual(self.ev("#lines"), 0)

    def test_a_line_joins_two_points_of_a_map(self):
        self.lua.execute("built = true")
        self.lua.execute('OM.Layer("Mine"):AddLine(1429, 0, 0, 1, 1, 4, 1, 0.3, 0.3, 0.85)')
        self.lua.execute('OM.Layer("Mine"):AddLine(1429, 0.5, 0.5, 1, 0)')
        self.assertEqual(self.ev("#lines"), 2)
        first = [self.ev("lines[1]." + k) for k in ("u1", "v1", "u2", "v2", "thickness", "r", "g", "b", "a")]
        for got, want in zip(first, (0.4, 0.6, 0.5, 0.7, 4, 1, 0.3, 0.3, 0.85)):
            self.assertAlmostEqual(got, want)
        second = [self.ev("lines[2]." + k) for k in ("u1", "v1", "u2", "v2", "thickness", "r", "g", "b", "a")]
        for got, want in zip(second, (0.45, 0.65, 0.5, 0.6, 3, 1, 1, 1, 1)):
            self.assertAlmostEqual(got, want)

    def test_the_cursor_on_and_off_a_pin_runs_its_scripts(self):
        self.lua.execute("built = true")
        self.lua.execute("""
            seen = {}
            pin = OM.Layer("Mine"):AddPin(1429, 0.5, 0.5, { atlas = "x" },
                function(p) seen[#seen + 1] = p == pin and "enter" or "enter?" end,
                function(p) seen[#seen + 1] = p == pin and "leave" or "leave?" end)
            -- (as Gamepad.lua and PadView.lua enter and leave what's under the controller's cursor)
            pin:GetScript("OnEnter")(pin, false)
            pin:GetScript("OnLeave")(pin, false)
            plain = OM.Layer("Mine"):AddPin(1429, 0.5, 0.5, { atlas = "x" })
        """)
        self.assertEqual(list(self.ev("seen").values()), ["enter", "leave"])
        self.assertIsNone(self.ev('plain:GetScript("OnEnter")'))
        self.assertIsNone(self.ev('plain:GetScript("OnLeave")'))

    def test_an_error_in_a_script_is_reported_and_goes_no_further(self):
        self.lua.execute("built = true")
        self.lua.execute("""
            pin = OM.Layer("Mine"):AddPin(1429, 0.5, 0.5, { atlas = "x" }, function() error("mine broke") end)
            ok = pcall(pin:GetScript("OnEnter"), pin, false)
        """)
        self.assertTrue(self.ev("ok"))
        self.assertEqual(self.ev("#errors"), 1)
        self.assertIn("mine broke", self.ev("errors[1]"))

    def test_clear_and_shown_are_the_set_s(self):
        self.lua.execute("built = true")
        self.lua.execute('local l = OM.Layer("Mine") l:Clear() l:SetShown(false) l:SetShown(1)')
        self.assertEqual(self.ev("cleared"), 1)
        self.assertEqual(list(self.ev("shown").values()), [False, True])

    def test_clear_leaves_the_pin_under_the_controller_s_cursor_first(self):
        # (PadView.lua is told of the layer's pins before they go back to be handed out again)
        self.lua.execute("built = true")
        self.lua.execute('l = OM.Layer("Mine") pin = l:AddPin(1429, 0.5, 0.5, { atlas = "x" }) l:Clear()')
        self.assertEqual(list(self.ev("order").values()), ["forget", "clear"])
        self.assertTrue(self.ev("forgot == l.set.pins and forgot[1] == pin"))
        # (and without the controller view's file, as on a client that hasn't it: cleared all the same)
        self.lua.execute("mod.PadViewForget = nil l:Clear()")
        self.assertEqual(self.ev("cleared"), 2)

    def test_which_map_is_on_screen(self):
        self.assertFalse(self.ev("OM.Showing()"))
        # (OpenMap's usual map stays "stitched" while the map is closed: not on screen then)
        self.lua.execute("stitched = true")
        self.assertFalse(self.ev("OM.Showing()"))
        self.lua.execute("mapShown = true")
        self.assertEqual(self.ev("OM.Showing()"), "stitched")
        # (the controller view on screen: OpenMap's usual map isn't set up then, but it's said first)
        self.lua.execute("stitched, padShown = false, true")
        self.assertEqual(self.ev("OM.Showing()"), "pad")

    def test_which_map_is_on_screen_without_blizzard_s_map(self):
        self.lua.execute("WorldMapFrame = nil stitched = true")
        self.assertFalse(self.ev("OM.Showing()"))

    def test_other_addons_are_told_when_it_changes_and_only_then(self):
        self.lua.execute("padShown = true mod.OnPadView(true)")
        self.lua.execute("mod.OnPadView(true)")                      # (shown again: nothing new to tell)
        self.lua.execute("padShown = false mod.OnPadView(false)")
        self.lua.execute("mod.OnPadView(false)")
        self.assertEqual(list(self.ev("told").values()), ["pad", "false"])
        # (OpenMap's usual map: WorldMap.lua says so on every map change and resize)
        self.lua.execute("mapShown = true stitched = true mod.OnStitchedChanged(true) mod.OnStitchedChanged(true)")
        self.lua.execute("stitched = false mod.OnStitchedChanged(false)")
        self.assertEqual(list(self.ev("told").values()), ["pad", "false", "stitched", "false"])

    def test_the_usual_map_goes_off_screen_and_comes_back_with_blizzard_s_map(self):
        # (it stays stitched while closed, and WorldMap.lua says nothing then: Blizzard's map's own show and hide)
        self.assertEqual(self.ev("loadedFor"), "Blizzard_WorldMap")
        self.lua.execute("stitched = true MapShown(true)")
        self.lua.execute("MapShown(false)")
        self.lua.execute("MapShown(true)")
        self.assertEqual(list(self.ev("told").values()), ["stitched", "false", "stitched"])

    def test_the_controller_view_goes_off_screen_with_blizzard_s_map(self):
        # (told as the map hides, before PadView.lua's own word comes; that one adds nothing then)
        self.lua.execute("padShown = true MapShown(true) mod.OnPadView(true)")
        self.lua.execute("padShown = false MapShown(false) mod.OnPadView(false)")
        self.assertEqual(list(self.ev("told").values()), ["pad", "false"])


if __name__ == "__main__":
    unittest.main()
