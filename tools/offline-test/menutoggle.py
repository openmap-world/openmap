"""Other addons' switches on OpenMap's tray (API.lua's RegisterMenuToggle, Panel.lua's SetLit), read from their
source: python -P tools/offline-test/menutoggle.py.

A switch's button glows (a gold edge) while its get() is true and its icon greys while it's false; version 5's
lit and grey set those apart (lit = fn, grey = fn or false for never), onRightClick gives it a right-click of its
own, and RefreshMenuToggles draws the buttons again. Without them a switch looks and works as before.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2] / "OpenMap"
API = (ROOT / "API.lua").read_text(encoding="utf-8")
PANEL = (ROOT / "Map" / "Panel.lua").read_text(encoding="utf-8")


def chunk(src, pattern):
    m = re.search(pattern, src, re.S)
    assert m, pattern
    return m.group(0)


class MenuToggleTests(unittest.TestCase):
    def setUp(self):
        from lupa.lua51 import LuaRuntime
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        register = chunk(API, r"\nfunction API\.RegisterMenuToggle\(owner, spec\)\n.*?\nend\n")
        refresh = chunk(API, r"\nfunction API\.RefreshMenuToggles\(\)\n.*?\nend\n")
        rows = chunk(API, r"\nfunction mod\.ExtraMenuRows\(row\)\n.*?\nend\n")
        setlit = chunk(PANEL, r"\nlocal function SetLit\(b, state\)\n.*?\nend\n").replace("local function SetLit", "function SetLit")
        self.lua.execute("""
            API, toggles, refreshed = {}, {}, 0
            tremove = table.remove
            ns = { L = setmetatable({}, { __index = function(_, k) return k end }) }
            mod = { RefreshPanel = function() refreshed = refreshed + 1 end, RightClickTip = function(t) return "Right-click: " .. t end }
            LIT, BRONZE = { 1, 0.8, 0 }, { 0.5, 0.3, 0.1 }
            function geterrorhandler() return function(e) error(e) end end
            function row(label, id, icon, get, set) return { label, get, set, id = id } end
            -- a tray button: its edge, glow and icon as SetLit leaves them
            function Button(entry)
                local b = { entry = entry, boxed = true, glow = {}, icon = {} }
                function b:SetBackdropBorderColor(r) self.edge = r end
                function b.glow:SetShown(v) self.shown = v end
                function b.icon:SetDesaturated(v) self.grey = v end
                function b.icon:SetAlpha(a) self.alpha = a end
                return b
            end
            function Look(entry, state)
                local b = Button(entry) SetLit(b, state)
                return b.glow.shown, b.icon.grey
            end
        """ + register + refresh + rows + setlit)

    def entry(self):
        return self.lua.eval("mod.ExtraMenuRows(row)")[2]   # (1: its section's heading)

    def look(self, entry, state):
        return self.lua.eval("Look")(entry, state)

    def test_as_before_without_lit_or_grey(self):
        self.lua.execute("on = true API.RegisterMenuToggle('A', { id = 'x', label = 'X', get = function() return on end, set = function() end })")
        e = self.entry()
        self.assertEqual(self.look(e, "on"), (True, False))
        self.assertEqual(self.look(e, "off"), (False, True))

    def test_lit_and_never_grey(self):
        # (Forever Nodes: left-click its panel, right-click its icons; lit while the icons are on, never greyed)
        self.lua.execute("""
            panel, icons = false, true
            API.RegisterMenuToggle('FN', { id = 'panel', label = 'FN', get = function() return panel end,
                set = function() panel = not panel end, lit = function() return icons end, grey = false,
                onRightClick = function() icons = not icons end, rightClickTip = 'map icons' })
        """)
        e = self.entry()
        self.assertEqual(self.look(e, "off"), (True, False))       # (panel closed, icons on: lit, not grey)
        e.onRight()
        self.assertEqual(self.look(e, "off"), (False, False))      # (icons off: not lit, still not grey)
        self.assertEqual(e.rightTip(), "Right-click: map icons")

    def test_grey_of_its_own(self):
        self.lua.execute("dim = true API.RegisterMenuToggle('A', { id = 'x', label = 'X', get = function() return true end, set = function() end, grey = function() return dim end })")
        e = self.entry()
        self.assertEqual(self.look(e, "on"), (True, True))
        self.lua.execute("dim = false")
        self.assertEqual(self.look(e, "on"), (True, False))

    def test_a_broken_lit_neither_lights_nor_breaks(self):
        self.lua.execute("API.RegisterMenuToggle('A', { id = 'x', label = 'X', get = function() return true end, set = function() end, lit = function() error('oops') end })")
        self.assertEqual(self.look(self.entry(), "on"), (False, False))

    def test_wrong_types_refused(self):
        for bad in ("lit = true", "grey = true", "grey = 'no'", "onRightClick = 1", "rightClickTip = 2"):
            with self.subTest(bad=bad):
                ok = self.lua.eval("function() return pcall(API.RegisterMenuToggle, 'A', { id = 'x', label = 'X', "
                                   "get = function() end, set = function() end, %s }) end" % bad)()
                self.assertFalse(ok[0] if isinstance(ok, tuple) else ok)

    def test_refresh_draws_again(self):
        before = self.lua.eval("refreshed")
        self.lua.execute("API.RefreshMenuToggles()")
        self.assertEqual(self.lua.eval("refreshed"), before + 1)

    def test_version_5(self):
        self.assertIn("local API = { major = 1, version = 5 }", API)



class MinimapAlwaysTests(unittest.TestCase):
    """The menu's minimap detail slider (Panel.lua's miniRow): the zoom it mixes in from, the other way round, so its far
    right is "Always" (from the whole world, at every zoom: minimapFrom at its least, Close.lua's MINI_FROM[1])."""

    def setUp(self):
        from lupa.lua51 import LuaRuntime
        block = PANEL[PANEL.index("\tlocal miniLo, miniHi = mod.MINI_FROM[1], mod.MINI_FROM[2]"):]
        block = block[:block.index("\topacityRow = SliderRow(")]
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            L = setmetatable({}, { __index = function(_, k) return k end })
            mod = { MINI_FROM = { 1, 60, 1 }, db = { minimapFrom = 20 } }
            function Icon() end
            function SliderRow(_, _, spec) row = spec return spec end
            sliders, COL = {}, 100
        """ + block)
        self.row = self.lua.eval("row")

    def test_far_right_is_always(self):
        self.assertEqual(self.row.text(60), "Always")
        self.row.set(60)
        self.assertEqual(self.lua.eval("mod.db.minimapFrom"), 1)     # (Close.lua: from the whole world)
        self.assertEqual(self.row.get(), 60)

    def test_further_right_sooner(self):
        self.lua.execute("mod.db.minimapFrom = 20")
        self.assertEqual(self.row.get(), 41)
        self.assertEqual(self.row.text(41), "20x")
        self.row.set(1)
        self.assertEqual(self.lua.eval("mod.db.minimapFrom"), 60)    # (the far left: the latest, 60x)
        close = (ROOT / "Map" / "Close.lua").read_text(encoding="utf-8")
        self.assertIn("from <= MINI_FROM[1] and 1", close)            # (at the least: there at every zoom)


    def test_strength_up_to_100(self):
        # (Minimap strength to 100%: never more than Minimap opacity, the most at any zoom; the menu's slider reads
        # Options' range; the hand-overs' strengths stay finite and in 0..1 at full strength)
        close = (ROOT / "Map" / "Close.lua").read_text(encoding="utf-8")
        self.assertIn('opts.minimapMix = { type = "range", name = ns.L["Minimap strength"], order = 51, min = 0, max = 1,', close)
        self.assertIn("local mix = math.min(base, most) *", close)
        self.assertIn('{ "minimapMix", L["Minimap strength"]', PANEL)
        from lupa.lua51 import LuaRuntime
        lua = LuaRuntime(unpack_returned_tuples=True)
        body = close[close.index("\t\t\tlocal a3 = mix * wn"):close.index("\t\t\tif lods then")]
        f = lua.eval("function(mix, wn, fine) " + body + " return a3, a2, a1 end")
        for mix in (1.0, 0.85):
            for wn in (0, 0.5, 1):
                for fine in (0, 0.5, 1):
                    for a in f(mix, wn, fine):
                        self.assertTrue(0 <= a <= 1 + 1e-9, (mix, wn, fine, a))



class EscapeListTests(unittest.TestCase):
    """OpenMap's windows aren't on Blizzard's UISpecialFrames (Core.lua's CloseOnEscape): Blizzard reads that list as it
    closes windows (Escape, every zone change), and OpenMap's names there made the rest of its pass OpenMap's, the world
    map's anchor with it: Report AFK in a battleground blocked (#472). They're closed after Blizzard's pass instead."""

    def setUp(self):
        from lupa.lua51 import LuaRuntime
        core = (ROOT / "Core.lua").read_text(encoding="utf-8")
        block = core[core.index("ns.EscapeFrames = {}"):core.index("function ns.UnregisterEvent(")]
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            ns = {}
            UISpecialFrames = setmetatable({}, { __newindex = function() error("wrote Blizzard's UISpecialFrames") end })
            closed = 0
            function CloseSpecialWindows() closed = closed + 1 return false end
            hooks = 0
            function hooksecurefunc(name, fn)
                local was = _G[name]
                _G[name] = function(...) local r = was(...) fn(...) return r end
                hooks = hooks + 1
            end
            local function Frame(shown) return { shown = shown, IsShown = function(self) return self.shown end, Hide = function(self) self.shown = false end } end
            OpenMapMenu, OpenMapNews, OpenMapBench = Frame(true), Frame(false), Frame(true)
        """ + block)

    def test_closed_after_blizzards_pass_never_on_its_list(self):
        self.lua.execute('ns.CloseOnEscape("OpenMapMenu") ns.CloseOnEscape("OpenMapNews") ns.CloseOnEscape("OpenMapMenu")')
        self.assertEqual(self.lua.eval("hooks"), 1)                     # (hooked once)
        self.assertEqual(self.lua.eval("#ns.EscapeFrames"), 2)          # (each name once)
        self.assertTrue(self.lua.eval("ns.EscapeFrameShown()"))
        self.lua.execute("CloseSpecialWindows()")
        self.assertEqual(self.lua.eval("closed"), 1)                    # (Blizzard's own pass ran, then ours)
        self.assertFalse(self.lua.eval("OpenMapMenu.shown"))
        self.assertTrue(self.lua.eval("OpenMapBench.shown"))           # (not on the list: left)
        self.assertFalse(self.lua.eval("ns.EscapeFrameShown()"))

    def test_no_name_put_on_blizzards_list(self):
        for f in list((ROOT / "Map").glob("*.lua")) + list(ROOT.glob("*.lua")):
            self.assertNotIn("tinsert(UISpecialFrames", f.read_text(encoding="utf-8"), f.name)


if __name__ == "__main__":
    unittest.main()
