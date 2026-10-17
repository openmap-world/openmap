# Brings the filled gaps into the addon. For each art-drawn/gaps/<region>.png (a fill of a gap region
# of art-drawn/gaps/regions.json, painted by hand on the plates gapregions.py exports to source/):
#   1. lined up with the region's zone art: scale and offset (a fill can come back at another
#      size or framing), found by matching the zone art's edges and kept in fits.json,
#      so it's found once (delete a region's entry to find it again)
#   2. cut to the region's fill area (source/<region>_fill.png: the continent's land the zone maps
#      don't fully cover, and a little sea past its coast, less Blizzard's own classic maps), faded
#      out over its own edge where it stops short of the region's
#   3. written as 256-px tiles at up to MAX_PX px a world unit (only those it shows anything in) to
#      OpenMap/Media/Textures/MapGapFill/<Gnn>_<tile>.tga, listed in OpenMap/Data/GapFills.lua
# Run gapregions.py first (it writes source/: each region's zone art and fill area).
# Stitch.lua draws them over the gaps' paper and under every zone map; render.py previews them.
#
# usage: python -P tools/map-preview/gapfills.py
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage, optimize

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
EDITED = os.path.join(root, "art-drawn", "gaps")
SRC = os.path.join(EDITED, "source")
OUT = os.path.join(root, "OpenMap", "Media", "Textures", "MapGapFill")
LUA = os.path.join(root, "OpenMap", "Data", "GapFills.lua")
TILE = 256
FRAME_FADE = 40                 # region px a fill fades out over at its own edge (inside the region)
BOX_FADE = 3                    # world units a fill fades out over towards its region's own edge (where the gap
                                #  runs on past it, unpainted yet: no hard line; a neighbour's fill overlaps it)
COAST_KEEP = 8                  # world units past the fill area that a painted coastline is kept out to, into the sea
COAST_DIFF = 0.04               # how much a painting must differ from the map as it was to count as painted there
MAX_PX = 10                     # px a world unit at most, as written: about the zone maps' own at the zooms
                                #  the gaps show at (closer in, the minimap mixes in over them); finer is only size


def load(p, mode):
    return np.asarray(Image.open(p).convert(mode)).astype(np.float32) / 255


def grad(rgb):
    g = ndimage.gaussian_filter(rgb.mean(axis=2), 1.5)
    return np.hypot(ndimage.sobel(g, 0), ndimage.sobel(g, 1))


def sample(p, img, yy, xx):
    """the fill at region px (yy, xx): region = s * fill + t"""
    sx, sy, tx, ty = p
    return ndimage.map_coordinates(img, [(yy - ty) / sy, (xx - tx) / sx], order=1, mode="nearest")


def fit(F, Z, start):
    """the fill's scale and offset on the region, by its edges against the zone art's"""
    fitmask = ndimage.binary_erosion(Z[..., 3] > 0.95, iterations=8)
    ys, xs = np.nonzero(fitmask)
    if len(ys) < 500: return start, 0.0
    pick = np.random.default_rng(1).choice(len(ys), min(60000, len(ys)), replace=False)
    ys, xs = ys[pick].astype(np.float32), xs[pick].astype(np.float32)
    gz, gf = grad(Z[..., :3]), grad(F[..., :3])
    tgt = gz[ys.astype(int), xs.astype(int)]
    tgt = (tgt - tgt.mean()) / tgt.std()

    def cost(p):
        v = sample(p, gf, ys, xs)
        v = (v - v.mean()) / (v.std() + 1e-6)
        return -np.mean(v * tgt)
    p0 = np.array(start, dtype=float)
    r = optimize.minimize(cost, p0, method="Nelder-Mead", options={"xatol": 0.01, "fatol": 1e-5, "maxiter": 800,
        "initial_simplex": [p0, p0 * [1.01, 1, 1, 1], p0 * [1, 1.01, 1, 1], p0 + [0, 0, 4, 0], p0 + [0, 0, 0, 4]]})
    return [float(v) for v in r.x], float(-r.fun)


