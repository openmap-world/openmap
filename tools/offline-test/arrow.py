"""Player arrow size (28px at 100%) and over-everything strata in Lua 5.1; run with python -P tools/offline-test/arrow.py."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"


class ArrowTests(unittest.TestCase):
    def test_arrow_default_size_scale_and_strata_only_on_own_arrow(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
        local function noop() end
        arrowSizes = {}
        arrowStrata = {}
        arrowLevels = {}
        ns = {
            L = setmetatable({}, { __index = function(_, k) return k end }),
            RegisterEvent = noop,
            Safe = { Value = function(v) return v end },
        }
        function ns:NewModule(_, m) self.mod = m; return m end
        function ns.Desc() return {} end
        function ns.Header() return {} end
        function ns.Bind(getTable, refresh)
            return function(info) return getTable()[info[#info]] end,
                function(info, value) getTable()[info[#info]] = value; refresh() end
        end
        function InCombatLockdown() return false end
        function IsInInstance() return false, "none" end
        Enum = { UIMapType = { Continent = 2, Zone = 3 } }
        C_Map = { GetMapInfo = function() return { mapType = 3 } end }
        MAP_CANVAS_MOUSE_WHEEL_ZOOM_BEHAVIOR_NONE = 0

        arrowTex = {
            SetTexture = noop,
            Hide = noop,
            Show = noop,
            IsShown = function() return true end,
            SetSize = function(_, w, h) table.insert(arrowSizes, { w, h }) end,
            GetParent = function() return arrowFrame end,
        }
        arrowFrame = {
            level = 1,
            strata = "MEDIUM",
            Hide = noop,
            Show = noop,
            SetScript = noop,
            GetFrameLevel = function(self) return self.level end,
            SetFrameLevel = function(self, v) self.level = v; table.insert(arrowLevels, v) end,
            GetFrameStrata = function(self) return self.strata end,
            SetFrameStrata = function(self, v) self.strata = v; table.insert(arrowStrata, v) end,
            CreateTexture = function() return arrowTex end,
        }
        function CreateFrame()
            return arrowFrame
        end
        ''')
        # Test Stitch.lua arrow base size (28px) and RaiseArrow strata
        stitch_src = (ROOT / 'Map/Stitch.lua').read_text(encoding='utf-8')
        # Extract SetPlayerScale and RaiseArrow + arrow creation check via WorldMap.lua + Stitch stubs
        lua.execute('''
        local S = {
            WORLD = 947, artTop = 180, built = true, playerScale = 1,
            IsBuilt = function() return true end,
            Rect = function() return 0, 1, 0, 1 end,
            ArtSize = function() return 1024 end,
            Size = function() return 1024, 768 end,
            Layout = function() return true end,
            Stitched = function() return true end,
            SetShown = function() end,
            GetPinSet = function() end,
            SetPlayer = function() end,
            SetPlayerHidden = function() end,
            SetWorldPinsHidden = function() end,
            SetPlacesFrom = function() end,
            SetFoundOnly = function() end,
            SetIconScale = function() end,
            SetGapFillsShown = function() end,
            ApplyGrade = function() end,
            SetZoom = function() end,
            RaiseArrow = function(level, strata)
                if strata then arrowFrame:SetFrameStrata(strata) end
                arrowFrame:SetFrameLevel(level)
            end,
            SetPlayerScale = function(k)
                arrowTex:SetSize(28 * k, 28 * k)
            end,
        }
        ns.MapStitch = S
        ''')
        # Verify Stitch.lua keeps 28 px as 100% (not 42), or Blizzard's own size for the player once known,
        # so OpenMap's arrow and Blizzard's are the same on screen in and out of combat
        self.assertIn("local ps, px = S.playerScale or 1, S.playerBase or 28", stitch_src)
        self.assertIn("arrow:SetSize(px * ps, px * ps)", stitch_src)
        self.assertIn("local px = S.playerBase or 28", stitch_src)
        self.assertIn("arrow:SetSize(px * k, px * k)", stitch_src)
        self.assertNotIn("42 * ps", stitch_src)
        self.assertNotIn("42 * k", stitch_src)

        wm_src = (ROOT / 'Map/WorldMap.lua').read_text(encoding='utf-8')
        mod, set_context = lua.execute(wm_src + '\nreturn mod, function(c, m, a) sc, map, active = c, m, a end', 'OpenMap', lua.globals().ns)
        lua.globals().mod = mod
        lua.globals().setContext = set_context
        group_strata_calls, group_levels, arrow_strata, arrow_level = lua.execute('''
        mod.db = {
            playerArrow = true,
            playerArrowScale = 1.5,
            playerArrowOnTop = true,
            iconScale = 1,
            iconsFrom = 1,
        }
        local groupStrataCalls = 0
        local groupLevels = {}
        local groupPin = {
            level = 10,
            strata = "MEDIUM",
            IsProtected = function() return false end,
            GetFrameLevel = function(self) return self.level end,
            SetFrameLevel = function(self, v) self.level = v; table.insert(groupLevels, v) end,
            GetFrameStrata = function(self) return self.strata end,
            SetFrameStrata = function(self, v) groupStrataCalls = groupStrataCalls + 1; self.strata = v end,
        }
        local sc = {
            GetFrameLevel = function() return 100 end,
            GetFrameStrata = function() return "MEDIUM" end,
            GetCanvasScale = function() return 1 end,
            GetWidth = function() return 1024 end,
            GetHeight = function() return 768 end,
            GetCurrentScrollX = function() return 0.5 end,
            GetCurrentScrollY = function() return 0.5 end,
        }
        local map = {
            IsShown = function() return true end,
            GetMapID = function() return 947 end,
            EnumeratePinsByTemplate = function(_, tpl)
                local done = false
                return function()
                    if not done and tpl == "GroupMembersPinTemplate" then
                        done = true
                        return groupPin
                    end
                end
            end,
        }
        setContext(sc, map, true)
        mod:Refresh()
        return groupStrataCalls, groupLevels[1], arrowFrame.strata, arrowFrame.level
        ''')
        self.assertEqual(0, group_strata_calls)
        self.assertLess(group_levels, 9000)
        self.assertEqual("HIGH", arrow_strata)
        self.assertEqual(9990, arrow_level)


if __name__ == "__main__":
    unittest.main()
