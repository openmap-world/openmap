# The masks of a client whose maps are painted whole (retail: Data/<client>/Client.lua's sea = false),
# from the game's own art and tables. WoW Forever's are render.py's (--bake-territory and the rest),
# made for its blank-parchment zone maps.
#   MapTerritory/<zone>.tga     where a zone's base art shows over its continent's: its own land (its
#                               explored-area pieces, filled), the cities in it, and what its art paints
#                               round them out to REACH world units, never onto another zone's own land;
#                               where two zones paint the same place, the one whose land is nearer has
#                               it (shared over BLEND); never on its frame (its burnt edge, its corners)
#   MapBackLand/<continent>.tga where a continent's art shows over the world's: its zones' own land and
#                               the band of shallows its art paints round it (SHALLOWS); the world's art
#                               (its sea, its islands) shows past it
#   MapMiniLand/<continent>.tga where the close-up minimap shows (Close.lua): its zones' own land
#   Data/<client>/Territories.lua  which zones and continents have them (ns.MapTerritories, ns.MapBackLands)
# Each zone's own land is its explored-area pieces (WorldMapOverlay), as render.py's own_land: zones
# without any (islands, cities) have no territory and are drawn through a round feather (Stitch.lua).
#
# usage: python -P tools/map-preview/territory.py <db2 dir> <texture cache> [preview dir]
#   (OPENMAP_CLIENT: the client, tools/clients.py; the textures are read from the cache, fetched from
#   wago.tools where they're missing; preview dir: each continent's masks, to look at)
import csv, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import clients, uimap
sys.path.insert(0, HERE)
from whole import Art

CANVAS = (1002, 668)            # a zone's art is worked on at this size, whatever its own (3:2, as all of them)
G = 2.0                         # grid px per world unit, laying a continent's zones out together
REACH = (6.0, 12.0)             # world units off its own land where a zone's painting is full / gone
BLEND = 4.0                     # world units: how fast a zone's claim falls off past the nearer one's own land
OTHERS = 1.5                    # world units over which a zone's painting gives way to another zone's own land
SHALLOWS = (28.0, 40.0)         # world units off the land where a continent's art is full / gone (its shallows band)
MINI = (2.0, 4.0)               # ... and the minimap's land
TERR_PX, LAND_PX = 256, 1024    # the masks' sizes


def frame_mask():
    """inside a zone map's frame, on its canvas: off its burnt edge and its decorated corners"""
    w, h = CANVAS
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum(np.minimum(xs, w - 1 - xs) / w, np.minimum(ys, h - 1 - ys) / h)
    t = np.clip((d - 0.02) / 0.03, 0, 1)
    # the corners' ornaments (Blizzard's gold knots, a dragon's head ...): an ellipse off each
    cx = np.minimum(xs, w - 1 - xs) / (0.17 * w)
    cy = np.minimum(ys, h - 1 - ys) / (0.2 * h)
    c = np.clip((np.hypot(np.clip(1 - cx, 0, None), np.clip(1 - cy, 0, None)) * -1 + 1) / 0.25, 0, 1)
    m = t * np.where((cx < 1) & (cy < 1), c, 1)
    return m * m * (3 - 2 * m)


