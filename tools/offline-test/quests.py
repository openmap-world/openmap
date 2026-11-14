"""The quests in your log on the map (Map/Quests.lua) in Lua 5.1: python -P tools/offline-test/quests.py

On OpenMap's usual map Blizzard's own pins draw the quests of the zone its map underneath is on, so
OpenMap leaves those out. In the controller view (PadView.lua) Blizzard's map is under the view, unseen,
and so are its pins: every quest must be OpenMap's icon there (#225), with the "!" of those to start
in the zone it is on, and a click mustn't open Blizzard's quest log, whose details set the pad's
buttons from OpenMap's code.
(What the icons look like, and where Blizzard's map is, needs the game: the stub has neither.)
"""
from pathlib import Path
import unittest

from lupa.lua51 import LuaRuntime

SRC = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "Quests.lua").read_text(encoding="utf-8")

STUB = r"""
NOOP = { __index = function(_, k) if k ~= "questMark" then return function() end end end }   -- (any method; no such field yet)
function wipe(t) for k in pairs(t) do t[k] = nil end return t end
ZONE, OTHER = 1429, 1430            -- two stitched zones: the one Blizzard's map is on, and the next
RECTS = { [ZONE] = { 0.2, 0.3, 0.4, 0.5 }, [OTHER] = { 0.3, 0.4, 0.4, 0.5 } }   -- world: l, r, t, b
QUESTS = {                           -- C_QuestLog.GetQuestsOnMap, by map (the host's quests are on its map too)
	[ZONE] = { { questID = 100, x = 0.5, y = 0.5 } },
	[OTHER] = { { questID = 200, x = 0.5, y = 0.5 } },
}
calls, drawn, offers, onSets, glides, scripts = {}, {}, {}, {}, {}, {}
pinsOf = { quests = drawn, questoffers = offers }   -- the pins each set has now
OFFERS, asked = {}, {}              -- C_QuestLine.GetAvailableQuestLines, by map; the maps it was asked about
stitched, host, padView, questPOI = false, nil, false, true
tip, details, opened = {}, {}, {}

S = { WORLD = 947 }
function S.Rect(id) local r = RECTS[id] if r then return r[1], r[2], r[3], r[4] end end
function S.IsBuilt() return true end
function S.PinSet(key) return { key = key } end
function S.ClearPinSet(set) wipe(pinsOf[set.key]) end
function S.SetPinSetOn(set, on) onSets[set.key] = on end
function S.Look() end
function S.GlideToWorld(u, v, z) glides[#glides + 1] = { u, v, z } end
function S.AddPin(set, u, v, look, data)
	local pin = setmetatable({ u = u, v = v, data = data, scripts = {} }, NOOP)
	function pin:SetScript(k, fn) self.scripts[k] = fn end
	function pin:CreateTexture() return setmetatable({}, NOOP) end
	local list = pinsOf[set.key]
	list[#list + 1] = pin
	return pin
end

Enum = { UIMapType = { Zone = 3, Continent = 2 } }
C_Map = {
	GetMapChildrenInfo = function() return { { mapID = ZONE }, { mapID = OTHER } } end,
	GetMapInfo = function(id) return { mapID = id, mapType = Enum.UIMapType.Zone } end,
}
Enum.QuestLineFloorLocation = { Above = 0, Below = 1, Same = 2 }
C_QuestLine = { GetAvailableQuestLines = function(id) asked[#asked + 1] = id return OFFERS[id] end }
C_QuestLog = {
	GetQuestsOnMap = function(id) return QUESTS[id] end,
	IsComplete = function() return false end,
	GetTitleForQuestID = function(id) return "Quest " .. id end,
	GetLogIndexForQuestID = function() end,
	GetQuestWatchType = function() end,
	AddQuestWatch = function(id) calls[#calls + 1] = "watch " .. id end,
}
C_SuperTrack = { SetSuperTrackedQuestID = function(id) calls[#calls + 1] = "track " .. id end }
GetCVarBool = function() return questPOI end
InCombatLockdown = function() return false end
C_Timer = { After = function() end }
hooksecurefunc = function() end
GameTooltip = setmetatable({}, { __index = function(t, k)
	return function(_, a, ...) if k == "AddLine" or k == "SetText" then tip[#tip + 1] = a end end
end })
CreateFrame = function() return setmetatable({}, NOOP) end
QuestMapFrame_ShowQuestDetails = function(id) details[#details + 1] = id end

L = setmetatable({}, { __index = function(_, k) return k end })
mod = { defaults = {}, db = {} }
ns = { MapStitch = S, L = L }
function ns:GetModule() return mod end
function mod.IsStitched() return stitched end
function mod.HostMap() return host end
function mod.ToWorld(id, x, y) local l, r, t, b = S.Rect(id) return l + x * (r - l), t + y * (b - t) end
function mod.PadViewOn() return padView end

-- Blizzard's map: on ZONE, windowed, its quest log shown
blizz = setmetatable({ QuestLog = setmetatable({}, NOOP) }, NOOP)
function blizz:GetMapID() return ZONE end
function blizz:IsMaximized() return false end
function blizz:IsShown() return true end
function blizz.QuestLog:IsShown() return true end
function blizz:HandleUserActionOpenSidePanel() opened[#opened + 1] = "side panel" end

assert(loadstring(SRC, "Quests.lua"))("OpenMap", ns)

function Refresh() mod:RefreshQuests() end
function Ids() local out = {} for i, p in ipairs(drawn) do out[i] = p.data.id end table.sort(out) return out end
function OfferIds() local out = {} for i, p in ipairs(offers) do out[i] = p.data.id end table.sort(out) return out end
"""