man = {e["file"][:-4]: e for e in json.load(open(os.path.join(EDITED, "regions.json")))}
fp = os.path.join(EDITED, "fits.json")
fits = json.load(open(fp, encoding="utf-8")) if os.path.exists(fp) else {}
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith(".tga"): os.remove(os.path.join(OUT, f))
listing = []
for f in sorted(os.listdir(EDITED)):
    stem = f[:-4]
    if not f.endswith(".png") or stem not in man: continue
    e = man[stem]
    W, H = e["size"]
    F = load(os.path.join(EDITED, f), "RGBA")
    Z = load(os.path.join(SRC, stem + ".png"), "RGBA")
    mask = load(os.path.join(SRC, stem + "_fill.png"), "L")
    fh, fw = F.shape[:2]
    if stem in fits:
        p = fits[stem]["fit"]
    else:
        start = [1.0, 1.0, 0.0, 0.0] if (fw, fh) == (W, H) else [W / fw, H / fh, 0.0, 0.0]
        p, score = fit(F, Z, start)
        fits[stem] = {"fit": p, "match": round(score, 3)}
        print("  fitted", stem, [round(v, 3) for v in p], "match %.2f" % score)
    sx, sy, tx, ty = p
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rgb = np.dstack([sample(p, F[..., c], yy, xx) for c in range(3)])
    own = sample(p, F[..., 3], yy, xx)
    # fading out over its own edge where that's inside the region (and towards the region's: BOX_FADE)
    x0, x1, y0, y1 = tx, tx + sx * (fw - 1), ty, ty + sy * (fh - 1)
    dist = np.full((H, W), 1e9, np.float32)
    if x0 > 3: dist = np.minimum(dist, xx - x0)
    if x1 < W - 4: dist = np.minimum(dist, x1 - xx)
    if y0 > 3: dist = np.minimum(dist, yy - y0)
    if y1 < H - 4: dist = np.minimum(dist, y1 - yy)
    inside = np.clip(dist / FRAME_FADE, 0, 1) * ((xx >= x0 - 1) & (xx <= x1 + 1) & (yy >= y0 - 1) & (yy <= y1 + 1))
    a = np.clip(mask, 0, 1) * inside * own
    to_box = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy))
    box_fade = np.clip(to_box / (BOX_FADE * e["pxPerUnit"]), 0, 1)
    box_fade = box_fade * box_fade * (3 - 2 * box_fade)
    a = a * box_fade
    # the painter's coastline and shallows past the fill area, out into the open sea (source/_sea.png:
    # no land, no zone art): what the painting changed there from how the map looked (source/_now.png),
    # joined to the fill area and within COAST_KEEP of it, specks left out
    sea_p = os.path.join(SRC, stem + "_sea.png")
    if os.path.exists(sea_p):
        sea = load(sea_p, "L") > 0.5
        now = load(os.path.join(SRC, stem + "_now.png"), "RGB")
        changed = ndimage.gaussian_filter(np.abs(rgb - now).mean(axis=2), 2) > COAST_DIFF
        near = ndimage.distance_transform_edt(mask < 0.5) <= COAST_KEEP * e["pxPerUnit"]
        coast = ndimage.binary_opening(changed & sea & near, iterations=2)
        lab, _ = ndimage.label(coast | (mask > 0.5))
        coast &= np.isin(lab, np.unique(lab[mask > 0.5]))
        coast = ndimage.gaussian_filter(ndimage.binary_dilation(coast, iterations=2).astype(np.float32), 1.5)
        a = np.maximum(a, np.clip(coast, 0, 1) * inside * own * box_fade)
        print("  coastline past the fill area kept: %.1f%% of the region" % (100 * float((coast > 0.5).mean())))
    k = min(1.0, MAX_PX / e["pxPerUnit"])
    if k < 1:
        W, H = max(1, round(W * k)), max(1, round(H * k))
        rgb = np.dstack([np.asarray(Image.fromarray((rgb[..., c] * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)).astype(np.float32) / 255 for c in range(3)])
        a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    cols, rows = -(-W // TILE), -(-H // TILE)
    num = stem[:3]
    tiles = []
    for j in range(rows):
        for i in range(cols):
            ys, xs = slice(j * TILE, min(H, (j + 1) * TILE)), slice(i * TILE, min(W, (i + 1) * TILE))
            ta = a[ys, xs]
            if ta.max() < 0.01: continue
            t = np.zeros((TILE, TILE, 4), np.float32)
            h_, w_ = ta.shape
            t[:h_, :w_, :3] = rgb[ys, xs]           # (its colour under clear pixels too: no dark fringe when filtered)
            t[:h_, :w_, 3] = ta
            Image.fromarray((np.clip(t, 0, 1) * 255).round().astype(np.uint8), "RGBA").save(
                os.path.join(OUT, "%s_%d.tga" % (num, j * cols + i + 1)), rle=True)
            tiles.append(j * cols + i + 1)
    listing.append((num, stem, e["world"], W, H, cols, tiles))
    print(stem, "%d of %d tiles" % (len(tiles), cols * rows), flush=True)
json.dump(dict(sorted(fits.items())), open(fp, "w", encoding="utf-8", newline="\n"), indent=1)
with open(LUA, "w", encoding="utf-8", newline="\n") as fh_:
    fh_.write("-- Filled gaps: fills of land no zone map covers, painted by hand (art-drawn/gaps), drawn by\n")
    fh_.write("-- Stitch.lua over the gaps' paper, under every zone. Each: its tiles' prefix (MapGapFill/<Gnn>_<tile>),\n")
    fh_.write("-- its box on the world (normalized: left, top, right, bottom), its size in px, its columns of\n")
    fh_.write("-- 256-px tiles, and the tiles drawn (row-major, from 1).\n")
    fh_.write("-- Generated by tools/map-preview/gapfills.py; regenerate rather than edit.\n\n")
    fh_.write("local _, ns = ...\n\nns.MapGapFills = {\n")
    for num, stem, world, W, H, cols, tiles in listing:
        fh_.write("\t{ \"%s\", { %s }, %d, %d, %d, { %s } },   -- %s\n" % (num, ", ".join("%.6f" % v for v in world), W, H, cols,
                  ", ".join(str(t) for t in tiles), stem[4:]))
    fh_.write("}\n")
size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
print("ok: %d fills, %d tiles, %.1f MB" % (len(listing), sum(len(x[6]) for x in listing), size / 1e6))
