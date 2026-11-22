# Builds OpenMap/Data/<client>/Explore.lua: the places still to explore for the game's "Explore <zone>"
# achievements, for the map's "Show places to explore" (Map/Explore.lua). WoW Forever only: a client
# without these achievements gets no file, and the option does nothing there.
#
#   1. the achievements: every Achievement titled "Explore ..." whose criteria (CriteriaTree, walked down
#      from Achievement.Criteria_tree) are of type 43, "reveal a world map overlay": each one's Asset is a
#      WorldMapOverlay, the explored-area piece Reveal.lua keys "w:h:x:y" on its zone's art (build.py).
#      (Explore Azeroth, Eastern Kingdoms and Kalimdor are made of other achievements, type 8: left out.)
#   2. the ground that explores a piece: the game sets an area's explored bit when you stand in it, and an
#      overlay counts as explored once any of its areas (AreaID_0..3) is. Outdoors your area is the map
#      chunk's (the ADTs' MCNK, a 33 1/3 yard square, its area ID at 0x34), read from the game's own files
#      (OPENMAP_WOW: the World of Warcraft folder, tools/casc), else wago.tools into <cache>.
#      Only an overlay's own areas count, not their child areas (AreaTable.ParentAreaID): a child area
#      with an explored bit of its own (AreaBit) sets that bit, not its parent's. The script prints the
#      overlays whose areas' children cover ground of their own, to look at when the tables change.
#   3. per piece: its areas' chunks inside its zone, their outline (the chunks' edges, joined into loops
#      and simplified), and where to go: the middle of the biggest stretch of that ground near the
#      piece's own middle (the chunk deepest inside it). A piece with no chunks of its own (its areas
#      are indoors: a cave, a building) has only a spot, its overlay's hit box's middle, and `indoor`.
# Positions are on the zone's own map (0..1 across and down), through its UiMapAssignment, as
# C_Map.GetWorldPosFromMapPos does.
#
# usage: python -P tools/map-data/explore.py <cache dir> [build]
import collections, csv, math, os, struct, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "map-caves"))
import clients, uimap
from wmo import chunks                              # (it puts tools/casc on the path too)
import numpy as np
from scipy import ndimage

DATA = clients.DATA
cache = sys.argv[1]
BUILD = sys.argv[2] if len(sys.argv) > 2 else clients.BUILD
os.makedirs(cache, exist_ok=True)
OUT = os.path.join(DATA, "Explore.lua")

O, CHUNK = 32 * 1600 / 3, 1600 / 3 / 16             # yards from a continent's corner to its middle; a map chunk's side
SIMPLIFY = 0.75                                     # chunks an outline may stray from the chunks' edges
SMALL = 3                                           # chunks a loop must hold to be drawn (one or two: a stray chunk)
MARGIN = 0.03                                       # how far past its zone's map a piece's ground is looked for


def table(name, build=BUILD):
    p = os.path.join(cache, "%s-%s.csv" % (name, build))
    if not os.path.exists(p) or os.path.getsize(p) < 100:
        req = urllib.request.Request("https://wago.tools/db2/%s/csv?build=%s" % (name, build), headers={"User-Agent": "openmap-data/1"})
        open(p, "wb").write(urllib.request.urlopen(req, timeout=60).read())
        time.sleep(0.2)
    return list(csv.DictReader(open(p, encoding="utf-8")))


achievements = table("Achievement")
if clients.NAME != "forever" or not any(a["Title_lang"].startswith("Explore ") for a in achievements):
    if os.path.exists(OUT): os.remove(OUT)
    raise SystemExit("explore: no Explore achievements for %s: no Explore.lua" % clients.NAME)