def main():
    db2, cache = sys.argv[1], sys.argv[2]
    preview = sys.argv[3] if len(sys.argv) > 3 else None
    w = uimap.World(db2)
    world = uimap.read_world(os.path.join(clients.DATA, "World.lua"))
    if not world: sys.exit("no World.lua for %s: run tools/map-data/world.py first" % clients.NAME)
    art = Art(db2, cache)
    read = lambda n: list(csv.DictReader(open(os.path.join(db2, n + ".csv"), encoding="utf-8")))
    pieces = {}
    for r in read("WorldMapOverlay"):
        pieces.setdefault(int(r["UiMapArtID"]), []).append(r)
    ptiles = {}
    for r in read("WorldMapOverlayTile"):
        if r["LayerIndex"] == "0":
            ptiles.setdefault(r["WorldMapOverlayID"], {})[(int(r["RowIndex"]), int(r["ColIndex"]))] = int(r["FileDataID"])
    W, H = w.art(uimap.WORLD)[1:3]
    FRAME = frame_mask()

    def own_land(m):
        """the zone's own land on its canvas: its pieces' alpha, closed and filled (None: it has none)"""
        a, aw, ah, tw, th = w.art(m)
        if not pieces.get(a): return None
        alpha = np.zeros((ah, aw), np.uint8)
        for o in pieces[a]:
            x, y = int(o["OffsetX"]), int(o["OffsetY"])
            for (row, col), fid in ptiles.get(o["ID"], {}).items():
                t = art.fetch(fid)
                if t is None: continue
                ta = np.asarray(t.getchannel("A"))
                X0, Y0 = x + col * 256, y + row * 256
                X1, Y1 = min(aw, X0 + ta.shape[1]), min(ah, Y0 + ta.shape[0])
                if X1 > X0 and Y1 > Y0:
                    alpha[Y0:Y1, X0:X1] = np.maximum(alpha[Y0:Y1, X0:X1], ta[:Y1 - Y0, :X1 - X0])
        o = np.asarray(Image.fromarray(alpha).resize(CANVAS, Image.BILINEAR)).astype(np.float32) / 255
        land = ndimage.binary_fill_holes(ndimage.binary_closing(o * FRAME > 0.5, np.ones((3, 3)), iterations=6))
        return land if land.any() else None

    def continent_of(m):
        for _ in range(10):
            if m in world["continents"]: return m
            m = w.parent(m)
        return None

    zones = [m for m, k in world["zones"].items() if k == 1]
    cities = [m for m, k in world["zones"].items() if k == 2]

    memo = {}
    def land_of(m):
        """a zone's own land with the cities in it (theirs, or whose middle is on its land: its art paints
        them till theirs comes in), on its canvas; None without pieces"""
        if m in memo: return memo[m]
        land = own_land(m)
        if land is not None:
            l, r, t, b = w.rect(m)
            for city in cities:
                ql, qr, qt, qb = w.rect(city)
                cx, cy = int(((ql + qr) / 2 - l) / (r - l) * CANVAS[0]), int(((qt + qb) / 2 - t) / (b - t) * CANVAS[1])
                if w.parent(city) != m and not (0 <= cx < CANVAS[0] and 0 <= cy < CANVAS[1] and land[cy, cx]): continue
                x0, x1 = int((ql - l) / (r - l) * CANVAS[0]), int((qr - l) / (r - l) * CANVAS[0])
                y0, y1 = int((qt - t) / (b - t) * CANVAS[1]), int((qb - t) / (b - t) * CANVAS[1])
                yy, xx = np.ogrid[0:CANVAS[1], 0:CANVAS[0]]
                land = land | (((xx - (x0 + x1) / 2) / max(1, (x1 - x0) / 2)) ** 2 + ((yy - (y0 + y1) / 2) / max(1, (y1 - y0) / 2)) ** 2 <= 0.6)
        memo[m] = land
        return land
    terr_dir, land_dir, mini_dir = (os.path.join(clients.TEX, d) for d in ("MapTerritory", "MapBackLand", "MapMiniLand"))
    for d in (terr_dir, land_dir, mini_dir): os.makedirs(d, exist_ok=True)
    done_terr, done_land = [], []
    for c in world["continents"]:
        cl, cr, ct, cb = w.rect(c)
        gw, gh = int((cr - cl) * W * G), int((cb - ct) * H * G)
        mine = [m for m in zones if continent_of(m) == c]
        def box(m):
            l, r, t, b = w.rect(m)
            return (int(round((l - cl) * W * G)), int(round((t - ct) * H * G)), int(round((r - cl) * W * G)), int(round((b - ct) * H * G)))
        def to_grid(img, m):
            x0, y0, x1, y1 = box(m)
            dst = np.zeros((gh, gw), np.float32)
            if x1 - x0 < 2 or y1 - y0 < 2: return dst
            a = np.asarray(Image.fromarray(np.clip(img, 0, 1).astype(np.float32), "F").resize((x1 - x0, y1 - y0), Image.BILINEAR))
            X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(gw, x1), min(gh, y1)
            if X1 > X0 and Y1 > Y0: dst[Y0:Y1, X0:X1] = a[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0]
            return dst
        def to_art(img, m):
            x0, y0, x1, y1 = box(m)
            pad = np.zeros((y1 - y0, x1 - x0), np.float32)
            X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(gw, x1), min(gh, y1)
            if X1 > X0 and Y1 > Y0: pad[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] = img[Y0:Y1, X0:X1]
            return np.asarray(Image.fromarray(pad, "F").resize(CANVAS, Image.BILINEAR))
        own, frame = {}, {}
        for m in mine:
            land = land_of(m)
            if land is None: continue
            own[m] = to_grid(land.astype(np.float32), m)
            frame[m] = to_grid(FRAME, m)
        if own:
            dist = {m: ndimage.distance_transform_edt(own[m] < 0.5) / G for m in own}
            near = {m: ndimage.gaussian_filter((dist[m] <= 0).astype(np.float32), OTHERS * G / 2) for m in own}
            dmin = np.full((gh, gw), 1e6, np.float32)
            avail = {}
            for m in own:
                others = np.zeros((gh, gw), np.float32)
                for n in own:
                    if n != m: others = np.maximum(others, near[n] * frame[n])
                u = np.clip(1 - (dist[m] - REACH[0]) / (REACH[1] - REACH[0]), 0, 1)
                avail[m] = frame[m] * np.clip(1 - others, 0, 1) * u * u * (3 - 2 * u)
                dmin = np.minimum(dmin, np.where(avail[m] > 0.01, dist[m], 1e6))
            claim, total = {}, np.zeros((gh, gw), np.float32)
            for m in own:
                claim[m] = avail[m] * np.exp(-np.clip(dist[m] - dmin, 0, 60) / BLEND)
                total += claim[m]
            norm = np.maximum(total, 1)
            for m in own:
                soft = np.clip(1 - dist[m], 0, 1)                    # (its own land, a little past it)
                terr = np.maximum(soft * frame[m], claim[m] / norm)
                a = Image.fromarray((np.clip(to_art(terr, m), 0, 1) * 255).astype(np.uint8)).resize((TERR_PX, TERR_PX), Image.LANCZOS)
                Image.merge("RGBA", (Image.new("L", (TERR_PX, TERR_PX), 255),) * 3 + (a,)).save(os.path.join(terr_dir, "%d.tga" % m))
                done_terr.append(m)
        # the continent's land: its zones' own land (and the islands drawn round, no zone's: a round
        # feather of theirs), its shallows past it. The minimap's: every zone's whose middle is on the
        # continent's map, another continent's too (Quel'Thalas' zones, on the Eastern Kingdoms' game map,
        # whose minimap is drawn through the Eastern Kingdoms' land: Close.lua's CONT_MAP)
        def land_of_zones(ms):
            land = np.zeros((gh, gw), bool)
            for m in ms:
                ln = land_of(m) if m in zones else None
                if ln is not None:
                    land |= to_grid(ln.astype(np.float32), m) > 0.5
                    continue
                x0, y0, x1, y1 = box(m)
                yy, xx = np.ogrid[0:gh, 0:gw]
                land |= ((xx - (x0 + x1) / 2) / max(1, (x1 - x0) / 2)) ** 2 + ((yy - (y0 + y1) / 2) / max(1, (y1 - y0) / 2)) ** 2 <= 0.35
            return land
        def middle_on(m):
            l, r, t, b = w.rect(m)
            return cl <= (l + r) / 2 <= cr and ct <= (t + b) / 2 <= cb
        land = land_of_zones(mine + [x for x in cities if continent_of(x) == c])
        mini = land_of_zones([m for m in zones + cities if middle_on(m)])
        if land.any():
            for out_dir, (a0, a1), ln in ((land_dir, SHALLOWS, land), (mini_dir, MINI, mini)):
                d = ndimage.distance_transform_edt(~ln) / G
                t = np.clip(1 - (d - a0) / (a1 - a0), 0, 1)
                a = Image.fromarray((t * t * (3 - 2 * t) * 255).astype(np.uint8)).resize((LAND_PX, LAND_PX), Image.LANCZOS)
                Image.merge("RGBA", (Image.new("L", (LAND_PX, LAND_PX), 255),) * 3 + (a,)).save(os.path.join(out_dir, "%d.tga" % c))
            done_land.append(c)
            if preview:
                os.makedirs(preview, exist_ok=True)
                sheet = np.zeros((gh, gw, 3), np.float32)
                d = ndimage.distance_transform_edt(~land) / G
                t = np.clip(1 - (d - SHALLOWS[0]) / (SHALLOWS[1] - SHALLOWS[0]), 0, 1)
                sheet[..., 2] = t * 0.6
                for i, m in enumerate(own):
                    sheet[..., i % 2] = np.maximum(sheet[..., i % 2], own[m] * (0.5 + 0.5 * (i % 3) / 2))
                Image.fromarray((sheet * 255).astype(np.uint8)).save(os.path.join(preview, "land-%d.png" % c))
        print("  %s: %d zones, %d territories" % (w.uimap[c]["Name_lang"], len(mine), len(own)), flush=True)

    path = os.path.join(clients.DATA, "Territories.lua")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("-- Which zones have a territory (Media/Textures/<client>/MapTerritory) and which continents a land mask\n")
        fh.write("-- (MapBackLand, MapMiniLand): Stitch.lua draws each through it.\n")
        fh.write("-- Generated by tools/map-preview/territory.py from the game's art (build %s); regenerate rather than edit.\n\n" % clients.BUILD)
        fh.write("local _, ns = ...\n\n")
        fh.write("ns.MapTerritories = {\n%s}\n\n" % "".join("\t[%d] = true,   -- %s\n" % (m, w.uimap[m]["Name_lang"]) for m in sorted(done_terr)))
        fh.write("ns.MapBackLands = {\n%s}\n" % "".join("\t[%d] = true,   -- %s\n" % (m, w.uimap[m]["Name_lang"]) for m in sorted(done_land)))
    print("wrote %s: %d territories, %d continents' land" % (os.path.relpath(path, clients.REPO), len(done_terr), len(done_land)))


if __name__ == "__main__":
    main()
