"""Questie's icons found in both its shapes (Map/Extras.lua's QuestieModule, PinSpec, SetUpAllPins):
python -P tools/offline-test/questie.py

Questie up to 12.7 brings its HereBeDragons pins as a LibStub library, "HereBeDragonsQuestie-Pins-2.0",
with the template "HereBeDragonsPinsTemplateQuestie"; 12.8 and later as one of its own modules
(QuestieLoader's HBDPins, not in LibStub) with a template of its own (pins.worldmapPinTemplate).
OpenMap must take over Questie's icons either way, or they don't show on the stitched map (#18).
(Taking them over, on the map, needs the game: the stub has no world map.)
"""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime

ROOT = Path(__file__).resolve().parents[2]
SRC = (ROOT / "OpenMap" / "Map" / "Extras.lua").read_text(encoding="utf-8")


def part(pattern):
    m = re.search(pattern, SRC, re.S)
    assert m, pattern
    return m.group(0)


class Questie(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            mod = {}
            set_up = {}                         -- name -> { lib, its spec }
            function SetUpPins(name, lib) set_up[name] = { lib, PinSpec(name, lib) } return "done" end
            function Tell(name) end
            OPEN_TRIES, pending = 3, {}
        """)
        code = "\n".join([
            part(r"\nlocal PIN_LIBS = \{.*?\n\}\n"),
            part(r"\nlocal DEFAULT_TEMPLATE = [^\n]*\n"),
            part(r"\nlocal QUESTIE_MODULE = .*?\nmod\.QUESTIE_MODULE = QUESTIE_MODULE\n"),
            part(r"\nlocal function PinSpec\(name, pins\).*?\nend\n").replace("local function PinSpec(", "function PinSpec("),
            part(r"\nlocal function SetUpAllPins\(opening\).*?\nend\n"),
        ])
        self.lua.execute(code + "\nSetUpAll = SetUpAllPins\n")

    def libstub(self, libs):
        self.lua.execute("""
            LibStub = setmetatable({ libs = %s }, { __call = function(self, n) return self.libs[n] end })
            function LibStub:IterateLibraries() return pairs(self.libs) end
        """ % libs)

    def test_old_questie_in_libstub(self):
        self.libstub("{ ['HereBeDragonsQuestie-Pins-2.0'] = { worldmapProvider = {} } }")
        self.lua.execute("QuestieLoader = { _modules = {} }")
        self.lua.execute("SetUpAll()")
        self.assertEqual(self.lua.eval("set_up['HereBeDragonsQuestie-Pins-2.0'][2].template"), "HereBeDragonsPinsTemplateQuestie")
        self.assertTrue(self.lua.eval("set_up['HereBeDragonsQuestie-Pins-2.0'][2].questie"))
        self.assertIsNone(self.lua.eval("QuestieLoader._modules.HBDPins"), "an older Questie given a module it hasn't")
        self.assertIsNone(self.lua.eval("set_up[mod.QUESTIE_MODULE]"))

    def test_questie_12_8_module(self):
        self.libstub("{ ['HereBeDragons-Pins-2.0'] = { worldmapProvider = {} } }")   # (another addon's)
        self.lua.execute("""QuestieLoader = { _modules = { HBDPins = { worldmapProvider = {},
            worldmapPinTemplate = 'HereBeDragonsPins-Questie-WorldMapPin' } } }""")
        self.lua.execute("SetUpAll()")
        self.assertTrue(self.lua.eval("set_up[mod.QUESTIE_MODULE] ~= nil"), "Questie 12.8's module not taken over")
        self.assertTrue(self.lua.eval("set_up[mod.QUESTIE_MODULE][1] == QuestieLoader._modules.HBDPins"))
        self.assertEqual(self.lua.eval("set_up[mod.QUESTIE_MODULE][2].template"), "HereBeDragonsPins-Questie-WorldMapPin")
        self.assertTrue(self.lua.eval("set_up[mod.QUESTIE_MODULE][2].questie"))
        self.assertEqual(self.lua.eval("set_up['HereBeDragons-Pins-2.0'][2].template"), "HereBeDragonsPinsTemplate")

    def test_module_without_libstub(self):
        self.lua.execute("LibStub = nil")
        self.lua.execute("QuestieLoader = { _modules = { HBDPins = { worldmapProvider = {} } } }")
        self.lua.execute("SetUpAll()")
        self.assertEqual(self.lua.eval("set_up[mod.QUESTIE_MODULE][2].template"), "HereBeDragonsPins-Questie-WorldMapPin")

    def test_no_questie(self):
        self.libstub("{}")
        self.lua.execute("QuestieLoader = nil")
        self.lua.execute("SetUpAll()")
        self.assertIsNone(self.lua.eval("next(set_up)"))
        self.assertIsNone(self.lua.eval("mod.QuestieModule()"))

    def test_padview_reads_the_module_too(self):
        src = (ROOT / "OpenMap" / "Map" / "PadView.lua").read_text(encoding="utf-8")
        self.assertIn("mod.QuestieModule", src)
        self.assertIn("name == mod.QUESTIE_MODULE", src)


class FadeWhileZooming(unittest.TestCase):
    """"Fade icons while zooming" off from v0.8.6 (Extras.lua's default), for saves made before too, once
    (WorldMap.lua's Migrate: each save has the old default written in); turned on again, it stays on"""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        src = (ROOT / "OpenMap" / "Map" / "WorldMap.lua").read_text(encoding="utf-8")
        m = re.search(r"\nfunction mod\.Migrate\(db\).*?\nend\n", src, re.S)
        self.assertIsNotNone(m, "Migrate in WorldMap.lua")
        self.lua.execute("mod = {}\n" + m.group(0))

    def test_default_off(self):
        self.assertIn("d.zoomHidePins = false", SRC)

    def test_old_save_turned_off_once(self):
        self.lua.execute("""
            db = { zoomHidePins = true }
            mod.Migrate(db)
            assert(db.zoomHidePins == false and db.zoomHidePinsOff == true)
            db.zoomHidePins = true                          -- (turned on again in the menu)
            mod.Migrate(db)
            assert(db.zoomHidePins == true)
        """)


class QuestieLiftedOnOpen(unittest.TestCase):
    """Questie's icons placed before the map's art was built (at login) are lifted over it when the map
    opens (Extras.lua's LiftQuestie, #194): Questie 12.8 doesn't redraw them on a map opened on the same zone"""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        code = "\n".join([
            part(r"\nlocal QUESTIE_BASE = [^\n]*\n"),
            part(r"\nlocal ICONS_ABOVE = [^\n]*\n"),
            part(r"\nlocal function Lift\(icon, questie\).*?\nend\n"),
            part(r"\nlocal function LiftQuestie\(\).*?\nend\n"),
        ])
        self.lua.execute("""
            S = {}
            mod = {}
            stitched, shown = true, true
            function mod.IsStitched() return stitched end
            local function Frame(level)
                local f = { level = level, fixed = true }
                function f:GetFrameLevel() return self.level end
                function f:SetFrameLevel(l) self.level = l end
                function f:SetFixedFrameLevel(on) self.fixed = on end
                function f:GetParent() return self.parent end
                return f
            end
            pins = {}
            for i = 1, 3 do
                local pin = Frame(100)
                local icon = Frame(2016 + i)
                icon.parent, pin.icon = pin, icon
                pins[i] = pin
            end
                        map = { IsShown = function() return shown end,
                EnumeratePinsByTemplate = function(_, t) local i = 0 return function() i = i + 1 return pins[i] end end }
            pins[3].icon.isManualIcon = true                 -- (a townsfolk icon)
            questie = { pins = {}, template = "HereBeDragonsPins-Questie-WorldMapPin" }
        """ + code + "\nLiftAll = LiftQuestie\n")

    def test_lifted_once_the_art_is_there(self):
        self.lua.execute("LiftAll()")                       # (no art yet: left as they are)
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017)
        self.lua.execute("S.artTop, S.iconLevel = 2083, 2091 LiftAll()")
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017 - 2015 + 2091 + 5 + 1)   # (a quest icon: over every set of OpenMap's icons, #92 #393)
        self.assertEqual(self.lua.eval("pins[3].icon.level"), 2019 - 2015 + 2083 + 1)   # (a townsfolk icon: over the art)
        self.lua.execute("LiftAll()")                       # (again: already over, unchanged)
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017 - 2015 + 2091 + 5 + 1)

    def test_a_quest_icon_set_below_questies_base_still_over_every_openmap_icon(self):
        # (a "?" Questie drew from under QUESTIE_BASE was lifted under OpenMap's townsfolk)
        self.lua.execute("pins[1].icon.level = 2003 S.artTop, S.iconLevel = 2083, 2091 LiftAll()")
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2091 + 5 + 1)
        self.assertGreater(self.lua.eval("pins[2].icon.level"), self.lua.eval("pins[1].icon.level"))   # (order kept above the base)

    def test_not_while_the_map_isnt_stitched_or_shown(self):
        self.lua.execute("S.artTop, S.iconLevel = 2083, 2091 stitched = false LiftAll()")
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017)
        self.lua.execute("stitched, shown = true, false LiftAll()")
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017)



