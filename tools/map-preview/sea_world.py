# Bakes the world sea's own masks (Stitch.lua; run after sea.py, whose MapSeaMask it reads):
#   MapSeaOut/<id>   where each continent's open sea is drawn past the world art's edges:
#                    the continent art's open sea (MapSeaMask) inside its feathered edge
#                    (MapFeatherWide), only where the world art itself has faded out (1 - the
#                    world's MapFeatherWide), so the two meet without a seam. Blizzard's own
#                    sea art comes out past the world map this way: the continents' compass
#                    roses, ship and sea serpent.
#   MapSeaCoast/947  the world art's open sea off the coasts, where its hatching is (found
#                    as light / dark stripes down the art, as render.py's land_of does, and
#                    only near land, so the whirlpool's strokes stay out): it goes early, as
#                    its strokes would grow huge; MapSeaOpen/947 is the rest, which stays.
# usage: python -P tools/map-preview/sea_world.py <db2 dir> <texture cache>
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

here = os.path.dirname(os.path.abspath(__file__))
db2, cache = sys.argv[1:3]
sys.argv = ["render.py", db2, cache, os.path.join(cache, "_preview")]
g = {"__name__": "sea_outer", "__file__": os.path.join(here, "render.py")}
src = open(os.path.join(here, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)
TEX = g["TEXDIR"]
N = 256

def alpha(path):
    return np.asarray(Image.open(path).convert("RGBA").getchannel("A").resize((N, N), Image.BILINEAR)).astype(np.float32) / 255

feather = alpha(os.path.join(TEX, "MapFeatherWide.tga"))
os.makedirs(os.path.join(TEX, "MapSeaOut"), exist_ok=True)
for m in g["maps"]:
    if m["kind"] != 2: continue
    l, r, t, b = m["rect"]
    # each mask pixel's place on the world art (normalized), and the world's feather there
    f = (np.arange(N) + 0.5) / N
    u = l + f[None, :] * (r - l)
    v = t + f[:, None] * (b - t)
    world = ndimage.map_coordinates(feather, [v * N - 0.5 + 0 * u, u * N - 0.5 + 0 * v], order=1, mode="constant", cval=0)
    out = alpha(os.path.join(TEX, "MapSeaMask", "%d.tga" % m["id"])) * feather * (1 - world)
    a = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))
    Image.merge("RGBA", (Image.new("L", (N, N), 255),) * 3 + (a,)).save(os.path.join(TEX, "MapSeaOut", "%d.tga" % m["id"]))
    print("outer sea", m["id"], m["name"], "covers %.0f%%" % (100 * (out > 0.05).mean()))

# ---- the world art's sea: its coastal hatching, apart from the open sea
COAST_REACH = 45                # world art px off the land where hatching counts as the coast's
world = next(m for m in g["maps"] if m["id"] == 947)
art = g["base"](world)[..., :3]
L = art.mean(2)
dy = np.abs(np.diff(L, axis=0, prepend=L[:1]))
dx = np.abs(np.diff(L, axis=1, prepend=L[:, :1]))
stripe = ndimage.gaussian_filter(ndimage.gaussian_filter(dy, 4) - ndimage.gaussian_filter(dx, 4), 3)
hatch = ndimage.binary_opening(stripe > g["HATCH_STRIPE"], iterations=2)
# land: the continents (MapLand/947, sea.py's) and the islands: the art's most saturated
# parchment, in pieces clear of its frame (whose aged edge is as saturated)
from PIL import ImageFilter
land = np.asarray(Image.open(os.path.join(TEX, "MapLand", "947.tga")).getchannel("A").resize(L.shape[::-1], Image.BILINEAR)) > 128
img = Image.fromarray((art * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4))
sat = ndimage.binary_opening(np.asarray(img.convert("HSV")).astype(np.float32)[..., 1] / 255 > 0.65, iterations=2)
h_, w_ = sat.shape
lab, n = ndimage.label(sat)
for i_, sl in enumerate(ndimage.find_objects(lab), 1):
    clear = sl[0].start > h_ * .08 and sl[0].stop < h_ * .92 and sl[1].start > w_ * .08 and sl[1].stop < w_ * .92
    if clear and (lab[sl] == i_).sum() >= 400: land |= lab == i_
near = ndimage.distance_transform_edt(~land) < COAST_REACH
coast = ndimage.binary_dilation(hatch & near, iterations=4) & near
coast = np.clip(ndimage.gaussian_filter(coast.astype(np.float32), 4) * 1.4, 0, 1)
coast = np.asarray(Image.fromarray((coast * 255).astype(np.uint8)).resize((N, N), Image.LANCZOS)).astype(np.float32) / 255
sea = alpha(os.path.join(TEX, "MapSeaMask", "947.tga"))
for name, part in (("MapSeaCoast", sea * coast), ("MapSeaOpen", sea * (1 - coast))):
    os.makedirs(os.path.join(TEX, name), exist_ok=True)
    a = Image.fromarray((np.clip(part, 0, 1) * 255).astype(np.uint8))
    Image.merge("RGBA", (Image.new("L", (N, N), 255),) * 3 + (a,)).save(os.path.join(TEX, name, "947.tga"))
print("world sea: coast %.0f%% of its sea" % (100 * (sea * coast).sum() / max(1, sea.sum())))
