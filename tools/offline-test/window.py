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
        UIParent = { GetWidth = function() return 1920 end, GetHeight = function() return 1080 end, GetEffectiveScale = function() return 1 end }

        local function makeFrame()
            local f = { scripts = {}, width = 100, height = 100, scale = 1, shown = true }
            function f:SetSize(w, h) self.width = w; self.height = h end
            function f:SetWidth(w) self.width = w end
            function f:SetHeight(h) self.height = h end
            function f:SetMovable() end
            function f:GetWidth() return self.width end
            function f:GetSize() return self.width, self.height end
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
            Skipped = function() return false end,
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

        # after /openmap reset (no place, size or scale saved), and in a battleground too: the corner still sizes
        # the window (test14's guard there made it inert; Report AFK's source was the Escape list, #472)
        for where in ("", 'function IsInInstance() return true, "pvp" end'):
            calls = lua.execute('''
            %s
            mod.db.window, mod.db.windowSize, mod.db.windowScale = false, false, 1
            local grip
            for _, f in ipairs(created) do
                if f.scripts.OnMouseDown and f.scripts.OnMouseUp then grip = f break end
            end
            testMap.calls = {}
            cursorX, cursorY = 500, 300
            grip.scripts.OnMouseDown(grip)
            cursorX, cursorY = 640, 200
            grip.scripts.OnUpdate(grip)
            grip.scripts.OnMouseUp(grip)
            IsInInstance = nil
            return table.concat(testMap.calls, ","), mod.db.windowSize and mod.db.windowSize[1] or 0
            ''' % where)
            self.assertIn("SetPoint", calls[0], where)
            self.assertGreater(calls[1], 0, where)                 # (the new size kept)

        # in a battleground or arena: Blizzard's window, laid out by Blizzard. Opening it, its quest log, a size or place
        # saved, the full-screen width: nothing from here (each left the map's scale or anchors OpenMap's, and Report AFK
        # from a group dot was blocked, #472). Outside, the saved size is put back again
        bg = lua.execute('''
        function IsInInstance() return true, "pvp" end
        mod.db.window, mod.db.windowSize, mod.db.fullWidth = { "TOPLEFT", "TOPLEFT", 40, -40 }, { 900, 620 }, true
        testMap.width, testMap.height = 700, 500
        testMap.calls = {}
        testMap.scripts.OnShow(testMap)
        testLog.scripts.OnShow(testLog)
        local windowed = table.concat(testMap.calls, ",")
        testMap.IsMaximized = function() return true end
        testMap.calls = {}
        testMap.scripts.OnShow(testMap)
        local maximized = table.concat(testMap.calls, ",") .. ":" .. testMap.width
        testMap.IsMaximized = function() return false end
        IsInInstance = nil
        testMap.calls = {}
        testMap.scripts.OnShow(testMap)
        return windowed, maximized, table.concat(testMap.calls, ","), testMap.width
        ''')
        self.assertEqual(bg[0], "")
        self.assertEqual(bg[1], ":700")
        self.assertIn("Spacer,Refit", bg[2])
        self.assertEqual(bg[3], 900)



    def test_not_clamped_until_moved_or_sized(self):
        # (the clamp is OpenMap's change to Blizzard's window: made at login, every opening read OpenMap's taint on its
        # anchor and Report AFK from a group dot was blocked in battlegrounds, #472. test19's log: with a place or size
        # saved it was still clamped at login, and blocked. Only once you move or size it, never in a battleground)
        src = (ROOT / 'Map/Window.lua').read_text(encoding='utf-8')
        setup = src[src.index("function mod:SetupWindow("):]
        self.assertNotIn("\t\tmap:SetClampedToScreen(true)\n", setup)
        self.assertNotIn("then ClampOn() end", setup)
        self.assertEqual(src.count("ClampOn()"), 2 + 1)      # (the grip's, the title bar's; and its own definition's name)
        on = src[src.index("local function ClampOn()"):]
        self.assertIn("InPvP()", on[:on.index("\nend")])


class BisectTests(unittest.TestCase):
    def test_left_out_only_in_the_version_it_was_set_in(self):
        # (/openmap bisect, for the test builds: a new version starts with everything on, the parts a test left out
        # forgotten, so nobody plays on with half of OpenMap off)
        src = (ROOT / 'Map/WorldMap.lua').read_text(encoding='utf-8')
        part = src[src.index("mod.BISECT = "):src.index("local function Timed(")]
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('printed = {} ns = { version = "v1", Print = function(_, m) printed[#printed + 1] = m end } mod = { db = {} }')
        lua.execute(part)
        lua.execute('mod:Bisect("Window Battlegrounds")')
        self.assertTrue(lua.eval('mod.Skipped("Window")'))
        self.assertFalse(lua.eval('mod.Skipped("Nav")'))
        lua.execute('ns.version = "v2"')
        self.assertFalse(lua.eval('mod.Skipped("Window")'))
        self.assertIsNone(lua.eval('mod.db.bisect'))
        lua.execute('mod:Bisect("Nav")')
        self.assertTrue(lua.eval('mod.Skipped("Nav")'))
        self.assertFalse(lua.eval('mod.Skipped("Battlegrounds")'))
        lua.execute('mod:Bisect("none")')
        self.assertIsNone(lua.eval('mod.db.bisect'))
        self.assertIsNone(lua.eval('mod.db.bisectVersion'))


if __name__ == "__main__":
    unittest.main()
