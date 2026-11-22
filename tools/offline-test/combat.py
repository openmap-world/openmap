"""Combat pin guards in Lua 5.1 (Combat.lua; PR #22, Ironship's): python -P tools/offline-test/combat.py."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            combat, visits, setters = false, 0, 0
            events, mod = {}, {}
            ns = { GetModule = function() return mod end }
            function ns.RegisterEvent(_, event, callback) events[event] = callback end
            function InCombatLockdown() return combat end
            -- (the next frame's callbacks, run by NextFrame: Combat.lua sweeps once a frame after addons load)
            timers = {}
            C_Timer = { After = function(_, fn) table.insert(timers, fn) end }
            function NextFrame()
                local run = timers
                timers = {}
                for _, fn in ipairs(run) do fn() end
            end
            function Pack(...) return { n = select('#', ...), ... } end
            function CreateFromMixins(...)
                local out = {}
                for i = 1, select('#', ...) do
                    for key, value in pairs(select(i, ...)) do out[key] = value end
                end
                return out
            end
            function hooksecurefunc(t, key, callback)
                local original = t[key]
                t[key] = function(...)
                    local result = Pack(original(...))
                    callback(...)
                    return unpack(result, 1, result.n)
                end
            end
            MapCanvasPinMixin = {
                SetOwningMap = function(self, map) self.owningMap = map end,
                GetMap = function(self) return self.owningMap end,
                IsForbidden = function(self) return self.forbidden or false end,
                OnLoad = function() end,
                Show = function() end,
                SetPassThroughButtons = function(self, ...)
                    assert(not combat, 'SetPassThroughButtons in combat')
                    setters = setters + 1
                    self.buttons = Pack(...)
                end,
                SetPropagateMouseClicks = function(self, enabled)
                    assert(not combat, 'SetPropagateMouseClicks in combat')
                    setters = setters + 1
                    self.propagates = enabled
                end,
                ShouldMouseButtonBePassthrough = function(_, button)
                    return button == 'RightButton'
                end,
            }
            function MapCanvasPinMixin:CheckMouseButtonPassthrough(...)
                self.receivedButtons = Pack(...)
                self:SetPassThroughButtons()
                local buttons = {}
                for i = 1, select('#', ...) do
                    local button = select(i, ...)
                    if self:ShouldMouseButtonBePassthrough(button) then
                        table.insert(buttons, button)
                    end
                end
                self:SetPassThroughButtons(unpack(buttons))
            end
            SuperTrackablePinMixin = {}
            function SuperTrackablePinMixin:DoesMapTypeAllowSuperTrack()
                return self:GetMap().allowSuperTrack
            end
            function SuperTrackablePinMixin:UpdateMousePropagation(...)
                self.receivedPropagation = Pack(...)
                self:SetPropagateMouseClicks(not self:DoesMapTypeAllowSuperTrack())
            end
            function SuperTrackablePinMixin:OnAcquired()
                self:UpdateMousePropagation()
            end
            ExistingPinMixin = CreateFromMixins(MapCanvasPinMixin, SuperTrackablePinMixin)
            function CreatePool(mixin)
                local pool = { active = {}, inactive = {} }
                function pool:Acquire()
                    local pin = table.remove(self.inactive)
                    local new = not pin
                    if new then pin = CreateFromMixins(mixin) end
                    self.active[pin] = true
                    return pin, new
                end
                function pool:Release(pin)
                    self.active[pin] = nil
                    pin:SetOwningMap(nil)
                    table.insert(self.inactive, pin)
                end
                function pool:EnumerateActive()
                    return function(state, previous)
                        local pin = next(state, previous)
                        if pin then visits = visits + 1 end
                        return pin
                    end, self.active
                end
                function pool:EnumerateInactive()
                    local index = 0
                    return function()
                        index = index + 1
                        local pin = self.inactive[index]
                        if pin then visits = visits + 1 end
                        return pin
                    end
                end
                return pool
            end
            map = {
                allowSuperTrack = true,
                pinPools = {},
                SetPropagateMouseClicks = MapCanvasPinMixin.SetPropagateMouseClicks,
                ScrollContainer = { MarkCanvasDirty = function() end },
                HookScript = function(self, script, callback) self[script] = callback end,
            }
            -- Order from Blizzard_MapCanvas.lua:280-335, Forever build 70425,
            -- Gethe/wow-ui-source@b401e0332adfbf0460d319b06d8ea29279a941f1.
            function map:AcquirePin(template, mixin)
                local pool = self.pinPools[template]
                if not pool then
                    pool = CreatePool(mixin)
                    self.pinPools[template] = pool
                end
                local pin, new = pool:Acquire()
                pin:SetOwningMap(self)
                if new then pin:OnLoad() end
                self.ScrollContainer:MarkCanvasDirty()
                pin:Show()
                pin:OnAcquired()
                pin:CheckMouseButtonPassthrough('RightButton')
                return pin
            end
        """)
        self.lua.execute((ROOT / "Map/Combat.lua").read_text(encoding="utf-8"),
                         "OpenMap", self.lua.globals().ns)

    def test_existing_copies_and_late_pool_are_guarded_before_on_acquired(self):
        self.lua.execute("""
            mod:SetupCombat(map)
            combat = true
            local pin = map:AcquirePin('late', ExistingPinMixin)
            assert(setters == 0)
            combat = false
            events.PLAYER_REGEN_ENABLED()
            assert(setters == 3 and pin.propagates == false)
            assert(pin.buttons.n == 1 and pin.buttons[1] == 'RightButton')
        """)

    def test_new_mixin_copies_inherit_guards(self):
        self.lua.execute("""
            mod:SetupCombat(map)
            local late = CreateFromMixins(MapCanvasPinMixin, SuperTrackablePinMixin)
            combat = true
            map:AcquirePin('late', late)
            assert(setters == 0)
            combat = false
            events.PLAYER_REGEN_ENABLED()
            assert(setters == 3)
        """)

    def test_addon_loaded_points_preexisting_private_copy_exported_later(self):
        self.lua.execute("""
            local late = CreateFromMixins(ExistingPinMixin)
            mod:SetupCombat(map)
            LaterPinMixin = late
            if events.ADDON_LOADED then events.ADDON_LOADED() events.ADDON_LOADED() end
            NextFrame()
            assert(#timers == 0)
            combat = true
            map:AcquirePin('late', LaterPinMixin)
            map:AcquirePin('late', LaterPinMixin)
            assert(setters == 0)
        """)

    def test_existing_active_and_inactive_pins(self):
        self.lua.execute("""
            local active = map:AcquirePin('existing', ExistingPinMixin)
            local inactive = map:AcquirePin('existing', ExistingPinMixin)
            map.pinPools.existing:Release(inactive)
            mod:SetupCombat(map)
            combat, setters = true, 0
            active:UpdateMousePropagation()
            active:CheckMouseButtonPassthrough('RightButton')
            local reused = map:AcquirePin('existing', ExistingPinMixin)
            assert(reused == inactive and setters == 0)
        """)

    def test_last_request_preserves_false_and_trailing_nil(self):
        self.lua.execute("""
            mod:SetupCombat(map)
            combat = true
            local pin = map:AcquirePin('pins', ExistingPinMixin)
            pin:CheckMouseButtonPassthrough('RightButton', false, nil)
            pin:UpdateMousePropagation(false, nil)
            map.allowSuperTrack = false
            combat = false
            events.PLAYER_REGEN_ENABLED()
            assert(pin.receivedButtons.n == 3)
            assert(pin.receivedButtons[2] == false and pin.receivedButtons[3] == nil)
            assert(setters == 3 and pin.propagates == true)
            assert(pin.receivedPropagation.n == 2)
            assert(pin.receivedPropagation[1] == false and pin.receivedPropagation[2] == nil)
            events.PLAYER_REGEN_ENABLED()
            assert(setters == 3)
        """)

    def test_released_and_forbidden_pins_are_not_flushed(self):
        self.lua.execute("""
            mod:SetupCombat(map)
            combat = true
            local released = map:AcquirePin('pins', ExistingPinMixin)
            local forbidden = map:AcquirePin('pins', ExistingPinMixin)
            map.pinPools.pins:Release(released)
            forbidden.forbidden = true
            combat = false
            events.PLAYER_REGEN_ENABLED()
            assert(setters == 0)
        """)

    def test_out_of_combat_request_replaces_pending_request(self):
        self.lua.execute("""
            mod:SetupCombat(map)
            combat = true
            local pin = map:AcquirePin('pins', ExistingPinMixin)
            combat = false
            pin:CheckMouseButtonPassthrough()
            pin:UpdateMousePropagation()
            assert(setters == 3 and pin.buttons.n == 0)
            events.PLAYER_REGEN_ENABLED()
            assert(setters == 3 and pin.buttons.n == 0)
        """)

    def test_1900_acquisitions_do_not_rescan_existing_pins(self):
        self.lua.execute("""
            mod:SetupCombat(map)
            combat, visits = true, 0
            for i = 1, 1900 do map:AcquirePin('many', ExistingPinMixin) end
            assert(setters == 0)
            assert(visits == 1, 'expected one new-pool visit, got ' .. visits)
            combat = false
            events.PLAYER_REGEN_ENABLED()
            assert(setters == 5700)
        """)

    def test_hbd_private_mixin_owns_its_mouse_passthrough(self):
        self.lua.execute("""
            -- HereBeDragons-Pins-2.0 r17 copies its private mixin before login,
            -- defines no-op SetPassThroughButtons and has no propagation call.
            local hbd = CreateFromMixins(MapCanvasPinMixin)
            local custom = function() end
            hbd.SetPassThroughButtons = custom
            hbd.OnAcquired = function() end
            mod:SetupCombat(map)
            combat = true
            for i = 1, 20 do
                local pin = map:AcquirePin('hbd', hbd)
                assert(pin.SetPassThroughButtons == custom)
            end
            assert(setters == 0)
            combat = false
            events.PLAYER_REGEN_ENABLED()
            assert(setters == 0)
        """)


