"""Boss pins' data (Data/Forever/DungeonBosses.lua) against the maps and boss lists it's for:
python -P tools/offline-test/bosses.py

Each boss's place must be on one of its instance's floors (Data/DungeonMaps.lua's, else
Data/DungeonDrawn.lua's, as Map/Dungeons.lua's FloorsOf picks them), inside the picture (0..1),
and a boss the game lists for it (Places.lua) or one placed by hand (tools/map-dungeons/bosses.json).
(The pins themselves, on the dungeon's map, and the placer need the game: the stub has no world map.)
"""
from pathlib import Path
import json
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "OpenMap" / "Data" / "Forever"


def load():
    lua = LuaRuntime(unpack_returned_tuples=True)
    ns = lua.eval("{ Media = { tex = '' } }")
    for name in ("Places.lua", "DungeonMaps.lua", "DungeonDrawn.lua", "DungeonMinimap.lua", "DungeonBosses.lua"):
        fn = lua.eval("function(src, ns) return assert(loadstring(src))('OpenMap', ns) end")
        fn((DATA / name).read_text(encoding="utf-8"), ns)
    return ns


class Bosses(unittest.TestCase):
    def test_places(self):
        ns = load()
        places = ns.MapPlaces
        placed = json.loads((ROOT / "tools" / "map-dungeons" / "bosses.json").read_text(encoding="utf-8")) \
            if (ROOT / "tools" / "map-dungeons" / "bosses.json").exists() else {}
        n = 0
        for key, bosses in ns.MapDungeonBosses.items():
            base = int(key[8:]) if isinstance(key, str) and key.startswith("minimap:") else key
            floors = ns.MapDungeonMinimap[base] if base != key else (ns.MapDungeonMaps[key] or ns.MapDungeonDrawn[key])
            self.assertTrue(floors, "%s: bosses for a dungeon with no map" % key)
            listed = set((places.bosses[base] or {}).values()) if isinstance(base, int) else set()
            listed |= set(placed.get(str(key), {}))
            for name, p in bosses.items():
                n += 1
                self.assertIn(name, listed, "%s: %s isn't one of its bosses" % (key, name))
                self.assertTrue(1 <= p[1] <= len(floors), "%s: %s on floor %s of %d" % (key, name, p[1], len(floors)))
                self.assertTrue(0 <= p[2] <= 1 and 0 <= p[3] <= 1, "%s: %s off its picture" % (key, name))
        self.assertGreater(n, 100, "fewer bosses placed than the journals alone give")


class InstanceHereTests(unittest.TestCase):
    """the map opened inside a dungeon finds it (Dungeons.lua's InstanceHere, against Places.lua), by its
    mapID: WoW Forever's own too, which the tables of Places.lua's build had none for (The Drowned City's
    drawn map didn't open inside it; #149 takes theirs from the live build's)"""

    def setUp(self):
        import re
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("ns = { Media = { tex = '' } }")
        run = self.lua.eval("function(src) return assert(loadstring(src))('OpenMap', ns) end")
        run((DATA / "Places.lua").read_text(encoding="utf-8"))
        src = (ROOT / "OpenMap" / "Map" / "Dungeons.lua").read_text(encoding="utf-8")
        m = re.search(r"\nlocal function InstanceHere\(\).*?\nend\n", src, re.S)
        self.assertIsNotNone(m, "InstanceHere in Dungeons.lua")
        self.lua.execute("""
            local ns = ns
            here = nil
            function IsInInstance() return here ~= nil end
            function GetInstanceInfo() return "x", "party", 1, "", 5, 0, false, here end
            local function Places() return ns.MapPlaces end
        """ + m.group(0) + """
            function Find(id) here = id local inst = InstanceHere() return inst and inst[2] end
        """)

    def test_by_map_id(self):
        self.assertEqual(self.lua.eval("Find(36)"), "Deadmines")

    def test_forevers_own(self):
        self.assertEqual(self.lua.eval("Find(2970)"), "The Drowned City")
        self.assertEqual(self.lua.eval("Find(3039)"), "Krol'dok Stronghold")
        self.assertEqual(self.lua.eval("Find(3001)"), "Shaper's Terrace")

    def test_not_in_one(self):
        self.assertIsNone(self.lua.eval("Find(nil)"))
        self.assertIsNone(self.lua.eval("Find(0)"))                              # (0: never one, not even a 0 left in the data)

    def test_every_drawn_map_is_found_inside_its_dungeon(self):
        ns = load()
        for key in ns.MapDungeonDrawn.keys():
            self.assertIsInstance(key, int, "%s: a drawn map by name: the map opened inside it can't find it" % key)
            self.assertIsNotNone(self.lua.eval("Find(%d)" % key), "%s: a drawn map no dungeon in Places.lua has" % key)