criteria = {r["ID"]: r for r in table("Criteria")}
kids = collections.defaultdict(list)
for r in table("CriteriaTree"): kids[r["Parent"]].append(r)
overlays = {r["ID"]: r for r in table("WorldMapOverlay")}
areas = {r["ID"]: r for r in table("AreaTable")}
for t in ("UiMap", "UiMapAssignment", "UiMapXMapArt", "UiMapArt", "UiMapArtStyleLayer", "Map"): table(t)
world = uimap.World(cache, "-" + BUILD)
zone_of_art = {}
for r in table("UiMapXMapArt"):
    if r["PhaseID"] == "0": zone_of_art.setdefault(int(r["UiMapArtID"]), int(r["UiMapID"]))
# WoW Forever's zones have new arts (UiMapXMapArt: Dun Morogh's is 2151), but the achievements, and the
# pieces the game draws (Reveal.lua), are on the old ones (1216), which UiMapXMapArt no longer names: an
# old art is the zone's whose own art has overlays for most of the same areas (redrawn: not always at the
# same places, Eastern Plaguelands, Silithus)
_areas = collections.defaultdict(set)
for o in overlays.values():
    _areas[int(o["UiMapArtID"])].update(o["AreaID_%d" % i] for i in range(4) if o["AreaID_%d" % i] != "0")
for art, ids in _areas.items():
    if art in zone_of_art: continue
    best = max(((len(ids & s), a) for a, s in _areas.items() if a in zone_of_art), default=(0, None))
    if best[0] * 2 > len(ids): zone_of_art[art] = zone_of_art[best[1]]
reveal = {}
for line in open(os.path.join(DATA, "Reveal.lua"), encoding="utf-8"):
    if line.startswith("\t["):
        art = int(line[2:line.index("]")])
        reveal[art] = {k.split('"')[1] for k in line.split("[")[2:]}


def leaves(tid):
    out = []
    for k in sorted(kids[tid], key=lambda r: int(r["OrderIndex"])):
        if k["CriteriaID"] != "0": out.append(criteria[k["CriteriaID"]])
        out += leaves(k["ID"])
    return out


def key_of(o): return "%s:%s:%s:%s" % (o["TextureWidth"], o["TextureHeight"], o["OffsetX"], o["OffsetY"])


# ---------------------------------------------------------------- 1. the achievements and their pieces
achs, pieces = {}, {}                               # id -> { title, map, art, keys }; (art, key) -> piece
for a in sorted(achievements, key=lambda a: int(a["ID"])):
    if not a["Title_lang"].startswith("Explore "): continue
    found = [overlays[c["Asset"]] for c in leaves(a["Criteria_tree"]) if c["Type"] == "43" and c["Asset"] in overlays]
    if not found: continue
    art = int(found[0]["UiMapArtID"])
    mapID = zone_of_art.get(art)
    keys = []
    for o in found:
        if int(o["UiMapArtID"]) != art: raise SystemExit("explore: %s spans two zone arts" % a["Title_lang"])
        k = key_of(o)
        if k not in reveal.get(art, ()): raise SystemExit("explore: %s's overlay %s (%s) isn't in Reveal.lua" % (a["Title_lang"], o["ID"], k))
        keys.append(k)
        ids = [int(o["AreaID_%d" % i]) for i in range(4) if o["AreaID_%d" % i] != "0"]
        pieces[(art, k)] = {"ach": int(a["ID"]), "areas": ids, "overlay": o, "map": mapID, "art": art}
    if mapID is None: raise SystemExit("explore: %s: no zone has its art %d" % (a["Title_lang"], art))
    achs[int(a["ID"])] = {"title": a["Title_lang"], "map": mapID, "art": art, "keys": keys}
print("explore:", len(achs), "achievements,", len(pieces), "pieces")


