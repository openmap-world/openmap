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
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017 - 2015 + 2091 + 1)   # (a quest icon: over OpenMap's icons, #92)
        self.assertEqual(self.lua.eval("pins[3].icon.level"), 2019 - 2015 + 2083 + 1)   # (a townsfolk icon: over the art)
        self.lua.execute("LiftAll()")                       # (again: already over, unchanged)
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017 - 2015 + 2091 + 1)

    def test_not_while_the_map_isnt_stitched_or_shown(self):
        self.lua.execute("S.artTop, S.iconLevel = 2083, 2091 stitched = false LiftAll()")
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017)
        self.lua.execute("stitched, shown = true, false LiftAll()")
        self.assertEqual(self.lua.eval("pins[1].icon.level"), 2017)


class StandaloneQuestieDBProvider(unittest.TestCase):
    """Standalone QuestieDB (LibQuestieDB) registers through OpenMapAPI.RegisterTownsfolkProvider
    using a single DecodeTable helper, offers the Quests tab only when quests are present, and
    never scans all QuestieDB.Object entries for mailboxes."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.qdb_src = (ROOT / "OpenMap" / "Map" / "QuestieDB.lua").read_text(encoding="utf-8")
        self.dungeons_src = (ROOT / "OpenMap" / "Map" / "Dungeons.lua").read_text(encoding="utf-8")
        self.townsfolk_src = (ROOT / "OpenMap" / "Map" / "Townsfolk.lua").read_text(encoding="utf-8")

        m_q = re.search(r"\nlocal function Questie\(\).*?\nend\n", self.dungeons_src, re.S)
        m_qs = re.search(r"\nlocal function QuestSource\(\).*?\nend\n", self.dungeons_src, re.S)
        assert m_q and m_qs

        self.lua.execute("""
            local provider
            mod = { db = {} }
            function mod.TownsfolkProvider() return provider end
            function mod.SetTownsfolkProvider(p) provider = p end
            function Journal() return nil end
            function NeedRoll() return nil end
            OpenMapAPI = {
                registered = {},
                RegisterTownsfolkProvider = function(owner, p)
                    OpenMapAPI.registered[owner] = p
                    mod.SetTownsfolkProvider(p)
                end
            }
            C_Map = { GetAreaInfo = function(id) return id == 209 and "Shadowfang Keep" or nil end }
        """)
        self.lua.execute(
            self.qdb_src.replace('local _, ns = ...\nlocal mod = ns.GetModule and ns:GetModule("worldmap") or ns.mod', "")
            + "\n" + m_q.group(0) + "\n" + m_qs.group(0)
            + "\nDungeonQuestSource = QuestSource\n"
        )

    def test_registers_provider_when_libquestiedb_present_and_questie_absent(self):
        self.lua.execute("""
            LibQuestieDB = {
                Npc = {
                    GetAllIds = function() return { [100] = true } end,
                    Get = function(id, field) return field == "name" and "Innkeeper" or nil end,
                },
                Object = {
                    Get = function() return nil end,
                },
                Quest = {
                    GetAllIds = function() return { [42] = true } end,
                    Get = function() return nil end,
                },
                Enum = { npcFlags = { INNKEEPER = 65536 } },
                Support = {
                    Get = function(name)
                        if name == "ZoneDB" then
                            return {
                                private = {
                                    areaIdToUiMapId = "return { [12] = 1429 }",
                                    areaIdToUiMapIdOverride = { [99] = 1430 },
                                    uiMapIdToAreaId = "return { [1429] = 12 }",
                                    dungeons = { [209] = { "Shadowfang Keep", {} } },
                                }
                            }
                        end
                    end
                },
            }
            mod.RegisterStandaloneQuestieDB()
        """)
        self.assertIsNotNone(self.lua.eval("OpenMapAPI.registered['QuestieDB']"))
        self.assertEqual(self.lua.eval("mod.TownsfolkProvider().zones:GetUiMapIdByAreaId(12)"), 1429)
        self.assertEqual(self.lua.eval("mod.TownsfolkProvider().zones:GetUiMapIdByAreaId(99)"), 1430)
        self.assertEqual(self.lua.eval("mod.TownsfolkProvider().zones:GetAreaIdByUiMapId(1429)"), 12)
        self.assertEqual(self.lua.eval("mod.TownsfolkProvider().zones:GetAreaIdByName('Shadowfang Keep')"), 209)
        self.assertEqual(self.lua.eval("DungeonQuestSource()"), "questie")

    def test_quests_tab_not_offered_when_provider_has_no_quests(self):
        self.lua.execute("""
            OpenMapAPI.RegisterTownsfolkProvider("OnlyNPCs", {
                db = {
                    NPCPointers = { [1] = true },
                    npcFlags = {},
                    QueryNPCSingle = function() end,
                },
                zones = { GetUiMapIdByAreaId = function() return 1429 end },
            })
        """)
        self.assertIsNone(self.lua.eval("DungeonQuestSource()"))

    def test_skips_when_questie_loader_or_existing_provider_present(self):
        self.lua.execute("""
            QuestieLoader = {}
            LibQuestieDB = {
                Npc = { GetAllIds = function() return {} end, Get = function() end },
                Enum = { npcFlags = {} },
                Support = { Get = function() return { private = { areaIdToUiMapId = {} } } end },
            }
            mod.RegisterStandaloneQuestieDB()
        """)
        self.assertIsNone(self.lua.eval("OpenMapAPI.registered['QuestieDB']"))

    def test_no_object_scan_for_mailboxes_and_single_decode_helper(self):
        self.assertNotIn("obj.GetAllIds", self.townsfolk_src)
        self.assertNotIn("DecodeTable", self.townsfolk_src)
        self.assertNotIn("DecodeZoneTable", self.dungeons_src)


if __name__ == "__main__":
    unittest.main()
