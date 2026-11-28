"""The game's quest tracking and waypoint calls kept out of fights, and a quest icon's click leaving the quest's
details to the player: python -P tools/offline-test/taint.py.

Made from OpenMap's code, AddQuestWatch, SetSuperTrackedQuestID, SetUserWaypoint and SetSuperTrackedUserWaypoint
have the objective tracker redraw on the next frame carrying OpenMap's taint; in a fight that redraw reads your
buffs, the game refuses ("auras ... secret while tainted by OpenMap") and the redraw stops (#295). The quest's
details opened from OpenMap's code held a quest ID it set, and their Share button's protected call was blocked
(#426). Run here: Core.lua's ns.OutOfCombat in Lua 5.1, and the call sites read from the files.
"""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


ADDON = Path(__file__).resolve().parents[2] / "OpenMap"
CORE = (ADDON / "Core.lua").read_text(encoding="utf-8")
QUESTS = (ADDON / "Map" / "Quests.lua").read_text(encoding="utf-8")
NAV = (ADDON / "Map" / "Nav.lua").read_text(encoding="utf-8")
PINS = (ADDON / "Map" / "Pins.lua").read_text(encoding="utf-8")


def function(src, head):
    m = re.search(r"\n" + re.escape(head) + r".*?\nend\n", src, re.S)
    assert m, head
    return m.group(0)


class OutOfCombatTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        helper = re.search(r"\nlocal afterFight, afterFightOwner = .*?\nfunction ns\.OutOfCombat\(key, fn\)\n.*?\nend\n", CORE, re.S)
        self.assertIsNotNone(helper, "ns.OutOfCombat")
        self.lua.execute("""
            fight = false
            function InCombatLockdown() return fight end
            ns, handlers = {}, {}
            function ns.RegisterEvent(owner, event, fn) handlers[event] = fn end
            function ns.UnregisterEvent(owner, event) handlers[event] = nil end
            function geterrorhandler() return error end
            calls = {}
        """ + helper.group(0))

    def test_out_of_a_fight_at_once(self):
        self.lua.execute('ns.OutOfCombat("quest", function() calls[#calls + 1] = "now" end)')
        self.assertEqual(self.lua.eval("#calls"), 1)

    def test_in_a_fight_as_it_ends_the_latest_one(self):
        self.lua.execute("""fight = true
            ns.OutOfCombat("quest", function() calls[#calls + 1] = "first" end)
            ns.OutOfCombat("quest", function() calls[#calls + 1] = "second" end)
            ns.OutOfCombat("waypoint", function() calls[#calls + 1] = "waypoint" end)""")
        self.assertEqual(self.lua.eval("#calls"), 0)
        self.lua.execute("fight = false handlers.PLAYER_REGEN_ENABLED()")
        got = sorted(self.lua.eval("calls")[i] for i in range(1, self.lua.eval("#calls") + 1))
        self.assertEqual(got, ["second", "waypoint"])
        self.assertIsNone(self.lua.eval("handlers.PLAYER_REGEN_ENABLED"))


class CallSiteTests(unittest.TestCase):
    def test_a_quest_icon_tracks_out_of_a_fight(self):
        click = function(QUESTS, "local function Click(pin)")
        self.assertIn('ns.OutOfCombat("quest", function()', click)
        before = click.split('ns.OutOfCombat("quest"')[0]
        self.assertNotIn("AddQuestWatch", before)
        self.assertNotIn("SetSuperTrackedQuestID(", before)

    def test_a_quest_icon_leaves_the_details_to_the_player(self):
        click = function(QUESTS, "local function Click(pin)")
        self.assertNotIn("ShowQuestDetails", click)

    def test_the_automatic_waypoint_move_not_in_a_fight(self):
        zone = function(NAV, "function mod.ZoneWaypoint()")
        self.assertRegex(zone.split("\n")[2], r"InCombatLockdown\(\)")

    def test_ctrl_clicks_waypoint_in_a_fight_waits(self):
        own = function(NAV, "function mod.OwnViewWaypoint()")
        self.assertIn('ns.OutOfCombat("waypoint", function()', own)
        before = own.split('ns.OutOfCombat("waypoint"')[0]
        self.assertNotIn("C_Map.SetUserWaypoint, UiMapPoint", before)

    def test_every_other_waypoint_call_out_of_a_fight(self):
        for name, src in (("Nav.lua", NAV), ("Pins.lua", PINS)):
            for m in re.finditer(r"pcall\(C_Map\.SetUserWaypoint, UiMapPoint", src):
                start = src.rfind("\nfunction ", 0, m.start())
                start = max(start, src.rfind("\nlocal function ", 0, m.start()))
                body = src[start:m.start()]
                self.assertTrue("InCombatLockdown()" in body or "OutOfCombat" in body,
                                "%s: a waypoint set with no combat check before it:\n%s" % (name, body[-300:]))


if __name__ == "__main__":
    unittest.main()