class DungeonMapSwitchTests(unittest.TestCase):
    """Exercise the dungeon map switch and its saved world map choice."""

    def load_map(self, saved_world_map=None, client="Forever", with_navbar=False):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / "tools" / "offline-test" / "stub.lua").read_text(encoding="utf-8"))
        self.addCleanup(self.lua.execute, r'assert(#ERRORS == 0, table.concat(ERRORS, "\n"))')
        ns = self.lua.table()
        run = self.lua.eval("function(src, path, ns) return assert(loadstring(src, '@' .. path))('OpenMap', ns) end")
        addon = ROOT / "OpenMap"
        data = DATA.parent / client
        for path in (data / "Client.lua", addon / "Core.lua", data / "Places.lua", data / "DungeonMaps.lua"):
            run(path.read_text(encoding="utf-8"), str(path), ns)
        drawn = data / "DungeonDrawn.lua"
        if drawn.is_file():
            run(drawn.read_text(encoding="utf-8"), str(drawn), ns)
        worldmap = ns.NewModule(ns, "worldmap")
        worldmap.padRoots = self.lua.table()
        ns.MapStitch = self.lua.eval("{ InstanceMap = function() end, InstanceName = function(inst) return inst[2] end }")
        path = addon / "Map" / "Dungeons.lua"
        run(path.read_text(encoding="utf-8"), str(path), ns)
        if saved_world_map is not None:
            self.lua.globals().OpenMapCharDB = self.lua.table(
                worldmap=self.lua.table(dungeonWorldMap=saved_world_map))
        ns.InitDB(ns)
        self.lua.globals().worldmap = worldmap
        self.map = self.lua.execute("""
            local stitch, withNavBar = ...
            local here
            C_Map = { GetBestMapForUnit = function() if not here then return 1444 end end,
                      GetMapInfo = function() end }
            function IsInInstance() return here ~= nil end
            function GetInstanceInfo() return "x", "party", 1, "", 5, 0, false, here end

            -- UIPanelButtonTemplate supplies this font string in the game.
            local create = CreateFrame
            function CreateFrame(kind, name, parent, template)
                local frame = create(kind, name, parent, template)
                if template == "UIPanelButtonTemplate" then
                    local text = frame:CreateFontString()
                    function frame:GetFontString() return text end
                end
                return frame
            end

            local map = CreateFrame("Frame")
            map:Hide()
            map.ScrollContainer = CreateFrame("Frame", nil, map)
            map.ScrollContainer:SetSize(600, 450)
            local shownMap = 1444
            stitch.WORLD = 947
            function stitch.FromYards() end  -- No entrance to go to on the world map.
            function stitch.OpenMap(id)
                if id == shownMap then return end
                shownMap = id
                map:OnMapChanged()
            end
            function worldmap.IsStitched() return shownMap == 1444 or shownMap == stitch.WORLD end
            function map:GetMapID() return shownMap end
            function map:OnMapChanged() end
            function map:RefreshOverlayFrames() end
            if withNavBar then
                local names = { [947] = "World", [1414] = "Kalimdor", [1444] = "Feralas" }
                function C_Map.GetMapInfo(id)
                    if names[id] then return { mapID = id, name = names[id] } end
                end
                function stitch.ChainAt() return { 947, 1414, 1444 } end
                local bar = CreateFrame("Frame", nil, map)
                map.NavBar = bar
                bar.homeButton = CreateFrame("Button", nil, bar)
                bar.homeButton.name = "World"
                bar.overflowButton = CreateFrame("Button", nil, bar)
                function bar.overflowButton:SetupMenu(generator) self.menuGenerator = generator end
                function bar.overflowButton:OpenMenu() self.opened = true end
                function bar.overflowButton:listFunc()
                    return { { id = #bar.navList, text = "Current", func = function() error("current crumb cannot navigate") end } }
                end
                bar.overflowButton:SetupMenu(function() end)
                function NavBar_Reset(frame) frame.navList = { frame.homeButton } end
                function NavBar_AddButton(frame, info)
                    local button = CreateFrame("Button", nil, frame)
                    for key, value in pairs(info) do button[key] = value end
                    table.insert(frame.navList, button)
                end
                function NavBar_CheckLength(frame) frame.checkedWidth = frame:GetWidth() end
                function bar:Refresh()
                    NavBar_Reset(self)
                    NavBar_AddButton(self, { name = names[shownMap], id = shownMap })
                end
                function bar:GoToMap(id) stitch.OpenMap(id) end
                function map:OpenAreaDropdownList() end  -- the native binding targets the selected crumb first
                bar:Refresh()
            end
            worldmap:SetupDungeons(map)

            function SetMap(id) stitch.OpenMap(id) end
            function CurrentMap() return map:GetMapID() end
            function SetLocation(id) here = id end
            function CornerButton(offset)
                local canvas = map.ScrollContainer
                local control = CreateFrame("Button", nil, map)
                function control:GetRight() return canvas:GetRight() - 4 end
                function control:GetLeft() return self:GetRight() - 32 end
                function control:GetTop() return canvas:GetTop() - offset end
                function control:GetBottom() return self:GetTop() - 32 end
                return control
            end
            function Find(id, reopenMap)
                SetLocation(id)
                map:Hide()
                RunTimers(0.3)  -- Reopen after the brief hide-and-show shortcut.
                if reopenMap then SetMap(reopenMap) end
                map:Show()
                RunTimers(0.15)
                if worldmap.DungeonViewShown() then return OpenMapDungeonView.inst[2] end
            end
            function ShownFloor()
                local view = OpenMapDungeonView
                local floor = view.floors[view.floor]
                return floor.name or floor.wing
            end
            function CloseMap() map:Hide() end
            return map
        """, ns.MapStitch, with_navbar)

    def test_map_switch_preserves_world_map_until_dungeon_map_is_selected(self):
        self.load_map()
        self.lua.execute("""
            assert(Find(429) == "Dire Maul - East")
            local initialFloor = ShownFloor()
            local floorButton = OpenMapDungeonView.side.pool.thumb[1]
            floorButton:GetScript("OnClick")(floorButton)
            local floor = ShownFloor()
            assert(floor ~= initialFloor, "the test did not select a different floor")
            local button = OpenMapDungeonMapSwitch
            assert(button:IsVisible() and button:GetText() == "World Map")
            local host = button:GetParent()
            local canvas = host.ScrollContainer
            local function CheckAnchor(expectedX, expectedY)
                local point, parent, anchor, x, y = button:GetPoint(1)
                assert(point == "TOPRIGHT" and parent == canvas and anchor == "TOPRIGHT"
                    and x == expectedX and y == expectedY)
            end
            local function Resize(width, expectedX, expectedY)
                canvas:SetWidth(width)
                canvas:GetScript("OnSizeChanged")(canvas)
                CheckAnchor(expectedX, expectedY)
            end
            Resize(200, -6, -6)
            Resize(600, -6, -6)
            local tracking, pin = CornerButton(2), CornerButton(34)
            host.overlayFrames = { tracking, pin }
            host:RefreshOverlayFrames()
            CheckAnchor(-44, -6)
            Resize(200, -8, -72)
            Resize(600, -44, -6)
            pin:Hide()
            host:RefreshOverlayFrames()
            CheckAnchor(-44, -6)
            tracking:Hide()
            host:RefreshOverlayFrames()
            CheckAnchor(-6, -6)
            local floorPicker = CreateFrame("Button", nil, host)
            function floorPicker:GetLeft() return 2 end
            function floorPicker:GetRight() return 162 end
            function floorPicker:GetTop() return canvas:GetTop() end
            function floorPicker:GetBottom() return self:GetTop() - 32 end
            host.overlayFrames = { floorPicker }
            Resize(200, -6, -72)
            Resize(600, -6, -6)
            button:GetScript("OnClick")(button)
            assert(not worldmap.DungeonViewShown(), "World Map did not dismiss the dungeon overlay")
            assert(OpenMapCharDB.worldmap.dungeonWorldMap == true, "World Map choice was not saved")
            assert(worldmap.db.dungeonInside == true, "the switch changed the default inside dungeons")
            assert(button:IsVisible() and button:GetText() == "Dungeon Map")
            SetMap(947)  -- Browse away from the first world map put up by the switch.
            assert(Find(429, 901) == nil, "reopening lost the World Map choice")
            assert(CurrentMap() == 947, "reopening lost the last browsed world map")
            assert(button:IsVisible() and button:GetText() == "Dungeon Map")
            button:GetScript("OnClick")(button)
            assert(worldmap.DungeonViewShown() and OpenMapDungeonView.inst[2] == "Dire Maul - East")
            assert(ShownFloor() == floor and button:GetText() == "World Map")
            assert(OpenMapCharDB.worldmap.dungeonWorldMap == nil, "Dungeon Map did not clear the saved choice")

            button:GetScript("OnClick")(button)
            CloseMap()
            SetLocation()
            FireEvent("PLAYER_ENTERING_WORLD")
            SetLocation(36)
            FireEvent("PLAYER_ENTERING_WORLD")
            assert(Find(36) == nil, "entering a different dungeon lost the World Map choice")
            assert(button:IsVisible() and button:GetText() == "Dungeon Map")
            button:GetScript("OnClick")(button)
            assert(worldmap.DungeonViewShown() and OpenMapDungeonView.inst[2] == "Deadmines")
            assert(OpenMapCharDB.worldmap.dungeonWorldMap == nil)
            CloseMap()
            SetLocation(429)
            FireEvent("PLAYER_ENTERING_WORLD")
            assert(Find(429) == "Dire Maul - East", "Dungeon Map did not restore automatic dungeon maps")
        """)

    def test_world_map_choice_survives_reloading_saved_variables(self):
        self.load_map()
        self.lua.execute("""
            assert(Find(429) == "Dire Maul - East")
            local button = OpenMapDungeonMapSwitch
            button:GetScript("OnClick")(button)
            FireEvent("PLAYER_LOGOUT")
        """)
        saved_world_map = self.lua.eval("OpenMapCharDB.worldmap.dungeonWorldMap")
        self.assertIs(saved_world_map, True)
        self.load_map(saved_world_map)
        self.lua.execute("""
            SetMap(901)
            SetLocation(429)
            FireEvent("PLAYER_ENTERING_WORLD", false, true)
            assert(Find(429) == nil, "reloading inside the dungeon lost the saved World Map choice")
            local button = OpenMapDungeonMapSwitch
            assert(button:IsVisible() and button:GetText() == "Dungeon Map")
            assert(button:GetParent():GetMapID() == 947, "reloading left the native instance map up")
            SetMap(1444)
            assert(Find(429, 901) == nil and CurrentMap() == 1444,
                "reopening after a reload lost the last browsed world map")
            button:GetScript("OnClick")(button)
            assert(worldmap.DungeonViewShown() and OpenMapDungeonView.inst[2] == "Dire Maul - East")
            assert(OpenMapCharDB.worldmap.dungeonWorldMap == nil and worldmap.db.dungeonInside == true)

            button:GetScript("OnClick")(button)
            SetLocation(36)
            FireEvent("PLAYER_ENTERING_WORLD", false, false)
            RunTimers(0.15)
            assert(not worldmap.DungeonViewShown() and button:IsVisible() and button:GetText() == "Dungeon Map")
            button:GetScript("OnClick")(button)
            assert(worldmap.DungeonViewShown() and OpenMapDungeonView.inst[2] == "Deadmines",
                "entering with the world map open did not update the switch")
        """)

    def test_saved_world_map_waits_until_gamepad_combat_ends(self):
        self.load_map(True)
        self.lua.execute("""
            local inCombat = true
            function worldmap.PadCombat() return inCombat end
            assert(Find(429, 901) == nil)
            assert(CurrentMap() == 901, "saved world map switched the game's map in combat")

            inCombat = false
            FireEvent("PLAYER_REGEN_ENABLED")
            RunTimers(0.15)
            assert(CurrentMap() == 947 and not worldmap.DungeonViewShown(), "world map was not restored after combat")
            assert(OpenMapDungeonMapSwitch:IsVisible() and OpenMapDungeonMapSwitch:GetText() == "Dungeon Map")
        """)

    def test_deferred_world_map_restore_rechecks_location_and_preference(self):
        self.load_map(True)
        self.lua.execute("""
            local inCombat = true
            function worldmap.PadCombat() return inCombat end
            assert(Find(429, 901) == nil)
            -- The location can already be different when the combat event runs.
            SetLocation(36)
            inCombat = false
            FireEvent("PLAYER_REGEN_ENABLED")
            RunTimers(0.15)
            assert(CurrentMap() == 901, "a deferred world map restore leaked into another dungeon")

            inCombat = true
            assert(Find(429, 901) == nil)
            OpenMapCharDB.worldmap.dungeonWorldMap = nil
            inCombat = false
            FireEvent("PLAYER_REGEN_ENABLED")
            RunTimers(0.15)
            assert(CurrentMap() == 901, "a deferred world map restore ignored a cleared preference")
        """)

    def test_native_dungeon_card_moves_below_the_switch_in_a_narrow_map(self):
        self.load_map(client="Retail")
        self.lua.execute("""
            Enum.UIMapType = { Dungeon = 4 }
            function C_Map.GetMapInfo(id)
                if id == 901 then return { mapType = Enum.UIMapType.Dungeon, name = 'Dungeon Floor' } end
            end
            Find(nil, 901)
            local button = OpenMapDungeonMapSwitch
            assert(button and button:IsVisible())
            local card
            for _, root in ipairs(worldmap.padRoots) do
                if root.back and root.fold then card = root end
            end
            assert(card and card:IsVisible())
            local host = button:GetParent()
            local canvas = host.ScrollContainer
            host.overlayFrames = { CornerButton(2), CornerButton(34) }
            host:RefreshOverlayFrames()
            local function Resize(width, switchY, cardY)
                canvas:SetWidth(width)
                canvas:GetScript("OnSizeChanged")(canvas)
                RunTimers(0.01)
                assert(select(5, button:GetPoint(1)) == switchY, "switch did not move to its expected row")
                assert(select(5, card:GetPoint(1)) == cardY, "card did not clear the map switch")
            end
            Resize(600, -6, -70)
            Resize(200, -72, -102)
            Resize(600, -6, -70)
        """)

    def test_existing_navbar_shows_the_dungeon_trail_and_selects_floors(self):
        self.load_map(with_navbar=True)
        self.lua.execute("""
            local host = ...
            local bar, home = host.NavBar, host.NavBar.navList[1]
            local overflow = bar.overflowButton
            local stockMenu = overflow.menuGenerator
            assert(Find(429) == "Dire Maul - East")
            local function CheckTrail()
                assert(host.NavBar == bar and bar:IsShown(), "dungeon replaced the stock navbar")
                local crumbs = bar.navList
                assert(#crumbs == 4 and crumbs[1] == home and crumbs[2].name == "Kalimdor" and crumbs[3].name == "Feralas")
                assert(crumbs[4].name == "Dire Maul - East — " .. ShownFloor(), "dungeon trail lost the selected floor")
                return crumbs[4]
            end
            CheckTrail()
            bar:Refresh()
            local crumb = CheckTrail()
            local initial = OpenMapDungeonView.floor
            local floors = crumb:listFunc()
            local nextFloor = initial == 1 and floors[2] or floors[1]
            nextFloor.func(nil, nextFloor.id)
            assert(OpenMapDungeonView.floor == nextFloor.id, "selecting a floor did not update the dungeon view")
            local collapsed = CheckTrail()
            bar:SetWidth(80)
            bar:GetScript("OnSizeChanged")(bar)
            assert(bar.checkedWidth == 80, "resizing did not recalculate breadcrumb overflow")
            collapsed:Hide()
            host:OpenAreaDropdownList(#bar.navList)
            assert(overflow.opened, "the controller did not open the visible overflow menu")
            local menu = { buttons = {} }
            function menu:SetTag() end
            function menu:CreateDivider() end
            function menu:CreateButton(_, callback) table.insert(self.buttons, callback) end
            overflow.menuGenerator(overflow, menu)
            assert(#menu.buttons == #floors, "collapsed dungeon crumb did not expose its floors")
            menu.buttons[initial]()
            assert(OpenMapDungeonView.floor == initial, "the overflow menu did not select the original floor")
            CheckTrail()

            bar:GoToMap(1444)
            assert(not worldmap.DungeonViewShown(), "stock navbar could not leave the dungeon for the same world host")
            assert(host.NavBar == bar and #bar.navList == 2 and bar.navList[1] == home and bar.navList[2].name == "Feralas",
                "leaving the dungeon did not restore the stock navbar")
            assert(overflow.menuGenerator == stockMenu, "leaving the dungeon did not restore the stock overflow menu")
        """, self.map)