# ---------------------------------------------------------------- 2. the game's terrain
CASC = []
def game_file(fid):
    """a file of the game's by file ID: from the install (OPENMAP_WOW), else wago.tools (kept in <cache>)"""
    if os.environ.get("OPENMAP_WOW"):
        if not CASC:
            from casc import Casc
            CASC.append(Casc(os.environ["OPENMAP_WOW"], clients.PRODUCT))
        try:
            return CASC[0].read(fid)
        except KeyError:
            pass
    work = os.path.join(cache, "_terrain")
    os.makedirs(work, exist_ok=True)
    p = os.path.join(work, "%d.bin" % fid)
    if not os.path.exists(p) or os.path.getsize(p) < 100:
        url = "https://wago.tools/api/casc/%d?download&version=%s" % (fid, BUILD)
        open(p, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "openmap-tools/1"}), timeout=120).read())
        time.sleep(0.15)
    data = open(p, "rb").read()
    return data if len(data) > 100 else None          # (a missing file answers with an empty or tiny body)


grids = {}
def grid(cont):
    """the continent's map chunks' areas: [row (along -X), col (along -Y)], 1024 x 1024"""
    if cont not in grids:
        g = np.zeros((1024, 1024), np.int32)
        w = dict(chunks(game_file(int(world.gamemap[cont]["WdtFileDataID"]))))
        for n in range(4096):
            if not struct.unpack_from("<I", w["MAIN"], n * 8)[0] & 1: continue
            data = game_file(struct.unpack_from("<8I", w["MAID"], n * 32)[0])   # (the tile's root file)
            if not data: continue
            ty, tx = divmod(n, 64)
            for tag, d in chunks(data):
                if tag != "MCNK": continue
                ix, iy = struct.unpack_from("<2I", d, 4)
                g[ty * 16 + iy, tx * 16 + ix] = struct.unpack_from("<I", d, 0x34)[0]
        grids[cont] = g
        print("terrain: continent", cont, int((g > 0).sum()), "chunks", flush=True)
    return grids[cont]


def zone_rows(mapID):
    """the zone's assignments on its game map(s) that place the zone itself (not a WMO's floor)"""
    return [r for r in world.assign.get(mapID, []) if r["WMOGroupID"] in ("0", "-1") and int(r["MapID"]) in world.gamemap]


def to_zone(row, X, Y):
    """yards on the row's game map -> the zone's map (0..1)"""
    return world._norm(row, X, Y)


# ---------------------------------------------------------------- the child areas: what they'd add
children = collections.defaultdict(list)
for r in areas.values(): children[r["ParentAreaID"]].append(r["ID"])
listed_child = 0
for (art, key), p in sorted(pieces.items()):
    rows = zone_rows(p["map"])
    if not rows: continue
    g = grid(int(rows[0]["MapID"]))
    own = int(np.isin(g, p["areas"]).sum())
    extra = [c for a in p["areas"] for c in children[str(a)] if int(c) not in p["areas"]]
    if not extra: continue
    n = int(np.isin(g, [int(c) for c in extra]).sum())
    if n:
        listed_child += 1
        names = ", ".join("%s (%s, bit %s)" % (areas[c]["AreaName_lang"], c, areas[c]["AreaBit"]) for c in extra)
        print("  children: %-30s own %4d chunks; its children's %4d: %s" % (areas[str(p["areas"][0])]["AreaName_lang"], own, n, names))
print("explore: %d pieces have child areas with ground of their own (not counted)" % listed_child)


# ---------------------------------------------------------------- 3. each piece's ground
def loops(mask):
    """the edges of a mask's cells, joined into closed loops of grid corners (row, col)"""
    H_, W_ = mask.shape
    pad = np.zeros((H_ + 2, W_ + 2), bool)
    pad[1:-1, 1:-1] = mask
    nxt = {}
    # each edge runs with the inside on its left: (r, c) corners
    for r, c in zip(*np.nonzero(pad)):
        if not pad[r - 1, c]: nxt[(r - 1, c)] = nxt.get((r - 1, c), []) + [(r - 1, c - 1)]   # top: right to left
        if not pad[r + 1, c]: nxt[(r, c - 1)] = nxt.get((r, c - 1), []) + [(r, c)]           # bottom: left to right
        if not pad[r, c - 1]: nxt[(r - 1, c - 1)] = nxt.get((r - 1, c - 1), []) + [(r, c - 1)]   # left: down
        if not pad[r, c + 1]: nxt[(r, c)] = nxt.get((r, c), []) + [(r - 1, c)]               # right: up
    out = []
    while nxt:
        start = next(iter(nxt))
        loop, at = [start], start
        while True:
            ways = nxt[at]
            to = ways.pop()
            if not ways: del nxt[at]
            if to == start: break
            loop.append(to)
            at = to
        out.append([(r, c) for r, c in loop])        # (corners: pad's (r, c) is the grid's corner r, c)
    return out


