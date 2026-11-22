"""The fog (Stitch.lua's Shade.Fog, Data/Forever/Fog.lua, Media/Textures/Forever/MapFog/, render.py --bake-fog): every
piece's file there at its size; whichever of a zone's pieces are unexplored, their shares never come to more than
the one shade (they don't stack darker where pieces overlap); and Shade.Fog.Show draws only the unexplored pieces',
each over its piece's rectangle: python -P tools/offline-test/fog.py. (Lua 5.1 through lupa and the standard
library only, as CI installs: the masks' DXT5 alpha read here)"""
from pathlib import Path
import random
import re
import struct
import unittest

from lupa.lua51 import LuaRuntime


ADDON = Path(__file__).resolve().parents[2] / "OpenMap"
STITCH = ADDON / "Map" / "Stitch.lua"
FOG = ADDON / "Data" / "Forever" / "Fog.lua"
FILES = ADDON / "Media" / "Textures" / "Forever" / "MapFog"
SHADE = 0.62                    # (Stitch.lua's UNDISCOVERED alpha: render.py's FOG_S)
STEP = 4                        # (art px between the points checked)


def zones():
    """{ mapID: [ (w, h, x, y, n, cw, ch, fw, fh) ] } from Fog.lua"""
    out = {}
    for mid, body in re.findall(r"\n\t\[(\d+)\] = \{ (.*) \},   --", FOG.read_text(encoding="utf-8")):
        out[int(mid)] = [tuple(int(v) for v in e) for e in re.findall(
            r'\["(\d+):(\d+):(\d+):(\d+)"\] = \{ (\d+), (\d+), (\d+), (\d+), (\d+) \}', body)]
    return out


def blp_size(path):
    with open(path, "rb") as f:
        head = f.read(20)
    assert head[:4] == b"BLP2", path.name
    return struct.unpack("<2I", head[12:20])


