"""A newer OpenMap out (News.lua's HeardVersion) in Lua 5.1: python -P tools/offline-test/version.py.

Which versions heard from others count as newer (releases only, this client's only), that the line in
chat comes once a session, and that the notice off says nothing and sends no version. What carries the
version (Friends.lua's hellos, and old copies hearing it) is in friends.py.
"""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"

STUB = r"""
printed = {}
mod = { defaults = {}, db = {} }
ns = { version = "v0.8.11", Client = "Forever", L = setmetatable({}, { __index = function(_, k) return k end }) }
function ns:GetModule() return mod end
function ns:Print(fmt, ...) printed[#printed + 1] = fmt:format(...) end
"""


class VersionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(STUB)
        src = (ROOT / "Map" / "News.lua").read_text(encoding="utf-8")
        self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", src)
        self.lua.execute("for k, v in pairs(mod.defaults) do mod.db[k] = v end")

    def hear(self, version, client="Forever"):
        self.lua.eval("mod.HeardVersion")(version, client)

    def printed(self):
        return list(self.lua.eval("printed").values())

    def test_on_by_default(self):
        self.assertTrue(self.lua.eval("mod.defaults.updateNotice"))

    def test_a_newer_release_is_told(self):
        for newer in ("v0.8.12", "v0.9.0", "v1.0.0", "v0.8.100"):
            with self.subTest(newer=newer):
                self.setUp()
                self.hear(newer)
                self.assertEqual(self.printed(), ["OpenMap %s is out (you have v0.8.11). Update through CurseForge." % newer])

    def test_the_same_or_older_is_not(self):
        for v in ("v0.8.11", "v0.8.10", "v0.7.99", "v0.8.9"):
            self.hear(v)
        self.assertEqual(self.printed(), [])

    def test_only_releases_count(self):
        # test builds, betas, a checkout's "dev", and anything not a version at all
        for v in ("v0.8.12-test", "v0.8.12-beta", "v0.9.0-test2", "dev", "0.8.12", "v0.8", "v0.8.12.1",
                  "v0.8.12 ", "", "v9999.0.0", "vX.Y.Z", None, 12):
            self.hear(v)
        self.assertEqual(self.printed(), [])

    def test_a_jump_too_far_is_not_believed(self):
        self.hear("v2.0.0")
        self.assertEqual(self.printed(), [])
        self.hear("v1.0.0")
        self.assertEqual(len(self.printed()), 1)

    def test_each_client_against_its_own(self):
        self.hear("v0.9.0", "Retail")
        self.hear("v0.9.0", None)
        self.assertEqual(self.printed(), [])
        self.lua.execute("ns.Client = 'Retail'")
        self.hear("v0.9.0", "Retail")
        self.assertEqual(len(self.printed()), 1)

    def test_once_a_session(self):
        self.hear("v0.8.12")
        self.hear("v0.8.13")
        self.hear("v0.8.12")
        self.assertEqual(len(self.printed()), 1)

    def test_a_test_build_counts_as_its_release(self):
        # (v0.8.11-test is told of v0.8.12, not of v0.8.11)
        self.lua.execute("ns.version = 'v0.8.11-test'")
        self.hear("v0.8.11")
        self.assertEqual(self.printed(), [])
        self.hear("v0.8.12")
        self.assertEqual(self.printed(), ["OpenMap v0.8.12 is out (you have v0.8.11-test). Update through CurseForge."])

    def test_a_checkout_is_never_told(self):
        self.lua.execute("ns.version = 'dev'")
        self.hear("v9.9.9")
        self.assertEqual(self.printed(), [])

    def test_off_says_nothing_and_sends_nothing(self):
        self.lua.execute("mod.db.updateNotice = false")
        self.hear("v0.8.12")
        self.assertEqual(self.printed(), [])
        self.assertIsNone(self.lua.eval("mod.VersionFields()"))
        self.lua.execute("mod.db.updateNotice = true")
        self.assertEqual(tuple(self.lua.eval("{ mod.VersionFields() }").values()), ("v0.8.11", "Forever"))

    def test_a_test_build_never_advertises_itself(self):
        # (a version that isn't out yet: never sent, and never believed if another copy sends it)
        for v in ("v0.8.12-test", "v0.8.12-test4", "v0.9.0-beta", "dev"):
            self.lua.execute("ns.version = '%s'" % v)
            self.assertIsNone(self.lua.eval("mod.VersionFields()"), v)
        self.lua.execute("ns.version = 'v0.8.11'")
        self.hear("v0.8.12-test")
        self.assertEqual(self.printed(), [])


