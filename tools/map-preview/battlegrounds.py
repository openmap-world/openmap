# Previews of the battlegrounds' maps as Map/Battlegrounds.lua draws them: Blizzard's map of each, and
# the battleground's own minimap tiles (Data/<client>/Battlegrounds.lua) over it as the map zooms in,
# softened and warmed as Close.lua's (S.MiniTileLook), through the feathered focus box, and mixed in
# as Battlegrounds.lua's Mix does.
# Per battleground: the whole map (the painted map alone, as it opens), one zoomed in a few steps and
# one at the deepest zoom, each about the view's middle (or a spot given as u,v), at the window's
# 1002 x 668. Keep the constants in step with Battlegrounds.lua's and Close.lua's.
#
# usage: python -P tools/map-preview/battlegrounds.py <cache dir> <World of Warcraft folder> <out dir> [build]
#   (the map art's tables from wago.tools into the cache: build, the one Battlegrounds.lua was made from)
#   OPENMAP_BG_MIX=0.5: every preview at that mix instead (to check the tiles lie on the art)
import csv, io, math, os, re, sys, time, urllib.request
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "casc"))
import clients
from casc import Casc

if len(sys.argv) < 4:
    sys.exit("usage: python -P tools/map-preview/battlegrounds.py <cache dir> <World of Warcraft folder> <out dir> [build]")
cache, wow, out = sys.argv[1], sys.argv[2], sys.argv[3]
SRC = open(os.path.join(clients.DATA, "Battlegrounds.lua"), encoding="utf-8").read()
BUILD = sys.argv[4] if len(sys.argv) > 4 else re.search(r"from build (\S+?)'s", SRC).group(1)
os.makedirs(out, exist_ok=True)
UA = {"User-Agent": "openmap-tools/1"}
W, H = 1002, 668
TILE = 1600 / 3
# Battlegrounds.lua's
ZOOM_STEP, DEEP_YARDS, LEAST_DEEP = 1.25, 360, 4
MINI_FADE, DEEP_FADE = (1.3, 2.5), (0.5, 1)
MIX, DEEP = 0.45, 0.85          # Close.lua's minimapMix, minimapDeep defaults
# Close.lua's: MINI_DESAT, PAPER, TONE_SHARE, DEFAULT_TONE
MINI_DESAT, PAPER, TONE_SHARE, DEFAULT_TONE = 0.35, (1, 0.93, 0.80), 0.25, (0.56, 0.45, 0.17)
STEPS_IN = 5                    # the middle preview: this many wheel notches in


def table(name):
    path = os.path.join(cache, "%s-%s.csv" % (name, BUILD))
    if not os.path.exists(path) or os.path.getsize(path) < 100:
        url = "https://wago.tools/db2/%s/csv?build=%s" % (name, BUILD)
        open(path, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())
        time.sleep(0.3)
    return list(csv.DictReader(open(path, encoding="utf-8")))


def smooth(x, r):
    t = max(0.0, min(1.0, (x - r[0]) / (r[1] - r[0])))
    return t * t * (3 - 2 * t)


def tint():
    top = max(DEFAULT_TONE)
    return np.array([PAPER[i] + (DEFAULT_TONE[i] / top - PAPER[i]) * TONE_SHARE for i in range(3)], np.float32)


def parse():
    bgs = {}
    for m in re.finditer(r'\[(\d+)\] = \{ (\d+), "([^"]*)", \{ ([^}]*) \}, \{ ([^}]*) \}, \{(.*?)\}, \{ ([^}]*) \} \}', SRC, re.S):
        tiles = {int(k): int(v) for k, v in re.findall(r"\[(\d+)\] = (\d+)", m.group(6))}
        bgs[int(m.group(1))] = (int(m.group(2)), m.group(3), [float(x) for x in m.group(4).split(",")],
                                [float(x) for x in m.group(5).split(",")], tiles, [float(x) for x in m.group(7).split(",")])
    return bgs