class IconLayers(unittest.TestCase):
    """OpenMap's townsfolk are its lowest icons (with the route lines): under quests' icons (OpenMap's, and Questie's
    lifted over ICONS_ABOVE), pins, dungeons, flight masters, your group's dots and your arrow"""

    def test_townsfolk_lowest(self):
        root = Path(__file__).resolve().parents[2] / "OpenMap" / "Map"
        levels = {}
        for f in root.glob("*.lua"):
            for key, level in re.findall(r'S\.PinSet\("([a-z_]+)"[^,)]*,\s*[^,)]+,\s*(\d+)\)', f.read_text(encoding="utf-8")):
                levels[key] = int(level)
        tf = re.search(r'S\.PinSet\("tf_" \.\. k\.key, k\.zoom, (\d+)\)', (root / "Townsfolk.lua").read_text(encoding="utf-8"))
        self.assertIsNotNone(tf)
        tf = int(tf.group(1))
        for key in ("quests", "questoffers", "userpins", "group", "flight", "waypoint", "ping", "friends"):
            self.assertLess(tf, levels[key], key)
        above = int(re.search(r"local ICONS_ABOVE = (\d+)", SRC).group(1))
        self.assertLess(tf, above + 1)                       # (Questie's quest icons: from ICONS_ABOVE + 1 up)
        # your arrow and Blizzard's group dots: thousands of levels over the view, over every icon (WorldMap.lua)
        player = int(re.search(r"local PLAYER_ABOVE = (\d+)", (root / "WorldMap.lua").read_text(encoding="utf-8")).group(1))
        self.assertGreater(player, 1000)


if __name__ == "__main__":
    unittest.main()
