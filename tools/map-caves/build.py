# Builds OpenMap's "underground" maps: Blizzard's own cave and pre-instance maps
# (micro maps) that WoW Forever ships the art for but doesn't wire to C_Map.
#   OpenMap/Data/Caves.lua              per cave: continent, world box, art tile file IDs
#   OpenMap/Media/Textures/MapCave/<uiMapID>.tga
#                                       where the cave is in its art (alpha): its floors and
#                                       walls, without the parchment, frame, title or corners
# Placement and tiles come from retail's tables (the micro maps are retail-era; Classic's
# tables don't have them); only caves whose every tile exists in the Forever build are kept.
#
# usage: python -P tools/map-caves/build.py <cache dir> [contact sheet.png]
#   (tables and textures are fetched from wago.tools into the cache)
import csv, json, os, struct, sys, time, urllib.request
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..", "OpenMap")
cache = sys.argv[1]
os.makedirs(cache, exist_ok=True)
CATA, FOREVER = "retail", "1.60.1.70245"
UA = {"User-Agent": "openmap-tools/1"}

def get(url, path):
    if not os.path.exists(path) or os.path.getsize(path) < 50:
        open(path, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())
        time.sleep(0.15)
    return path

def table(name, build):
    url = "https://wago.tools/db2/%s/csv" % name + ("" if build == "retail" else "?build=%s" % build)
    return list(csv.DictReader(open(get(url,
        os.path.join(cache, "%s-%s.csv" % (name, build))), encoding="utf-8")))

def blp(fid):
    p = get("https://wago.tools/api/casc/%s?download&version=%s" % (fid, FOREVER), os.path.join(cache, "%s.blp" % fid))
    try:
        return Image.open(p).convert("RGBA")
    except Exception:            # uncompressed BLP2, which Pillow doesn't read
        b = open(p, "rb").read(); w, h = struct.unpack("<II", b[12:20]); off = struct.unpack("<16I", b[20:84])[0]
        return Image.frombytes("RGBA", (w, h), b[off:off + w * h * 4], "raw", "BGRA")

def exists_in_forever(fid):
    p = os.path.join(cache, "exists-%s.json" % fid)
    if not os.path.exists(p):
        try:
            r = urllib.request.urlopen(urllib.request.Request("https://wago.tools/api/casc/%s?download&version=%s" % (fid, FOREVER), headers=UA), timeout=60)
            data = r.read(); ok = len(data) > 100
            if ok: open(os.path.join(cache, "%s.blp" % fid), "wb").write(data)
        except Exception:
            ok = False
        json.dump(ok, open(p, "w")); time.sleep(0.15)
    return json.load(open(p))

# ------------------------------------------------------------------ the caves
uimap = {r["ID"]: r for r in table("UiMap", CATA)}
assign = {}
for r in table("UiMapAssignment", CATA):
    assign.setdefault(r["UiMapID"], []).append(r)
art_of = {r["UiMapID"]: r["UiMapArtID"] for r in table("UiMapXMapArt", CATA) if r["PhaseID"] == "0"}
tiles = {}
for r in table("UiMapArtTile", CATA):
    if r["LayerIndex"] == "0":
        tiles.setdefault(r["UiMapArtID"], {})[(int(r["RowIndex"]), int(r["ColIndex"]))] = r["FileDataID"]

# later expansions' maps of the same places (classic has none of these)
SKIP_NAMES = {"Dalaran", "New Tinkertown", "Light's Hope Chapel", "Caverns of Time"}
# and only places Forever's world has: a micro map named for an area in its own AreaTable (not
# Greymane Manor in Gilneas, Spitescale Cavern on the remade Echo Isles, Legion's Keeper's Rest and
# Karazhan Catacombs), or one of these, places classic has under no name of their own
KEEP_NAMES = {
    "Scarlet Monastery Entrance",   # the monastery's courtyard, before its doors
    "Frostmane Hovel",              # Coldridge Valley's troll cave (kept until it's checked in game:
                                    #  classic has a troll cave there, its map may be Cataclysm's)
}
areas = {r["AreaName_lang"] for r in table("AreaTable", FOREVER)}
caves = []
for mid, u in uimap.items():
    if u["Name_lang"] in SKIP_NAMES: continue
    if u["Name_lang"] not in areas and u["Name_lang"] not in KEEP_NAMES: continue
    if u["Type"] != "5" or mid not in art_of: continue           # micro maps: caves, pre-instance areas
    rows = [a for a in assign.get(mid, []) if a["MapID"] in ("0", "1")]
    if not rows: continue
    a = rows[0]
    t = tiles.get(art_of[mid], {})
    fids = [t.get((r, c)) for r in range(3) for c in range(4)]
    if None in fids or not all(exists_in_forever(f) for f in fids): continue
    box = [float(a["Region_%d" % i]) for i in (0, 1, 3, 4)]      # world minX, minY, maxX, maxY
    um = [float(a[k]) for k in ("UiMin_0", "UiMin_1", "UiMax_0", "UiMax_1")]
    caves.append({"id": int(mid), "name": u["Name_lang"], "cont": int(a["MapID"]), "box": box, "ui": um, "fids": fids})