def main():
    casc = Casc(wow, clients.PRODUCT)
    img = lambda fid: Image.open(io.BytesIO(casc.read(fid))).convert("RGBA")
    art_of = {int(r["UiMapID"]): int(r["UiMapArtID"]) for r in table("UiMapXMapArt") if r["PhaseID"] == "0"}
    art_tiles = {}
    for r in table("UiMapArtTile"):
        if r["LayerIndex"] == "0":
            art_tiles.setdefault(int(r["UiMapArtID"]), {})[(int(r["RowIndex"]), int(r["ColIndex"]))] = int(r["FileDataID"])
    T = tint()
    feather = Image.open(os.path.join(clients.TEX, "MapFeather.tga")).getchannel("A")
    for ui, (mid, name, box, part, tiles, focus) in sorted(parse().items()):
        # Blizzard's map: its 4 x 3 tiles of 256, the picture the top-left 1002 x 668
        paint = Image.new("RGBA", (1024, 768))
        for (row, col), fid in art_tiles[art_of[ui]].items():
            paint.paste(img(fid), (col * 256, row * 256))
        paint = paint.crop((0, 0, W, H))
        # the minimap over it at 4x the map's pixels (each yard of it then as sharp as its tiles)
        S = 4
        mini = np.zeros((H * S, W * S, 3), np.float32)
        cover = np.zeros((H * S, W * S), np.float32)
        x0, y0, x1, y1 = box
        u = lambda y: part[0] + (part[2] - part[0]) * (y1 - y) / (y1 - y0)
        v = lambda x: part[1] + (part[3] - part[1]) * (x1 - x) / (x1 - x0)
        for key, fid in tiles.items():
            tx, ty = key // 64, key % 64
            ua, va, ub, vb = u((32 - tx) * TILE), v((32 - ty) * TILE), u((31 - tx) * TILE), v((31 - ty) * TILE)
            pa, pb = int(round(ua * W * S)), int(round(ub * W * S))
            qa, qb = int(round(va * H * S)), int(round(vb * H * S))
            t = np.asarray(img(fid).convert("RGB").resize((pb - pa, qb - qa), Image.BILINEAR)).astype(np.float32) / 255
            grey = t @ np.array([0.299, 0.587, 0.114], np.float32)
            t = (t + (grey[..., None] - t) * MINI_DESAT) * T
            # (cut to the map, as the textures are)
            sa, sb, ra, rb = max(pa, 0), min(pb, W * S), max(qa, 0), min(qb, H * S)
            if sb <= sa or rb <= ra: continue
            mini[ra:rb, sa:sb] = t[ra - qa:rb - qa, sa - pa:sb - pa]
            cover[ra:rb, sa:sb] = 1
        # where it shows: MapFeather over the focus box (Battlegrounds.lua's mask)
        fl, ft = int(round(focus[0] * W * S)), int(round(focus[1] * H * S))
        fr, fb = int(round(focus[2] * W * S)), int(round(focus[3] * H * S))
        fm = np.asarray(feather.resize((fr - fl, fb - ft), Image.BILINEAR)).astype(np.float32) / 255
        mask = np.zeros_like(cover)
        sa, sb, ra, rb = max(fl, 0), min(fr, W * S), max(ft, 0), min(fb, H * S)
        mask[ra:rb, sa:sb] = fm[ra - ft:rb - ft, sa - fl:sb - fl]
        cover = cover * mask
        big = np.asarray(paint.convert("RGB").resize((W * S, H * S), Image.BILINEAR)).astype(np.float32) / 255
        across = max(x1 - x0, y1 - y0)
        deep = max(LEAST_DEEP, across / DEEP_YARDS)
        slug = re.sub(r"[^a-z]+", "-", name.lower()).strip("-")
        for label, zoom in (("1-whole", 1.0), ("2-zoom%.1fx" % ZOOM_STEP ** STEPS_IN, ZOOM_STEP ** STEPS_IN), ("3-deepest%.1fx" % deep, deep)):
            mix = min(MIX, DEEP) * smooth(zoom, MINI_FADE)
            mix = mix + (DEEP - mix) * smooth(zoom, (deep * DEEP_FADE[0], deep * DEEP_FADE[1]))
            if os.environ.get("OPENMAP_BG_MIX"): mix = float(os.environ["OPENMAP_BG_MIX"])
            a = (mix * cover)[..., None]
            frame = big * (1 - a) + mini * a
            # the view: 1/zoom of the map about the middle of the land the tiles cover
            ys, xs = np.nonzero(cover[::S, ::S])
            cu = (xs.mean() / W) if len(xs) else 0.5
            cv = (ys.mean() / H) if len(ys) else 0.5
            hw, hh = 0.5 / zoom, 0.5 / zoom
            cu, cv = min(max(cu, hw), 1 - hw), min(max(cv, hh), 1 - hh)
            l, t = int((cu - hw) * W * S), int((cv - hh) * H * S)
            r, b = int((cu + hw) * W * S), int((cv + hh) * H * S)
            view = Image.fromarray((np.clip(frame[t:b, l:r], 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
            p = os.path.join(out, "%s-%s-mix%02d.png" % (slug, label, round(mix * 100)))
            view.save(p)
            print(p)


main()