class ByMapIDTests(unittest.TestCase):
    """what was kept per dungeon by name (the quill's drawings, the bosses placed) for WoW Forever's own
    goes to its mapID once they have one (Dungeons.lua's ByMapID, #149), never over what's there already"""

    def setUp(self):
        import re
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        src = (ROOT / "OpenMap" / "Map" / "Dungeons.lua").read_text(encoding="utf-8")
        m = re.search(r"\nlocal function ByMapID\(all, inst\).*?\nend\n", src, re.S)
        self.assertIsNotNone(m, "ByMapID in Dungeons.lua")
        self.lua.execute(m.group(0) + "\n Move = ByMapID")

    def test_moved_once(self):
        self.lua.execute("""
            all = { ["The Drowned City"] = { "lines" } }
            Move(all, { 2970, "The Drowned City" })
            assert(all[2970][1] == "lines" and all["The Drowned City"] == nil)
            Move(all, { 2970, "The Drowned City" })
            assert(all[2970][1] == "lines")
        """)

    def test_never_over_whats_there(self):
        self.lua.execute("""
            all = { ["The Drowned City"] = { "old" }, [2970] = { "new" } }
            Move(all, { 2970, "The Drowned City" })
            assert(all[2970][1] == "new" and all["The Drowned City"][1] == "old")
            Move(nil, { 2970, "x" })                    -- (nothing kept yet)
            local none = {}
            Move(none, { 0, "Somewhere" })              -- (no mapID: stays by name)
            assert(next(none) == nil)
        """)

if __name__ == "__main__":
    unittest.main()
