# The world's WMOs (caves, buildings ...) on the two continents, read from the game's own files:
# where each is placed, its groups, the minimap pictures of their insides, and which are caves.
# Used by minimap.py (Data/CaveMinimap.lua) and build.py (the MapCave masks: a cave map's cave).
#
# How it's placed (each step checked against the game's own data while writing this):
#   * the WDT lists each map tile's object file (MAID); its MODF entries place each WMO: position
#     (world X = 17066.67 - pos[2], Y = 17066.67 - pos[0], Z = pos[1]), yaw (rot[1], degrees),
#     scale / 1024. Local (x, y) lands at origin + R(yaw + 180) (x, y): the root's box put that way
#     matches MODF's own world box exactly, for every WMO tried.
#   * the root (MOHD: groups, WMO ID; MOGI: each group's flags and box) and WMOMinimapTexture
#     (WMO ID, group, block x / y, file): 2 px a yard; block (bx, by) starts at the group box's
#     min x + 128 bx, min y + 128 by, its picture's left and bottom edges there (x right, y up).
#     Put so, each block covers its group's floor (the floor seen from above overlaps it 0.9+).
#   * underground: a group inside (MOGI flag 0x2000) whose floor is 4+ yards under the terrain (the
#     tiles' heights, MCVT) over two-thirds of its box. That takes in half-buried houses too, so
#     only the game's own caves count: its WMOs filed under world/wmo/dungeon/ (caves, dens, mines,
#     tunnels, crypts, barrows, hives, ogre mounds, dungeon entrances), any with "cave" in its file
#     name, and WoW Forever's own new ones looked at one by one (REVIEWED).
#
# OPENMAP_WOW: the World of Warcraft folder; the game's files are read from it (tools/casc), else
# fetched from wago.tools into the cache (some thousands of files, slowly). The file names come from
# the community listfile (github.com/wowdev/wow-listfile), fetched into the cache once (about 150 MB).
import csv, io, math, os, struct, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "casc"))
BUILD = "1.60.1.70245"
UA = {"User-Agent": "openmap-tools/1"}
LISTFILE = "https://github.com/wowdev/wow-listfile/releases/latest/download/community-listfile.csv"
O = 32 * 1600 / 3               # world yards from the map's corner to its middle
TILE = 1600 / 3
INTERIOR = 0x2000
DEEP = 4                        # yards a group's floor lies under the terrain to count as underground
# WoW Forever's own WMOs (no names but numbers in the listfile), looked at one by one: underground
# caves, crypts, tunnels and vaults (its houses, inns, cities and odd pieces left out)
REVIEWED = {
    "world/wmo/autogen-names/unknown/21064.wmo", "world/wmo/autogen-names/unknown/21140.wmo",
    "world/wmo/autogen-names/unknown/21106.wmo", "world/wmo/autogen-names/riverglades/20519.wmo",
    "world/wmo/autogen-names/unknown/20959.wmo", "world/wmo/autogen-names/unknown/20740.wmo",
    "world/wmo/autogen-names/unknown/21067.wmo", "world/wmo/autogen-names/hyjal/19312.wmo",
    "world/wmo/autogen-names/unknown/21654.wmo", "world/wmo/autogen-names/winterspring/21137.wmo",
    "world/wmo/autogen-names/unknown/20606.wmo", "world/wmo/autogen-names/blackmawhold/21177.wmo",
    "world/wmo/cataclysm/twilighthighlands/th_obsidianblackdragonshrine.wmo",
}


def chunks(data):
    out, i = [], 0
    while i + 8 <= len(data):
        tag = data[i:i + 4][::-1].decode("latin1")
        size = struct.unpack_from("<I", data, i + 4)[0]
        out.append((tag, data[i + 8:i + 8 + size]))
        i += 8 + size
    return out


def cave_kind(path):
    """a WMO the game files as a cave or underground place (by its file name)"""
    if not path: return False
    if path.startswith("world/wmo/dungeon/"): return "gm_dungeon" not in path    # (not the GMs' own prison)
    return "cave" in path.rsplit("/", 1)[-1] or path in REVIEWED