def thin(pts, tol):
    """Douglas-Peucker on an open run of points"""
    if len(pts) < 3: return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    L = math.hypot(x2 - x1, y2 - y1)
    i, dm = 0, -1
    for k in range(1, len(pts) - 1):
        d = abs((y2 - y1) * pts[k][0] - (x2 - x1) * pts[k][1] + x2 * y1 - y2 * x1) / L if L else math.hypot(pts[k][0] - x1, pts[k][1] - y1)
        if d > dm: i, dm = k, d
    if dm <= tol: return [pts[0], pts[-1]]
    return thin(pts[:i + 1], tol)[:-1] + thin(pts[i:], tol)


def thin_loop(loop, tol):
    """a closed loop simplified, split at its two points furthest apart"""
    far = max(range(len(loop)), key=lambda k: (loop[k][0] - loop[0][0]) ** 2 + (loop[k][1] - loop[0][1]) ** 2)
    a = thin(loop[:far + 1], tol)
    b = thin(loop[far:] + [loop[0]], tol)
    return a[:-1] + b[:-1]


B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
def enc(v):
    """a position (0..1, a little past) as two characters: 1/4096ths, from -1/8"""
    n = max(0, min(4095, int(round((v + 0.125) / 1.25 * 4095))))
    return B64[n >> 6] + B64[n & 63]


def lua_str(s): return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