class SafeTests(unittest.TestCase):
    """Regression tests against the actual Safe.XY and Safe.PlayerPos in Core.lua."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            _G = _G or {}
            secrets = {}
            function issecretvalue(v) return secrets[v] == true end
            function GetAddOnMetadata() return 'dev' end
            function CreateFrame()
                return { SetScript = function() end, RegisterEvent = function() end }
            end
            C_Map = {}
            local ns = { Client = 'Forever' }
            local chunk = assert(loadstring(...))
            chunk('OpenMap', ns)
            Safe = ns.Safe
        """, (ROOT / "Core.lua").read_text(encoding="utf-8"))

    def test_safe_xy_handles_plain_secret_and_throwing_vectors(self):
        self.lua.execute("""
            assert(Safe.XY(nil) == nil)
            assert(Safe.XY(42) == nil)

            local secretVec = { x = 0.25, y = 0.75 }
            secrets[secretVec] = true
            local sx, sy = Safe.XY(secretVec)
            assert(sx == nil and sy == nil)

            local x, y = Safe.XY({ x = 0.2, y = 0.8 })
            assert(x == 0.2 and y == 0.8)

            local secretCoord = {}
            secrets[secretCoord] = true
            local px, py = Safe.XY({ x = secretCoord, y = 0.5 })
            assert(px == nil and py == 0.5)

            local gx, gy = Safe.XY({ GetXY = function() return 0.3, 0.7 end })
            assert(gx == 0.3 and gy == 0.7)

            local sgx, sgy = Safe.XY({ GetXY = function() return 0.4, secretCoord end })
            assert(sgx == 0.4 and sgy == nil)

            local tx, ty = Safe.XY({ GetXY = function() error('blocked in combat') end })
            assert(tx == nil and ty == nil)
        """)

    def test_safe_player_pos_handles_inferred_explicit_secret_and_throwing_apis(self):
        self.lua.execute("""
            local calls = {}
            local posVec = { GetXY = function() return 0.25, 0.75 end }
            C_Map.GetBestMapForUnit = function(unit)
                table.insert(calls, 'best:' .. unit)
                return 1429
            end
            C_Map.GetPlayerMapPosition = function(mapID, unit)
                table.insert(calls, 'pos:' .. mapID .. ':' .. unit)
                return posVec
            end

            local id, x, y, pos = Safe.PlayerPos()
            assert(id == 1429 and x == 0.25 and y == 0.75 and pos == posVec)
            assert(calls[1] == 'best:player' and calls[2] == 'pos:1429:player')

            calls = {}
            local eid, ex, ey, epos = Safe.PlayerPos(1453)
            assert(eid == 1453 and ex == 0.25 and ey == 0.75 and epos == posVec)
            assert(#calls == 1 and calls[1] == 'pos:1453:player')

            C_Map.GetPlayerMapPosition = function() return nil end
            local mid, mx, my = Safe.PlayerPos()
            assert(mid == 1429 and mx == nil and my == nil)

            local secretVec = { GetXY = function() return 0.1, 0.9 end }
            secrets[secretVec] = true
            C_Map.GetPlayerMapPosition = function() return secretVec end
            local sid, srx, sry = Safe.PlayerPos(1429)
            assert(sid == 1429 and srx == nil and sry == nil)

            local secretCoord = {}
            secrets[secretCoord] = true
            C_Map.GetPlayerMapPosition = function()
                return { GetXY = function() return secretCoord, 0.5 end }
            end
            local cid, cx, cy = Safe.PlayerPos(1429)
            assert(cid == 1429 and cx == nil and cy == nil)

            C_Map.GetPlayerMapPosition = function() error('map position secret') end
            local fid, fx, fy = Safe.PlayerPos()
            assert(fid == 1429 and fx == nil and fy == nil)

            C_Map.GetBestMapForUnit = function() error('unit map blocked') end
            assert(Safe.PlayerPos() == nil)
        """)


if __name__ == "__main__":
    unittest.main()
