"""What the map shows in a fight (OwnView.lua's own view) against what it shows out of one:
python -P tools/offline-test/combatlayers.py.

Out of combat OpenMap's art and icons are on Blizzard's map canvas. In a fight that canvas is see-through under
OpenMap's own view (nothing of Blizzard's map may be set then), so every layer the map shows needs its way onto
the view: moved there with the art and icon roots (S.Rehost), put there (other addons' HereBeDragons icons), or
drawn there again (your group, a quest's area, your arrow). LAYERS lists each layer and the code that brings it;
a frame of OpenMap's made on Blizzard's canvas itself is one the view wouldn't show, so each is listed too. And
your group's dots on the view are run here in Lua 5.1.
"""
from pathlib import Path
import re
import unittest

from lupa.lua51 import LuaRuntime


MAP = Path(__file__).resolve().parents[2] / "OpenMap" / "Map"


def src(name):
    return (MAP / name).read_text(encoding="utf-8")


def code_lines(text):
    return [line.split("--")[0] for line in text.splitlines()]


# layer: (file, what in it brings the layer onto the own view in a fight)
LAYERS = {
    "art, names, explored shading, fog, sea chart": ("Stitch.lua", "root:SetParent(to)"),
    "OpenMap's icon sets (every S.PinSet: dungeons, boats, flights, routes, townsfolk, explore helper, "
    "your pins, the waypoint, find me, friends and guild, sketches, Questie's paths)": ("Stitch.lua", "pinRoot:SetParent(over)"),
    "your arrow (OpenMap's own in a fight)": ("WorldMap.lua", "not InCombatLockdown() and not (mod.db.playerArrowOnTop"),
    "your party and raid (the game's dots on the view)": ("Nav.lua", "hasNativeRings = TryOwnGroup(stockPin, host, members)"),
    "your quests (OpenMap's icons)": ("Quests.lua", "(mod.OwnViewOn and mod.OwnViewOn())"),
    "the quests of the zone Blizzard's map is on (its pins are under the view)": ("Quests.lua", "local host = not pad and mod.HostMap() or nil"),
    "a quest's area (hovered or focused)": ("PadView.lua", "ShowAreaOn(area.own, own, root"),
    "other addons' HereBeDragons icons (Questie's ...)": ("OwnView.lua", "PlaceIcons()"),
    "the place name under the cursor": ("Extras.lua", "(mod.OwnViewHover and mod.OwnViewHover())"),
    "the coordinates": ("OwnView.lua", "mod.CoordsBar and mod.CoordsBar()"),
    "the brightness shade": ("OwnView.lua", "mod.brightnessShade"),
    "Ctrl-click: Blizzard's waypoint": ("WorldMap.lua", "if own.on and mod.OwnViewWaypoint then mod.OwnViewWaypoint() return true end"),
    "wheel zoom, drag, clicks": ("OwnView.lua", 'view:SetScript("OnMouseWheel"'),
}

# OpenMap's code that reaches Blizzard's canvas itself: each one's way in a fight
ON_BLIZZARDS_CANVAS = {
    "Compat.lua": "other addons' frames on it lifted over the art (out of combat; under the view in a fight)",
    "Extras.lua": "its scale read for Questie's icons",
    "Nav.lua": "your group's rings out of a fight; in one, TryOwnGroup's frames on the view",
    "WorldMap.lua": "the art's home out of a fight (S.Rehost moves it onto the view in one)",
}


class LayerTests(unittest.TestCase):
    def test_every_layer_onto_the_view(self):
        for layer, (name, needle) in LAYERS.items():
            self.assertIn(needle, src(name), layer)

    def test_icon_sets_and_art_move_with_the_view(self):
        stitch = src("Stitch.lua")
        pinset = re.search(r"\nfunction S\.PinSet\(key, minZoom, level\)\n.*?\nend\n", stitch, re.S).group(0)
        self.assertIn('CreateFrame("Frame", nil, pinRoot)', pinset)
        rehost = re.search(r"\nfunction S\.Rehost\(canvas\)\n.*?\nend\n", stitch, re.S).group(0)
        for needle in ("root:SetParent(to)", "chart:SetParent(to)", "pinRoot:SetParent(over)"):
            self.assertIn(needle, rehost)
        own = src("OwnView.lua")
        self.assertIn("S.Rehost(canvas)", own)
        self.assertIn("S.Rehost(nil)", own)

    def test_nothing_new_on_blizzards_canvas(self):
        # (a layer made on Blizzard's canvas is under the view in a fight, unseen: give it a way onto the view, then
        # list it here)
        found = set()
        for path in MAP.glob("*.lua"):
            for line in code_lines(path.read_text(encoding="utf-8")):
                if "GetCanvas()" in line or re.search(r"CreateFrame\([^)]*sc\.Child", line):
                    found.add(path.name)
        self.assertEqual(found, set(ON_BLIZZARDS_CANVAS))