class World:
    def __init__(self, cache):
        self.cache = cache
        os.makedirs(cache, exist_ok=True)
        self.casc = None
        if os.environ.get("OPENMAP_WOW"):
            from casc import Casc
            self.casc = Casc(os.environ["OPENMAP_WOW"], "wow_classic_beta")
        self.heights = {}
        self._scan()

    def get(self, url, path, least=50):
        if not os.path.exists(path) or os.path.getsize(path) < least:
            open(path, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600).read())
            time.sleep(0.15)
        return path

    def table(self, name):
        return list(csv.DictReader(open(self.get("https://wago.tools/db2/%s/csv?build=%s" % (name, BUILD),
            os.path.join(self.cache, "%s-%s.csv" % (name, BUILD))), encoding="utf-8")))

    def read(self, fid):
        """a game file by file ID, or None where the build has none"""
        if self.casc:
            try:
                return self.casc.read(fid)
            except KeyError:
                return None
        p = os.path.join(self.cache, "%d.bin" % fid)
        if not os.path.exists(p):
            data = urllib.request.urlopen(urllib.request.Request(
                "https://wago.tools/api/casc/%d?download&version=%s" % (fid, BUILD), headers=UA), timeout=120).read()
            open(p, "wb").write(data)
            time.sleep(0.15)
        data = open(p, "rb").read()
        return data if len(data) > 100 else None    # (a missing file answers with an empty or tiny body)

    def _scan(self):
        maps = {r["ID"]: r for r in self.table("Map")}
        self.tiles, self.placed, self.roots = {}, {}, {}
        for cont in (0, 1):
            c = dict(chunks(self.read(int(maps[str(cont)]["WdtFileDataID"]))))
            for n in range(64 * 64):
                y, x = divmod(n, 64)
                if not struct.unpack_from("<I", c["MAIN"], n * 8)[0] & 1: continue
                ids = struct.unpack_from("<8I", c["MAID"], n * 32)     # (root, obj0, obj1, tex0, lod, map, map normal, minimap)
                self.tiles[(cont, x, y)] = ids
                obj = ids[1] and self.read(ids[1])
                for tag, d in chunks(obj or b""):
                    if tag != "MODF": continue
                    for k in range(len(d) // 64):
                        fid, uid = struct.unpack_from("<II", d, k * 64)
                        flags, _, _, scale = struct.unpack_from("<4H", d, k * 64 + 56)
                        if flags & 8:                                   # (the name is a file ID)
                            self.placed[(cont, uid)] = dict(cont=cont, fid=fid, pos=struct.unpack_from("<3f", d, k * 64 + 8),
                                yaw=struct.unpack_from("<3f", d, k * 64 + 20)[1], scale=scale / 1024)
        for p in self.placed.values():
            if p["fid"] in self.roots: continue
            data = self.read(p["fid"])
            if not data:
                self.roots[p["fid"]] = None
                continue
            rc = dict(chunks(data))
            ng = struct.unpack_from("<I", rc["MOHD"], 4)[0]
            self.roots[p["fid"]] = dict(wid=struct.unpack_from("<I", rc["MOHD"], 32)[0],
                groups=[(struct.unpack_from("<I", rc["MOGI"], g * 32)[0], struct.unpack_from("<6f", rc["MOGI"], g * 32 + 4)) for g in range(ng)])
        self.blocks = {}
        for r in self.table("WMOMinimapTexture"):
            self.blocks.setdefault(int(r["WMOID"]), {}).setdefault(int(r["GroupNum"]), []).append(
                (int(r["BlockX"]), int(r["BlockY"]), int(r["FileDataID"])))
        wanted = {fid for fid, r in self.roots.items() if r and r["wid"] in self.blocks}
        self.paths = {}
        for line in open(self.get(LISTFILE, os.path.join(self.cache, "community-listfile.csv"), 10 ** 6), encoding="utf-8", errors="replace"):
            a, _, b = line.partition(";")
            if a.isdigit() and int(a) in wanted: self.paths[int(a)] = b.strip().lower()

    # ---------------------------------------------------------------- the terrain's height
    def _tile_heights(self, cont, tx, ty):
        """the tile's outer height grid (129 x 129, rows north to south, columns west to east)"""
        key = (cont, tx, ty)
        if key not in self.heights:
            grid = None
            ids = self.tiles.get(key)
            data = ids and self.read(ids[0])
            if data:
                grid = [[None] * 129 for _ in range(129)]
                for tag, d in chunks(data):
                    if tag != "MCNK": continue
                    ix, iy = struct.unpack_from("<2I", d, 4)
                    z0 = struct.unpack_from("<f", d, 0x68 + 8)[0]          # (its position: X, Y, Z)
                    sub = dict(chunks(d[128:]))
                    if "MCVT" not in sub: continue
                    h = struct.unpack("<145f", sub["MCVT"][:580])           # (rows of 9 outer, 8 inner)
                    for r in range(9):
                        for c in range(9):
                            grid[iy * 8 + r][ix * 8 + c] = z0 + h[r * 17 + c]
            self.heights[key] = grid
        return self.heights[key]

    def terrain(self, cont, X, Y):
        tx, ty = int((O - Y) // TILE), int((O - X) // TILE)
        g = self._tile_heights(cont, tx, ty)
        if not g: return None
        fx, fy = ((O - Y) - tx * TILE) / (TILE / 128), ((O - X) - ty * TILE) / (TILE / 128)
        c0, r0 = min(int(fx), 127), min(int(fy), 127)
        q = (g[r0][c0], g[r0][c0 + 1], g[r0 + 1][c0], g[r0 + 1][c0 + 1])
        if None in q: return None
        dx, dy = fx - c0, fy - r0
        return q[0] * (1 - dx) * (1 - dy) + q[1] * dx * (1 - dy) + q[2] * (1 - dx) * dy + q[3] * dx * dy

    # ---------------------------------------------------------------- a WMO's groups
    @staticmethod
    def world(p, lx, ly):
        """a WMO's local point, in world yards (X, Y)"""
        a = math.radians(p["yaw"] + 180)
        s = p["scale"]
        return (O - p["pos"][2] + (lx * math.cos(a) - ly * math.sin(a)) * s,
                O - p["pos"][0] + (lx * math.sin(a) + ly * math.cos(a)) * s)

    def underground(self, p, box):
        floor = p["pos"][1] + box[2] * p["scale"]
        n = deep = 0
        for fx in (0.15, 0.5, 0.85):
            for fy in (0.15, 0.5, 0.85):
                h = self.terrain(p["cont"], *self.world(p, box[0] + (box[3] - box[0]) * fx, box[1] + (box[4] - box[1]) * fy))
                if h is None: continue
                n += 1
                deep += h - floor >= DEEP
        return n >= 5 and deep >= 2 / 3 * n

    def inside(self, p):
        """a placed WMO's inside groups with minimap pictures: [(group, box)]"""
        root = self.roots.get(p["fid"])
        if not root or root["wid"] not in self.blocks: return []
        own = self.blocks[root["wid"]]
        return [(g, box) for g, (flags, box) in enumerate(root["groups"]) if g in own and flags & INTERIOR]

    def cave_groups(self, p, under=True):
        """a placed WMO's inside groups with minimap pictures, if it's a cave (under: only those under the
        terrain): [(group, box)]"""
        if not cave_kind(self.paths.get(p["fid"])): return []
        return [(g, box) for g, box in self.inside(p) if not under or self.underground(p, box)]

    def pictures(self, p, g, box):
        """a group's minimap pictures: (file, width, height, left x, bottom y (local yards)), the ones the build has"""
        out = []
        for bx, by, fid in self.blocks[self.roots[p["fid"]]["wid"]][g]:
            data = self.read(fid)
            if not data or data[:4] != b"BLP2": continue
            w, h = struct.unpack("<II", data[12:20])
            out.append((fid, w, h, box[0] + bx * 128, box[1] + by * 128))
        return out

    def picture(self, fid):
        """a minimap picture (RGBA)"""
        from PIL import Image
        data = self.read(fid)
        try:
            return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception:            # (uncompressed BLP2, which Pillow doesn't read)
            w, h = struct.unpack("<II", data[12:20]); off = struct.unpack("<16I", data[20:84])[0]
            return Image.frombytes("RGBA", (w, h), data[off:off + w * h * 4], "raw", "BGRA")

    def footprint(self, cont, box, z, to_page, size):
        """where the caves are on a page: every cave WMO's inside groups within z (a floor's heights) and
        near box (yards), their minimap pictures' alpha laid on the page (to_page: yards -> px)"""
        import numpy as np
        from PIL import Image
        W, H = size
        out = np.zeros((H, W), np.float32)
        x0, y0, x1, y1 = box
        for (c, _), p in self.placed.items():
            if c != cont: continue
            ox, oy = O - p["pos"][2], O - p["pos"][0]
            if not (x0 - 400 <= ox <= x1 + 400 and y0 - 400 <= oy <= y1 + 400): continue
            for g, gbox in self.cave_groups(p, under=False):
                gz0, gz1 = p["pos"][1] + gbox[2] * p["scale"], p["pos"][1] + gbox[5] * p["scale"]
                if gz1 < z[0] or gz0 > z[1]: continue                 # (another floor's)
                for fid, w, h, lx0, ly0 in self.pictures(p, g, gbox):
                    def page(col, row):
                        return to_page(*self.world(p, lx0 + col / 2, ly0 + (h - row) / 2))
                    o, cx, cy = page(0, 0), page(1, 0), page(0, 1)
                    A = np.array([[cx[0] - o[0], cy[0] - o[0]], [cx[1] - o[1], cy[1] - o[1]]])
                    inv = np.linalg.inv(A)
                    coeffs = (inv[0, 0], inv[0, 1], -(inv[0, 0] * o[0] + inv[0, 1] * o[1]),
                              inv[1, 0], inv[1, 1], -(inv[1, 0] * o[0] + inv[1, 1] * o[1]))
                    a = self.picture(fid).getchannel("A").transform((W, H), Image.AFFINE, coeffs, resample=Image.BILINEAR)
                    out = np.maximum(out, np.asarray(a).astype(np.float32) / 255)
        return out