def blp_alpha(path):
    """a BLP2's (DXT5, as tools/map-textures/blp.py writes it) first level's alpha: (width, height, bytes)"""
    data = path.read_bytes()
    assert data[:4] == b"BLP2" and data[8] == 2 and data[10] == 7, path.name   # (encoding 2: DXT; alpha type 7: DXT5)
    w, h = struct.unpack("<2I", data[12:20])
    at = struct.unpack("<I", data[20:24])[0]
    out = bytearray(w * h)
    bw = (w + 3) // 4
    for by in range((h + 3) // 4):
        for bx in range(bw):
            o = at + (by * bw + bx) * 16
            a0, a1 = data[o], data[o + 1]
            if a0 > a1:
                pal = [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
            else:
                pal = [a0, a1] + [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)] + [0, 255]
            bits = int.from_bytes(data[o + 2:o + 8], "little")
            for i in range(16):
                x, y = bx * 4 + i % 4, by * 4 + i // 4
                if x < w and y < h:
                    out[y * w + x] = pal[(bits >> (3 * i)) & 7]
    return w, h, out


class FileTests(unittest.TestCase):
    def test_every_piece_has_its_file_at_its_size(self):
        z = zones()
        self.assertGreater(len(z), 30)
        for mid, entries in z.items():
            self.assertGreater(len(entries), 0, mid)
            for e in entries:
                w, h, x, y, n, cw, ch, fw, fh = e
                p = FILES / ("%d_%d.blp" % (mid, n))
                self.assertTrue(p.exists(), p.name)
                self.assertEqual(blp_size(p), (fw, fh), p.name)
                self.assertTrue(0 < cw <= fw and 0 < ch <= fh, p.name)


class NeverDarkerTests(unittest.TestCase):
    def test_any_unexplored_set_is_at_most_the_shade(self):
        rng = random.Random(3)
        for mid, entries in zones().items():
            # at points of the zone's art every STEP px: each piece's share there (its mask's nearest px)
            at = {}
            for i, (w, h, x, y, n, cw, ch, fw, fh) in enumerate(entries):
                mw, _, a = blp_alpha(FILES / ("%d_%d.blp" % (mid, n)))
                for py in range((y + STEP - 1) // STEP * STEP, y + h, STEP):
                    v = min(ch - 1, (py - y) * ch // h)
                    for px in range((x + STEP - 1) // STEP * STEP, x + w, STEP):
                        share = a[v * mw + min(cw - 1, (px - x) * cw // w)]
                        if share:
                            at.setdefault((px, py), []).append((i, share / 255))
            for trial in range(4):
                un = set(range(len(entries))) if trial == 0 else {i for i in range(len(entries)) if rng.random() < 0.5}
                worst = 0
                for shares in at.values():
                    through = 1.0                       # what shows through: prod(1 - share)
                    for i, sh in shares:
                        if i in un:
                            through *= 1 - sh
                    worst = max(worst, 1 - through)
                self.assertLessEqual(worst, SHADE + 0.03, "%d: %.3f darker than the shade" % (mid, worst))


class ShowTests(unittest.TestCase):
    def setUp(self):
        src = STITCH.read_text(encoding="utf-8")
        m = re.search(r"\nShade\.Fog = .*?\nfunction Shade\.Fog\.Show\(.*?\nend\n", src, re.S)
        self.assertIsNotNone(m, "Shade.Fog in Stitch.lua")
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute("""
            NONE, TEX, UNDISCOVERED = {}, "T\\\\", { 0.1, 0.2, 0.3, 0.62 }
            S = { artTop = 50 }
            Shade = { on = true, k = 0.5 }
            ns = { MapFog = { [7] = { ["100:50:10:20"] = { 1, 50, 25, 64, 32 }, ["40:40:0:0"] = { 2, 20, 20, 32, 32 } } } }
            pieces = { [7] = { ["100:50:10:20"] = { unexplored = true }, ["40:40:0:0"] = { unexplored = false } } }
            placed = {}
            function strsplit(sep, s)
                local out = {}
                for part in (s .. sep):gmatch("(.-)" .. sep) do out[#out + 1] = part end
                return unpack(out)
            end
            local function Region()
                local r = { shown = true }
                function r:SetAllPoints() end
                function r:SetFrameLevel() end
                function r:Show() self.shown = true end
                function r:Hide() self.shown = false end
                function r:SetShown(on) self.shown = on end
                function r:SetTexture(f) self.file = f end
                function r:SetTexCoord(...) self.coord = { ... } end
                function r:SetVertexColor(...) self.color = { ... } end
                function r:CreateTexture() return Region() end
                return r
            end
            function CreateFrame() return Region() end
            root = Region()
            function Place(mapID) return { left = 1000, top = 2000, sx = 2, sy = 3 } end
            function Record(tex, x, y, w, h) placed[tex] = { x, y, w, h } end
            function Shade.Collect() return { on = true }, nil end
            function Shade.Anchor(recs, on) recs.on = on end
        """)
        self.lua.execute(m.group(0))

    def test_only_unexplored_pieces_over_their_rectangles(self):
        self.lua.execute("Shade.Fog.Show(7, true)")
        t = self.lua.eval("Shade.Fog.zones[7].tex")
        un, ex = t["100:50:10:20"], t["40:40:0:0"]
        self.assertTrue(un.shown)
        self.assertFalse(ex.shown)
        self.assertEqual(tuple(self.lua.eval("placed")[un].values()), (1000 + 10 * 2, 2000 + 20 * 3, 100 * 2, 50 * 3))
        self.assertEqual(un.file, "T\\MapFog\\7_1")
        self.assertEqual(tuple(un.coord.values()), (0, 50 / 64, 0, 25 / 32))
        self.assertEqual(tuple(un.color.values()), (0.1, 0.2, 0.3, 0.5))   # (the shade's colour, Darkening's strength)

    def test_explored_goes_and_off_hides(self):
        self.lua.execute("Shade.Fog.Show(7, true)")
        self.lua.execute('pieces[7]["100:50:10:20"].unexplored = false Shade.Fog.Show(7, true)')
        self.assertFalse(self.lua.eval("Shade.Fog.zones[7].tex")["100:50:10:20"].shown)
        self.lua.execute("Shade.Fog.Show(7, false)")
        self.assertFalse(self.lua.eval("Shade.Fog.zones[7].frame").shown)

    def test_only_while_darkening(self):
        self.assertTrue(self.lua.eval("Shade.Fog.Has(7)"))
        self.assertFalse(self.lua.eval("Shade.Fog.Has(8)"))
        self.lua.execute("Shade.on = false")
        self.assertFalse(self.lua.eval("Shade.Fog.Has(7)"))


if __name__ == "__main__":
    unittest.main()