class OwnGroupTests(unittest.TestCase):
    """your group on the own view: Nav.lua's frames there, run with stubs for the game's"""

    def setUp(self):
        nav = src("Nav.lua")
        look = re.search(r"\nlocal function GroupLook\(unit\)\n.*?\nend\n", nav, re.S).group(0)
        start = nav.index("\nlocal ownGroup ")
        end = nav.index("\nend\n", nav.index("\nlocal function TryOwnGroup(")) + 5
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            Safe = { Value = function(v) return v end,
                Call = function(fn, ...) local ok, v = pcall(fn, ...) if ok then return v end end }
            groupLooks, DOT = {}, { atlas = "WhiteCircle-RaidBlips", texture = "x" }
            RAID_CLASS_COLORS = { MAGE = { r = 0.25, g = 0.78, b = 0.92 }, PRIEST = { r = 1, g = 1, b = 1 } }
            RING_TEXTURE, RING_SIZE = "ring", 16
            S = { WORLD = 947 }
            classes = { party1 = "MAGE", party2 = "PRIEST" }
            function UnitClass(u) return nil, classes[u] end
            function UnitGUID(u) return "G-" .. u end
            function UnitIsUnit(a, b) return a == b end
            function UnitName(u) return "Name-" .. u end
            raid = false
            function IsInRaid() return raid end
            function UnitInSubgroup(u) return u == "raid1" end
            made = {}
            function CreateFrame(kind, _, parent)
                local f = { kind = kind, parent = parent, units = {}, shown = true }
                function f:IsProtected() return false end
                function f:SetAllPoints() end
                function f:EnableMouse() end
                function f:SetScript(k, fn) self[k] = fn end
                function f:SetFrameStrata(s) self.strata = s end
                function f:SetFrameLevel(l) self.level = l end
                function f:SetUiMapID(id) self.mapID = id end
                function f:ClearUnits() self.units = {} end
                function f:AddUnit(unit, asset, w, h, r, g, b, a, sub, facing)
                    self.units[#self.units + 1] = { unit = unit, asset = asset, w = w, r = r, g = g, b = b }
                end
                function f:FinalizeUnits() self.final = true end
                function f:Show() self.shown = true end
                function f:Hide() self.shown = false end
                function f:GetMouseOverUnits() return "party1" end
                made[#made + 1] = f
                return f
            end
            GameTooltip = { IsOwned = function(self, f) return self.owner == f end, Hide = function(self) self.owner = nil end,
                SetOwner = function(self, f) self.owner = f end, SetText = function(self, t) self.text = t end }
            canvas = {}
            ownOn, scale = true, 2
            mod = {}
            function mod.OwnCanvas() if ownOn then return canvas, scale, 9300, "HIGH" end end
            function mod.GroupDotSize(pin, kind) return (kind == "raid" and 8.25 or 11) * 1.5, 1.5 end
            stockPin = {}
        """ + look + nav[start:end] + "\n_G.TryOwnGroup = TryOwnGroup\n")

    def test_dots_on_the_view_in_blizzards_size_and_class_colour(self):
        self.assertTrue(self.lua.eval("TryOwnGroup(stockPin, 1429, { 'party1', 'party2' })"))
        rings, dots = self.lua.eval("made[2]"), self.lua.eval("made[1]")
        self.assertEqual((dots.kind, dots.mapID, dots.strata), ("UnitPositionFrame", 1429, "HIGH"))
        self.assertTrue(self.lua.eval("made[1].parent == canvas and made[2].parent == canvas"))
        self.assertGreater(dots.level, rings.level)       # (the rings under the dots, both over OpenMap's icons' level)
        self.assertGreater(rings.level, 9300)
        d = dots.units[1]
        self.assertEqual((d.unit, d.asset, d.w), ("party1", "WhiteCircle-RaidBlips", 11 * 1.5 / 2))
        self.assertAlmostEqual(d.r, 0.25)
        self.assertEqual(rings.units[2].w, 16 * 1.5 / 2)

    def test_never_you(self):
        # (your arrow is OpenMap's own in a fight: no dot of the game's for you on the view, should you be passed in)
        self.lua.eval("TryOwnGroup(stockPin, 1429, { 'player', 'party1' })")
        dots, rings = self.lua.eval("made[1]"), self.lua.eval("made[2]")
        self.assertEqual([dots.units[i].unit for i in range(1, len(dots.units) + 1)], ["party1"])
        self.assertEqual([rings.units[i].unit for i in range(1, len(rings.units) + 1)], ["party1"])

    def test_raid_dots(self):
        self.lua.execute("raid = true")
        self.lua.eval("TryOwnGroup(stockPin, 1429, { 'raid1', 'raid2' })")
        dots = self.lua.eval("made[1]")
        self.assertEqual((dots.units[1].asset, dots.units[1].w), ("WhiteDotCircle-RaidBlips", 11 * 1.5 / 2))
        self.assertEqual((dots.units[2].asset, dots.units[2].w), ("WhiteCircle-RaidBlips", 8.25 * 1.5 / 2))

    def test_not_on_the_whole_world_nor_without_the_view(self):
        self.assertFalse(self.lua.eval("TryOwnGroup(stockPin, 947, { 'party1' })"))
        self.lua.execute("ownOn = false")
        self.assertFalse(self.lua.eval("TryOwnGroup(stockPin, 1429, { 'party1' })"))

    def test_names_on_hover(self):
        self.lua.eval("TryOwnGroup(stockPin, 1429, { 'party1', 'party2' })")
        self.lua.execute("made[1].OnUpdate(made[1])")
        self.assertEqual(self.lua.eval("GameTooltip.text"), "Name-party1")

    def test_resized_with_the_view(self):
        self.lua.eval("TryOwnGroup(stockPin, 1429, { 'party1' })")
        self.lua.execute("scale = 4")
        self.lua.eval("TryOwnGroup(stockPin, 1429, { 'party1' })")
        self.assertEqual(self.lua.eval("made[1]").units[1].w, 11 * 1.5 / 4)


if __name__ == "__main__":
    unittest.main()
