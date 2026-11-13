"""Navigation behavior checks in Lua 5.1; run with python tools/offline-test/navigation.py."""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            zone, playerU, playerV = 1, .5, .5
            mod = { defaults = {}, db = {}, char = {} }
            ns = {
                MapStitch = { Rect = function() return 0, 1, 0, 1 end },
                Safe = {
                    Call = function(fn, ...) if fn then return fn(...) end end,
                    XY = function(p) return p.x, p.y end,
                    IsSecret = function() return false end,
                },
                L = setmetatable({}, { __index = function(_, key) return key end }),
            }
            function ns:GetModule() return mod end
            C_Map = {
                GetBestMapForUnit = function() return zone end,
                GetPlayerMapPosition = function()
                    if playerU then return { x = playerU, y = playerV } end
                end,
            }
            function mod.ToWorld(_, x, y) return x, y end
            function mod.ViewNow() return .5, .5, 4 end
            function mod.HostMap() return 1 end
            function mod.ViewHalfExtents() return .1, .05 end
            function mod.IsStitched() return true end
            function mod.FitZoom() return 8 end
            function mod.Glide(u, v, zoom) target = { u, v, zoom } end
            function ns:Print() end
        """)
        self.lua.execute((ROOT / "Map/Nav.lua").read_text(encoding="utf-8"),
                         "OpenMap", self.lua.globals().ns)
        self.lua.execute("""
            function options()
                local opts = {}
                mod:NavOptions(opts,
                    function(info) return mod.db[info[#info]] end,
                    function(info, value) mod.db[info[#info]] = value end,
                    function() return false end)
                return opts
            end
        """)

    def test_one_exclusive_choice(self):
        self.lua.execute("""
            local opts = options()
            assert(opts.reopenView.type == 'select')
            assert(not opts.rememberView and not opts.rememberViewInView)
            local count = 0
            for _ in pairs(opts.reopenView.values) do count = count + 1 end
            assert(count == 5)
            for _, mode in ipairs({ 'player', 'zoom', 'inzone', 'always', 'visible' }) do
                opts.reopenView.set({ 'reopenView' }, mode)
                assert(opts.reopenView.get({ 'reopenView' }) == mode)
            end
        """)

    def test_last_outdoor_position_is_remembered_without_a_viewport(self):
        self.lua.execute("""
            function mod.FitZoom() error('no map viewport at login') end
            playerU, playerV, zone = .3, .7, 1454
            mod.RememberOutsideInstance()
            assert(mod.outsideInstanceView[1] == .3 and mod.outsideInstanceView[2] == .7)
            assert(mod.outsideInstanceView[3] == 1454)
            playerU = nil
            mod.RememberOutsideInstance()
            assert(mod.outsideInstanceView[1] == .3, 'unknown position overwrote outdoor fallback')
        """)

    def test_saved_preferences_migrate(self):
        for old, expected in [('', 'player'), ('rememberView=true', 'always'),
                              ("reopenView='zone'", 'always'),
                              ('rememberView=false', 'player'),
                              ('rememberView=true,rememberViewInView=true', 'visible')]:
            with self.subTest(old=old):
                self.lua.execute(f"""
                    mod.db = {{ {old} }}
                    local opt = options().reopenView
                    assert(opt.get({{ 'reopenView' }}) == '{expected}')
                    assert(mod.db.reopenView == '{expected}')
                    assert(mod.db.rememberView == nil and mod.db.rememberViewInView == nil)
                """)

    def test_visible_mode_checks_both_axes_across_zones(self):
        self.lua.execute("""
            mod.db.reopenView = 'visible'
            mod:OnMapHidden()
            zone = 2
            assert(mod.SavedView() == .5)
            playerU = .61
            local u, v, zoom = mod.SavedView()
            assert(u == playerU and v == playerV and zoom == 8)
            playerU, playerV = .5, .56
            u, v, zoom = mod.SavedView()
            assert(u == playerU and v == playerV and zoom == 8)
            playerV = .5
            assert(mod.SavedView() == .5)
        """)

    def test_unknown_position_and_explicit_quest_map_do_not_restore(self):
        self.lua.execute("""
            mod.db.reopenView = 'visible'
            mod:OnMapHidden()
            playerU = nil
            assert(mod.SavedView() == nil)
            playerU = .5
            assert(mod.SavedView(999) == nil)
        """)

    def test_always_mode_restores_across_zones_outside_previous_view(self):
        self.lua.execute("""
            mod.db.reopenView = 'always'
            mod:OnMapHidden()
            playerU = .8
            assert(mod.SavedView() == .5)
            zone = 2
            local u, v, zoom = mod.SavedView(2)
            assert(u == .5 and v == .5 and zoom == 4)
            assert(mod.SavedView(999) == nil)
        """)

    def test_inzone_mode_opens_on_the_whole_zone(self):
        # (#143: the zone you're in, in the middle at its fitting zoom, wherever you are in it)
        self.lua.execute("""
            mod.db.reopenView = 'inzone'
            mod:OnMapHidden()
            playerU, playerV = .8, .7
            local u, v, zoom = mod.SavedView()
            assert(u == .5 and v == .5 and zoom == 8)
            assert(mod.SavedView(999) == nil)
            assert(mod.SavedView(nil, true) == nil)   -- (not a saved view: Blizzard's own opening isn't moved again)
        """)

    def test_player_mode_never_restores(self):
        self.lua.execute("""
            mod.db.reopenView = 'player'
            mod:OnMapHidden()
            playerU, playerV = .8, .7
            local u, v, zoom = mod.SavedView()
            assert(u == playerU and v == playerV and zoom == 8)
            assert(mod.SavedView(999) == nil)
        """)

    def test_first_open_centers_on_player(self):
        self.lua.execute("""
            playerU, playerV = .8, .7
            local u, v, zoom = mod.SavedView(1)
            assert(u == playerU and v == playerV and zoom == 8)
        """)

    def test_find_me_can_preserve_zoom(self):
        self.lua.execute("""
            mod:FindMe(true)
            assert(target[1] == playerU and target[2] == playerV and target[3] == 4)
            mod:FindMe()
            assert(target[3] == 8)
        """)

    def test_map_menu_choices_are_exclusive(self):
        self.lua.execute((ROOT / "Map/Panel.lua").read_text(encoding="utf-8"),
                         "OpenMap", self.lua.globals().ns)
        self.lua.execute("""
            -- Reach the real menu rows without building game frames.
            local function upvalue(fn, wanted)
                for i = 1, 100 do
                    local name, value = debug.getupvalue(fn, i)
                    if name == wanted then return value end
                    if not name then break end
                end
                error('Missing menu function: ' .. wanted)
            end
            local rows = upvalue(upvalue(mod.RefreshPanel, 'Fill'), 'Rows')()
            local choices = {}
            for _, row in ipairs(rows) do
                assert(row.id ~= 'rememberView')
                if row.id and row.id:match('^reopenView%.') then
                    choices[#choices + 1] = row
                end
            end
            assert(#choices == 5)
            function mod:Refresh() end
            for _, selected in ipairs(choices) do
                selected[3](true)
                local checked = 0
                for _, row in ipairs(choices) do
                    if row[2]() then checked = checked + 1 end
                end
                assert(checked == 1 and selected[2]())
                selected[3](false)
                assert(selected[2]()) -- the current choice cannot be deselected
            end
        """)


class GroupPinTests(unittest.TestCase):
    def setUp(self):
        self.lua = lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute(Path(__file__).with_name("stub.lua").read_text(encoding="utf-8"))
        lua.execute("""
            mod = { defaults = {}, db = { group = true }, char = {} }
            ns = {
                Media = { tex = "", path = "addon/" },
                Safe = {
                    Call = function(fn, ...) return fn(...) end,
                    Value = function(value) return value end,
                    XY = function(p) return p.x, p.y end,
                    IsSecret = function() return false end,
                },
                L = setmetatable({}, { __index = function(_, key) return key end }),
                GetModule = function() return mod end,
            }
            first = { guid = "Player-1-0010", x = .101, y = .101 }
            second = { guid = "Player-1-0011", x = .121, y = .121 }
            roster = { party1 = first, party2 = second }
            UnitExists = function(unit) return roster[unit] ~= nil end
            UnitIsUnit = function(unit, other) return unit == other end
            UnitGUID = function(unit) return roster[unit].guid end
            UnitName = function(unit) return roster[unit].name or unit end
            IsInGroup = function() return true end
            IsInRaid = function() return roster.raid1 ~= nil end
            C_Map.GetBestMapForUnit = function() return 3 end
            C_Map.GetPlayerMapPosition = function(_, unit) return roster[unit] end
            mod.ToWorld = function(_, x, y) return x, y end
            mod.IsStitched = function() return true end
            mod.HostMap = function() return ns.MapStitch.WORLD end
            GameTooltip.ownerChanges = 0
            function GameTooltip:SetOwner(owner)
                self.owner = owner
                self.ownerChanges = self.ownerChanges + 1
            end
            function GameTooltip:IsOwned(owner) return self.owner == owner end
            function GameTooltip:ClearLines() self.lines = {} end
            function GameTooltip:AddLine(text) self.lines[#self.lines + 1] = text end
        """)
        for name in ("Stitch", "Nav"):
            lua.execute((ROOT / f"Map/{name}.lua").read_text(encoding="utf-8"),
                        "OpenMap", lua.globals().ns)
        lua.execute("""
            C_Map.GetMapArtLayers = function() return { { layerWidth = 100, layerHeight = 100 } } end
            C_Map.GetMapRectOnMap = function() return 0, 1, 0, 1 end
            assert(ns.MapStitch.Build(CreateFrame("Frame"), 100, 80, 2000))
            mod:BuildNav()
        """)

    def test_hovered_pin_moves_in_place_and_follows_the_member(self):
        self.lua.execute("""
            mod.RefreshGroup()
            local set = ns.MapStitch.GetPinSet("group")
            local function pinFor(unit)
                for _, pin in ipairs(set.pins) do
                    if pin.unit == unit then return pin end
                end
            end
            local a, b = assert(pinFor("party1")), assert(pinFor("party2"))
            local enter, leave = a:GetScript("OnEnter"), a:GetScript("OnLeave")
            local anchor, cell = a.anchor, a:GetParent()
            local hides = 0
            a:HookScript("OnHide", function() hides = hides + 1 end)
            enter(a)
            assert(GameTooltip:IsOwned(a) and GameTooltip:IsShown())

            mod.RefreshGroup()
            assert(pinFor("party1") == a and pinFor("party2") == b and hides == 0,
                "an unchanged refresh recycled a group button")
            first.x = .102
            mod.RefreshGroup()
            assert(pinFor("party1") == a and a.anchor == anchor and hides == 0)
            assert(a.u == first.x and a.v == first.y)
            local _, _, _, x, y = anchor:GetPoint()
            assert(x == first.x * 100 and y == -first.y * 100)
            assert(a:GetScript("OnEnter") == enter and a:GetScript("OnLeave") == leave)
            assert(GameTooltip:IsOwned(a) and GameTooltip:IsShown())

            first.x = .145
            mod.RefreshGroup()
            assert(pinFor("party1") == a and a.anchor == anchor and hides == 0)
            assert(a:GetParent() ~= cell and a.u == first.x)
            assert(GameTooltip:IsOwned(a) and GameTooltip:IsShown())

            GameTooltip:SetOwner(b)
            leave(a)
            assert(GameTooltip:IsOwned(b) and GameTooltip:IsShown())
            enter(a)

            roster = { raid1 = second, raid2 = first }
            mod.RefreshGroup()
            assert(pinFor("raid2") == a and pinFor("raid1") == b and hides == 0)
            roster.raid2 = nil
            mod.RefreshGroup()
            assert(#set.pins == 1 and pinFor("raid1") == b and hides == 1)
            assert(not a:IsShown() and not GameTooltip:IsShown())
        """)

    def test_hovered_fallback_updates_the_name_when_a_slot_is_reused(self):
        self.lua.execute("""
            first.guid, first.name = nil, "First member"

            mod.RefreshGroup()
            local set = ns.MapStitch.GetPinSet("group")
            local pin = set.pins[1]
            local hides = 0
            pin:HookScript("OnHide", function() hides = hides + 1 end)
            pin:GetScript("OnEnter")(pin)
            assert(GameTooltip.lines[1] == "First member")

            roster.party1 = { name = "Replacement member", x = .102, y = .101 }
            mod.RefreshGroup()
            assert(set.pins[1] == pin and pin.u == .102 and hides == 0)
            assert(GameTooltip:IsShown() and GameTooltip:IsOwned(pin) and GameTooltip.ownerChanges == 1)
            assert(GameTooltip.lines[1] == "Replacement member",
                "the hovered pin still shows the previous occupant's name")
        """)

    def _setup_native_map(self, reject_map=False):
        self.lua.globals().reject_native_map = reject_map
        self.lua.execute("""
            local host, stockHost = 3, 3
            first.zone, second.zone = host, 4
            C_Map.GetBestMapForUnit = function(unit) return roster[unit].zone end
            C_Map.GetPlayerMapPosition = function(mapID, unit)
                local member = roster[unit]
                if member and member.zone == mapID then return member end
            end
            mod.HostMap = function() return host end
            nativeIconScale = 1
            mod.NativeGroupIconScale = function() return nativeIconScale end
            ns.RegisterEvent = function() end
            ns.Print = function() end

            worldMap = CreateFrame("Frame")
            worldMap:Hide()
            worldMap.ScrollContainer = CreateFrame("Frame", nil, worldMap)
            local canvas = CreateFrame("Frame", nil, worldMap.ScrollContainer)
            stockPin = CreateFrame("Frame", nil, canvas)
            stockPin:SetFrameLevel(73)
            stockPin.GetFrameStrata = function() return "HIGH" end
            stockPin.GetUiMapID = function() return stockHost end
            stockPin.SetUiMapID = function(_, mapID) stockHost = mapID end
            worldMap.SetMapID = function(_, mapID) host = mapID end
            worldMap.OnMapChanged = function(_, deferStockPin)
                if not deferStockPin then stockPin:SetUiMapID(host) end
            end
            worldMap.GetCanvas = function() return canvas end
            local canvasScale = 2
            worldMap.GetCanvasScale = function() return canvasScale end
            worldMap.OnCanvasScaleChanged = function(_, scale) canvasScale = scale end
            worldMap.EnumeratePinsByTemplate = function(_, template)
                return next, template == "GroupMembersPinTemplate" and { [stockPin] = true } or {}
            end

            local createFrame = CreateFrame
            CreateFrame = function(kind, ...)
                local frame = createFrame(kind, ...)
                if kind == "UnitPositionFrame" then
                    ringFrame = frame
                    frame.SetFrameStrata = function(self, strata) self.strata = strata end
                    frame.GetFrameStrata = function(self) return self.strata or "MEDIUM" end
                    frame.SetUiMapID = function(self, mapID)
                        if not reject_native_map then self.mapID = mapID end
                    end
                    frame.GetUiMapID = function(self) return self.mapID end
                    frame.ClearUnits = function(self) self.units = {} end
                    frame.AddUnit = function(self, unit, asset, width, height)
                        assert(asset:sub(-13) == "GroupRing.tga")
                        assert(width == 16 * nativeIconScale / worldMap:GetCanvasScale() and height == width)
                        self.unitWidth = width
                        self.units[#self.units + 1] = unit
                    end
                    frame.FinalizeUnits = function() end
                    frame.EnableMouse = function(self, enabled) self.mouseEnabled = enabled end
                end
                return frame
            end
            mod:SetupNav(worldMap)
            group = ns.MapStitch.GetPinSet("group")
        """)

    def test_native_ring_uses_stock_layer_and_keeps_stitched_fallback(self):
        self._setup_native_map()
        self.lua.execute("""
            local function checkNativeRing()
                assert(ringFrame and ringFrame:IsShown())
                assert(#ringFrame.units == 1 and ringFrame.units[1] == "party1")
                assert(#group.pins == 1 and group.pins[1].unit == "party2")
                local fallback = group.pins[1]
                assert(fallback.Ring:GetWidth() == 16 and fallback.RingGap == nil and fallback:GetWidth() == 12)
            end

            worldMap:Show()
            checkNativeRing() -- the ring is present before the first update
            assert(ringFrame:GetParent() == worldMap:GetCanvas())
            assert(ringFrame:GetFrameLevel() == stockPin:GetFrameLevel() - 1)
            assert(ringFrame:GetFrameStrata() == stockPin:GetFrameStrata())
            assert(ringFrame.mouseEnabled == false)

            RunOnUpdate(.016)
            worldMap:Hide()
            assert(not ringFrame:IsShown())
            worldMap:Show()
            checkNativeRing()
            RunOnUpdate(.016)

            worldMap:Hide()
            stockPin:Hide()
            worldMap:Show()
            assert(not ringFrame:IsShown() and #group.pins == 2)
            stockPin:Show()
            RunOnUpdate(.016)
            checkNativeRing() -- retry as soon as Blizzard has prepared the pin
            assert(#ERRORS == 0, ERRORS[1])
        """)

    def test_native_ring_tracks_the_applied_stock_icon_size(self):
        self._setup_native_map()
        self.lua.execute("""
            worldMap:Show()
            local ring = ringFrame
            assert(ring.unitWidth == 8)

            mod.db.iconScale = .6
            mod.RefreshNativeRingLayout()
            assert(ring.unitWidth == 8) -- the stock size has not changed yet
            nativeIconScale = .6
            mod.RefreshNativeRingLayout()
            assert(ringFrame == ring and math.abs(ring.unitWidth - 4.8) < 1e-6)

            nativeIconScale = 2
            mod.RefreshNativeRingLayout()
            assert(ringFrame == ring and ring.unitWidth == 16)
        """)

    def test_native_ring_resizes_on_canvas_scale_change(self):
        self._setup_native_map()
        self.lua.execute("""
            worldMap:Show()
            local ring, fallback = ringFrame, group.pins[1]
            assert(ring.unitWidth == 8)
            worldMap:OnCanvasScaleChanged(4)
            assert(ringFrame == ring and ring.unitWidth == 4 and group.pins[1] == fallback)
            local units = ring.units
            worldMap:OnCanvasScaleChanged(4)
            assert(ring.units == units)
            worldMap:OnCanvasScaleChanged(2)
            assert(ringFrame == ring and ring.unitWidth == 8 and group.pins[1] == fallback)

            units = ring.units
            stockPin:SetFrameLevel(74)
            mod.RefreshNativeRingLayout()
            assert(ring:GetFrameLevel() == 73 and ring.units == units)
            worldMap:SetMapID(nil) -- stitching stops while Blizzard's map stays open
            mod.RefreshNativeRingLayout()
            assert(not ring:IsShown() and worldMap:IsShown() and stockPin:IsShown())
        """)

    def test_native_ring_returns_on_the_first_update_after_a_host_switch(self):
        self._setup_native_map()
        self.lua.execute("""
            C_Map.GetMapRectOnMap = function(id)
                if id == 4 then return .1, .2, .1, .2 end
                return 0, 1, 0, 1
            end
            first.x = .7
            worldMap:Show()
            RunOnUpdate(.016) -- advance past the opening refresh
            local ring = ringFrame
            assert(ring:IsShown() and ring:GetUiMapID() == 3 and ring.units[1] == "party1")

            worldMap:SetMapID(4)
            worldMap:OnMapChanged(true) -- the stock group pin still reports the old map here
            assert(#group.pins == 1 and group.pins[1].unit == "party2")
            stockPin:SetUiMapID(4)
            RunOnUpdate(.016)

            assert(ringFrame == ring and ring:IsShown() and ring:GetUiMapID() == 4,
                "the native ring missed the first frame after the stock pin changed maps")
            assert(#ring.units == 1 and ring.units[1] == "party2")
            assert(#group.pins == 1 and group.pins[1].unit == "party1")
            assert(#ERRORS == 0, ERRORS[1])
        """)

    def test_city_handoff_keeps_the_ring_and_uses_fallback_outside(self):
        self._setup_native_map()
        self.lua.execute("""
            C_Map.GetMapRectOnMap = function(id)
                if id == 4 then return .1, .2, .1, .2 end
                return 0, 1, 0, 1
            end
            first.x, first.y = .15, .15
            second.x, second.y, second.zone = .7, .7, 3
            local cityPosition
            local position = C_Map.GetPlayerMapPosition
            C_Map.GetPlayerMapPosition = function(id, unit)
                if id == 4 and unit == "party1" then return cityPosition end
                return position(id, unit)
            end

            worldMap:Show()
            RunOnUpdate(.016)
            local ring = ringFrame
            assert(#ring.units == 2 and #group.pins == 0)
            worldMap:SetMapID(4)
            worldMap:OnCanvasScaleChanged(2) -- the stock pin still has the old map ID
            worldMap:OnMapChanged()
            assert(ringFrame == ring and ring:IsShown() and ring:GetUiMapID() == 4)
            assert(#ring.units == 1 and ring.units[1] == "party1")
            assert(#group.pins == 1 and group.pins[1].unit == "party2")

            local units = ring.units
            RunOnUpdate(.016)
            assert(ring.units == units and #group.pins == 1)
            cityPosition = { x = .5, y = .5 }
            NOW = NOW + .03
            RunOnUpdate(.03)
            assert(ring.units == units and #group.pins == 1)

            worldMap:SetMapID(3)
            worldMap:OnMapChanged()
            assert(ringFrame == ring and ring:IsShown() and ring:GetUiMapID() == 3)
            assert(#ring.units == 2 and #group.pins == 0)

            cityPosition = nil
            worldMap:SetMapID(4)
            worldMap:OnMapChanged()
            RunOnUpdate(.016)
            NOW = NOW + .11
            RunOnUpdate(.11)
            assert(not ring:IsShown() and #group.pins == 2)
            assert(#ERRORS == 0, ERRORS[1])
        """)

    def test_same_map_position_gap_keeps_native_outline(self):
        self._setup_native_map()
        self.lua.execute("""
            local position = C_Map.GetPlayerMapPosition
            local missing = false
            C_Map.GetBestMapForUnit = function() return 4 end
            C_Map.GetPlayerMapPosition = function(id, unit)
                if id == 4 then return roster[unit] end
                if missing and unit == "party1" then return end
                return position(id, unit)
            end
            worldMap:Show()
            RunOnUpdate(.016)
            local ring, fallback = ringFrame, group.pins[1]
            local units = ring.units
            missing = true
            NOW = NOW + .501
            RunOnUpdate(.501)
            assert(ring:IsShown() and ring.units == units and #group.pins == 1 and group.pins[1] == fallback)
            missing = false
            NOW = NOW + .021
            RunOnUpdate(.021)
            assert(ring:IsShown() and ring.units == units and #group.pins == 1 and group.pins[1] == fallback)
            assert(#ERRORS == 0, ERRORS[1])
        """)

    def test_same_map_position_retries_expire_independently(self):
        self._setup_native_map()
        self.lua.execute("""
            C_Map.GetMapRectOnMap = function(id)
                if id == 3 then return 0, .5, 0, .5 end
                return 0, 1, 0, 1
            end
            local positions = { party1 = first, party2 = second }
            C_Map.GetBestMapForUnit = function() return 4 end
            C_Map.GetPlayerMapPosition = function(id, unit)
                if id == 3 then return positions[unit] end
                if id == 4 then return roster[unit] end
            end
            local function advance(elapsed)
                NOW = NOW + elapsed
                RunOnUpdate(elapsed)
            end
            worldMap:Show()
            advance(.016)
            local ring = ringFrame
            assert(#ring.units == 2 and #group.pins == 0)
            positions.party1 = nil
            advance(.501)
            assert(#ring.units == 2 and #group.pins == 0)
            advance(.08)
            positions.party2 = nil
            advance(.02)
            advance(.005)
            assert(#ring.units == 1 and ring.units[1] == "party2")
            assert(#group.pins == 1 and group.pins[1].unit == "party1")
            second.x = .7 -- its other map now proves it is outside the host
            advance(.021)
            assert(not ring:IsShown() and #group.pins == 2)
            assert(#ERRORS == 0, ERRORS[1])
        """)

    def test_rejected_native_map_keeps_stitched_pins(self):
        self._setup_native_map(reject_map=True)
        self.lua.execute("""
            worldMap:Show()
            assert(ringFrame and not ringFrame:IsShown())
            assert(#group.pins == 2)
            assert(group.pins[1].unit == "party1" and group.pins[2].unit == "party2")
            assert(stockPin:IsShown())
        """)


if __name__ == "__main__":
    unittest.main()