out_pieces = collections.defaultdict(dict)
outlined = indoor = 0
for (art, key), p in sorted(pieces.items()):
    o, mapID = p["overlay"], p["map"]
    w_, h_, ox, oy = map(int, key.split(":"))
    AW, AH = world.layer.get(world.style_of.get(art), (1002, 668))[:2]     # (the piece's own art's size)
    # the piece's own middle: its hit box's, else its texture's (the zone's map, 0..1)
    ht, hb, hl, hr = (int(o[k]) for k in ("HitRectTop", "HitRectBottom", "HitRectLeft", "HitRectRight"))
    if hr > hl and hb > ht: mu, mv = (hl + hr) / 2 / AW, (ht + hb) / 2 / AH
    else: mu, mv = (ox + w_ / 2) / AW, (oy + h_ / 2) / AH
    rec = {"ach": p["ach"], "areas": p["areas"], "name": areas.get(str(p["areas"][0]), {}).get("AreaName_lang", "?")}
    rows = zone_rows(mapID)
    best = None
    if rows:
        row = rows[0]
        cont = int(row["MapID"])
        g = grid(cont)
        on = np.isin(g, p["areas"])
        # (only near the zone's own map: an area's ID used again far off isn't this piece's ground)
        R, C = np.nonzero(on)
        if len(R):
            X, Y = O - (R + 0.5) * CHUNK, O - (C + 0.5) * CHUNK
            U, V = to_zone(row, X, Y)
            far = (U < -MARGIN) | (U > 1 + MARGIN) | (V < -MARGIN) | (V > 1 + MARGIN)
            on[R[far], C[far]] = False
        if on.any():
            r0, r1 = np.nonzero(on.any(1))[0][[0, -1]]
            c0, c1 = np.nonzero(on.any(0))[0][[0, -1]]
            sub = on[r0:r1 + 1, c0:c1 + 1]
            lab, n = ndimage.label(sub, np.ones((3, 3)))
            sizes = ndimage.sum(sub, lab, range(1, n + 1))
            depth = ndimage.distance_transform_edt(np.pad(sub, 1))[1:-1, 1:-1]
            def corner_zone(r, c):          # a grid corner (row r, col c of the chunks) on the zone's map
                return to_zone(row, O - (r0 + r) * CHUNK, O - (c0 + c) * CHUNK)
            # where to go: in the stretches holding a fair share of the ground, the one nearest the piece's
            # middle; in it, the chunk deepest inside (nearest that middle of those as deep)
            big = max(sizes)
            cands = []
            for k in range(1, n + 1):
                if sizes[k - 1] < max(SMALL, big * 0.25): continue
                rr, cc = np.nonzero(lab == k)
                us, vs = corner_zone(rr + 0.5, cc + 0.5)
                dist = np.hypot((us - mu) * AW, (vs - mv) * AH)
                i = int(np.argmax(depth[rr, cc] - 1e-4 * dist))
                cands.append((float(dist.min()), float(us[i]), float(vs[i])))
            _, au, av = min(cands)
            rec["at"] = (au, av)
            # its outline: the loops round its stretches (and holes), simplified
            lps = []
            for lp in loops(sub):
                if len(lp) < 2 * SMALL + 2: continue        # (a loop round one or two chunks)
                pts = thin_loop(lp, SIMPLIFY)
                if len(pts) < 3: continue
                lps.append("".join(enc(u) + enc(v) for u, v in (corner_zone(r, c) for r, c in pts)))
            rec["outline"] = " ".join(lps)
            outlined += 1
    if "at" not in rec:
        rec["at"] = (mu, mv)
        rec["indoor"] = True
        indoor += 1
    out_pieces[art][key] = rec

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write("-- Places to explore, for the map's \"Show places to explore\" (Map/Explore.lua): the game's \"Explore <zone>\"\n"
            "-- achievements, each an explored-area piece of its zone's map (Reveal.lua's \"w:h:x:y\").\n"
            "--   achievements[id] = { uiMapID, art }   (its name: the game's, GetAchievementInfo)\n"
            "--   pieces[art][\"w:h:x:y\"] = { achievement, { areaID, ... }, x, y, outline, indoor = true }\n"
            "--     x, y: where to go to explore it, on its zone's map (0..1): the middle of the ground that explores it\n"
            "--     outline: that ground's edges, loops split by spaces; each point two pairs of characters (A-Za-z0-9+/,\n"
            "--     base 64, high then low): n / 4095 * 1.25 - 0.125 across, then down. indoor: none of its ground is\n"
            "--     outdoors (a cave, a building): x, y is its piece's middle, and there's no outline\n"
            "-- Generated by tools/map-data/explore.py from the game's tables and terrain (build %s); regenerate rather than edit.\n\n" % BUILD)
    f.write("local _, ns = ...\n\nns.MapExplore = {\n\tachievements = {\n")
    for aid in sorted(achs):
        a = achs[aid]
        f.write("\t\t[%d] = { %d, %d },   -- %s\n" % (aid, a["map"], a["art"], a["title"]))
    f.write("\t},\n\tpieces = {\n")
    for art in sorted(out_pieces):
        f.write("\t\t[%d] = {\n" % art)
        for key, r in sorted(out_pieces[art].items()):
            f.write("\t\t\t[%s] = { %d, { %s }, %.4f, %.4f%s%s },   -- %s\n" % (
                lua_str(key), r["ach"], ", ".join(str(a) for a in r["areas"]), r["at"][0], r["at"][1],
                (", " + lua_str(r["outline"])) if r.get("outline") else "", ", indoor = true" if r.get("indoor") else "", r["name"]))
        f.write("\t\t},\n")
    f.write("\t},\n}\n")
print("explore: %d pieces outlined, %d indoor only; %s, %d bytes" % (outlined, indoor, os.path.relpath(OUT, clients.REPO), os.path.getsize(OUT)))
