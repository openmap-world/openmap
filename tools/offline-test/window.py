"""Windowed resize and quest-log spacer anchoring in Lua 5.1; run with python -P tools/offline-test/window.py."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"


class WindowTests(unittest.TestCase):
    def test_spacer_anchoring_and_clamp_order(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
        local function noop() end
        ns = {
            L = setmetatable({}, { __index = function(_, k) return k end }),
            RegisterEvent = noop,
            GetModule = function() return mod end,
            Safe = { Value = function(v) return v end, Finite = function(v) return v end },
        }
        inCombat = false
        function InCombatLockdown() return inCombat end
        function hooksecurefunc(t, k, fn)
            local orig = t[k]
            t[k] = function(...)
                local r = { orig(...) }
                fn(...)
                return unpack(r)
            end
        end
        cursorX, cursorY = 500, 300
        function GetCursorPosition() return cursorX, cursorY end
        function IsMouseButtonDown() return true end
        C_Timer = { After = function(_, fn) fn() end }
        UIParent = { GetWidth = function() return 1920 end, GetHeight = function() return 1080 end }

        local function makeFrame()
            local f = { scripts = {}, width = 100, height = 100, scale = 1, shown = true }
            function f:SetSize(w, h) self.width = w; self.height = h end
            function f:SetWidth(w) self.width = w end
            function f:SetHeight(h) self.height = h end
            function f:SetMovable() end
            function f:GetWidth() return self.width end
            function f:GetHeight() return self.height end
            function f:GetEffectiveScale() return 1 end
            function f:GetScale() return self.scale end
            function f:SetScale(s) self.scale = s end
            function f:IsShown() return self.shown end
            function f:SetShown(v) self.shown = v and true or false end
            function f:Show() self.shown = true end
            function f:Hide() self.shown = false end
            function f:SetFrameLevel(v) self.level = v end
            function f:GetFrameLevel() return self.level or 1 end
            function f:SetFrameStrata(v) self.strata = v end
            function f:GetFrameStrata() return self.strata or "MEDIUM" end
            function f:SetPoint(...) local c = rawget(self, "calls"); if c then table.insert(c, "SetPoint") end end
            function f:ClearAllPoints() end
            function f:GetPoint() return "TOPLEFT", UIParent, "TOPLEFT", 100, -100 end
            function f:GetNumPoints() return 1 end
            function f:GetLeft() return 100 end
            function f:GetRight() return 800 end
            function f:GetTop() return 800 end
            function f:GetBottom() return 300 end
            function f:SetClampedToScreen() end
            function f:SetHitRectInsets() end
            function f:SetAlpha() end
            function f:SetNormalTexture() end
            function f:SetHighlightTexture() end
            function f:SetPushedTexture() end
            function f:GetNormalTexture() return { SetTexCoord = noop, SetVertexColor = noop, SetAllPoints = noop, SetBlendMode = noop, SetAlpha = noop } end
            function f:GetHighlightTexture() return { SetTexCoord = noop, SetVertexColor = noop, SetAllPoints = noop, SetBlendMode = noop, SetAlpha = noop } end
            function f:GetPushedTexture() return { SetTexCoord = noop, SetVertexColor = noop, SetAllPoints = noop, SetBlendMode = noop, SetAlpha = noop } end
            function f:SetText() end
            function f:SetNormalFontObject() end
            function f:SetClampRectInsets() local c = rawget(self, "calls"); if c then table.insert(c, "Clamp") end end
            function f:EnableMouse() end
            function f:RegisterForDrag() end
            function f:SetScript(k, v) self.scripts[k] = v end
            function f:HookScript(k, v)
                local prev = self.scripts[k]
                self.scripts[k] = function(...)
                    if prev then prev(...) end
                    v(...)
                end
            end
            function f:CreateTexture()
                return {
                    SetAllPoints = noop, SetSize = noop, SetPoint = noop,
                    SetTexture = noop, SetTexCoord = noop, SetAlpha = noop,
                }
            end
            return f
        end

        created = {}
        function CreateFrame()
            local f = makeFrame()
            table.insert(created, f)
            return f
        end

        testLog = makeFrame()
        testMap = makeFrame()
        testMap.calls = {}
        testMap.width, testMap.height = 700, 500
        testMap.QuestLog = testLog
        testMap.ScrollContainer = {
            OnCanvasSizeChanged = function() table.insert(testMap.calls, "Refit") end,
            GetFrameLevel = function() return 1 end,
        }
        function testMap:IsMaximized() return false end
        function testMap:UpdateSpacerFrameAnchoring() table.insert(self.calls, "Spacer") end

        mod = {
            defaults = {},
            db = { windowSize = { 900, 620 }, windowScale = 1 },
            ChatOverMap = noop,
            EndResize = noop,
            KeepPadCursor = function(fn, self) return fn(self) end,
        }
        ns.WorldMap = mod
        ''')
        source = (ROOT / 'Map/Window.lua').read_text(encoding='utf-8')
        lua.execute(source, 'OpenMap', lua.globals().ns)
        apply_calls, log_calls, combat_calls, drag_calls = lua.execute('''
        mod:SetupWindow(testMap)
        testMap.calls = {}
        testMap.scripts.OnShow(testMap)
        local applyCalls = table.concat(testMap.calls, ",")

        testMap.calls = {}
        testLog.scripts.OnShow(testLog)
        local logCalls = table.concat(testMap.calls, ",")

        testMap.calls = {}
        inCombat = true
        testLog.scripts.OnShow(testLog)
        local combatCalls = table.concat(testMap.calls, ",")
        inCombat = false

        local grip
        for _, f in ipairs(created) do
            if f.scripts.OnMouseDown and f.scripts.OnMouseUp then
                grip = f
                break
            end
        end
        testMap.calls = {}
        cursorX, cursorY = 500, 300
        grip.scripts.OnMouseDown(grip)
        cursorX, cursorY = 620, 220
        grip.scripts.OnUpdate(grip)
        grip.scripts.OnMouseUp(grip)
        local dragCalls = table.concat(testMap.calls, ",")

        return applyCalls, logCalls, combatCalls, dragCalls
        ''')
        self.assertIn("Spacer,Refit", apply_calls)
        self.assertEqual("Spacer,Refit", log_calls)
        self.assertEqual("", combat_calls)
        self.assertIn("Clamp,SetPoint", drag_calls)
        self.assertTrue(drag_calls.endswith("Spacer,Refit"))



if __name__ == "__main__":
    unittest.main()
