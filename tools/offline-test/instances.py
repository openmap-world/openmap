"""Temporary world-marker filtering, using the production Lua 5.1 visibility paths."""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
STITCH = (ROOT / 'OpenMap/Map/Stitch.lua').read_text()
WORLD = (ROOT / 'OpenMap/Map/WorldMap.lua').read_text()


class InstanceTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            S, sets, zoomNow = {}, {}, 4
            pinRoot = { GetFrameLevel = function() return 1 end }
            function CreateFrame()
                return {
                    SetAllPoints = function() end, SetFrameLevel = function() end,
                    SetShown = function(self, on) self.shown = on end,
                    Hide = function(self) self.shown = false end,
                }
            end
            mod = { db = { hideWorldPinsInInstances = true } }
            ns = { Safe = { Value = function(v) if v ~= 'secret' then return v end end } }
            function IsInInstance() return inside, kind end
            inside, kind = false, 'none'
        """)
        helpers = STITCH[STITCH.index('local places ='):STITCH.index('-- the menu\'s Icon size:')]
        for name in ('PinSet', 'SetPinSetOn'):
            helpers += re.search(r'function S\.' + name + r'\(.*?\nend\n', STITCH, re.S).group()
        self.lua.execute(helpers)
        self.lua.execute(re.search(r'function mod:RefreshInstancePins\(.*?\nend\n', WORLD, re.S).group())
        self.lua.execute("""
            affected = { 'friends', 'friendzones', 'boats', 'zeppelins', 'routes', 'flight', 'route', 'quests' }
            preserved = { 'group', 'waypoint', 'ping', 'userpins', 'sketch', 'dungeons', 'needroll' }
            for _, keys in ipairs({ affected, preserved }) do
                for _, key in ipairs(keys) do S.PinSet(key, 0) end
            end
            function Check(hidden)
                for _, key in ipairs(affected) do
                    assert(sets[key].frame.shown == (not hidden), key)
                    assert(sets[key].on, key .. ' preference changed')
                end
                for _, key in ipairs(preserved) do assert(sets[key].frame.shown, key) end
            end
            mod:RefreshInstancePins()
        """)

    def test_enter_exit_all_instance_types(self):
        self.lua.execute("""
            Check(false)
            for _, value in ipairs({ 'party', 'raid', 'pvp', 'arena' }) do
                inside, kind = true, value
                mod:RefreshInstancePins()
                Check(true)
                inside, kind = false, 'none'
                mod:RefreshInstancePins()
                Check(false)
            end
        """)

    def test_toggle_inside_and_existing_preferences(self):
        self.lua.execute("""
            S.SetPinSetOn(sets.boats, false)
            inside, kind = true, 'party'
            mod:RefreshInstancePins()
            mod.db.hideWorldPinsInInstances = false
            mod:RefreshInstancePins()
            assert(sets.friends.frame.shown and not sets.boats.frame.shown)
            mod.db.hideWorldPinsInInstances = true
            mod:RefreshInstancePins()
            inside, kind = false, 'none'
            mod:RefreshInstancePins()
            assert(sets.friends.frame.shown and not sets.boats.frame.shown)
            assert(not sets.boats.on)
        """)

    def test_disabled_option_and_saved_preferences_are_preserved(self):
        self.lua.execute("""
            mod.db.friends, mod.db.guild, mod.db.boats = true, false, true
            mod.db.routes, mod.db.allQuests, mod.db.group = false, true, true
            local saved = {}
            for key, value in pairs(mod.db) do saved[key] = value end
            inside, kind = true, 'party'
            mod:RefreshInstancePins()
            inside, kind = false, 'none'
            mod:RefreshInstancePins()
            for key, value in pairs(saved) do assert(mod.db[key] == value, key) end
            for key, value in pairs(mod.db) do assert(saved[key] == value, key) end
            mod.db.hideWorldPinsInInstances = false
            inside, kind = true, 'party'
            mod:RefreshInstancePins()
            Check(false)
            mod.db.hideWorldPinsInInstances = nil
            mod:RefreshInstancePins()
            Check(false)
        """)

    def test_updates_zoom_and_lazy_build_cannot_override_filter(self):
        self.lua.execute("""
            inside, kind = true, 'raid'
            mod:RefreshInstancePins()
            for _, key in ipairs(affected) do S.SetPinSetOn(sets[key], true) end
            Check(true)
            sets.quests = nil
            local late = S.PinSet('quests', 0)
            assert(late.frame.shown == false, 'late set leaked before next view update')
            local built = 0
            late.build = function() built = built + 1 end
            S.SetPinSetOn(late, true)
            assert(built == 0)
            inside, kind = false, 'none'
            mod:RefreshInstancePins()
            assert(built == 1 and late.frame.shown)
            sets.flight.minZoom = 6
            mod:RefreshInstancePins()
            assert(not sets.flight.frame.shown, 'zoom restriction lost')
        """)

    def test_secret_and_unknown_instance_values(self):
        self.lua.execute("""
            for _, value in ipairs({ 'none', 'scenario', 'secret' }) do
                inside, kind = true, value
                mod:RefreshInstancePins()
                Check(false)
            end
            inside, kind = 'secret', 'party'
            mod:RefreshInstancePins()
            Check(false)
        """)

    def test_events_apply_with_map_closed_and_on_login(self):
        block = re.search(r'\tfor _, event in ipairs\(\{ "PLAYER_ENTERING_WORLD".*?\n\tmod:RefreshInstancePins\(\)', WORLD, re.S).group()
        self.lua.execute("""
            events = {}
            self = { instancePinsEvents = {} }
            function ns.RegisterEvent(owner, event, fn) events[event] = fn end
            inside, kind = true, 'party'
        """ + block + """
            Check(true)
            for _, event in ipairs({ 'PLAYER_ENTERING_WORLD', 'ZONE_CHANGED_NEW_AREA', 'ZONE_CHANGED', 'ZONE_CHANGED_INDOORS' }) do
                inside, kind = false, 'none'
                events[event]()
                Check(false)
                inside, kind = true, 'pvp'
                events[event]()
                Check(true)
            end
        """)


class InstanceHostTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        helpers = re.search(r'local function Attach\(.*?\nend\n', WORLD, re.S).group()
        for name in ('InstanceWorldHidden', 'CursorWorld'):
            helpers += re.search(r'function mod\.' + name + r'\(.*?\nend\n', WORLD, re.S).group()
        helpers += re.search(r'function mod:RefreshInstancePins\(.*?\nend\n', WORLD, re.S).group()
        helpers += re.search(r'function mod:BrowseInstanceWorld\(.*?\nend\n', WORLD, re.S).group()
        helpers += re.search(r'local function OnCanvasClick\(.*?\nend\n', WORLD, re.S).group()
        mouse = WORLD[WORLD.index('\tns.RegisterEvent(self.instancePinsEvents, "GLOBAL_MOUSE_UP"'):]
        mouse = mouse[:mouse.index('\n\tmod:RefreshInstancePins()')]
        self.lua.execute("""
            mod = { db = { hideWorldPinsInInstances = true, dungeonMaps = false }, enabled = true }
            S = { shown = true }
            function S.IsBuilt() return true end
            function S.Layout() return true end
            function S.SetShown(on) S.shown = on end
            function S.SetPlayer() end
            function S.SetWorldPinsHidden(on) S.filtered = on end
            function mod:UpdateBrightness() end
            ns = { Safe = { Value = function(v) return v end } }
            events, timers = {}, {}
            function ns.RegisterEvent(_, event, fn) events[event] = fn end
            C_Timer = { After = function(_, fn) timers[#timers + 1] = fn end }
            overlay = true
            function mod:Refresh() self:RefreshInstancePins() refreshed = (refreshed or 0) + 1 end
            function mod.ShowNow(u, v, zoom)
                assert(not overlay, 'world restored before the instance overlay was dismissed')
                target = { u, v, zoom }
            end
            inside, kind = false, 'none'
            function IsInInstance() return inside, kind end
            local map = { id = 947, shown = true }
            function map:GetMapID() return self.id end
            function map:IsShown() return self.shown end
            local sc = {}
            function sc:IsMouseOver() return not outside end
            function sc:CreateZoomLevels() levels = (levels or 0) + 1 end
            function sc:SetMouseWheelZoomMode(value) self.wheel = value end
            function sc:SetScalingMode(value) self.scaling = value end
            local ticker = {}
            function ticker:Show() self.shown = true end
            function ticker:Hide() self.shown = false end
            function Stitchable(id) return id == 947 or id == 1 end
            function BlizzardArt() end
            function RaisePlayer() raised = (raised or 0) + 1 end
            groupBlipSizes, loweredGroupBlips = {}, {}   -- (WorldMap.lua's, from #217: the group blips' sizes and levels)
            function ScaleGroupBlips() end
            function LayerGroupBlips() end
            local active, anim = true, {}
            local wheelMode, scalingMode = 'native', 'native'
            MAP_CANVAS_MOUSE_WHEEL_ZOOM_BEHAVIOR_NONE = 'openmap'
        """ + helpers + '\nlocal self = mod\n' + mouse + """
            function State(id)
                if id then map.id = id end
                Attach(map.id)
            end
            function Active() return active end
            function Cursor() return mod.CursorWorld() end
            function Click(button) return OnCanvasClick(nil, button) end
            function Closed(on) map.shown = not on end
            function Wheel() return sc.wheel end
            function Ticking() return ticker.shown end
            function Mouse(button) events.GLOBAL_MOUSE_UP(nil, 'GLOBAL_MOUSE_UP', button) end
            function Flush()
                local pending = timers
                timers = {}
                for _, fn in ipairs(pending) do fn() end
            end
            function Reopen()
                mod.instanceWorldBrowsing = nil
                mod.instanceMapGeneration = (mod.instanceMapGeneration or 0) + 1
                mod:RefreshInstancePins()
            end
        """)

    def test_right_click_restores_interactive_world_after_needroll_closes(self):
        self.lua.execute("""
            inside, kind = true, 'party'
            function mod.InstanceEntranceView() return .4, .3, 24 end
            State(947)
            Mouse('RightButton')
            assert(not Active() and overlay and not target, 'dismissal was not deferred')
            overlay = false
            Flush()
            assert(Active() and S.shown and not S.filtered and mod.instanceWorldBrowsing)
            assert(target[1] == .4 and target[2] == .3 and target[3] == 24)
            assert(levels == 1 and refreshed == 1, 'zoom levels or markers were not refreshed')
            assert(not mod.instanceWorldHidden, 'world hover/group blips still disabled')
            Mouse('RightButton')
            Flush()
            assert(levels == 1, 'subsequent world right-click recentered instead of zooming out')
            overlay = true
            Reopen()
            assert(not Active() and S.filtered and mod.instanceWorldHidden)
        """)

    def test_world_browsing_falls_back_to_last_outdoor_player_position(self):
        self.lua.execute("""
            inside, kind = true, 'party'
            mod.outsideInstanceView = { .7, .6, 1454 }
            function mod.FitZoom(zone) assert(zone == 1454) return 24 end
            mod.db.maxZoom = 16
            State(947)
            Mouse('RightButton')
            overlay = false
            Flush()
            assert(target[1] == .7 and target[2] == .6 and target[3] == 16)
            inside, kind = false, 'none'
            mod:RefreshInstancePins()
            assert(not mod.instanceWorldBrowsing and Active())
        """)

    def test_right_click_ignores_other_ui_and_stale_reopen_callbacks(self):
        self.lua.execute("""
            inside, kind = true, 'party'
            State(947)
            Mouse('LeftButton')
            outside = true
            Mouse('RightButton')
            Flush()
            assert(not Active() and not mod.instanceWorldBrowsing)
            outside = false
            function mod.MenuShown() return true end
            Mouse('RightButton')
            Flush()
            assert(not Active() and not mod.instanceWorldBrowsing, 'menu click dismissed the dungeon')
            mod.MenuShown = nil
            Mouse('RightButton')
            Reopen()
            Flush()
            assert(not Active() and not mod.instanceWorldBrowsing, 'old click affected a new dungeon view')
            Mouse('RightButton')
            Closed(true)
            Flush()
            assert(not Active() and not mod.instanceWorldBrowsing, 'closed map was restored')
        """)

    def test_unknown_entrance_and_no_outdoor_position_still_restore_navigation(self):
        self.lua.execute("""
            inside, kind = true, 'party'
            State(947)
            Mouse('RightButton')
            overlay = false
            Flush()
            assert(Active() and not S.filtered and not target)
        """)

    def test_ragefire_chasm_uses_entrance_and_orgrimmar_zoom(self):
        self.lua.execute((ROOT / 'OpenMap/Data/Forever/Places.lua').read_text(), 'OpenMap', self.lua.globals().ns)
        dungeons = (ROOT / 'OpenMap/Map/Dungeons.lua').read_text()
        entrance = re.search(r'function S.EntranceAt\(.*?\nend\n', dungeons, re.S).group()
        view = re.search(r'function mod.InstanceEntranceView\(.*?\nend\n', dungeons, re.S).group()
        self.lua.execute("""
            local Safe = ns.Safe
            local function Places() return ns.MapPlaces end
            instanceID = 389
            function GetInstanceInfo() return nil, nil, nil, nil, nil, nil, nil, instanceID end
            function S.FromYards(continent, x, y)
                assert(continent == 1 and x == 1816.8 and y == -4423.4, 'not the recorded RFC entrance')
                return .23, .45
            end
            function S.ChainAt(u, v)
                assert(u == .23 and v == .45)
                return { 947, 1414, 1411, 1454 }
            end
            function mod.FitZoom(zone) assert(zone == 1454, 'not Orgrimmar zoom') return 24 end
        """ + entrance + view + """
            inside, kind = true, 'party'
            State(947)
            Mouse('RightButton')
            overlay = false
            Flush()
            assert(target[1] == .23 and target[2] == .45 and target[3] == 24)
            instanceID = 999999
            assert(mod.InstanceEntranceView() == nil, 'unknown instance invented a position')
            instanceID = 0
            assert(mod.InstanceEntranceView() == nil)
        """)

    def test_world_host_suspends_and_restores_on_instance_events(self):
        self.lua.execute("""
            State(947)
            assert(Active() and S.shown)
            for _, value in ipairs({ 'party', 'raid', 'pvp', 'arena' }) do
                inside, kind = true, value
                mod:RefreshInstancePins()
                assert(not Active() and not S.shown, 'world art and its group pins still shown')
                assert(Cursor() == nil, 'world cursor still active')
                assert(Wheel() == 'native' and Ticking(), 'native zoom or protected-pin retry lost')
                assert(Click('LeftButton') and Click('RightButton'), 'click fell through to world navigation')
                inside, kind = false, 'none'
                mod:RefreshInstancePins()
                assert(Active() and S.shown and not mod.instanceWorldHidden)
                assert(mod.db.dungeonMaps == false and mod.db.hideWorldPinsInInstances)
            end
        """)

    def test_native_dungeon_map_and_openmap_dungeon_setting_are_preserved(self):
        self.lua.execute("""
            inside, kind = true, 'party'
            State(2)
            assert(not Active() and not mod.instanceWorldHidden)
            assert(not Click('LeftButton'), 'native dungeon click swallowed')
            State(947)
            assert(mod.instanceWorldHidden)
            mod.db.dungeonMaps = true
            mod:RefreshInstancePins()
            assert(Active() and not mod.instanceWorldHidden, 'OpenMap dungeon option ignored')
            mod.db.dungeonMaps = false
            mod:RefreshInstancePins()
            assert(not Active())
            mod.db.hideWorldPinsInInstances = false
            mod:RefreshInstancePins()
            assert(Active() and not mod.instanceWorldHidden)
        """)

    def test_closed_map_and_host_changes(self):
        self.lua.execute("""
            Closed(true)
            inside, kind = true, 'party'
            mod:RefreshInstancePins()
            assert(not Active() and not S.shown)
            Closed(false)
            State(1)
            assert(not Active() and Ticking())
            State(2)
            assert(not mod.instanceWorldHidden, 'native dungeon blips would be suppressed')
            inside, kind = false, 'none'
            State(947)
            assert(Active() and S.shown)
        """)

    def test_hover_label_does_not_query_world_under_overlay(self):
        extras = (ROOT / 'OpenMap/Map/Extras.lua').read_text()
        label = re.search(r'local function AreaLabelOnUpdate\(.*?\nend\n', extras, re.S).group()
        self.lua.execute("""
            MAP_AREA_LABEL_TYPE = { AREA_NAME = 1 }
            local self = { clears = 0, evaluations = 0 }
            function self:ClearLabel() self.clears = self.clears + 1 end
            function self:EvaluateLabels() self.evaluations = self.evaluations + 1 end
            -- No dataProvider: querying the world label would fail this test.
        """ + label + """
            inside, kind = true, 'party'
            State(947)
            AreaLabelOnUpdate(self)
            assert(self.clears == 1 and self.evaluations == 1)
        """)

    def test_coordinates_do_not_query_world_under_overlay(self):
        extras = (ROOT / 'OpenMap/Map/Extras.lua').read_text()
        coords = re.search(r'local function UpdateCoords\(.*?\nend\n', extras, re.S).group()
        self.lua.execute("""
            local throttle = 0
            local bar = { player = { at = {} }, cursor = {} }
            function bar.player.at:SetText(text) self.text = text end
            function bar.cursor:GetParent() return self end
            function bar.cursor:Hide() self.hidden = true end
            -- No C_Map: querying coordinates underneath the overlay would fail.
        """ + coords + """
            inside, kind = true, 'party'
            State(947)
            UpdateCoords(nil, 0.1)
            assert(bar.player.at.text == '' and bar.cursor.hidden)
        """)


if __name__ == '__main__':
    unittest.main()