caves.sort(key=lambda c: c["id"])
print(len(caves), "caves")

# ------------------------------------------------------------------ where the cave is in its art
def cave_mask(a):
    """its pale floors (and lava, water) against the art's overall parchment tone, grown to
    take in the dark wall band; the frame, title banners and corner knots left out"""
    rgb = a[..., :3]
    L = ndimage.gaussian_filter(rgb.mean(2), 1.5)
    h, w = L.shape
    hsv = np.asarray(Image.fromarray((rgb * 255).astype(np.uint8)).convert("HSV")).astype(np.float32) / 255
    inner = np.zeros((h, w), bool); inner[int(h * .15):int(h * .85), int(w * .1):int(w * .9)] = True
    paper = np.median(L[inner])
    m = (L > paper + 0.09) | ((hsv[..., 1] > 0.6) & (hsv[..., 2] > 0.55)) | \
        ((hsv[..., 0] > 0.45) & (hsv[..., 0] < 0.7) & (hsv[..., 1] > 0.12) & (L > paper))
    keepout = np.zeros_like(m)
    keepout[:, : int(w * 0.11)] = keepout[:, int(w * 0.89):] = True
    keepout[: int(h * 0.07)] = keepout[int(h * 0.93):] = True
    for y0, y1 in ((0, int(h * 0.13)), (int(h * 0.87), h)):
        keepout[y0:y1, int(w * 0.28):int(w * 0.72)] = True
    m &= ~keepout
    m = ndimage.binary_closing(ndimage.binary_opening(m, iterations=1), iterations=3)
    lab, n = ndimage.label(m)
    if n == 0: return np.zeros((h, w), np.float32)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    cents = ndimage.center_of_mass(m, lab, range(1, n + 1))
    big = sizes.max()
    boxes = ndimage.find_objects(lab)
    def wanted(i):
        s_, (cy, cx) = sizes[i], cents[i]
        if s_ < max(600, big * 0.04): return False
        ys_, xs_ = boxes[i]
        # a strip along the frame (the pale band inside the left / right border): not cave,
        # however big, unless it reaches well into the map
        if (xs_.stop < w * 0.2 or xs_.start > w * 0.8) and (xs_.stop - xs_.start) < w * 0.12: return False
        near_edge = cx < w * 0.2 or cx > w * 0.8 or cy < h * 0.18 or cy > h * 0.82
        return not near_edge or s_ > big * 0.35       # pale paper near the frame isn't cave
    keep = np.isin(lab, [i + 1 for i in range(n) if wanted(i)])
    keep = ndimage.binary_dilation(keep, iterations=14)
    keep = ndimage.binary_opening(ndimage.binary_fill_holes(keep) & ~keepout, iterations=6)
    core_clear = np.ones((h, w), bool)                                # (the core obeys the banner / corner clears too)
    core_clear[: int(h * 0.06)] = core_clear[int(h * 0.86):] = False
    core_clear[: int(h * 0.12), : int(w * 0.30)] = core_clear[: int(h * 0.12), int(w * 0.68):] = False
    for ys in (slice(0, int(h * 0.2)), slice(int(h * 0.8), h)):
        for xs in (slice(0, int(w * 0.16)), slice(int(w * 0.82), w)):
            core_clear[ys, xs] = False
    keep &= core_clear
    core = np.clip(ndimage.gaussian_filter(keep.astype(np.float32), 4) * 1.4 - 0.2, 0, 1)
    # a soft halo of the map's own parchment around the cave, fading out well before
    # the frame, so the cave sits in a patch of its paper rather than a hard cut-out
    halo = ndimage.gaussian_filter(ndimage.binary_dilation(keep, iterations=40).astype(np.float32), 18)
    clear = np.ones((h, w), np.float32)
    clear[: int(h * 0.06)] = clear[int(h * 0.86):] = 0              # (banners run along the top and bottom,
    clear[: int(h * 0.12), : int(w * 0.30)] = clear[: int(h * 0.12), int(w * 0.68):] = 0   # name tabs in the top corners)
    clear[:, : int(w * 0.07)] = clear[:, int(w * 0.95):] = 0
    for y0, y1 in ((0, int(h * 0.13)), (int(h * 0.87), h)):          # title banners
        clear[y0:y1, int(w * 0.28):int(w * 0.72)] = 0
    for ys in (slice(0, int(h * 0.2)), slice(int(h * 0.8), h)):      # corner knots
        for xs in (slice(0, int(w * 0.16)), slice(int(w * 0.82), w)):
            clear[ys, xs] = 0
    # faded out before the clear zones' edges (a blur would spread into them, a cut would show)
    fade = ndimage.gaussian_filter(ndimage.binary_erosion(clear > 0.5, iterations=18).astype(np.float32), 8)
    return np.maximum(core, np.clip(halo, 0, 1) * 0.8) * fade

