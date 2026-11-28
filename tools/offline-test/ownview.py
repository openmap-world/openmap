"""The own view, the map in a fight (OwnView.lua, Stitch.lua's S.Rehost) in Lua 5.1:
python -P tools/offline-test/ownview.py.

In combat OpenMap's art, chart and icons move onto frames of OpenMap's own, which it scrolls and scales
itself; Blizzard's map is left as it is (nothing written: #345 #347 #368). Checked here:
- OwnView.lua touches nothing of Blizzard's map but reads, and its canvas's alpha (see the file's head);
- the canvas is placed so the host map's point (x, y) is at the view's centre at the scale asked for;
- HereBeDragons' icons (Questie's ...) land at their world point on the view, and go back to their pin;
- the switch up and down keeps OpenMap's frames' levels and gives them back;
- S.Rehost moves the art and icon layer onto OpenMap's frames and back, anchored as Layout has them.
"""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"
OWNVIEW = (ROOT / "Map" / "OwnView.lua").read_text(encoding="utf-8")
STITCH = (ROOT / "Map" / "Stitch.lua").read_text(encoding="utf-8")


class NoBlizzardWritesTests(unittest.TestCase):
    """every use of Blizzard's map in OwnView.lua is a read, but the canvas's alpha"""

    READS = {"GetCanvasScale", "GetCurrentScrollX", "GetCurrentScrollY", "GetWidth", "GetHeight", "IsShown",
             "GetMapID"}

    def test_only_reads(self):
        for i, line in enumerate(OWNVIEW.splitlines(), 1):
            code = line.split("--")[0]
            for m in re.finditer(r"\b(sc|map)((?:\.Child)?)\s*([.:])\s*(\w+)\s*(=?)", code):
                name, op, assign = m.group(4), m.group(3), m.group(5)
                self.assertNotEqual(assign, "=", "line %d writes a field: %s" % (i, line.strip()))
                if op == ":":
                    allowed = name in self.READS or (m.group(2) == ".Child" and name == "SetAlpha")
                    self.assertTrue(allowed, "line %d calls %s on Blizzard's map: %s" % (i, name, line.strip()))
                elif m.group(2) == "" and name not in ("ScrollContainer", "Child"):
                    self.fail("line %d reads a field of Blizzard's map: %s" % (i, line.strip()))

    def test_no_blizzard_method_replaced_or_hooked(self):
        self.assertNotRegex(OWNVIEW, r"hooksecurefunc\(\s*(sc|map)\b")
        self.assertNotRegex(OWNVIEW, r"\b(WorldMapFrame|QuestMapFrame)\b")


def frames_stub():
    return r"""
    frames = {}
    local function Frame(parent)
        local f = { parent = parent, level = parent and (parent.level or 0) + 1 or 0, scale = 1, children = {},
            shown = true, alpha = 1, w = 0, h = 0 }
        if parent then parent.children[#parent.children + 1] = f end
        function f:GetParent() return self.parent end
        function f:SetParent(p)
            if self.parent then for i, c in ipairs(self.parent.children) do if c == self then table.remove(self.parent.children, i) break end end end
            self.parent = p
            if p then p.children[#p.children + 1] = self end
            -- (as the game: a frame given another parent goes one level over it, its children with it)
            if p then self:SetFrameLevel(p.level + 1) end
        end
        function f:GetChildren() return unpack(self.children) end
        function f:GetFrameLevel() return self.level end
        -- (as the game: a frame's children move with it when its level changes)
        local function shift(fr, d) for _, c in ipairs(fr.children) do c.level = c.level + d shift(c, d) end end
        function f:SetFrameLevel(l) local d = l - self.level self.level = l shift(self, d) end
        function f:SetScale(s) self.scale = s end
        function f:GetScale() return self.scale end
        function f:ClearAllPoints() self.point = nil end
        function f:SetPoint(...) self.point = { ... } end
        function f:SetAllPoints(t) self.point = { "ALL", t } if t then self.w, self.h = t.w, t.h end end
        function f:SetSize(w, h) self.w, self.h = w, h end
        function f:GetWidth() return self.w end
        function f:GetHeight() return self.h end
        function f:Show() self.shown = true end
        function f:Hide() self.shown = false end
        function f:IsShown() return self.shown end
        function f:SetAlpha(a) self.alpha = a end
        function f:GetAlpha() return self.alpha end
        function f:SetFixedFrameLevel(on) self.fixed = on end
        function f:SetFrameStrata(st) self.strata = st end
        function f:GetFrameStrata() return self.strata or (self.parent and self.parent:GetFrameStrata()) or "MEDIUM" end
        function f:HasFixedFrameLevel() return self.fixed or false end
        function f:EnableMouse() end
        function f:EnableMouseWheel() end
        function f:SetClipsChildren() end
        function f:SetScript(k, fn) self[k] = fn end
        frames[#frames + 1] = f
        return f
    end
    _G.Frame = Frame
    function CreateFrame(_, _, parent) return Frame(parent) end
    """


class OwnViewTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(frames_stub() + r"""
            fight = true
            function InCombatLockdown() return fight end
            function IsMouseButtonDown() return false end
            wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
            -- Blizzard's map: a scroll container 800 x 600 and its canvas 2000 x 1500 at scale 2, scrolled to (0.4, 0.6)
            sc = Frame(nil) sc.w, sc.h = 800, 600
            sc.Child = Frame(sc) sc.Child.w, sc.Child.h = 2000, 1500
            function sc:GetCanvasScale() return 2 end
            function sc:GetCurrentScrollX() return 0.4 end
            function sc:GetCurrentScrollY() return 0.6 end
            map = Frame(nil) map.ScrollContainer = sc
            function map:GetMapID() return 1429 end
            -- OpenMap's frames, on Blizzard's canvas as Stitch.lua puts them
            art = Frame(sc.Child) art.level = 2100
            layer = Frame(art) layer.level = 2120
            icons = Frame(sc) icons.level = 2190
            set = Frame(icons) set.level = 2193
            rehosted = nil
            S = { IsBuilt = function() return true end, Rect = function() return 0, 1, 0, 1 end }
            function S.Roots() return art, icons, nil end
            function S.Rehost(c)
                rehosted = c
                art:SetParent(c or sc.Child)
                icons:SetParent(c and c:GetParent() or sc)
            end
            mod = { own = { on = false } }
            function mod.IsStitched() return true end
            ns = { MapStitch = S, Safe = { Finite = function() return true end } }
            function ns:GetModule() return mod end
            -- WorldMap.lua's maths: world = the host map's normalized point; a view px is 1/1000 of the world at zoom 1
            function mod.OwnInput()
                return {
                    View = function()
                        local o = mod.own
                        if o.on then return o.x, o.y, o.scale end
                        return 0.4, 0.6, 2
                    end,
                    PerPx = function(zoom) return 1 / (1000 * zoom), 1 / (1000 * zoom) end,
                    CursorOffset = function() return 0, 0 end,
                    Wheel = function() end, PressDown = function() end, Click = function() end, Grab = function() end,
                }
            end
        """)
        self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", OWNVIEW)
        self.lua.execute("mod:SetupOwnView(map)")

    def test_up_only_in_a_fight(self):
        self.lua.execute("fight = false")
        self.assertFalse(self.lua.eval("mod.OwnViewStart()"))
        self.lua.execute("fight = true")
        self.assertTrue(self.lua.eval("mod.OwnViewStart()"))

    def test_up_at_the_view_blizzards_canvas_has(self):
        self.lua.eval("mod.OwnViewStart")()
        own = self.lua.eval("mod.own")
        self.assertEqual((own.scale, own.x, own.y), (2, 0.4, 0.6))

    def test_canvas_puts_the_point_at_the_centre(self):
        self.lua.eval("mod.OwnViewStart")()
        self.lua.execute("mod.own.scale, mod.own.x, mod.own.y = 3, 0.25, 0.5 mod.OwnViewPlace()")
        # (the canvas's TOPLEFT offset in its own units: the point x * width at the view's centre at scale 3)
        p = self.lua.eval("rehosted.point")
        ox, oy = p[4], p[5]
        self.assertAlmostEqual((ox + 0.25 * 2000) * 3, 400)
        self.assertAlmostEqual((-oy + 0.5 * 1500) * 3, 300)
        self.assertEqual(self.lua.eval("rehosted.scale"), 3)

    def test_nothing_of_blizzards_canvas_moved(self):
        self.lua.eval("mod.OwnViewStart")()
        self.lua.execute("mod.own.scale, mod.own.x = 5, 0.1 mod.OwnViewPlace()")
        self.assertIsNone(self.lua.eval("sc.Child.point"))
        self.assertEqual(self.lua.eval("sc.Child.scale"), 1)
        self.assertEqual(self.lua.eval("sc.Child.alpha"), 0)     # (see-through only)

    def test_levels_lifted_and_given_back(self):
        self.lua.eval("mod.OwnViewStart")()
        self.assertGreater(self.lua.eval("art.level"), 9000)
        self.assertEqual(self.lua.eval("layer.level - art.level"), 20)    # (their order kept)
        self.assertEqual(self.lua.eval("set.level - icons.level"), 3)
        self.lua.execute("fight = false mod.OwnViewStop(false)")
        self.assertEqual((self.lua.eval("art.level"), self.lua.eval("layer.level"), self.lua.eval("icons.level"),
                          self.lua.eval("set.level")), (2100, 2120, 2190, 2193))
        self.assertEqual(self.lua.eval("sc.Child.alpha"), 1)
        self.assertIsNone(self.lua.eval("rehosted"))

    def test_icons_on_a_strata_over_the_arts_and_given_back(self):
        self.lua.eval("mod.OwnViewStart")()
        self.assertEqual(self.lua.eval("icons:GetFrameStrata()"), "HIGH")
        self.assertEqual(self.lua.eval("art:GetFrameStrata()"), "MEDIUM")
        self.lua.execute("fight = false mod.OwnViewStop(false)")
        self.assertEqual(self.lua.eval("icons:GetFrameStrata()"), "MEDIUM")

    def test_icons_over_the_art_and_not_under_the_see_through_canvas(self):
        # (no icons in a fight, test11: every level counted twice put the art at the top, over the icons)
        self.lua.eval("mod.OwnViewStart")()
        self.assertGreater(self.lua.eval("set.level"), self.lua.eval("layer.level"))
        self.assertLess(self.lua.eval("set.level"), 9900)
        # (OpenMap's icon layer on the view, not under Blizzard's canvas, which is made see-through)
        self.lua.execute("""
            function under(f, anc) while f do if f == anc then return true end f = f.parent end return false end
        """)
        self.assertFalse(self.lua.eval("under(icons, sc.Child)"))
        self.assertFalse(self.lua.eval("under(set, sc.Child)"))
        self.assertEqual(self.lua.eval("icons.alpha"), 1)

    def test_frames_made_later_at_the_arts_levels_are_lifted(self):
        # (the close-up's, a shade's: made in the fight at the art's own levels, under the view)
        self.lua.eval("mod.OwnViewStart")()
        self.lua.execute("late = Frame(layer) late.level = 2125")
        self.lua.execute("for _, f in ipairs(frames) do if f.OnUpdate then f.OnUpdate(f, 1) end end")
        self.assertEqual(self.lua.eval("late.level - layer.level"), 5)
        self.lua.execute("fight = false mod.OwnViewStop(false)")
        self.assertEqual(self.lua.eval("late.level"), 2125)

    def test_combat_over_puts_the_view_on_blizzards_canvas_first(self):
        self.lua.execute("""
            calls = {}
            function mod.SetViewNow(s, x, y) calls[#calls + 1] = { 'set', s, x, y, mod.own.on, rehosted ~= nil } end
            mod.OwnViewStart()
            mod.own.scale, mod.own.x, mod.own.y = 4, 0.3, 0.7
            fight = false
            mod.OwnViewStop(true)
        """)
        c = self.lua.eval("calls[1]")
        # (the own view off, so SetView writes Blizzard's canvas; the art still on OpenMap's frames: no jump)
        self.assertEqual((c[1], c[2], c[3], c[4], c[5], c[6]), ("set", 4, 0.3, 0.7, False, True))


