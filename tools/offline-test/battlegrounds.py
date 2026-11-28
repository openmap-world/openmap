"""Battlegrounds' maps in Lua 5.1 (Map/Battlegrounds.lua with Data/<client>/Battlegrounds.lua): the zoom
steps put on Blizzard's map of one, and the battleground's minimap tiles laid over it, cut to it and
mixed in as it zooms: python -P tools/offline-test/battlegrounds.py."""
from pathlib import Path
import os
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"
CLIENT = {"forever": "Forever", "retail": "Retail"}[os.environ.get("OPENMAP_CLIENT", "forever").lower()]
DATA = ROOT / "Data" / CLIENT / "Battlegrounds.lua"


@unittest.skipUnless(DATA.exists(), "this client has no battlegrounds' data")
class BattlegroundTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            hooks = {}
            function hooksecurefunc(t, name, fn)
                local was = t[name]
                t[name] = function(...) local a, b, c = was(...) fn(...) return a, b, c end
            end
            function InCombatLockdown() return false end
            -- regions that remember what was done to them
            local R = {}
            R.__index = R
            local function New(kind, parent)
                local r = setmetatable({ kind = kind, parent = parent, shown = true, alpha = 1, points = {}, kids = {} }, R)
                if parent then table.insert(parent.kids, r) end
                return r
            end
            function R:Show() self.shown = true end
            function R:Hide() self.shown = false end
            function R:SetShown(v) self.shown = v and true or false end
            function R:IsShown() return self.shown end
            function R:SetAlpha(a) self.alpha = a end
            function R:SetAllPoints() end
            function R:SetFrameLevel(l) self.level = l end
            function R:GetParent() return self.parent end
            function R:GetWidth() return self.w end
            function R:GetHeight() return self.h end
            function R:CreateTexture() return New("Texture", self) end
            function R:CreateMaskTexture() return New("MaskTexture", self) end
            function R:AddMaskTexture(m) self.mask = m end
            function R:SetTexture(f) self.file = f end
            function R:SetTexCoord(l, r, t, b) self.coord = { l, r, t, b } end
            function R:ClearAllPoints() self.points = {} end
            function R:SetPoint(_, _, _, x, y) self.points = { x, y } end
            function R:SetSize(w, h) self.size = { w, h } end
            function R:SetDesaturation(d) self.desat = d end
            function R:SetVertexColor(r, g, b) self.tint = { r, g, b } end
            function R:HookScript(name, fn) hooks[name] = fn end
            function CreateFrame(kind, _, parent) return New(kind, parent) end

            canvas = New("Frame")
            canvas.w, canvas.h = 1002, 668
            sc = New("Frame")
            sc.mapID, sc.scale = 1460, 0.8
            -- Blizzard's own zoom steps for a battleground's map: one (it doesn't zoom)
            function sc:CreateZoomLevels() self.zoomLevels = { { scale = 0.8, layerIndex = 1 } } created = (created or 0) + 1 end
            function sc:ResetZoom() self.scale = self.zoomLevels[1].scale end
            function sc:GetCanvasScale() return self.scale end
            map = New("Frame")
            map.ScrollContainer = sc
            map.mapID = 1460
            function map:GetMapID() return self.mapID end
            function map:GetCanvas() return canvas end
            function map:GetPinFrameLevelsManager() return { GetValidFrameLevel = function() return 42 end } end
            function map:OnMapChanged() end
            function map:OnCanvasScaleChanged() end
            function map:SetMap(id) self.mapID, sc.mapID = id, id sc:CreateZoomLevels() self:OnMapChanged() end

            names = { [1459] = "Alterac Valley", [1460] = "Warsong Gulch", [1461] = "Arathi Basin", [2524] = "Darkspear Islands" }
            C_Map = { GetMapInfo = function(id) return names[id] and { name = names[id] } end }
            stitched = false
            S = {}
            function S.MiniTileLook(t) t:SetDesaturation(0.35) t:SetVertexColor(1, 0.9, 0.7) end
            mod = { defaults = {}, db = { minimap = true, minimapMix = 0.45, minimapDeep = 0.85 } }
            function mod.IsStitched() return stitched end
            ns = { MapStitch = S, Media = { tex = "Tex\\\\" }, L = setmetatable({}, { __index = function(_, k) return k end }) }
            function ns:GetModule() return mod end
        """)
        g = self.lua.globals()
        load = self.lua.execute("return function(src, name, ns) local f = assert(loadstring(src, '@' .. name)) return f('OpenMap', ns) end")
        for path in (DATA, ROOT / "Map" / "Battlegrounds.lua"):
            load(path.read_text(encoding="utf-8"), path.name, g.ns)
        for k, v in self.lua.eval("mod.defaults").items():
            g.mod.db[k] = v
        self.lua.execute("mod:SetupBattlegrounds(map)")
        self.g = g

    def ids(self):
        return list(self.lua.eval("ns.MapBattlegrounds").keys())

    def test_data_covers_each_map(self):
        # every battleground's map is covered by its tiles, cut to it, none over another
        part = self.lua.eval("mod.BattlegroundTilePart")
        self.assertGreaterEqual(len(self.ids()), 3)
        for mid in self.ids():
            bg = self.lua.eval("ns.MapBattlegrounds")[mid]
            area = 0
            for key in bg[5].keys():
                p = part(bg, key)
                if p[0] is None: continue
                u0, v0, u1, v1, l, r, t, b = p
                self.assertTrue(0 <= u0 < u1 <= 1 and 0 <= v0 < v1 <= 1, (mid, key, p))
                self.assertTrue(0 <= l < r <= 1 and 0 <= t < b <= 1, (mid, key, p))
                area += (u1 - u0) * (v1 - v0)
            self.assertLessEqual(area, 1 + 1e-6, mid)
            # (the land the battleground has terrain in: Alterac Valley's map runs on past its, east and west)
            self.assertGreater(area, 0.6, mid)
            focus = bg[6]
            self.assertTrue(focus[1] < focus[3] and focus[2] < focus[4] and focus[1] < 0.5 < focus[3], mid)

    def test_zoom_steps(self):
        self.lua.execute("map:Show() hooks.OnShow() map:SetMap(1460)")
        zl = [z.scale for z in self.lua.eval("sc.zoomLevels").values()]
        deep = self.lua.eval("mod.BattlegroundDeepest(1460)")
        self.assertAlmostEqual(zl[0], 0.8)
        self.assertAlmostEqual(zl[-1], 0.8 * deep)
        self.assertGreaterEqual(deep, 4)
        for a, b in zip(zl, zl[1:]):
            self.assertGreater(b, a)
            self.assertLessEqual(b / a, 1.25 + 1e-9)
        # Alterac Valley, much bigger, goes further in
        self.assertGreater(self.lua.eval("mod.BattlegroundDeepest(1459)"), deep)

    def test_other_maps_keep_blizzards_steps(self):
        self.lua.execute("names[1413] = 'The Barrens' map:SetMap(1413)")
        self.assertEqual(len(self.lua.eval("sc.zoomLevels")), 1)
        self.lua.execute("stitched = true map:SetMap(1460)")
        self.assertEqual(len(self.lua.eval("sc.zoomLevels")), 1)

    def test_tiles_laid_out_and_mixed_in(self):
        self.lua.execute("map:Show() map:SetMap(1460)")
        layer = self.lua.eval("canvas.kids[1]")
        self.assertEqual(layer.level, 42)
        tex = [t for t in layer.kids.values() if t.shown and t.kind == "Texture"]
        mask = [t for t in layer.kids.values() if t.kind == "MaskTexture"]
        self.assertEqual(len(mask), 1)
        self.assertTrue(mask[0].file.endswith("MapFeather"))
        # (the focus box, from Data's: past the map's edges where it's set so)
        focus = self.lua.eval("ns.MapBattlegrounds[1460][6]")
        self.assertAlmostEqual(mask[0].points[1], focus[1] * 1002)
        self.assertAlmostEqual(mask[0].size[1], (focus[3] - focus[1]) * 1002)
        self.assertGreater(len(tex), 0)
        for t in tex:
            x, y = t.points[1], t.points[2]
            w, h = t.size[1], t.size[2]
            self.assertTrue(-1e-6 <= x and x + w <= 1002 + 1e-6 and y <= 1e-6 and -y + h <= 668 + 1e-6)
            self.assertEqual(t.desat, 0.35)
        # every tile through the mask
        self.assertTrue(self.lua.eval("""(function(layer)
            local m
            for _, k in ipairs(layer.kids) do if k.kind == "MaskTexture" then m = k end end
            for _, k in ipairs(layer.kids) do if k.kind == "Texture" and k.mask ~= m then return false end end
            return true end)(canvas.kids[1])"""))
        # the whole map: the painted map alone; zoomed right in: toward the minimap's most
        self.assertFalse(layer.shown)
        self.lua.execute("sc.scale = sc.zoomLevels[#sc.zoomLevels].scale map:OnCanvasScaleChanged()")
        self.assertTrue(layer.shown)
        self.assertAlmostEqual(tex[0].alpha, 0.85, places=3)
        mid = self.lua.eval("mod.BattlegroundMix(1460, 3)")
        self.assertTrue(0.3 < mid < 0.85, mid)
        # Minimap detail off: none
        self.lua.execute("mod.db.minimap = false map:OnCanvasScaleChanged()")
        self.assertFalse(layer.shown)

    def test_off(self):
        self.lua.execute("map:Show() map:SetMap(1460) sc.scale = 4 mod.SetBattlegroundMaps(false)")
        self.assertEqual(len(self.lua.eval("sc.zoomLevels")), 1)
        self.assertAlmostEqual(self.lua.eval("sc.scale"), 0.8)
        self.assertFalse(self.lua.eval("canvas.kids[1]").shown)
        self.lua.execute("mod.SetBattlegroundMaps(true)")
        self.assertGreater(len(self.lua.eval("sc.zoomLevels")), 1)

    def test_gamepad_ui_leaves_blizzards_map(self):
        self.lua.execute("InputUtil = { IsGamepadUIEnabled = function() return true end } map:Show() map:SetMap(1460)")
        self.assertEqual(len(self.lua.eval("sc.zoomLevels")), 1)
        self.assertFalse(self.lua.eval("canvas.kids[1] and canvas.kids[1].shown or false"))

    def test_closed_map_lets_go(self):
        self.lua.execute("map:Show() map:SetMap(1460) sc.scale = 4 map:OnCanvasScaleChanged() map:Hide() hooks.OnHide()")
        layer = self.lua.eval("canvas.kids[1]")
        self.assertFalse(layer.shown)
        self.assertFalse(any(t.shown for t in layer.kids.values() if t.kind == "Texture"))

    def enter(self, instanceID):
        # (in a battleground: Blizzard's zoom table remembered, to see nothing of OpenMap's replaced it)
        self.lua.execute("""
            function IsInInstance() return true, "pvp" end
            function GetInstanceInfo() return "", "pvp", 0, "", 40, 0, false, %d end
            local create = sc.CreateZoomLevels
            sc.CreateZoomLevels = function(self) create(self) blizzards = self.zoomLevels end
        """ % instanceID)

    def test_inside_its_battleground_blizzards_map(self):
        # (its zoom steps never OpenMap's there, switch on or off: Blizzard reads them as it resets the map, the scale a
        # right-click on a group dot reads; Report AFK was blocked, #472)
        self.enter(489)
        self.lua.execute("map:Show() hooks.OnShow() map:SetMap(1460) sc.scale = 4 map:OnCanvasScaleChanged()")
        self.assertTrue(self.lua.eval("sc.zoomLevels == blizzards"))
        self.assertEqual(len(self.lua.eval("sc.zoomLevels")), 1)
        # (the minimap's detail there only with Minimap detail at "Always", at Minimap strength at Blizzard's one view:
        # OpenMap's own layer. Not otherwise: it has no zoom to wait for, and nobody gets it who didn't ask)
        self.assertFalse(self.lua.eval("canvas.kids[1] and canvas.kids[1].shown or false"))
        self.assertEqual(self.lua.eval("mod.BattlegroundMix(1460, 1)"), 0)
        self.lua.execute("mod.db.minimapFrom = 1 map:OnCanvasScaleChanged()")
        self.assertTrue(self.lua.eval("canvas.kids[1] and canvas.kids[1].shown or false"))
        self.assertAlmostEqual(self.lua.eval("mod.BattlegroundMix(1460, 1)"), 0.45, places=3)
        self.lua.execute("mod.db.minimap = false map:OnCanvasScaleChanged()")
        self.assertFalse(self.lua.eval("canvas.kids[1].shown"))
        self.lua.execute("mod.db.minimap = true mod.SetBattlegroundMaps(false)")
        self.assertFalse(self.lua.eval("canvas.kids[1].shown"))
        self.lua.execute("mod.SetBattlegroundMaps(true)")
        self.assertTrue(self.lua.eval("sc.zoomLevels == blizzards"))
        before = self.lua.eval("created")
        self.lua.execute("mod.SetBattlegroundMaps(false) mod.SetBattlegroundMaps(true)")
        self.assertEqual(self.lua.eval("created"), before)

    def test_diagnostic(self):
        # (/openmap bg: three lines, on a battleground's map and on another)
        self.lua.execute("""
            printed = {}
            function ns:Print(t) printed[#printed + 1] = t end
            function IsInInstance() return true, "pvp" end
            map:Show() map:SetMap(1460) mod:BattlegroundDiag()
            names[1413] = 'The Barrens' map:SetMap(1413) mod:BattlegroundDiag()
        """)
        printed = list(self.lua.eval("printed").values())
        self.assertEqual(len(printed), 6)
        self.assertIn("Warsong Gulch", printed[0])
        self.assertIn("zoom steps", printed[1])
        self.assertIn("not a battleground's", printed[3])

    def test_inside_one_another_still_zooms(self):
        # (Alterac Valley's map looked at from Warsong Gulch: not the one you're in)
        self.enter(489)
        self.lua.execute("map:Show() map:SetMap(1459)")
        self.assertGreater(len(self.lua.eval("sc.zoomLevels")), 1)

    def test_search_places(self):
        places = self.lua.eval("mod.BattlegroundPlaces()")
        names = [p.name for p in places.values()]
        self.assertEqual(names, sorted(names))
        self.assertIn("Warsong Gulch", names)


if __name__ == "__main__":
    unittest.main()