MASK = 128                      # the masks are soft: 128 px is plenty
sheet_path = sys.argv[2] if len(sys.argv) > 2 else None    # (optional: a contact sheet of every cave as shown)
sheet = Image.new("RGB", (6 * 336, 8 * 225)) if sheet_path else None
outdir = os.path.join(ROOT, "Media", "Textures", "MapCave")
os.makedirs(outdir, exist_ok=True)
for f in os.listdir(outdir):                # (a cave no longer kept leaves no mask behind)
    if f.endswith(".tga"): os.remove(os.path.join(outdir, f))
kept = []
for c in caves:
    img = Image.new("RGBA", (1002, 668))
    for n, f in enumerate(c["fids"]):
        img.paste(blp(f), ((n % 4) * 256, (n // 4) * 256))
    m = cave_mask(np.asarray(img).astype(np.float32) / 255)
    if m.mean() < 0.01:
        print("  no cave found in", c["name"], c["id"]); continue
    a = Image.fromarray((m * 255).astype(np.uint8)).resize((MASK, MASK), Image.LANCZOS)
    Image.merge("RGBA", (Image.new("L", (MASK, MASK), 255),) * 3 + (a,)).save(os.path.join(outdir, "%d.tga" % c["id"]))
    kept.append(c)
    if sheet is not None:                       # the cave as it will show: its art through the mask
        shown = np.asarray(img).astype(np.float32) / 255
        shown = shown[..., :3] * m[..., None] + np.array([0.2, 0.15, 0.1]) * (1 - m[..., None])
        tile = Image.fromarray((shown * 255).astype(np.uint8)).resize((334, 223))
        k = len(kept) - 1
        sheet.paste(tile, ((k % 6) * 336, (k // 6) * 225))

with open(os.path.join(ROOT, "Data", "Caves.lua"), "w", encoding="utf-8", newline="\n") as f:
    f.write("-- Caves and pre-instance areas (Blizzard's micro maps): their art and where it lies.\n")
    f.write("--   [uiMapID] = { name, continent, minX, minY, maxX, maxY (world yards), uiMin x, y, uiMax x, y, { 12 tile file IDs } }\n")
    f.write("-- Generated by tools/map-caves/build.py; regenerate rather than edit.\n\nlocal _, ns = ...\n\nns.MapCaves = {\n")
    for c in kept:
        f.write("\t[%d] = { %s, %d, %.1f, %.1f, %.1f, %.1f, %.3f, %.3f, %.3f, %.3f, { %s } },\n" % (
            c["id"], '"' + c["name"].replace('"', '\\"') + '"', c["cont"], *c["box"], *c["ui"], ", ".join(c["fids"])))
    f.write("}\n")
print("kept", len(kept))
if sheet is not None: sheet.save(sheet_path)