class IconMirrorTests(unittest.TestCase):
    """HereBeDragons' icons put on the own view at their world point, and given back to their pin"""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(frames_stub() + r"""
            fight = true
            function InCombatLockdown() return fight end
            function IsMouseButtonDown() return false end
            wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
            sc = Frame(nil) sc.w, sc.h = 800, 600
            sc.Child = Frame(sc) sc.Child.w, sc.Child.h = 2000, 1500
            function sc:GetCanvasScale() return 1 end
            function sc:GetCurrentScrollX() return 0.5 end
            function sc:GetCurrentScrollY() return 0.5 end
            map = Frame(nil) map.ScrollContainer = sc
            function map:GetMapID() return 947 end
            art = Frame(sc.Child) icons = Frame(sc)
            S = { IsBuilt = function() return true end }
            function S.Rect(id) if id == 1429 then return 0.4, 0.6, 0.4, 0.6 end end
            function S.Roots() return art, icons, nil end
            function S.Rehost(c) art:SetParent(c or sc.Child) icons:SetParent(c and c:GetParent() or sc) end
            mod = { own = { on = false } }
            function mod.IsStitched() return true end
            ns = { MapStitch = S, Safe = { Finite = function() return true end } }
            function ns:GetModule() return mod end
            function mod.OwnInput()
                return {
                    View = function() return 0.5, 0.5, 4 end,
                    PerPx = function(zoom) return 1 / (1000 * zoom), 1 / (1000 * zoom) end,
                    CursorOffset = function() return 0, 0 end,
                    Wheel = function() end, PressDown = function() end, Click = function() end, Grab = function() end,
                }
            end
            -- a pins library with two icons: one on a pin of Blizzard's canvas, one at the map's edge (off the view)
            pin = Frame(sc.Child)
            near = Frame(pin) near.UiMapID, near.x, near.y = 1429, 50, 50
            near.level, near.fixed = 2101, true      -- (Questie's: a fixed level, from 2015 up)
            far = Frame(nil) far.UiMapID, far.x, far.y = 1429, 0, 0
            lib = { worldmapPins = { [near] = { uiMapID = 1429 }, [far] = { uiMapID = 1429 } } }
            LibStub = { IterateLibraries = function() return pairs({ ["HereBeDragons-Pins-2.0"] = lib }) end }
        """)
        self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", (ROOT / "Map" / "OwnView.lua").read_text(encoding="utf-8"))
        self.lua.execute("mod:SetupOwnView(map) mod.OwnViewStart() mod.own.u, mod.own.v, mod.own.zoom = 0.5, 0.5, 8 mod.OwnViewPlace()")

    def test_at_their_world_point(self):
        # (near: the zone's middle, 0.5, 0.5 in the world: the view's centre)
        self.assertEqual(self.lua.eval("near:GetParent() == pin"), False)
        p = self.lua.eval("near.point")
        self.assertEqual((p[1], p[4], p[5]), ("CENTER", 0, 0))
        self.assertTrue(self.lua.eval("near.shown"))

    def test_out_of_view_not_put_on_it(self):
        # (far: 0.4, 0.4 in the world, 800 view px off at zoom 8: past the view's half-width, 400)
        self.assertEqual(self.lua.eval("far.parent"), None)

    def test_over_the_layer_though_its_level_is_fixed(self):
        # (test15: Questie's icons kept their fixed 2101, under the view's art)
        layer = self.lua.eval("near.parent")
        self.assertGreater(self.lua.eval("near.level"), layer.level)
        self.assertGreater(self.lua.eval("near.level"), 9000)
        self.assertTrue(self.lua.eval("near.fixed"))

    def test_its_own_level_given_back(self):
        self.lua.execute("fight = false mod.OwnViewStop(false)")
        self.assertEqual(self.lua.eval("near.level"), 2101)
        self.assertTrue(self.lua.eval("near.fixed"))

    def test_given_back_to_their_pin(self):
        self.lua.execute("fight = false mod.OwnViewStop(false)")
        self.assertTrue(self.lua.eval("near:GetParent() == pin"))
        p = self.lua.eval("near.point")
        self.assertEqual(p[1], "CENTER")
        self.assertTrue(self.lua.eval("near.point[2] == pin"))

    def release(self):
        # (the library's pin released in the fight, as HereBeDragons' OnReleased: the icon hidden, on UIParent)
        self.lua.execute("""
            UIParent = Frame(nil)
            near:Hide() near:SetParent(UIParent) near:ClearAllPoints()
            for _, f in ipairs(frames) do if f.OnUpdate then f.OnUpdate(f, 1) end end
        """)

    def test_released_icon_not_given_back_to_the_screen(self):
        # (taken again from UIParent, it was given back there as the map closed: in the middle of the screen)
        self.release()
        self.assertTrue(self.lua.eval("near.shown"))
        self.lua.execute("fight = false mod.OwnViewStop(false)")
        self.assertFalse(self.lua.eval("near:GetParent() == UIParent"))
        self.assertFalse(self.lua.eval("near.shown"))

    def test_not_given_back_to_a_pin_holding_another_icon(self):
        self.lua.execute("other = Frame(nil) pin.icon = other")
        self.lua.execute("fight = false mod.OwnViewStop(false)")
        self.assertFalse(self.lua.eval("near:GetParent() == pin"))
        self.assertFalse(self.lua.eval("near.shown"))