class Quests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().SRC = SRC
        self.lua.execute(STUB)
        self.lua.execute("mod:SetupQuests(blizz)")

    def ids(self):
        return list(self.lua.eval("Ids()").values())

    def usual_map(self):
        # OpenMap's usual map: set up, Blizzard's map on ZONE underneath
        self.lua.execute("stitched, host, padView = true, ZONE, false")

    def controller_view(self):
        # PadView.lua: OpenMap's usual map not set up (no host), the view the map
        self.lua.execute("stitched, host, padView = false, nil, true")

    def test_usual_map_leaves_blizzards_own_zone_to_blizzard(self):
        self.usual_map()
        self.lua.execute("Refresh()")
        self.assertEqual(self.ids(), [200], "the host zone's quest drawn over Blizzard's own pin for it")

    def test_usual_map_with_all_quests_off_draws_none(self):
        self.usual_map()
        self.lua.execute("mod.db.allQuests = false Refresh()")
        self.assertEqual(self.ids(), [])
        self.assertFalse(self.lua.eval("onSets.quests"))

    def test_controller_view_draws_every_zone_including_blizzards(self):
        # Blizzard's map is under the view, unseen: the zone it is on has no quest icons but these (#225)
        self.controller_view()
        self.lua.execute("Refresh()")
        self.assertEqual(self.ids(), [100, 200])
        self.assertTrue(self.lua.eval("onSets.quests"))

    def test_controller_view_icons_are_where_the_quests_are_in_the_world(self):
        self.controller_view()
        self.lua.execute("Refresh()")
        by_id = {self.lua.eval(f"drawn[{i}].data.id"): (self.lua.eval(f"drawn[{i}].u"), self.lua.eval(f"drawn[{i}].v"))
                 for i in (1, 2)}
        self.assertAlmostEqual(by_id[100][0], 0.25)
        self.assertAlmostEqual(by_id[100][1], 0.45)
        self.assertAlmostEqual(by_id[200][0], 0.35)

    def test_controller_view_with_all_quests_off_draws_blizzards_zone_only(self):
        self.controller_view()
        self.lua.execute("mod.db.allQuests = false Refresh()")
        self.assertEqual(self.ids(), [100])

    def test_controller_view_with_all_quests_off_and_no_known_zone_draws_none(self):
        self.controller_view()
        self.lua.execute("RECTS[ZONE] = nil mod.db.allQuests = false Refresh()")
        self.assertEqual(self.ids(), [])

    def test_quest_objectives_filter_off_draws_none_in_the_controller_view_too(self):
        self.controller_view()
        self.lua.execute("questPOI = false Refresh()")
        self.assertEqual(self.ids(), [])
        self.assertFalse(self.lua.eval("onSets.quests"))

    def test_nothing_before_either_map_is_the_map(self):
        self.lua.execute("stitched, host, padView = false, nil, false Refresh()")
        self.assertEqual(self.ids(), [])

    def test_set_up_twice_hooks_once(self):
        self.lua.execute("""
            n = 0
            CreateFrame = function() n = n + 1 return setmetatable({}, NOOP) end
            mod:SetupQuests(blizz)
        """)
        self.assertEqual(self.lua.eval("n"), 0, "its events and hooks made again")

    def offer_ids(self):
        return list(self.lua.eval("OfferIds()").values())

    def offers(self):
        # what Blizzard's map would show as "!" in its zone: the ones to start, and the ones not to draw
        self.lua.execute("""
            OFFERS[ZONE] = {
                { questID = 300, questName = "Seeds", questLineName = "The Farm", x = 0.5, y = 0.5, floorLocation = 2 },
                { questID = 301, questName = "In your log", x = 0.1, y = 0.1, inProgress = true },
                { questID = 302, questName = "Hidden", x = 0.1, y = 0.1, isHidden = true },
                { questID = 303, questName = "Upstairs", x = 0.1, y = 0.1, floorLocation = 0 },
                { questID = 100, questName = "Also in the log (as an icon already)", x = 0.5, y = 0.5 },
                { questID = 304, questName = "No floor given", x = 0.8, y = 0.8 },
                { questName = "No id", x = 0.1, y = 0.1 },
                { questID = 305, questName = "No place" },
            }
            OFFERS[OTHER] = { { questID = 306, questName = "Next zone", x = 0.5, y = 0.5 } }
        """)

    def test_controller_view_draws_the_quests_you_can_start_in_blizzards_zone(self):
        self.controller_view()
        self.offers()
        self.lua.execute("Refresh()")
        self.assertEqual(self.offer_ids(), [300, 304])
        self.assertTrue(self.lua.eval("onSets.questoffers"))
        self.assertEqual(self.ids(), [100, 200], "the quests in the log changed")

    def test_the_quests_to_start_are_asked_for_in_blizzards_zone_only(self):
        # (its own pins are for the one zone it's on; another zone's would be a request for each)
        self.controller_view()
        self.offers()
        self.lua.execute("Refresh()")
        self.assertEqual(list(self.lua.eval("asked").values()), [self.lua.eval("ZONE")])

    def test_the_quest_to_start_is_where_it_is_with_its_name_on_the_tooltip(self):
        self.controller_view()
        self.offers()
        self.lua.execute("Refresh() pin = offers[1] pin.scripts.OnEnter(pin)")
        self.assertAlmostEqual(self.lua.eval("pin.u"), 0.25)
        self.assertAlmostEqual(self.lua.eval("pin.v"), 0.45)
        self.assertEqual(list(self.lua.eval("tip").values()), ["Seeds", "The Farm"])
        self.assertIsNone(self.lua.eval("rawget(pin, 'OnClick')"), "a click that does something: it only has a tooltip")

    def test_the_quests_to_start_stay_with_quests_from_every_zone_off(self):
        self.controller_view()
        self.offers()
        self.lua.execute("mod.db.allQuests = false Refresh()")
        self.assertEqual(self.offer_ids(), [300, 304])

    def test_no_quests_to_start_on_the_usual_map(self):
        # (Blizzard's own pins show them there)
        self.usual_map()
        self.offers()
        self.lua.execute("Refresh()")
        self.assertEqual(self.offer_ids(), [])
        self.assertFalse(self.lua.eval("onSets.questoffers"))
        self.assertEqual(self.lua.eval("#asked"), 0)

    def test_the_quests_to_start_go_with_the_view_and_the_filter(self):
        self.controller_view()
        self.offers()
        self.lua.execute("Refresh() questPOI = false Refresh()")
        self.assertEqual(self.offer_ids(), [])
        self.assertFalse(self.lua.eval("onSets.questoffers"))
        self.lua.execute("questPOI = true Refresh()")
        self.assertEqual(self.offer_ids(), [300, 304])
        self.lua.execute("padView, stitched = false, false Refresh()")   # (the view isn't the map any more)
        self.assertEqual(self.offer_ids(), [])
        self.assertFalse(self.lua.eval("onSets.questoffers"))

    def test_no_quests_to_start_in_a_zone_the_art_doesnt_have(self):
        self.controller_view()
        self.offers()
        self.lua.execute("RECTS[ZONE] = nil Refresh()")
        self.assertEqual(self.offer_ids(), [])

    def test_no_quests_to_start_without_the_quest_line_api(self):
        self.controller_view()
        self.offers()
        self.lua.execute("C_QuestLine = nil Refresh()")
        self.assertEqual(self.offer_ids(), [])
        self.assertEqual(self.ids(), [100, 200])

    def click(self):
        self.lua.execute("Refresh() pin = drawn[1] pin.OnClick(pin)")

    def test_click_in_the_controller_view_tracks_and_zooms_but_leaves_blizzards_quest_log(self):
        self.controller_view()
        self.click()
        self.assertEqual(list(self.lua.eval("calls").values()), ["watch 100", "track 100"])
        self.assertEqual(self.lua.eval("#glides"), 1)
        self.assertEqual(self.lua.eval("#details"), 0, "Blizzard's quest details opened from OpenMap's code")
        self.assertEqual(self.lua.eval("#opened"), 0, "Blizzard's quest log opened from OpenMap's code")

    def test_click_on_the_usual_map_still_shows_the_quest_in_the_log(self):
        self.usual_map()
        self.click()   # (the one zone Blizzard's map isn't on: 200)
        self.assertEqual(list(self.lua.eval("calls").values()), ["watch 200", "track 200"])
        self.assertEqual(list(self.lua.eval("details").values()), [200])

    def hint(self):
        self.lua.execute("Refresh() pin = drawn[1] pin.scripts.OnEnter(pin) hint = tip[#tip]")
        return self.lua.eval("hint")

    def test_tooltip_in_the_controller_view_doesnt_promise_the_quest_log(self):
        self.controller_view()
        self.assertEqual(self.hint(), "Click: track this quest and zoom to it")

    def test_tooltip_on_the_windowed_usual_map_does(self):
        self.usual_map()
        self.assertEqual(self.hint(), "Click: track this quest, zoom to it and show it in the quest log")


if __name__ == "__main__":
    unittest.main()
