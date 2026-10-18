"""Caves underground in Lua 5.1 (Close.lua with Data/Caves.lua and Data/CaveMinimap.lua):
python -P tools/offline-test/caves.py."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"


class CaveTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            wipe = function(t) for k in pairs(t) do t[k] = nil end return t end
            tremove = table.remove
            GetTime = function() return 0 end
            errors = {}
            geterrorhandler = function() return function(e) table.insert(errors, e) end end
            -- frames and textures that remember what was done to them
            local function Region(kind, parent)
                local r = { kind = kind, parent = parent, calls = {}, shown = true, alpha = 1, level = 1, children = {} }
                if parent then table.insert(parent.children, r) end
                return setmetatable(r, { __index = function(t, k)
                    return function(self, ...) self.calls[k] = { ... } end
                end })
            end
            local F = {}
            function F.Show(self) self.shown = true end
            function F.Hide(self) self.shown = false end
            function F.SetShown(self, v) self.shown = v and true or false end
            function F.SetAlpha(self, a) self.alpha = a end
            function F.GetFrameLevel(self) return self.level end
            function F.SetFrameLevel(self, l) self.level = l end
            function F.CreateTexture(self, _, layer, _, sub) local t = Region("Texture", self) t.layer, t.sub = layer, sub return t end
            function F.CreateMaskTexture(self) return Region("MaskTexture", self) end
            local function New(kind, parent)
                local r = Region(kind, parent)
                for k, fn in pairs(F) do rawset(r, k, fn) end
                return r
            end
            function CreateFrame(kind, _, parent) return New(kind, parent) end

            -- the world: an even projection of yards (Stitch.lua's S.FromYards), 44700 yards across
            local O = 32 * 1600 / 3
            S = { viewHooks = {} }
            function S.Size() return 1.5, 1 end
            S.CaveMasks = "MapCave/"
            function S.FromYards(cont, x, y)
                local du = cont == 0 and 0.55 or 0.04
                return du + (8000 - y) / 44700, 0.1 + (6933 - x) / 29800
            end
            function S.ChainAt() return { 947, contMap } end
            function S.PlaceWorld(region, u0, v0, u1, v1) region.place = { u0, v0, u1, v1 } end
            function S.SetUnderground(t) underground = t end
            contMap = 1415
            setmetatable(S, { __index = function() return function() end end })

            mod = { defaults = {}, db = { underground = true } }
            ns = { MapStitch = S, Media = { path = "Interface\\\\AddOns\\\\OpenMap\\\\Media\\\\" },
                L = setmetatable({}, { __index = function(_, k) return k end }) }
            function ns:GetModule() return mod end
        """)
        g = self.lua.globals()
        for rel in ("Data/Caves.lua", "Data/CaveMinimap.lua", "Map/Close.lua"):
            fn = self.lua.execute("return function(src, name, ns) local f = assert(loadstring(src, '@' .. name)) return f('OpenMap', ns) end")
            fn((ROOT / rel).read_text(encoding="utf-8"), rel, g.ns)
        self.lua.execute("""
            under = CreateFrame("Frame")
            S.closeLayers = { under = under, minimap = CreateFrame("Frame"), grain = CreateFrame("Frame") }
            -- a cave from the minimap's list: the first a few hundred yards across, and its middle
            function Pick(cont, least, most)
                for i, c in ipairs(ns.MapCaveMinimap) do
                    local w = math.max(c[4] - c[2], c[5] - c[3])
                    if c[1] == cont and w >= least and w <= most then return i, c end
                end
            end
            function Middle(c)
                contMap = c[1] == 0 and 1415 or 1414    -- (the view over its continent)
                return S.FromYards(c[1], (c[2] + c[4]) / 2, (c[3] + c[5]) / 2)
            end
            -- the view on a world point, `across` normalized wide (3:2), at zoom `steps`
            function Look(u, v, across, steps)
                S.SetView(u, v, across / 2, across / 3, steps, steps)
            end
            function Shown()
                local out = {}
                for _, f in ipairs(under.children) do
                    if f.kind == "Frame" and f.shown then table.insert(out, f) end
                end
                return out
            end
            -- the frame showing a picture file, if one is up
            function Up(fid)
                for _, f in ipairs(Shown()) do
                    for _, t in ipairs(f.children) do
                        if t.kind == "Texture" and t.calls.SetTexture and t.calls.SetTexture[1] == fid then return f end
                    end
                end
            end
        """)

    def test_minimap_cave_surfaces_as_it_fills_the_view(self):
        self.lua.execute("""
            local i, c = Pick(0, 150, 300)
            assert(i, 'a cave of a few hundred yards')
            local u, v = Middle(c)
            local u0, v0, u1, v1 = S.CaveRectAt(u, v)
            assert(u0 and u0 < u and u < u1 and v0 < v and v < v1, 'its box round its middle')
            local w = u1 - u0
            local p = c[6]
            Look(u, v, w * 20, 120)                -- a speck: not yet
            assert(not Up(p[1]), 'surfaced as a speck')
            Look(u, v, w * 1.2, 120)               -- it fills the view
            local shown = { Up(p[1]) }
            assert(shown[1], 'up')
            assert(shown[1].alpha > 0.95, 'all the way up: ' .. shown[1].alpha)
            assert(underground > 0.9, 'the surface dims round it')
            -- each picture: the game's file, clamped to nothing past it, turned as the data says,
            -- a square of its side round its centre
            local textures = 0
            for _, t in ipairs(shown[1].children) do
                if t.kind == "Texture" then textures = textures + 1 end
            end
            assert(textures == #c[6] / 7, 'every picture: ' .. textures)
            local t = shown[1].children[1]
            assert(t.calls.SetTexture[1] == p[1] and t.calls.SetTexture[2] == "CLAMPTOBLACKADDITIVE")
            assert(t.calls.SetRotation[1] == p[5])
            local tc = t.calls.SetTexCoord
            assert(tc[1] == 0 and tc[2] == p[6] and tc[3] == p[7] and tc[4] == 1)
            local cu, cv = S.FromYards(c[1], p[2], p[3])
            local pl = t.place
            assert(math.abs((pl[1] + pl[3]) / 2 - cu) < 1e-9 and math.abs((pl[2] + pl[4]) / 2 - cv) < 1e-9, 'centred')
            assert(math.abs((pl[3] - pl[1]) - p[4] / 44700) < 1e-9 and math.abs((pl[4] - pl[2]) - p[4] / 29800) < 1e-9, 'its side')
            -- lowest floor first: draw sublevels never fall
            local last = -9
            for _, tx in ipairs(shown[1].children) do
                if tx.kind == "Texture" then assert(tx.sub >= last and tx.sub <= 7) last = tx.sub end
            end
            Look(u, v, w * 20, 120)                -- back out: it sinks
            assert(not Up(p[1]))
        """)

    def test_a_cave_waits_for_the_zoom(self):
        self.lua.execute("""
            local _, c = Pick(1, 400, 900)
            local u, v = Middle(c)
            local u0, _, u1 = S.CaveRectAt(u, v)
            Look(u, v, (u1 - u0) * 1.2, 20)        -- it would fill the view, but the zoom's a zone's
            assert(not Up(c[6][1]))
            Look(u, v, (u1 - u0) * 1.2, 60)
            assert(Up(c[6][1]))
        """)

    def test_blizzards_cave_map_surfaces_too(self):
        self.lua.execute("""
            local c = ns.MapCaves[38]            -- Fargodeep Mine
            local u, v = S.FromYards(c[2], (c[3] + c[5]) / 2, (c[4] + c[6]) / 2)
            local u0, v0, u1, v1 = S.CaveRectAt(u, v)
            assert(u0, 'its box')
            Look(u, v, (u1 - u0) * 1.2, 120)
            assert(Up(c[11][1]))
        """)

    def test_nothing_round_open_ground_and_the_option_off(self):
        self.lua.execute("""
            assert(S.CaveRectAt(0.02, 0.98) == nil, 'a cave out at sea')
            local _, c = Pick(0, 150, 300)
            local u, v = Middle(c)
            mod.db.underground = false
            assert(S.CaveRectAt(u, v) == nil, 'the zoom goes on with caves off')
            Look(u, v, 0.001, 120)
            assert(#Shown() == 0)
        """)

    def test_the_cave_at_an_entrance(self):
        self.lua.execute("""
            local i, c = Pick(1, 100, 900)
            local key, u0 = S.CaveAt(c[1], (c[2] + c[4]) / 2, (c[3] + c[5]) / 2)
            assert(u0, 'found')
            assert(key == -i or ns.MapCaves[key], 'a cave of either list')
        """)

    def tearDown(self):
        errs = list(self.lua.globals().errors.values())
        failed = dict(self.lua.globals().S.closeFailed.items())
        self.assertNotIn("underground", failed, failed.get("underground"))
        self.assertFalse([e for e in errs if "underground" in str(e)], errs)


if __name__ == "__main__":
    unittest.main()
