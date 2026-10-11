# Bakes what a city that comes in early (Orgrimmar) needs to sit in its zone's map:
#   MapBanner/<city uiMapID>.tga    the zone map's name banner for it ("ORGRIMMAR" on Durotar's),
#                                   cut from the zone's own overlay art, so Stitch.lua can keep
#                                   it over the city's map while the city fades in under it
#   MapBannerHole/<zone uiMapID>.tga  the zone's art without it (Stitch.lua draws the zone's own
#                                   art through this: the copy is the banner, so once you're
#                                   close it can go, leaving none of the zone's round the city)
#   MapCityMask/<city uiMapID>.tga  the city's own map cut down to the city (its plan, not the
#                                   blank parchment round it, which would cover the zone's
#                                   painting of the land about it), and its own name banner
#                                   where CITY_TITLES has it (its title up close)
# The cuts are traced by hand on the art (BANNERS, CITIES, CITY_TITLES: in its 1002 x 668 pixels),
# softened at the edge.
# usage: python -P tools/map-preview/banners.py <db2 dir> <texture cache>
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

here = os.path.dirname(os.path.abspath(__file__))
db2, cache = sys.argv[1:3]
sys.argv = ["render.py", db2, cache, os.path.join(cache, "_preview")]
g = {"__name__": "banners", "__file__": os.path.join(here, "render.py")}
src = open(os.path.join(here, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)
TEX = g["TEXDIR"]

# city -> its zone, and the banner's outline on the zone's art: rectangles and polygons
BANNERS = {
    "Orgrimmar": ("Durotar", [
        ("rect", (352, 10, 584, 55)),                                       # the plate
        ("poly", [(354, 24), (318, 26), (292, 30), (279, 40), (279, 54), (286, 66), (298, 74),
                  (310, 72), (306, 62), (318, 58), (354, 55)]),            # the left scroll end
        ("poly", [(582, 24), (620, 26), (648, 30), (661, 40), (662, 56), (656, 70), (646, 77),
                  (640, 72), (646, 62), (640, 55), (582, 55)]),            # the right one
    ]),    "Undercity": ("Tirisfal Glades", [
        ("rect", (540, 487, 696, 522)),                                     # the plate
        ("poly", [(541, 499), (520, 500), (500, 505), (489, 513), (487, 524), (492, 532),
                  (500, 535), (505, 528), (513, 521), (541, 521)]),        # the left scroll end
        ("poly", [(695, 499), (716, 500), (736, 505), (747, 513), (750, 524), (745, 532),
                  (737, 535), (731, 528), (723, 521), (695, 521)]),        # the right one
    ]),
}
# city -> its plan's outline on its own art: the valleys, the Drag and the gate (its banner, top
# left, is CITY_TITLES'; not the Horde emblem, bottom right)
CITIES = {
    "Orgrimmar": [(300, 205), (430, 200), (560, 172), (610, 80), (700, 30), (800, 40), (845, 120),
                  (830, 250), (760, 300), (655, 340), (630, 420), (600, 500), (575, 560), (575, 662),
                  (440, 662), (440, 600), (330, 618), (240, 565), (200, 515), (120, 505), (85, 420),
                  (125, 330), (230, 340), (320, 300)],
    # the ring and its quarters, the Ruins above, the Sewers (its banner, top left, is
    # CITY_TITLES'; not the Forsaken emblem, bottom left)
    "Undercity": [(120, 200), (170, 165), (300, 165), (350, 140), (430, 135), (430, 60), (470, 50),
                  (560, 45), (580, 35), (740, 35), (760, 55), (850, 55), (905, 95), (905, 200),
                  (870, 260), (880, 380), (910, 440), (900, 520), (830, 530), (760, 470), (660, 480),
                  (620, 520), (630, 600), (595, 625), (525, 625), (470, 610), (430, 560), (420, 470),
                  (420, 400), (450, 330), (400, 290), (330, 250), (270, 320), (170, 330), (110, 280)],
}
# city -> its own name banner's outline on its own art, kept in its cut: up close it's the city's
# title, and its zone's banner for it (MapBanner, bigger, over the city) goes as the city comes in
CITY_TITLES = {
    "Orgrimmar": [(218, 160), (240, 152), (298, 150), (298, 140), (527, 140), (527, 150), (560, 154),
                  (566, 168), (556, 180), (527, 190), (300, 193), (252, 199), (226, 196), (215, 180)],
    "Undercity": [(30, 95), (45, 84), (108, 80), (108, 63), (338, 63), (338, 80), (400, 84), (415, 95),
                  (412, 118), (395, 129), (338, 119), (110, 119), (50, 129), (32, 118)],
}
CITY_SOFT = 50                  # art px over which a city's cut fades (out from its outline: the plan stays whole)
TITLE_FRAME = (10, 28)          # art px from the art's edge where a kept banner's cut is gone / whole (its torn frame)

def pow2(n):
    p = 16
    while p < n: p *= 2
    return p

os.makedirs(os.path.join(TEX, "MapBanner"), exist_ok=True)
os.makedirs(os.path.join(TEX, "MapCityMask"), exist_ok=True)
os.makedirs(os.path.join(TEX, "MapBannerHole"), exist_ok=True)
by_name = {m["name"]: m for m in g["maps"]}
rows = []
for city, (zone, shapes) in BANNERS.items():
    c, z = by_name[city], by_name[zone]
    art = (np.clip(g["overlay_canvas"](z["art"]), 0, 1) * 255).astype(np.uint8)
    mask = Image.new("L", (1002, 668), 0)
    d = ImageDraw.Draw(mask)
    for kind, shape in shapes:
        if kind == "rect": d.rectangle(shape, fill=255)
        else: d.polygon(shape, fill=255)
    mask = np.asarray(mask.filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    mask *= art[..., 3] / 255.0                         # (only where the overlay art is)
    hole = Image.fromarray(((1 - mask) * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS)
    Image.merge("RGBA", (Image.new("L", (256, 256), 255),) * 3 + (hole,)).save(os.path.join(TEX, "MapBannerHole", "%d.tga" % z["id"]))
    ys, xs = np.nonzero(mask > 0.01)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    w, h = pow2(x1 - x0), pow2(y1 - y0)
    out = np.zeros((h, w, 4), np.uint8)
    out[: y1 - y0, : x1 - x0, :3] = art[y0:y1, x0:x1, :3]
    out[: y1 - y0, : x1 - x0, 3] = (mask[y0:y1, x0:x1] * 255).astype(np.uint8)
    Image.fromarray(out, "RGBA").save(os.path.join(TEX, "MapBanner", "%d.tga" % c["id"]))
    rows.append((c["id"], z["id"], x0, y0, w, h, city))
    print("banner", city, "on", zone, "at", (int(x0), int(y0)), "size", (w, h))

def soft_cut(poly):
    """an outline filled, grown and blurred: whole inside, fading out over CITY_SOFT past it"""
    mask = Image.new("L", (1002, 668), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    mask = mask.filter(ImageFilter.MaxFilter(2 * (CITY_SOFT // 3) + 1))     # (grown, so the fade starts outside it)
    return np.asarray(mask.filter(ImageFilter.GaussianBlur(CITY_SOFT / 3))).astype(np.float32)

# a banner near the art's edge (Undercity's): its cut fades out inside the art's torn frame, not at
# the art's rectangle (a straight line)
ys_, xs_ = np.mgrid[0:668, 0:1002]
from_edge = np.minimum(np.minimum(xs_, 1001 - xs_), np.minimum(ys_, 667 - ys_)).astype(np.float32)
INSIDE_FRAME = np.clip((from_edge - TITLE_FRAME[0]) / (TITLE_FRAME[1] - TITLE_FRAME[0]), 0, 1)

cut = []
for city, poly in CITIES.items():
    c = by_name[city]
    m_ = soft_cut(poly)
    if city in CITY_TITLES: m_ = np.maximum(m_, soft_cut(CITY_TITLES[city]) * INSIDE_FRAME)
    mask = Image.fromarray(np.clip(m_ + 0.5, 0, 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS)
    Image.merge("RGBA", (Image.new("L", (256, 256), 255),) * 3 + (mask,)).save(os.path.join(TEX, "MapCityMask", "%d.tga" % c["id"]))
    cut.append((c["id"], city))
    print("city cut", city)

with open(os.path.join(g["REPO"], "OpenMap", "Data", "Banners.lua"), "w", encoding="utf-8", newline="\n") as fh:
    fh.write("-- City banners: [city uiMapID] = { zone uiMapID, x, y, width, height }: the zone's name banner for\n")
    fh.write("-- the city, at (x, y) in the zone's art pixels, in Media/Textures/MapBanner/<city> (width x height).\n")
    fh.write("-- Generated by tools/map-preview/banners.py; regenerate rather than edit.\n\nlocal _, ns = ...\n\nns.MapBanners = {\n")
    for cid, zid, x0, y0, w, h, city in rows:
        fh.write("\t[%d] = { %d, %d, %d, %d, %d },   -- %s\n" % (cid, zid, x0, y0, w, h, city))
    fh.write("}\n\n-- zones whose own art is drawn without that banner (Media/Textures/MapBannerHole/<zone>)\nns.MapBannerHoles = {\n")
    for cid, zid, x0, y0, w, h, city in rows:
        fh.write("\t[%d] = true,   -- (%s's banner)\n" % (zid, city))
    fh.write("}\n\n-- cities whose own map is cut down to the city (Media/Textures/MapCityMask/<city>)\nns.MapCityCuts = {\n")
    for cid, city in cut:
        fh.write("\t[%d] = true,   -- %s\n" % (cid, city))
    fh.write("}\n\n-- ... and whose cut keeps their own name banner: their zone's banner for them goes as they come in\nns.MapCityTitles = {\n")
    for cid, city in cut:
        if city in CITY_TITLES: fh.write("\t[%d] = true,   -- %s\n" % (cid, city))
    fh.write("}\n")
