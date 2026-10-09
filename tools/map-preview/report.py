# Renders a player's report code (from the in-game "Report a problem" button) out of game:
# the same place and zoom, with their circles drawn in red, for triage.
# usage: python -P tools/map-preview/report.py <db2 dir> <texture cache> <out.png> "OM1|..."
import os, sys
from PIL import Image, ImageDraw

db2, cache, out, code = sys.argv[1:5]
parts = code.strip().split("|", 7)
if len(parts) < 8 or parts[0] != "OM1":
    sys.exit("not an OpenMap report code (expected OM1|...)")
_, version, mapid, u, v, zoom, circles, note = parts
u, v, zoom = float(u), float(v), float(zoom)
print("version %s, map %s, zoom %.1f, note: %s" % (version, mapid, zoom, note))

here = os.path.dirname(os.path.abspath(__file__))
sys.argv = ["render.py", db2, cache, os.path.dirname(os.path.abspath(out)) or "."]
g = {"__name__": "report", "__file__": os.path.join(here, "render.py")}
src = open(os.path.join(here, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)
g["render"](u, v, zoom, out)

im = Image.open(out).convert("RGB")
d = ImageDraw.Draw(im)
OW, OH = im.size
px = min(OW / 1002.0, OH / 668.0) * zoom
for c in filter(None, circles.split(";")):
    cu, cv, r = map(float, c.split(":"))
    x, y = (cu - u) * 1002 * px + OW / 2, (cv - v) * 668 * px + OH / 2
    rx, ry = r * 1002 * px, r * 1.5 * 668 * px
    d.ellipse([x - rx, y - ry, x + rx, y + ry], outline=(220, 40, 25), width=4)
d.rectangle([0, OH - 24, OW, OH], fill=(0, 0, 0))
d.text((8, OH - 18), ("OpenMap %s  map %s  zoom %.1f   %s" % (version, mapid, zoom, note))[:180], fill=(255, 220, 120))
im.save(out)
print("wrote", out)
