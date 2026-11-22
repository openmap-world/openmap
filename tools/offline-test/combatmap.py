"""The map in a fight (WorldMap.lua), read from its source: python -P tools/offline-test/combatmap.py.

In combat nothing of Blizzard's map is written from OpenMap's code (#345 #347 #368), so the map stays as it is
then. Two things follow from that and are checked here: your arrow is OpenMap's own in a fight (Blizzard's,
protected then, can't be lifted over the art again and went under it), and a view Blizzard reset in a fight
(the quest log opened from the tracker: the whole map) is put back to OpenMap's as combat ends. And Blizzard's
own scale changes wait a frame for OpenMap's view out of combat, so an opening lays the icons out once (#293).
"""
from pathlib import Path
import re
import unittest


WORLDMAP = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "WorldMap.lua").read_text(encoding="utf-8")


def function(name):
    m = re.search(r"\nfunction %s\(.*?\nend\n" % re.escape(name), WORLDMAP, re.S)
    assert m, name
    return m.group(0)


class CombatMapTests(unittest.TestCase):
    def test_openmaps_arrow_in_combat(self):
        m = re.search(r"local _, mx, my = ns\.Safe\.PlayerPos\(mapID\)\n\tif (.*?) then\n\t\tS\.SetPlayer\(nil\)", WORLDMAP)
        self.assertIsNotNone(m, "the ticker's arrow choice")
        self.assertIn("not InCombatLockdown()", m.group(1))

    def test_a_reset_in_combat_waits_for_its_end(self):
        hook = re.search(r'hooksecurefunc\(sc, "ResetZoom", function\(self\)\n(.*?)\n\tend\)', WORLDMAP, re.S)
        self.assertIsNotNone(hook, "the ResetZoom hook")
        body = hook.group(1)
        # (in combat: into the own view where it can come up, OwnView.lua, else noted for combat's end;
        # nothing of Blizzard's written either way)
        fight = re.search(r"if InCombatLockdown\(\) then\n(.*?)\n\t\t\treturn\n\t\tend", body, re.S)
        self.assertIsNotNone(fight)
        self.assertIn("mod.OwnViewStart()", fight.group(1))
        self.assertIn("resetDue = true", fight.group(1))
        self.assertIn("mod.ResetDue()", function("mod.CombatOver"))

    def test_nothing_of_blizzards_map_set_in_combat(self):
        # (SetView keeps the view for combat's end: the canvas isn't touched then)
        m = re.search(r"\nlocal function SetView\(scale, x, y\)\n(.*?)\nend\n", WORLDMAP, re.S)
        branch = re.search(r"\tif InCombatLockdown\(\) then\n(.*?)\n\t\treturn\n\tend", m.group(1), re.S).group(1)
        for line in branch.splitlines():
            self.assertNotRegex(line.split("--")[0], r"\bsc\s*[.:\[]", line)

    def test_blizzards_scale_change_laid_out_once(self):
        # (#293: its reset as the map opens laid the icon sets out for the whole world, then for OpenMap's view
        # again: Blizzard's own change waits a frame for OpenMap's; in combat, or before the map is up, at once)
        m = re.search(r'dp\.OnCanvasScaleChanged = Ours\("scale changed", function\(\)\n(.*?)\n\tend\)', WORLDMAP, re.S)
        self.assertIsNotNone(m)
        self.assertIn("if viewSetting or InCombatLockdown() or not active then return ApplyZoom() end", m.group(1))
        self.assertIn("C_Timer.After(0", m.group(1))
        sv = re.search(r"\nlocal function SetView\(scale, x, y\)\n(.*?)\nend\n", WORLDMAP, re.S).group(1)
        self.assertIn("viewSetting = true\n\tmap:OnCanvasScaleChanged()\n\tviewSetting, scaleWaiting = false, false", sv)


    def test_opened_in_a_fight_the_own_view_comes_up(self):
        # (not only once zoomed or dragged: its icons were never moved onto it before that)
        m = re.search(r'local shown = Ours\("map shown", function\(\)\n(.*?)\n\tend\)', WORLDMAP, re.S)
        self.assertIsNotNone(m)
        self.assertIn("if InCombatLockdown() and mod.OwnViewStart then", m.group(1))