class RehostTests(unittest.TestCase):
    """S.Rehost: root, the chart and pinRoot onto OpenMap's frames and back, anchored as Layout has them"""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        m = re.search(r"\nfunction S\.Rehost\(canvas\)\n.*?\nend\n", STITCH, re.S)
        self.assertIsNotNone(m)
        self.lua.execute(frames_stub() + r"""
            S = {}
            sc = Frame(nil)
            blizzCanvas = Frame(sc)
            S.chartHost = { blizzCanvas, 10 }
            root = Frame(blizzCanvas)
            pinRoot = Frame(sc)
            host = { l = 300, t = 200 }
            view = Frame(sc)
            ownCanvas = Frame(view)
        """ + m.group(0))

    def test_onto_and_back(self):
        self.lua.execute("S.Rehost(ownCanvas)")
        self.assertTrue(self.lua.eval("root:GetParent() == ownCanvas"))
        self.assertTrue(self.lua.eval("pinRoot:GetParent() == view"))
        p = self.lua.eval("root.point")
        self.assertEqual((p[1], p[3], p[4], p[5]), ("TOPLEFT", "TOPLEFT", -300, 200))
        self.assertTrue(self.lua.eval("root.point[2] == ownCanvas"))
        self.lua.execute("S.Rehost(nil)")
        self.assertTrue(self.lua.eval("root:GetParent() == blizzCanvas"))
        self.assertTrue(self.lua.eval("pinRoot:GetParent() == sc"))
        self.assertTrue(self.lua.eval("root.point[2] == blizzCanvas"))


if __name__ == "__main__":
    unittest.main()
