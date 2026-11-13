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
        self.lua.execute(re.search(r'function mod:RefreshInstancePins\(\).*?\nend\n', WORLD, re.S).group())
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


if __name__ == '__main__':
    unittest.main()
