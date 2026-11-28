"""The map's search on its title bar (Map/Nav.lua): left of the window's buttons, as wide as the title leaves it,
shown only with OpenMap's map, made out of combat, nothing of Blizzard's written, and the key binding typing into
it; and what it finds (the world's places, OpenMap's data, your pins, Questie's NPCs, objects and quests, indexed a
chunk a frame and only read): python -P tools/offline-test/search.py."""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


ROOT = Path(__file__).resolve().parents[2] / "OpenMap"
NAV = (ROOT / "Map" / "Nav.lua").read_text(encoding="utf-8")
PANEL = (ROOT / "Map" / "Panel.lua").read_text(encoding="utf-8")
BINDINGS = (ROOT / "Bindings.xml").read_text(encoding="utf-8")


class TitleSearchTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            fighting, stitched, padView = false, false, false
            function InCombatLockdown() return fighting end
            events, timers = {}, {}
            ns = { L = setmetatable({}, { __index = function(_, k) return k end }) }
            function ns.RegisterEvent(owner, event, fn) events[event] = fn end
            function ns.UnregisterEvent(owner, event) events[event] = nil end
            C_Timer = { After = function(_, fn) timers[#timers + 1] = fn end }
            function Flush() local t = timers timers = {} for _, fn in ipairs(t) do fn() end end
            Look = { Dropdown = function() return 4, 4, 4, 4 end }
            mod = { enabled = true }
            function mod.IsStitched() return stitched end
            function mod.PadViewOn() return padView end

            -- frames that remember what was done to them
            local F = {}
            F.__index = F
            made = {}
            function CreateFrame(kind, _, parent, template)
                local f = setmetatable({ kind = kind, parent = parent, template = template, shown = true,
                    w = 0, h = 0, level = parent and (parent.level or 0) + 1 or 0, scripts = {}, hooks = {} }, F)
                made[#made + 1] = f
                if template == "SearchBoxTemplate" then f.Instructions = setmetatable({}, F) end
                return f
            end
            function F:SetSize(w, h) self.w, self.h = w, h end
            function F:SetWidth(w) self.w = w end
            function F:SetHeight(h) self.h = h end
            function F:GetWidth() return self.w end
            function F:GetHeight() return self.h end
            function F:SetAllPoints(t) self.all = t end
            function F:ClearAllPoints() self.points = {} end
            function F:SetPoint(...) self.points = self.points or {} table.insert(self.points, { ... }) end
            function F:SetFrameLevel(l) self.level = l end
            function F:GetFrameLevel() return self.level end
            function F:SetFrameStrata(s) self.strata = s end
            function F:EnableMouse(on) self.mouse = on end
            function F:Show() self.shown = true end
            function F:Hide() self.shown = false if self.scripts.OnHide then self.scripts.OnHide(self) end end
            function F:SetShown(on) if on then self:Show() else self:Hide() end end
            function F:IsShown() return self.shown end
            function F:SetAutoFocus() end
            function F:SetText(t) self.text = t end
            function F:GetText() return self.text or "" end
            function F:SetScript(name, fn) self.scripts[name] = fn end
            function F:HookScript(name, fn) self.hooks[name] = fn end
            function F:SetFocus() self.focus = true end
            function F:ClearFocus() self.focus = false end
            function F:HasFocus() return self.focus or false end
            function F:HighlightText() self.highlighted = true end

            -- Blizzard's map: locked, so a write from OpenMap's code errors
            local function Locked(t)
                return setmetatable(t, { __index = F, __newindex = function(_, k) error("wrote Blizzard's " .. tostring(k)) end })
            end
            title = Locked({ cx = 500, sw = 120 })
            rawset(title, 'GetCenter', function(self) return self.cx end)
            rawset(title, 'GetStringWidth', function(self) return self.sw end)
            buttons = Locked({ shown = true, left = 900 })
            rawset(buttons, 'GetLeft', function(self) return self.left end)
            close = Locked({ shown = true, left = 950 })
            rawset(close, 'GetLeft', function(self) return self.left end)
            border = Locked({ TitleContainer = Locked({ TitleText = title }), MaximizeMinimizeFrame = buttons, CloseButton = close, level = 30 })
            map = Locked({ shown = true, w = 1000, h = 700, level = 10, scripts = {}, hooks = {} })
            rawset(map, "BorderFrame", border)
            opened = 0
            function ToggleWorldMap() opened = opened + 1 rawset(map, "shown", true) end
            WorldMapFrame = map
        """)
        chunk = NAV[NAV.index("local places                    --"):NAV.index("-- Group members")]
        chunk = chunk[:chunk.rindex("--------")]
        self.lua.execute("local S, Safe = S or {}, {}\nlocal L, map = ns.L\n" + chunk.replace("local Look, Safe, L", "") +
                         "\n_G.Refresh = mod.RefreshTitleSearch\n_G.Box = function() return box end\n_G.List = function() return list end\n")
        self.g = self.lua.globals()

    def setup(self):
        self.lua.execute("mod.SetupTitleSearch(map)")

    def box(self):
        return self.lua.eval("Box()")

    def holder(self):
        return self.box().parent

    def test_left_of_the_window_buttons_as_wide_as_the_title_leaves(self):
        self.setup()
        self.lua.execute("stitched = true Refresh()")
        box = self.box()
        p = box.points[1]
        self.assertEqual((p[1], p[3]), ("RIGHT", "LEFT"))
        self.assertTrue(self.lua.eval("function(t) return t == buttons end")(p[2]))
        self.assertLess(p[4], 0)
        # (from the title's right end, 560, to the buttons, 900, less a gap each side)
        self.assertEqual(box.w, 190)
        # a narrow window: only the room there is, down to the least
        self.lua.execute("rawset(buttons, 'left', 700) rawset(map, 'w', 600) Refresh()")
        self.assertEqual(self.box().w, 120)
        self.lua.execute("rawset(buttons, 'left', 600) rawset(map, 'w', 500) Refresh()")
        self.assertEqual(self.box().w, 90)
        # full screen's buttons hidden: by the close button
        self.lua.execute("rawset(buttons, 'shown', false) rawset(map, 'w', 1900) Refresh()")
        self.assertTrue(self.lua.eval("function(t) return t == close end")(self.box().points[1][2]))
        # the results drop down under it, their right edge under its
        lst = self.lua.eval("List()")
        self.assertEqual((lst.points[1][1], lst.points[1][3]), ("TOPRIGHT", "BOTTOMRIGHT"))

    def test_above_the_title_bar(self):
        self.setup()
        self.assertGreater(self.holder().level, self.lua.eval("border.level"))
        self.assertGreater(self.holder().level, self.lua.eval("map.level") + 5)   # (Window.lua's drag strip)

    def test_only_with_openmaps_map(self):
        self.setup()
        self.assertFalse(self.holder().shown)
        self.lua.execute("stitched = true Refresh()")
        self.assertTrue(self.holder().shown)
        # Blizzard's own map (a battleground's, a dungeon's): gone, and what was typed put down
        self.lua.execute("Box():SetFocus() List():Show() stitched = false Refresh()")
        self.assertFalse(self.holder().shown)
        self.assertFalse(self.box().focus)
        self.assertFalse(self.lua.eval("List()").shown)
        # the Gamepad UI's own view, and OpenMap off
        self.lua.execute("stitched = true padView = true Refresh()")
        self.assertFalse(self.holder().shown)
        self.lua.execute("padView = false mod.enabled = false Refresh()")
        self.assertFalse(self.holder().shown)

    def test_made_out_of_combat(self):
        self.lua.execute("fighting = true")
        self.setup()
        self.assertIsNone(self.box())
        self.lua.execute("fighting = false events.PLAYER_REGEN_ENABLED()")
        self.assertIsNotNone(self.box())
        self.assertIsNone(self.lua.eval("events.PLAYER_REGEN_ENABLED"))

    def test_key_binding_types_into_it(self):
        self.setup()
        self.lua.execute("stitched = true mod.FocusSearch()")
        self.assertTrue(self.box().focus)
        # the map closed: opened first
        self.lua.execute("Box():ClearFocus() rawset(map, 'shown', false) mod.FocusSearch() Flush()")
        self.assertEqual(self.lua.eval("opened"), 1)
        self.assertTrue(self.box().focus)
        # ... not in combat
        self.lua.execute("Box():ClearFocus() rawset(map, 'shown', false) fighting = true mod.FocusSearch() Flush()")
        self.assertEqual(self.lua.eval("opened"), 1)
        self.assertFalse(self.box().focus)

    def test_bound_and_named(self):
        self.assertIn('OpenMap_Binding("search")', BINDINGS)
        self.assertIn('SEARCH = L["Find a place"]', PANEL)
        self.assertIn('if id == "search"', PANEL)
        # (not in the menu as well: one search box, Nav.lua's)
        self.assertNotIn("mod.CreateSearch(", PANEL)



class SourcesTests(unittest.TestCase):
    """What the search finds, and what a pick does."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            timers, printed, glided, pinged = {}, {}, nil, {}
            C_Timer = { After = function(_, fn) timers[#timers + 1] = fn end,
                NewTimer = function(_, fn) return { Cancel = function() end } end }
            function Flush() local t = timers timers = {} for _, fn in ipairs(t) do fn() end return #t end
            function geterrorhandler() return function(e) error(e) end end
            ns = { L = setmetatable({}, { __index = function(_, k) return k end }) }
            function ns:Print(t) printed[#printed + 1] = t end
            Enum = { UIMapType = { Continent = 2, Zone = 3 } }
            -- two zones side by side on a world of 0..1
            local rects = { [1429] = { 0.5, 0.6, 0.5, 0.6 }, [1411] = { 0.2, 0.3, 0.4, 0.5 }, [1414] = { 0, 0.45, 0, 1 } }
            C_Map = {
                GetMapChildrenInfo = function(_, kind)
                    if kind == 2 then return { { mapID = 1414, name = "Kalimdor" } } end
                    return { { mapID = 1429, name = "Elwynn Forest" }, { mapID = 1411, name = "Durotar" } }
                end,
                GetAreaInfo = function(id) return ({ [87] = "Goldshire", [362] = "Razor Hill" })[id] end,
            }
            S = { WORLD = 947 }
            function S.Rect(id) local r = rects[id] if r then return r[1], r[2], r[3], r[4] end end
            function S.FromYards(cont, x, y) if cont == 0 or cont == 1 then return x / 1000, y / 1000 end end
            function S.InstanceName(inst) return inst[2] end
            function S.ClearPinSet() pinged = {} end
            function S.AddPin(_, u, v) pinged[#pinged + 1] = { u, v } return { EnableMouse = function() end } end
            function S.GlideToRect(u0, v0, u1, v1) glided = { "rect", u0, v0, u1, v1 } end
            function S.OpenMap(id) glided = { "open", id } end
            mod = { db = { pins = { list = {} }, townsfolk = {} } }
            function mod.ToWorld(id, x, y) local l, r, t, b = S.Rect(id) if l then return l + x * (r - l), t + y * (b - t) end end
            function mod.Glide(u, v) glided = { "point", u, v } end
            function mod.ViewNow() return 0, 0, 1 end
            function mod.HasTownsfolk() return true end
            function mod:RefreshTownsfolk() townsfolkRefreshed = true end
            mod.TOWNSFOLK = { { key = "innkeeper", name = "Innkeepers" } }
            ns.MapPlaces = {
                instances = { { 0, 100, 200, { { 36, "Deadmines", false, 17, 26 } } } },
                transports = { { "boat", "Booty Bay - Ratchet", 1, 10, 20, 0, 30, 40 }, { "boat", "Booty Bay - Ratchet", 0, 30, 40, 1, 10, 20 },
                    { "airship", "To Zephras Isle", 2991, 1, 1, 1, 50, 60 } },
            }
            ns.MapCaves = { [2] = { "Burning Blade Coven", 1, 200, 400, 210, 420 } }
            ns.MapExplore = { achievements = { [776] = { 1429, 1 } }, pieces = { [1] = { ["a"] = { 776, { 87 }, 0.5, 0.5 } } } }
            ns.MapGapPlaces = { { 17732, "Excavation Site: Wetlands", { 0, 0, 1, 1 }, { 0.77, 0.46 } } }

            -- Questie's database, locked: a write from OpenMap's code errors
            local function Locked(t) return setmetatable(t, { __newindex = function(_, k) error("wrote Questie's " .. tostring(k)) end }) end
            local npcs = Locked({
                [1] = Locked({ name = "Innkeeper Farley", spawns = Locked({ [12] = { { 50, 50 } } }) }),
                [2] = Locked({ name = "Spirit Healer", spawns = Locked({ [12] = { { 10, 10 } }, [14] = { { 90, 90 } } }) }),
                [3] = Locked({ name = "Nobody Anywhere" }),
                [4] = Locked({ name = "Marshal Dughan", spawns = Locked({ [12] = { { 40, 60 } } }) }),
                [5] = Locked({ name = "Spirit Healer", spawns = Locked({ [14] = { { 50, 10 } } }) }),
            })
            local objects = Locked({ [10] = Locked({ name = "Peacebloom", spawns = Locked({ [12] = { { 20, 20 }, { 30, 30 } } }) }) })
            local quests = Locked({ [100] = Locked({ name = "A Threat Within", startedBy = Locked({ { 4 } }), finishedBy = Locked({ { 1 } }) }),
                [101] = Locked({ name = "Nowhere Quest" }) })
            local function Pointers(t) local p = {} for id in pairs(t) do p[id] = true end return Locked(p) end
            queries = 0
            QDB = Locked({ NPCPointers = Pointers(npcs), ObjectPointers = Pointers(objects), QuestPointers = Pointers(quests),
                QueryNPCSingle = function(id, k) queries = queries + 1 return npcs[id] and npcs[id][k] end,
                QueryObjectSingle = function(id, k) queries = queries + 1 return objects[id] and objects[id][k] end,
                QueryQuestSingle = function(id, k) queries = queries + 1 return quests[id] and quests[id][k] end })
            ZoneDB = Locked({ GetUiMapIdByAreaId = function(_, area) return ({ [12] = 1429, [14] = 1411 })[area] end })
            QuestieLoader = { ImportModule = function(_, name) return ({ QuestieDB = QDB, ZoneDB = ZoneDB })[name] end }
            box = { text = "", focus = true }
            function box:GetText() return self.text end
            function box:HasFocus() return self.focus end
            function box:ClearFocus() self.focus = false end
            function box:SetText(t) self.text = t end
        """)
        chunk = NAV[NAV.index("local places                    --"):NAV.index("-- Group members")]
        chunk = chunk[:chunk.index("-- the search box, on `parent`")]
        self.lua.execute("local Safe, L = {}, ns.L\n" + chunk.replace("local box, list", "local list = { Hide = function() end }")
                         + "\n_G.Go = Go\n_G.pingSetOn = function() pingSet = {} end\n")
        self.lua.execute("pingSetOn()")

    def found(self, text):
        out = self.lua.eval("mod.SearchResults")(text)
        return [(r[1].name, r[1].kind) for r in out.values()]

    def index(self):
        self.lua.execute("mod.IndexQuestieSearch()")
        frames = 0
        while self.lua.eval("Flush()") > 0:
            frames += 1
        return frames

    def test_openmaps_own_places(self):
        self.assertIn(("Elwynn Forest", "Zone"), self.found("elwynn"))
        self.assertIn(("Deadmines", "Dungeon"), self.found("deadm"))
        self.assertIn(("Goldshire", "Area"), self.found("goldsh"))
        self.assertIn(("Excavation Site: Wetlands", "Area"), self.found("excavation"))
        self.assertIn(("Burning Blade Coven", "Cave"), self.found("blade"))
        self.assertIn(("Innkeepers", "Townsfolk"), self.found("innkeep"))
        # a boat's route: one entry, both docks pinged and shown together; an airship off the stitched map: its dock here only
        self.assertEqual(self.found("booty"), [("Booty Bay - Ratchet", "Boat")])
        self.lua.execute("Go(mod.SearchResults('booty')[1][1])")
        self.assertEqual(len(self.lua.eval("pinged")), 2)
        self.assertEqual(self.lua.eval("glided[1]"), "rect")

    def test_pins_by_their_notes(self):
        self.lua.execute("mod.db.pins.list = { { map = 1429, x = 0.5, y = 0.5, note = 'Herbs here' }, { map = 1429, x = 0.1, y = 0.1, note = '' } }")
        self.assertEqual(self.found("herbs"), [("Herbs here", "Map pin")])

    def test_questie_indexed_a_chunk_a_frame_and_only_read(self):
        self.assertEqual(self.found("farley"), [])          # (not before the search is used)
        self.assertEqual(self.lua.eval("queries"), 0)
        self.lua.execute("mod.IndexQuestieSearch()")
        self.assertEqual(self.lua.eval("queries"), 0)       # (nothing on the frame it's asked for)
        self.index()
        self.assertIn(("Innkeeper Farley", "NPC"), self.found("farley"))
        self.assertIn(("Peacebloom", "Object"), self.found("peace"))
        self.assertIn(("A Threat Within", "Quest"), self.found("threat"))
        # (nothing without a place: an NPC with no spawns, a quest nobody gives)
        self.assertEqual(self.found("nobody"), [])
        self.assertEqual(self.found("nowhere"), [])

    def test_spread_over_frames(self):
        self.lua.execute("CHUNK_TEST = true")
        frames = self.index()
        self.assertGreaterEqual(frames, 1)
        src = NAV[NAV.index("local function IndexQuestie()"):NAV.index("mod.IndexQuestieSearch = IndexQuestie")]
        self.assertIn("for _ = 1, CHUNK do", src)
        self.assertIn("C_Timer.After(0, Step)", src)

    def test_picks(self):
        self.index()
        # an NPC at several places, in two records of one name: one entry, each place pinged, all shown together
        self.assertEqual(self.found("spirit healer"), [("Spirit Healer", "NPC")])
        self.lua.execute("Go(mod.SearchResults('spirit healer')[1][1])")
        self.assertEqual(len(self.lua.eval("pinged")), 3)
        self.assertEqual(self.lua.eval("glided[1]"), "rect")
        # one place: glided to and pinged
        self.lua.execute("Go(mod.SearchResults('farley')[1][1])")
        self.assertEqual(self.lua.eval("glided[1]"), "point")
        self.assertAlmostEqual(self.lua.eval("glided[2]"), 0.55)
        # a quest: who gives it and who takes it in
        self.lua.execute("Go(mod.SearchResults('threat')[1][1])")
        pts = sorted(tuple(round(c, 3) for c in p.values()) for p in self.lua.eval("pinged").values())
        self.assertEqual(pts, [(0.54, 0.56), (0.55, 0.55)])
        # a townsfolk kind: turned on
        self.lua.execute("Go(mod.SearchResults('innkeepers')[1][1])")
        self.assertTrue(self.lua.eval("mod.db.townsfolk.innkeeper"))
        self.assertTrue(self.lua.eval("townsfolkRefreshed"))

    def test_capped_and_grouped_by_kind(self):
        self.lua.execute("""
            local list = {}
            for i = 1, 30 do list[i] = { map = 1429, x = 0.5, y = 0.5, note = 'Mark ' .. i } end
            mod.db.pins.list = list
            ns.MapCaves[3] = { 'Marked Cave Of Many Words', 1, 1, 1, 2, 2 }
        """)
        found = self.found("mark")
        kinds = [k for _, k in found]
        self.assertEqual(kinds.count("Map pin"), 4)          # (at most PER_KIND of one kind)
        # the cave's longer name sorts after the pins', but caves come first: grouped by kind
        self.assertEqual(kinds, ["Cave"] + ["Map pin"] * 4)

    def test_no_questie(self):
        self.lua.execute("QuestieLoader = nil")
        self.assertEqual(self.index(), 0)
        self.assertIn(("Elwynn Forest", "Zone"), self.found("elwynn"))


if __name__ == "__main__":
    unittest.main()
