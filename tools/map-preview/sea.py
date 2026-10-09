# Bakes the ocean's textures from Blizzard's own continent art (no drawn imagery):
#   MapSea.tga           a seamless tile of the open sea's mottled parchment (the Forbidding
#                        Sea, east of the Eastern Kingdoms), its colour moved to the sea
#                        colour Stitch.lua fills with (SEA), so it only adds texture
#   MapHatch.tga         a seamless tile of the coastal wave strokes (the hatched band off
#                        Kalimdor's east coast): the strokes' ink as alpha, in their colour
#   MapCoast/<id>.tga    each continent's coastal band (sea within reach of its land),
#                        where the strokes are drawn: only coasts no zone paints its own
#                        sea along (Stitch.lua shows the zone's own there)
# Prints the tiles' sizes in continent-art pixels (Stitch.lua's SEA_TILE, HATCH_TILE).
# usage: python -P tools/map-preview/sea.py <db2 dir> <texture cache>
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

here = os.path.dirname(os.path.abspath(__file__))
db2, cache = sys.argv[1:3]
sys.argv = ["render.py", db2, cache, os.path.join(cache, "_preview")]
g = {"__name__": "sea", "__file__": os.path.join(here, "render.py")}
src = open(os.path.join(here, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)
TEX, SEA = g["TEXDIR"], np.array(g["SEA"], np.float32)
art = {m["id"]: g["base"](m)[..., :3] for m in g["maps"] if m["id"] in (1414, 1415)}

def wrap(a, kx, ky, detail=False):
    """a crop made to tile: its last kx columns / ky rows crossfaded into its first.
    `detail` (zero-mean texture): the crossfade keeps its contrast, so no faint band"""
    h, w = a.shape[:2]
    a = a.copy()
    def mix(x, y, r):
        m = x * (1 - r) + y * r
        return m / np.sqrt((1 - r) ** 2 + r ** 2) if detail else m
    if kx:
        r = np.linspace(0, 1, kx + 2)[1:-1].reshape((1, kx) + (1,) * (a.ndim - 2))
        a[:, :kx] = mix(a[:, w - kx:], a[:, :kx], r)
        a = a[:, :w - kx]
    if ky:
        r = np.linspace(0, 1, ky + 2)[1:-1].reshape((ky, 1) + (1,) * (a.ndim - 2))
        a[:ky] = mix(a[h - ky:], a[:ky], r)
        a = a[:h - ky]
    return a

FIELD_VARIATION = 0.35          # how much of the sea colour's own variation is kept
SEA_CONTRAST = 0.17             # alpha per unit of mottling (~ the art's own contrast at full strength)

# ---- the sea: from the client's one high-resolution map, the 3840 x 2560 overview of the
# Eastern Kingdoms (interface/worldmap/easternkingdoms/easternkingdoms1..150: unused by any
# map in this build), about four times as fine as the classic art. A 512 px patch of its open
# sea (clear of its lettering, compass and serpents): its orange hatching (retail's style,
# and it would repeat with the tile) painted out from around it, only the fine crackle and
# mottling kept, made to tile, at the classic art's scale (512 px ~ 128 continent px)
HD_FIRST, HD_COLS = 2353944, 15            # its tiles' file IDs are given in name order
HD_PATCH = (3020, 1460, 512)               # x, y, size in its pixels
def hd_patch():
    x0, y0, n = HD_PATCH
    ids = {k: HD_FIRST + i for i, k in enumerate(sorted(range(1, 151), key=str))}
    out = np.zeros((n, n, 3), np.float32)
    for row in range(y0 // 256, (y0 + n - 1) // 256 + 1):
        for col in range(x0 // 256, (x0 + n - 1) // 256 + 1):
            im = g["fetch"](ids[row * HD_COLS + col + 1])
            t = np.asarray(im.convert("RGB")).astype(np.float32) / 255
            ty0, tx0 = row * 256, col * 256
            ys, xs = max(y0, ty0), max(x0, tx0)
            ye, xe = min(y0 + n, ty0 + 256), min(x0 + n, tx0 + 256)
            out[ys - y0:ye - y0, xs - x0:xe - x0] = t[ys - ty0:ye - ty0, xs - tx0:xe - tx0]
    return out

patch = hd_patch()
# the orange streaks: warmer than around them, and long across: filled from their surroundings,
# with mottling from a little way off so the fill isn't smooth
warm = patch[..., 0] - patch[..., 2]
hband = ndimage.uniform_filter1d(warm - ndimage.gaussian_filter(warm, 12), 41, axis=1)
streak = ndimage.binary_dilation(hband > 0.035, iterations=3)
keep = (~streak).astype(np.float32)
fill = np.dstack([ndimage.gaussian_filter(patch[..., c] * keep, 6, mode="wrap") for c in range(3)]) / np.maximum(ndimage.gaussian_filter(keep, 6, mode="wrap"), 1e-3)[..., None]
fine = patch - np.dstack([ndimage.gaussian_filter(patch[..., c], 6, mode="wrap") for c in range(3)])
patch = np.where(streak[..., None], fill + np.roll(fine, 23, axis=0), patch)
broad = np.dstack([ndimage.gaussian_filter(patch[..., c], 9, mode="wrap") for c in range(3)])   # (only the fine crackle: broader shades show the tile repeating)
detail = (patch - broad).mean(2)
sd = detail.std()
detail = np.clip(detail, -2.2 * sd, 2.2 * sd)               # the odd ink spot evened out, or it repeats with the tile
# the painted-out streaks leave rows a shade lighter or darker: each row's (and column's)
# own average taken out, so no line repeats with the tile
detail = detail - ndimage.uniform_filter1d(detail.mean(1, keepdims=True), 3, axis=0)
detail = detail - detail.mean(0, keepdims=True)
tile = wrap(detail[..., None], 64, 64, detail=True)[..., 0]
tile = tile / tile.std()                                     # (unit contrast)
TILE_PX = 512
SEA_CONTRAST = 0.11                                          # (finer than the old tile: lighter, or it reads as noise)
# as two overlays the game lays over the sea's colour field (MapSeaField), so they add the
# paper's mottling without changing its colour: darker flecks (dark ink, alpha = how dark)
# and lighter ones
for name, sign, rgb in (("MapSeaDark", -1, (0.22, 0.22, 0.18)), ("MapSeaLight", 1, (0.86, 0.84, 0.74))):
    a = np.clip(sign * tile * SEA_CONTRAST, 0, 1)
    al = Image.fromarray((a * 255).astype(np.uint8)).resize((TILE_PX, TILE_PX), Image.LANCZOS)
    Image.merge("RGBA", tuple(Image.new("L", (TILE_PX, TILE_PX), int(c * 255)) for c in rgb) + (al,)).save(os.path.join(TEX, name + ".tga"))
print("SEA_TILE", 128, "continent px (from", tile.shape[1], "px of the 4K map)")
if os.path.exists(os.path.join(TEX, "MapSea.tga")): os.remove(os.path.join(TEX, "MapSea.tga"))

# ---- the strokes: off Kalimdor's east coast, between the shore and the open sea. Ink is
# darker than the sea paper around it; the tile's height is a whole number of
# strokes (the rows' own period), so it wraps without doubled lines
k = art[1414]
box = k[440:560, 607:651]
Lum = box.mean(2)
paper = ndimage.percentile_filter(Lum, 85, size=(7, 9))
ink = np.clip((paper - Lum) / 0.12, 0, 1)
ink = ndimage.uniform_filter1d(ink, 5, axis=1)             # along the strokes: whole lines, not the paper's speckle
ink = np.clip((ink - 0.3) / 0.4, 0, 1)
prof = ink.mean(1) - ink.mean()
best = max(range(60, 86), key=lambda p: float(np.dot(prof[:len(prof) - p], prof[p:]) / (len(prof) - p)))
ink = ink[:best + 4]
color = (box[:best + 4][ink > 0.6].mean(0)) if (ink > 0.6).any() else np.array([0.36, 0.24, 0.14])
tile = wrap(ink, 10, 4)
th, tw = tile.shape
im = Image.fromarray((np.clip(tile, 0, 1) * 255).astype(np.uint8)).resize((128, 256), Image.LANCZOS)
Image.merge("RGBA", tuple(Image.new("L", (128, 256), int(c * 255)) for c in color) + (im,)).save(os.path.join(TEX, "MapHatch.tga"))
print("HATCH_TILE", tw, "x", th, "continent px; ink colour", color.round(3), "coverage", round(float(tile.mean()), 3))

# ---- the coastal bands: full a few pixels off the shore, gone ~36 continent px out
os.makedirs(os.path.join(TEX, "MapCoast"), exist_ok=True)
for m in g["maps"]:
    if m["kind"] != 2: continue
    land = g["land_of"](m) > 0.5
    d = ndimage.distance_transform_edt(~land)
    band = np.clip(1 - (d - 6) / 30, 0, 1) * np.clip((d - 1) / 3, 0, 1)
    band = ndimage.gaussian_filter(band * band * (3 - 2 * band), 2)
    # not where a zone paints its own coastal sea (Blizzard's finer hatching is there)
    cover = np.zeros_like(band)
    l, r, t, b = m["rect"]
    for z in g["zones"]:
        zl, zr, zt, zb = z["rect"]
        if zr < l or zl > r or zb < t or zt > b: continue
        sh = g["shore"](z)
        x0, y0, w_, h_ = (zl - l) / (r - l) * 1002, (zt - t) / (b - t) * 668, (zr - zl) / (r - l) * 1002, (zb - zt) / (b - t) * 668
        X0, Y0, X1, Y1 = max(0, int(x0)), max(0, int(y0)), min(1002, int(x0 + w_) + 1), min(668, int(y0 + h_) + 1)
        if X1 <= X0 or Y1 <= Y0: continue
        ys_ = ((np.arange(Y0, Y1) + 0.5 - y0) / h_ * 668 - 0.5)[:, None].repeat(X1 - X0, 1)
        xs_ = ((np.arange(X0, X1) + 0.5 - x0) / w_ * 1002 - 0.5)[None, :].repeat(Y1 - Y0, 0)
        cover[Y0:Y1, X0:X1] = np.maximum(cover[Y0:Y1, X0:X1], ndimage.map_coordinates(sh, [ys_, xs_], order=1, cval=0))
    band = band * (1 - np.clip(ndimage.gaussian_filter(cover, 2) * 1.6, 0, 1))
    a = Image.fromarray((band * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS)
    Image.merge("RGBA", (Image.new("L", (256, 256), 255),) * 3 + (a,)).save(os.path.join(TEX, "MapCoast", "%d.tga" % m["id"]))
    print("coast", m["id"], m["name"])

# ---- the backdrop art's two parts (Stitch.PlaceBackdrop): its land with its coastal band
# (MapBackLand/<id>: Blizzard's shallow-water halo and hatching, kept with the land) and its
# open sea (MapSeaMask/<id>: the rest, faded out early with its sea lettering). For the
# world art, the continents' masks placed where each continent sits on it
def name_ink(m, land):
    """the continent's big lettering where it runs off the land into the sea ("Kalimdor",
    "Eastern Kingdoms" ...): thin dark strokes, letter-sized, in rows"""
    L = g["base"](m)[..., :3].mean(2)
    ink = (ndimage.grey_closing(L, size=(7, 7)) - L > 0.08) & (land < 0.5)
    lab, n = ndimage.label(ink)
    boxes = ndimage.find_objects(lab)
    cand = [(i, (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2, sl[0].stop - sl[0].start)
            for i, sl in enumerate(boxes, 1) if 10 <= sl[0].stop - sl[0].start <= 48 and 3 <= sl[1].stop - sl[1].start <= 50]
    hit = np.zeros(L.shape, bool)
    for i, cy, cx, h in cand:
        if sum(1 for j, y2, x2, h2 in cand if j != i and abs(y2 - cy) < h * 0.6 and abs(x2 - cx) < h * 5) >= 1:
            hit |= lab == i
    return np.clip(ndimage.gaussian_filter(ndimage.binary_dilation(hit, iterations=6).astype(np.float32), 2) * 1.5, 0, 1)

COAST_KEEP = (14, 26)           # continent art px off the land where the kept coastal band is full / gone
for d_ in ("MapSeaMask", "MapBackLand"):
    os.makedirs(os.path.join(TEX, d_), exist_ok=True)
def save_masks(keep, mid):
    for d_, a_ in (("MapBackLand", keep), ("MapSeaMask", 1 - keep)):
        im = Image.fromarray((np.clip(a_, 0, 1) * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS)
        Image.merge("RGBA", (Image.new("L", (256, 256), 255),) * 3 + (im,)).save(os.path.join(TEX, d_, "%d.tga" % mid))
world_keep = np.zeros((668, 1002), np.float32)
world_land = np.zeros((668, 1002), np.float32)
def place_on_world(dst, piece, m):
    l, r, t, b = m["rect"]
    box = (int(round(l * 1002)), int(round(t * 668)), int(round(r * 1002)), int(round(b * 668)))
    pc = np.asarray(Image.fromarray((piece * 255).astype(np.uint8)).resize((box[2] - box[0], box[3] - box[1]), Image.BILINEAR)).astype(np.float32) / 255
    x0, y0, x1, y1 = max(0, box[0]), max(0, box[1]), min(1002, box[2]), min(668, box[3])   # (rects run past the world's edge)
    dst[y0:y1, x0:x1] = np.maximum(dst[y0:y1, x0:x1], pc[y0 - box[1]:y1 - box[1], x0 - box[0]:x1 - box[0]])
for m in g["maps"]:
    if m["kind"] != 2: continue
    land = g["field_img"](m)[..., 3]
    land = ndimage.gaussian_filter(np.clip(land * 1.5, 0, 1), 1.5)     # (a touch past the coast)
    d = ndimage.distance_transform_edt(land < 0.5)
    band = np.clip(1 - (d - COAST_KEEP[0]) / (COAST_KEEP[1] - COAST_KEEP[0]), 0, 1)
    band = band * band * (3 - 2 * band) * (1 - name_ink(m, land))
    keep = np.maximum(land, band)
    save_masks(keep, m["id"])
    place_on_world(world_keep, keep, m)
    place_on_world(world_land, land, m)
    print("sea mask", m["id"], m["name"])
save_masks(world_keep, 947)
a = Image.fromarray((np.clip(world_land, 0, 1) * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS)
Image.merge("RGBA", (Image.new("L", (256, 256), 255),) * 3 + (a,)).save(os.path.join(TEX, "MapLand", "947.tga"))   # (the world art's land, as a mask)
print("sea mask 947 world")

# ---- the sea's colour field: the world / continent art's own sea, ink and lettering left
# out, smoothed (the zone maps' painted sea and our mottling go over it)
os.makedirs(os.path.join(TEX, "MapSeaField"), exist_ok=True)
def pushpull(c, w):
    h, wd = w.shape
    if min(h, wd) < 4:
        m = (c * w[..., None]).sum((0, 1)) / max(float(w.sum()), 1e-6)
        return np.broadcast_to(m, c.shape).astype(np.float32).copy()
    H2, W2 = (h + 1) // 2, (wd + 1) // 2
    cp = np.zeros((H2 * 2, W2 * 2, 3), np.float32); wp = np.zeros((H2 * 2, W2 * 2), np.float32)
    cp[:h, :wd] = c * w[..., None]; wp[:h, :wd] = w
    cs, ws = cp.reshape(H2, 2, W2, 2, 3).sum((1, 3)), wp.reshape(H2, 2, W2, 2).sum((1, 3))
    low = pushpull(cs / np.maximum(ws, 1e-6)[..., None], np.minimum(ws, 1))
    up = ndimage.zoom(low, (2, 2, 1), order=1)[:h, :wd]
    up = np.pad(up, ((0, h - up.shape[0]), (0, wd - up.shape[1]), (0, 0)), mode="edge")
    return c * w[..., None] + up * (1 - w[..., None])
for m in g["maps"]:
    if m["id"] != 947 and m["kind"] != 2: continue
    a = g["base"](m)[..., :3].astype(np.float32)
    sea = np.asarray(Image.open(os.path.join(TEX, "MapSeaMask", "%d.tga" % m["id"])).convert("RGBA").getchannel("A").resize((1002, 668))).astype(np.float32) / 255
    L = a.mean(2)
    ink = L < ndimage.median_filter(L, 9) - 0.035                     # lettering, compass lines, wave strokes
    w = ((sea > 0.9) & ~ndimage.binary_dilation(ink, iterations=2) & (g["M_WIDE"] > 0.6)).astype(np.float32)
    field = pushpull(a * w[..., None], w)
    field = np.dstack([ndimage.gaussian_filter(field[..., c], 8) for c in range(3)])
    # its broad blotches (the world art's green-blue washes) evened out: a third of the way
    # from the sea's average colour, so the sea reads as one sea
    mean = field[w > 0].mean(0)
    field = mean + (field - mean) * FIELD_VARIATION
    Image.fromarray((np.clip(field, 0, 1) * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS).save(
        os.path.join(TEX, "MapSeaField", "%d.tga" % m["id"]))
    print("sea field", m["id"], m["name"], field[w > 0].mean(0).round(3))