# Pins.lua with every frame a stand-in that takes any call (its list and card aren't what's tested)
PINS_STUB = r"""
local U = setmetatable({}, {})
getmetatable(U).__index = function() return function() return U end end
getmetatable(U).__call = function() return U end
getmetatable(U).__concat = function(a, b) return tostring(a) .. tostring(b) end
NOW, sent, events, frames = 1000, {}, {}, {}
local function Frame()
	local f = { scripts = {}, shown = false }
	function f:SetScript(k, fn) self.scripts[k] = fn end
	function f:HookScript(k, fn) self.scripts[k] = fn end
	function f:Hide() self.shown = false end
	function f:Show() self.shown = true end
	function f:IsShown() return self.shown end
	function f:GetPoint() end
	function f:GetText() return "" end
	frames[#frames + 1] = f
	-- (a method, capitalised, takes any call; a field, lower case, is nil until set)
	return setmetatable(f, { __index = function(_, k) if k:match("^%u") then return function() return U end end end })
end
CreateFrame = function() return Frame() end
StaticPopupDialogs, StaticPopup_Show = {}, function() end
C_Map = { GetMapInfo = function() return { name = "Elwynn Forest" } end }
GetTime, time = function() return NOW end, function() return NOW end
tinsert, tremove = table.insert, table.remove
strtrim = function(s) return (s:gsub("^%s+", ""):gsub("%s+$", "")) end
strsplit = function(sep, s, n)
	local out = {}
	for piece in (s .. sep):gmatch("([^" .. sep .. "]*)" .. sep) do out[#out + 1] = piece end
	return unpack(out)
end
Ambiguate = function(n) return (n:gsub("%-.*", "")) end
UnitName = function() return "Me" end
IsInRaid, IsInGroup, IsInGuild = function() return false end, function() return true end, function() return true end
C_ChatInfo = { RegisterAddonMessagePrefix = function() end,
	SendAddonMessage = function(prefix, text, channel, target) sent[#sent + 1] = text .. "@" .. channel end }
printed = {}
mod = { defaults = {}, db = {}, padRoots = {} }
function mod.RefreshPins() end
ns = { version = "v0.8.11", Client = "Forever", L = setmetatable({}, { __index = function(_, k) return k end }),
	MapStitch = setmetatable({ Rect = function() return 0, 1, 0, 1 end }, { __index = function() return function() return U end end }),
	Look = setmetatable({ Window = function() return 20, U, U end, Dropdown = function() return 4, 4, 4, 4 end }, { __index = function() return function() return U end end }),
	Safe = { IsSecret = function() return false end, Value = function(v) return v end } }
function ns:GetModule() return mod end
function ns:Print(fmt, ...) printed[#printed + 1] = fmt:format(...) end
function ns.RegisterEvent(_, event, fn) events[event] = fn end
function Fire(event, ...) events[event](nil, event, ...) end
function Run(seconds)
	for _ = 1, seconds * 10 do
		NOW = NOW + 0.1
		for _, f in ipairs(frames) do if f.shown and f.scripts.OnUpdate then f.scripts.OnUpdate(f, 0.1) end end
	end
end
-- (any other of the game's functions: there, answering nothing)
setmetatable(_G, { __index = function(_, k) if type(k) == "string" and k:match("^%u%l") then return function() end end end })
"""


class PinsVersionTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute(PINS_STUB)
        for name in ("Pins.lua", "News.lua"):
            src = (ROOT / "Map" / name).read_text(encoding="utf-8")
            self.lua.execute("local f = assert(loadstring(...)) f('OpenMap', ns)", src)
        self.lua.execute("""
            for k, v in pairs(mod.defaults) do mod.db[k] = v end
            mod:SetupPins(CreateFrame())
        """)

    def drop_and_share(self):
        # a pin dropped with "Send new pins to group" on, its card closed: shared with the party
        self.lua.execute("mod.db.pinsShareGroup = true mod.db.pinsFollowNew = false mod.AddPin(1429, 0.5, 0.5) mod.FinishPin()")
        self.lua.eval("Run")(2)
        return list(self.lua.eval("sent").values())

    def test_a_share_starts_with_the_version_once_a_session(self):
        first = self.drop_and_share()
        self.assertEqual(first[0], "V1\tv0.8.11\tForever@PARTY")
        self.assertTrue(first[1].startswith("P1\t1429\t"), first)
        again = self.drop_and_share()[len(first):]
        self.assertEqual([t[:2] for t in again], ["P1"])

    def test_with_the_notice_off_a_share_is_pins_only(self):
        self.lua.execute("mod.db.updateNotice = false")
        self.assertEqual([t[:2] for t in self.drop_and_share()], ["P1"])

    def test_heard_from_the_group_whatever_pins_shared_is(self):
        self.lua.execute("""
            mod.db.pinsShared = false
            Fire("CHAT_MSG_ADDON", "OpenMap", "V1\tv0.9.0\tForever", "WHISPER", "Stranger-Forever")
            Fire("CHAT_MSG_ADDON", "OpenMap", "V1\tv0.9.0", "PARTY", "Grouped-Forever")
            Fire("CHAT_MSG_ADDON", "OpenMap", "V1", "PARTY", "Grouped-Forever")
        """)
        self.assertEqual(list(self.lua.eval("printed").values()), [])
        self.lua.execute('Fire("CHAT_MSG_ADDON", "OpenMap", "V1\tv0.9.0\tForever", "PARTY", "Grouped-Forever")')
        self.assertEqual(list(self.lua.eval("printed").values()),
                         ["OpenMap v0.9.0 is out (you have v0.8.11). Update through CurseForge."])


if __name__ == "__main__":
    unittest.main()