class CombatEndTests(unittest.TestCase):
    """the combat view's view kept as combat ends, through what follows it in mod.CombatOver: OpenMap's zoom
    levels put in (Blizzard resets its view, OpenMap's reset follows) and a reset noted in the fight (the zoom
    jumped as the fight ended, test16)"""

    def setUp(self):
        from lupa.lua51 import LuaRuntime
        over = function("mod.CombatOver")
        flush = function("mod.FlushWaitingView")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            fight, active, anim, afterCombat, resetDue, waitingView = false, true, nil, true, false, nil
            function GetTime() return 0 end
            function InCombatLockdown() return fight end
            view = { scale = 1, x = 0.5, y = 0.5 }
            function SetView(scale, x, y) view = { scale = scale, x = x, y = y } end
            own = { on = true, scale = 3, x = 0.2, y = 0.7 }
            map = { GetMapID = function() return 1429 end, IsShown = function() return true end }
            mod = {}
            -- (as OwnView.lua: the view on Blizzard's canvas, then the art back)
            function mod.OwnViewStop() own.on = false SetView(3, 0.2, 0.7) end
            -- (Blizzard's reset as the zoom levels come in, OpenMap's reset following it: "When reopening the map")
            sc = { OnCanvasSizeChanged = function() SetView(1, 0.5, 0.5) end }
            function KeepPadCursor(fn, ...) return fn(...) end
            function mod.ResetDue() end
        """ + flush + over)

    def test_the_view_kept(self):
        self.lua.execute("mod.CombatOver()")
        v = self.lua.eval("view")
        self.assertEqual((v.scale, v.x, v.y), (3, 0.2, 0.7))

    def test_without_the_own_view_as_before(self):
        self.lua.execute("own.on = false afterCombat = false mod.CombatOver()")
        v = self.lua.eval("view")
        self.assertEqual((v.scale, v.x, v.y), (1, 0.5, 0.5))


class ArrowSizeTests(unittest.TestCase):
    """OpenMap's arrow (in a fight) the size of Blizzard's on screen (out of it): Blizzard's size for the player
    times the arrow-size setting, both on the map's view at scale 1"""

    def setUp(self):
        from lupa.lua51 import LuaRuntime
        stitch = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "Stitch.lua").read_text(encoding="utf-8")
        chunks = [re.search(r"\nfunction %s\(.*?\nend\n" % n, stitch, re.S).group(0) for n in (r"S\.SetPlayerScale", r"S\.SetPlayerBase")]
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            S = {}
            arrow = { SetSize = function(self, w, h) self.w, self.h = w, h end }
        """ + "".join(chunks))

    def test_same_size_as_blizzards(self):
        # (Blizzard's: its size for the player, 36, times the setting, 1.5, on screen)
        self.lua.execute("S.SetPlayerBase(36) S.SetPlayerScale(1.5)")
        self.assertEqual(self.lua.eval("arrow.w"), 36 * 1.5)
        self.lua.execute("S.SetPlayerScale(1)")
        self.assertEqual(self.lua.eval("arrow.w"), 36)

    def test_same_on_screen_size_at_every_zoom(self):
        # Blizzard's arrow: its size over the canvas's scale (SynchronizePinSizes), on the canvas at that scale. Ours:
        # its size on the icons' root, which is on the map's view, never scaled, in and out of a fight (S.Rehost
        # puts it on the own view's parent, the view, not on the scaled canvas)
        self.lua.execute("S.SetPlayerBase(27) S.SetPlayerScale(1.85)")
        for scale in (0.25, 1, 3.7):
            blizzards = (27 * 1.85 / scale) * scale
            self.assertAlmostEqual(self.lua.eval("arrow.w"), blizzards)
        root = Path(__file__).resolve().parents[2] / "OpenMap" / "Map"
        rehost = re.search(r"\nfunction S\.Rehost\(canvas\)\n.*?\nend\n",(root / "Stitch.lua").read_text(encoding="utf-8"), re.S).group(0)
        self.assertIn("local over = canvas and canvas:GetParent()", rehost)
        own = (root / "OwnView.lua").read_text(encoding="utf-8")
        self.assertIn("view:SetAllPoints(sc)", own)
        self.assertNotIn("view:SetScale", own)

    def test_same_art_as_blizzards(self):
        # (the minimap's arrow has a wide clear edge: at the same size it was a third as big, test19)
        root = Path(__file__).resolve().parents[2] / "OpenMap" / "Map"
        stitch = (root / "Stitch.lua").read_text(encoding="utf-8")
        self.assertIn('S.PLAYER_ATLAS = "UI-WorldMapArrow"', stitch)
        self.assertIn("arrow:SetAtlas(S.PLAYER_ATLAS)", stitch)

    def test_28_before_blizzards_is_known(self):
        self.lua.execute("S.playerScale = 1 S.SetPlayerScale(2)")
        self.assertEqual(self.lua.eval("arrow.w"), 56)


class ArrowFollowTests(unittest.TestCase):
    """OpenMap's arrow (yours in a fight) turns and moves every frame, as Blizzard's does: its frame's OnUpdate,
    with no throttle (on WorldMap.lua's tenth-of-a-second ticker it stepped round, test20)"""

    def setUp(self):
        from lupa.lua51 import LuaRuntime
        stitch = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "Stitch.lua").read_text(encoding="utf-8")
        self.assertIn('arrow:GetParent():SetScript("OnUpdate", function() S.FollowPlayer() end)', stitch)
        names = (r"S\.SetPlayer", r"S\.PlacePlayer", r"S\.FollowPlayer")
        chunks = [re.search(r"\nfunction %s\(.*?\nend\n" % n, stitch, re.S).group(0) for n in names]
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            S, player, playerHidden = {}, {}, false
            root, W, H, scaleNow, host = {}, 100, 100, 1, { k = 1 }
            turns, moves = 0, 0
            arrow = { shown = true }
            function arrow:IsShown() return self.shown end
            function arrow:Show() self.shown = true end
            function arrow:Hide() self.shown = false end
            function arrow:ClearAllPoints() end
            function arrow:SetPoint() moves = moves + 1 end
            function arrow:SetRotation(r) turns = turns + 1 self.r = r end
            here = { 0.5, 0.5, 0 }
            function S.PlayerSource() return here[1], here[2], here[3] end
        """ + "".join(chunks) + "\nOnUpdate = function() S.FollowPlayer() end\n")

    def test_turns_every_frame(self):
        self.lua.execute("OnUpdate() for i = 1, 10 do here[3] = i / 10 OnUpdate() end")
        self.assertEqual(self.lua.eval("turns"), 11)
        self.assertAlmostEqual(self.lua.eval("arrow.r"), 1.0)

    def test_nothing_set_when_nothing_changed(self):
        self.lua.execute("OnUpdate() turns, moves = 0, 0 for i = 1, 10 do OnUpdate() end")
        self.assertEqual((self.lua.eval("turns"), self.lua.eval("moves")), (0, 0))

    def test_moves_every_frame(self):
        self.lua.execute("OnUpdate() moves = 0 for i = 1, 5 do here[1] = 0.5 + i / 1000 OnUpdate() end")
        self.assertEqual(self.lua.eval("moves"), 5)

    def test_not_while_hidden(self):
        self.lua.execute("arrow.shown = false for i = 1, 5 do here[3] = i OnUpdate() end")
        self.assertEqual(self.lua.eval("turns"), 0)


class ResizeTests(unittest.TestCase):
    """the window's corner dragged keeps the view, its centre and its scale, at every step of the drag. Replayed
    here against a stand-in for the game's scroll container: each change of size has the game lay its map out
    again (its reset to the whole map, then OpenMap's hook on it; its room to pan worked out for the new size;
    the map's size-change scripts), before or after the drag's own step, as the game may order them. In a fight
    the own view is laid out again for the window's new size"""

    def setUp(self):
        from lupa.lua51 import LuaRuntime
        names = ("mod.BeginResize", "mod.FollowResize", "mod.ResizeStep", "mod.OwnViewResized")
        chunks = [function(n) for n in names]
        reset = re.search(r"\nlocal function ResetView\(self\)\n.*?\nend\n", WORLDMAP, re.S).group(0)
        kept = re.search(r"\nlocal function Kept\(want, have\).*?\n", WORLDMAP).group(0)
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            own, active, anim, userMoved, live = { on = false }, true, nil, false, nil
            fight = false
            function InCombatLockdown() return fight end
            function GetTime() return 0 end
            function Clamp(x, a, b) return math.max(a, math.min(b, x)) end
            W = 1000                                  -- (the map, the host: world = map coordinates here)
            -- the game's scroll container: its view w x h px, the canvas's scale, its scroll (the view's centre,
            -- normalized on the map) and its room to pan
            sc = { w = 800, h = 600, scale = 2, x = 0.45, y = 0.55 }
            function sc:GetWidth() return self.w end
            function sc:GetHeight() return self.h end
            function sc:GetLeft() return 0 end
            function sc:GetCanvasScale() return self.scale end
            function sc:CalculateScrollExtents()
                local hx, hy = self.w / 2 / self.scale / W, self.h / 2 / self.scale / W
                self.scrollXExtentsMin, self.scrollXExtentsMax = math.min(hx, 0.5), math.max(1 - hx, 0.5)
                self.scrollYExtentsMin, self.scrollYExtentsMax = math.min(hy, 0.5), math.max(1 - hy, 0.5)
            end
            function sc:SetNormalizedHorizontalScroll(x) self.x = x end
            function sc:SetNormalizedVerticalScroll(y) self.y = y end
            function sc:MarkAreaTriggersDirty() end
            function sc:MarkViewRectDirty() end
            map = { IsShown = function() return true end, GetMapID = function() return 1 end }
            local function FitPx() return math.min(sc.w / W, sc.h / W) end
            function ZoomFor(mapID, scale) return scale / FitPx() end
            function ScaleFor(mapID, zoom) return zoom * FitPx() end
            function FromWorld(mapID, u, v) return u, v end
            function View() return sc.x, sc.y, ZoomFor(1, sc.scale) end
            function SetView(scale, x, y)
                sc.scale = scale
                sc:CalculateScrollExtents()
                sc.x = Clamp(x, sc.scrollXExtentsMin, sc.scrollXExtentsMax)
                sc.y = Clamp(y, sc.scrollYExtentsMin, sc.scrollYExtentsMax)
            end
            function ShowWorld(u, v, zoom) SetView(ScaleFor(1, zoom), u, v) end
            function ApplyView() end
            function LeastZoom() return 0.1 end
            function MaxZoomAt() return 100 end
            S = { ArtSize = function() return W, W end }
            mod = {}
            placed, zoomed = 0, 0
            function mod.OwnViewPlace() placed = placed + 1 end
            function ApplyZoom() zoomed = zoomed + 1 end
        """ + kept + "".join(chunks) + reset + """
            -- the game's own layout of its map at a change of size: its reset to the whole map (OpenMap's hook on
            -- it after), its room to pan for the new size (the scroll clamped to it), the size-change scripts
            function GameLayout()
                sc.scale = math.min(sc.w / W, sc.h / W)
                sc.x, sc.y = 0.5, 0.5
                ResetView({ mapID = 1, GetWidth = function() return sc.w end, GetHeight = function() return sc.h end })
                sc:CalculateScrollExtents()
                sc.x = Clamp(sc.x, sc.scrollXExtentsMin, sc.scrollXExtentsMax)
                sc.y = Clamp(sc.y, sc.scrollYExtentsMin, sc.scrollYExtentsMax)
                mod.ResizeStep()
            end
            -- only its room to pan worked out again (no reset), then the size-change scripts
            function GameExtents()
                sc:CalculateScrollExtents()
                sc.x = Clamp(sc.x, sc.scrollXExtentsMin, sc.scrollXExtentsMax)
                sc.y = Clamp(sc.y, sc.scrollYExtentsMin, sc.scrollYExtentsMax)
                mod.ResizeStep()
            end
        """)

    def drag(self, order):
        self.lua.execute("mod.BeginResize()")
        u0, v0, s0 = self.lua.eval("sc.x"), self.lua.eval("sc.y"), self.lua.eval("sc.scale")
        for i in range(1, 41):
            # (wider and taller, then narrower and shorter than it began)
            w, h = 800 + 25 * (i if i <= 20 else 40 - i * 1.6), 600 + 15 * (i if i <= 20 else 40 - i * 1.7)
            self.lua.execute("sc.w, sc.h = %f, %f" % (w, h))
            step = order[i % len(order)]
            self.lua.execute({"layout": "GameLayout()", "extents": "GameExtents()", "ours": "mod.FollowResize()",
                              "layout+ours": "GameLayout() mod.FollowResize()",
                              "ours+layout": "mod.FollowResize() GameLayout()"}[step])
            self.assertAlmostEqual(self.lua.eval("sc.x"), u0, 9, "step %d (%s): the centre moved" % (i, step))
            self.assertAlmostEqual(self.lua.eval("sc.y"), v0, 9, "step %d (%s): the centre moved" % (i, step))
            self.assertAlmostEqual(self.lua.eval("sc.scale"), s0, 9, "step %d (%s): the scale changed" % (i, step))
        # (the drop: the game lays it out once more, then the drag ends)
        self.lua.execute("GameLayout()")
        self.assertAlmostEqual(self.lua.eval("sc.x"), u0, 9)
        self.assertAlmostEqual(self.lua.eval("sc.scale"), s0, 9)

    def test_a_drag_keeps_the_centre_and_scale_the_game_first(self):
        self.drag(["layout+ours", "extents", "ours", "layout"])

    def test_a_drag_keeps_the_centre_and_scale_ours_first(self):
        self.drag(["ours+layout", "ours", "extents", "ours+layout"])

    def test_in_a_fight_laid_out_again_at_the_same_centre_and_scale(self):
        self.lua.execute("own = { on = true, scale = 3, x = 0.2, y = 0.7, zoom = 3 } sc.w, sc.h = 1000, 800 mod.OwnViewResized()")
        own = self.lua.eval("own")
        self.assertEqual((own.scale, own.x, own.y), (3, 0.2, 0.7))
        self.assertAlmostEqual(own.zoom, 3 / 0.8)
        self.assertEqual((self.lua.eval("placed"), self.lua.eval("zoomed")), (1, 1))

    def test_the_own_view_follows_its_size(self):
        own = (Path(__file__).resolve().parents[2] / "OpenMap" / "Map" / "OwnView.lua").read_text(encoding="utf-8")
        self.assertIn('view:SetScript("OnSizeChanged", function() if mod.OwnViewResized then mod.OwnViewResized() end end)', own)
        self.assertIn('sc:HookScript("OnSizeChanged", mod.ResizeStep)', WORLDMAP)


class AfterFightTests(unittest.TestCase):
    """a fight over, the map keeps the view it ended on through what the game does to its map just after (its
    quest log's update held over the fight, the window laid out again: each a reset to its whole map, which
    OpenMap's hook on it turned into the whole map: the map went out as the fight ended, test21)"""

    def setUp(self):
        from lupa.lua51 import LuaRuntime
        over = function("mod.CombatOver")
        flush = function("mod.FlushWaitingView")
        reset = re.search(r"\nlocal function ResetView\(self\)\n.*?\nend\n", WORLDMAP, re.S).group(0)
        top = re.search(r"\nlocal afterFight .*?\nlocal AFTER_FIGHT = [^\n]*\n", WORLDMAP, re.S).group(0)
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            now = 100
            function GetTime() return now end
            fight, active, anim, afterCombat, resetDue, waitingView, userMoved, live, resize = false, true, nil, false, false, nil, false, nil, nil
            function InCombatLockdown() return fight end
            view = { scale = 1, x = 0.5, y = 0.5 }
            function SetView(scale, x, y) view = { scale = scale, x = x, y = y } end
            function ShowWorld(u, v, zoom) view = { u = u, v = v, zoom = zoom } end
            function View() return 0.5, 0.5, 1 end
            function Clamp(x, a, b) return math.max(a, math.min(b, x)) end
            function LeastZoom() return 0.5 end
            function MaxZoomAt() return 100 end
            function ZoomFor(m, s) return s end
            own = { on = true, scale = 3, x = 0.2, y = 0.7, u = 0.41, v = 0.52, zoom = 6.5 }
            map = { GetMapID = function() return 1429 end, IsShown = function() return true end }
            sc = { GetWidth = function() return 800 end, GetHeight = function() return 600 end }
            S = { ArtSize = function() return 1000, 700 end }
            mod = {}
            function mod.OwnViewStop() own.on = false end
            function KeepPadCursor(fn, ...) return fn(...) end
            function mod.ResetDue() end
        """ + top + flush + over + reset + "\n_G.ResetView = ResetView\n")
        self.self_ = "{ mapID = 1429, GetWidth = function() return 800 end, GetHeight = function() return 600 end }"

    def test_the_games_reset_just_after_keeps_the_fights_view(self):
        self.lua.execute("mod.CombatOver() now = now + 0.5 ResetView(%s)" % self.self_)
        v = self.lua.eval("view")
        self.assertEqual((v.u, v.v, v.zoom), (0.41, 0.52, 6.5))

    def test_later_a_reset_is_the_games_again(self):
        self.lua.execute("mod.CombatOver() now = now + 10 ResetView(%s)" % self.self_)
        self.assertEqual(self.lua.eval("view").u, None)       # (the whole map: SetView)


class ClosedInAFightTests(unittest.TestCase):
    """the map closed in a fight reopens on the view it closed on: the own view's, noted before the own view stops
    (noted after, it was Blizzard's canvas's, the view from before the fight)"""

    def test_the_view_noted_before_the_own_view_stops(self):
        m = re.search(r"\n\tdp\.OnHide = function\(\)\n(.*?)\n\tend\n", WORLDMAP, re.S)
        self.assertIsNotNone(m, "dp.OnHide")
        body = m.group(1)
        noted, stopped = body.find("mod:OnMapHidden()"), body.find("mod.OwnViewStop(")
        self.assertGreaterEqual(noted, 0)
        self.assertGreaterEqual(stopped, 0)
        self.assertLess(noted, stopped)


if __name__ == "__main__":
    unittest.main()
