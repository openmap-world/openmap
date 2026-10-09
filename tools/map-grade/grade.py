# Colour matching for OpenMap's stitched world map.
# For each zone: composite its overlay pieces (the zone's land) into the 1002x668
# zone canvas; measure the mean colour of its border band (land within BAND_IN px
# of its outline: the border mountains, water excluded); derive multipliers that
# take that band to a shared palette at the zone's own brightness; and write a
# soft band mask (1 at the outline, fading BAND_IN px inward and BAND_OUT px
# outward) the map draws a corrected copy of the zone through. Also per zone:
#   MapTerritory  where its base art shows: its land and a little past it
#   MapCore       its interior (from CORE_IN px inside the outline), drawn again
#                 over the neighbours' parchment halos
# MapTerritory is then widened to any land in the zone's rectangle by
# tools/map-preview/render.py --bake-territory (it needs the continent art).
#
# usage: python -P tools/map-grade/grade.py <Reveal.lua> <tex dir> <out Grade.lua> <mask dir> <preview dir>
import re, sys, os, math
import numpy as np
from scipy import ndimage
from PIL import Image

reveal_path, tex_dir, out_lua, mask_dir, prev_dir = sys.argv[1:6]
os.makedirs(prev_dir, exist_ok=True)
os.makedirs(mask_dir, exist_ok=True)
tex_out = os.path.dirname(os.path.normpath(mask_dir))
terr_dir, core_dir = (os.path.join(tex_out, n) for n in ("MapTerritory", "MapCore"))
for d_ in (terr_dir, core_dir): os.makedirs(d_, exist_ok=True)
TILE, CW, CH = 256, 1002, 668
BAND_IN, BAND_OUT = 90, 50      # zone-canvas px
TERR_FULL, TERR_SOFT = 40, 60   # territory: full this far past the land, then fading over this
CORE_IN, CORE_SOFT = 30, 40     # interior: from this far inside the outline, fading in over this
UNDER_FULL, UNDER_SOFT = 80, 160  # underpaint: full this far past the land, then fading over this
STAT_BAND = 45                  # px inside the outline measured for the band colour
MASK = 128                      # mask texture size

src = open(reveal_path, encoding="utf-8").read()
zones = re.findall(r'--\[\[(\d+): ([^\]]+)\]\]\s*\n\s*\[(\d+)\] = \{(.*?)\},\n', src)

def load(fid):
    p = os.path.join(tex_dir, fid + ".blp")
    return Image.open(p).convert("RGBA") if os.path.exists(p) else None

def composite(pieces):
    canvas = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
    missing = 0
    for key, files in pieces:
        w, h, x, y = map(int, key.split(":"))
        ids = [f.strip() for f in files.split(",")]
        cols, rows = math.ceil(w / TILE), math.ceil(h / TILE)
        for j in range(rows):
            ph = TILE if j < rows - 1 else h - (rows - 1) * TILE
            for k in range(cols):
                idx = j * cols + k
                if idx >= len(ids): continue
                im = load(ids[idx])
                if im is None: missing += 1; continue
                pw = TILE if k < cols - 1 else w - (cols - 1) * TILE
                im = im.crop((0, 0, min(pw, im.width), min(ph, im.height)))
                layer = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
                layer.paste(im, (x + k * TILE, y + j * TILE))
                canvas = Image.alpha_composite(canvas, layer)
    return canvas, missing

def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)

def lum(c): return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]

def push_pull(rgba):
    # fills the transparent parts with the land's colours, spread smoothly outward
    a = rgba[..., 3:4]
    levels = [(rgba[..., :3] * a, a)]
    while min(levels[-1][1].shape[:2]) > 4:
        p, w = levels[-1]
        h2, w2 = p.shape[0] // 2 * 2, p.shape[1] // 2 * 2
        p, w = p[:h2, :w2], w[:h2, :w2]
        levels.append(((p[0::2, 0::2] + p[1::2, 0::2] + p[0::2, 1::2] + p[1::2, 1::2]) / 4,
                       (w[0::2, 0::2] + w[1::2, 0::2] + w[0::2, 1::2] + w[1::2, 1::2]) / 4))
    col = levels[-1][0] / np.maximum(levels[-1][1], 1e-4)
    for p, w in reversed(levels[:-1]):
        up = np.asarray(Image.fromarray(np.clip(col * 255, 0, 255).astype(np.uint8)).resize(
            (p.shape[1], p.shape[0]), Image.BILINEAR)).astype(np.float32) / 255
        k = np.clip(w * 4, 0, 1)
        col = p / np.maximum(w, 1e-4) * k + up * (1 - k)
    return col

def save_rgba(rgb, alpha, path):
    img = np.dstack([np.clip(rgb, 0, 1), np.clip(alpha, 0, 1)])
    Image.fromarray((img * 255).astype(np.uint8), "RGBA").resize((MASK, MASK), Image.LANCZOS).save(path)

def save_mask(values, path):
    # white, alpha = values, squeezed to MASK x MASK (the map stretches it over the zone's art)
    alpha = Image.fromarray((np.clip(values, 0, 1) * 255).astype(np.uint8)).resize((MASK, MASK), Image.LANCZOS)
    Image.merge("RGBA", (Image.new("L", (MASK, MASK), 255),) * 3 + (alpha,)).save(path)

results = []
for mapid, name, artid, body in zones:
    pieces = re.findall(r'\["([\d:]+)"\] = "([^"]+)"', body)
    img, missing = composite(pieces)
    if missing:
        print("%-24s missing %d tiles, skipped" % (name, missing)); continue
    a = np.asarray(img).astype(np.float32)
    land = a[..., 3] > 128
    land = ndimage.binary_closing(land, structure=np.ones((3, 3)), iterations=6)
    land = ndimage.binary_fill_holes(land)
    din = ndimage.distance_transform_edt(land)            # inside: px to the outline
    dout = ndimage.distance_transform_edt(~land)          # outside: px to the land
    band = np.where(land, smooth(1 - din / BAND_IN), smooth(1 - dout / BAND_OUT))
    terr = smooth(1 - np.maximum(0, dout - TERR_FULL) / TERR_SOFT)   # the zone's land and just past it
    core = smooth((din - CORE_IN) / CORE_SOFT)
    under_a = smooth(1 - np.maximum(0, dout - UNDER_FULL) / UNDER_SOFT)

    rgb = a[..., :3]
    sel = land & (din <= STAT_BAND) & (a[..., 3] > 200) & (rgb[..., 2] < rgb[..., 0])   # no water
    mean = rgb[sel].mean(axis=0) if sel.any() else None
    results.append((int(mapid), name, img, band, mean))
    save_mask(terr, os.path.join(terr_dir, "%d.tga" % int(mapid)))
    save_mask(core, os.path.join(core_dir, "%d.tga" % int(mapid)))
    print("%-24s band %s px %d" % (name, None if mean is None else [round(float(c)) for c in mean], int(sel.sum())), flush=True)

valid = [r for r in results if r[4] is not None]
T = np.mean([r[4] for r in valid], axis=0)
LT = lum(T)
print("target", [round(float(c)) for c in T])

grade = {}
for mapid, name, img, band, mean in results:
    if mean is None: continue
    want = T * min(1.0, lum(mean) / LT)                    # the palette, no brighter than the zone
    m = np.minimum(want / np.maximum(mean, 1), 1.0)        # vertex colours can only darken
    grade[mapid] = (name, m)
    save_mask(band, os.path.join(mask_dir, "%d.tga" % mapid))

with open(out_lua, "w", encoding="utf-8", newline="\n") as f:
    f.write("-- Colour matching for the stitched world map: uiMapID -> { r, g, b } multipliers\n")
    f.write("-- that take a zone's border band (land within %dpx of its outline, water left out)\n" % STAT_BAND)
    f.write("-- to the shared palette (the mean of every zone's band: %d, %d, %d), no brighter\n" % tuple(round(float(c)) for c in T))
    f.write("-- than the zone was. The map applies them through Media/Textures/MapBand/<uiMapID>,\n")
    f.write("-- full strength at the outline, fading %dpx inward and %dpx outward.\n" % (BAND_IN, BAND_OUT))
    f.write("-- Generated from the zones' overlay art; regenerate rather than edit.\n\n")
    f.write("local _, ns = ...\n\nns.MapGrade = {\n")
    for mapid in sorted(grade):
        name, m = grade[mapid]
        f.write("\t[%d] = { %.3f, %.3f, %.3f }, -- %s\n" % (mapid, m[0], m[1], m[2], name))
    f.write("}\n")

# previews: each zone before (top) / after (bottom), in a grid
thumbs = []
for mapid, name, img, band, mean in results:
    if mapid not in grade: continue
    m = grade[mapid][1]
    a = np.asarray(img).astype(np.float32)
    k = 1 + (m[None, None, :] - 1) * band[..., None]
    after = a.copy(); after[..., :3] = np.clip(a[..., :3] * k, 0, 255)
    pair = np.concatenate([a, after], axis=0)
    thumbs.append(Image.fromarray(pair.astype(np.uint8)).resize((CW // 4, CH // 2), Image.LANCZOS))
cols = 8
rows = math.ceil(len(thumbs) / cols)
sheet = Image.new("RGBA", (cols * (CW // 4), rows * (CH // 2)), (40, 40, 40, 255))
for i, t in enumerate(thumbs):
    sheet.alpha_composite(t, ((i % cols) * (CW // 4), (i // cols) * (CH // 2)))
sheet.convert("RGB").save(os.path.join(prev_dir, "grade_sheet.jpg"), quality=85)
print("wrote", out_lua, len(grade), "zones")
