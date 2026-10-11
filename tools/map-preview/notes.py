# Renders map notes (the in-game Map notes tool's Export, /openmap notes) out of game: one image
# per note at its place and zoom, its painted area in its kind's colour and its text, and an
# index (notes.md) listing them all. For working through the notes someone left on the map.
# usage: python -P tools/map-preview/notes.py <db2 dir> <texture cache> <out dir> <notes.txt> [#id ...]
#   notes.txt: the exported text, as pasted (OpenMap map notes | ... then one #id line per note)
import math, os, re, sys
from PIL import Image, ImageDraw, ImageFont

db2, cache, outdir, notes_file = sys.argv[1:5]
only = {int(a.lstrip("#")) for a in sys.argv[5:]}
KIND_COLOR = {"fix": (255, 82, 61), "look": (255, 199, 51), "idea": (107, 184, 255)}
AREA_SHARE = 0.45               # a painted area fills about this much of the view (when the note has no zoom)
POINT_ZOOM = 8                  # a note at a point, with no zoom

LINE = re.compile(r"^#(\d+) (\w+) \| (.*?) \((\d+)\) \| at ([\d.\-]+) ([\d.\-]+) \| zoom ([\d.]+) \| ?(.*)$")
notes = []
for raw in open(notes_file, encoding="utf-8"):
    line = raw.rstrip("\n")
    m = LINE.match(line.strip())
    if m:
        notes.append({"id": int(m.group(1)), "kind": m.group(2), "zone": m.group(3), "zone_id": int(m.group(4)),
                      "u": float(m.group(5)), "v": float(m.group(6)), "zoom": float(m.group(7)), "text": m.group(8),
                      "radius": None, "strokes": []})
    elif line.strip().startswith("area r=") and notes:
        head, _, rest = line.strip()[len("area r="):].partition(" ")
        notes[-1]["radius"] = float(head)
        for part in rest.split(";"):
            pts = [tuple(map(float, p.split())) for p in part.split(",") if p.strip()]
            if pts: notes[-1]["strokes"].append(pts)
if not notes:
    sys.exit("no notes found (expected lines like: #1 fix | Elwynn Forest (1429) | at 0.41 0.67 | zoom 12.0 | text)")
if only: notes = [n for n in notes if n["id"] in only]

here = os.path.dirname(os.path.abspath(__file__))
os.makedirs(outdir, exist_ok=True)
sys.argv = ["render.py", db2, cache, outdir]
g = {"__name__": "notes", "__file__": os.path.join(here, "render.py")}
src = open(os.path.join(here, "render.py"), encoding="utf-8").read()
exec(compile(src[:src.index("views = sys.argv[4:]")], "render", "exec"), g)
OW, OH = g["OW"], g["OH"]
W, H = 1002.0, 668.0
base = min(OW / W, OH / H)        # output px per world unit at zoom 1
try:
    FONT = ImageFont.load_default(size=18)   # (Pillow 10.1+; older: its small bitmap font)
except TypeError:
    FONT = ImageFont.load_default()

def view_of(n):
    """the note's centre and a zoom: its own, else one that frames its area"""
    pts = [p for s in n["strokes"] for p in s]
    if n["zoom"] > 0: return n["u"], n["v"], n["zoom"]
    if not pts: return n["u"], n["v"], POINT_ZOOM
    r = n["radius"] or 0
    us, vs = [p[0] for p in pts], [p[1] for p in pts]
    du = (max(us) - min(us) + 2 * r) * W
    dv = (max(vs) - min(vs) + 2 * r * W / H) * H
    z = min(AREA_SHARE * OW / (du * base), AREA_SHARE * OH / (dv * base))
    return (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2, max(1, min(z, 120))

index = ["# Map notes", "", "Rendered out of game by tools/map-preview/notes.py from `%s`." % os.path.basename(notes_file), ""]
for n in notes:
    cu, cv, zoom = view_of(n)
    path = os.path.join(outdir, "note_%d.png" % n["id"])
    g["render"](cu, cv, zoom, path)
    im = Image.open(path).convert("RGBA")
    px = base * zoom
    def to_px(u, v): return (u - cu) * W * px + OW / 2, (v - cv) * H * px + OH / 2
    col = KIND_COLOR.get(n["kind"], (255, 255, 255))
    over = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    if n["strokes"] and n["radius"]:
        rp = max(2, n["radius"] * W * px)
        for s in n["strokes"]:
            # dabs along the stroke, as the game draws them
            for (u0, v0), (u1, v1) in zip(s, s[1:] or s):
                x0, y0 = to_px(u0, v0)
                x1, y1 = to_px(u1, v1)
                k = max(1, int(math.hypot(x1 - x0, y1 - y0) / (rp * 0.33)))
                for i in range(k + 1):
                    x, y = x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k
                    d.ellipse([x - rp, y - rp, x + rp, y + rp], fill=col + (60,))
    x, y = to_px(n["u"], n["v"])
    d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=col + (255,), outline=(0, 0, 0, 255), width=2)
    im = Image.alpha_composite(im, over)
    d = ImageDraw.Draw(im)
    label = "#%d %s: %s" % (n["id"], n["kind"], n["text"] or "(no text)")
    d.text((x + 11, y - 10), label[:120], fill=(0, 0, 0, 255), font=FONT)
    d.text((x + 10, y - 11), label[:120], fill=col + (255,), font=FONT)
    d.rectangle([0, OH - 24, OW, OH], fill=(0, 0, 0, 255))
    d.text((8, OH - 18), ("#%d %s | %s (%d) | zoom %.1f | %s" % (n["id"], n["kind"], n["zone"], n["zone_id"], zoom, n["text"]))[:180],
           fill=(255, 220, 120, 255))
    im.convert("RGB").save(path)
    index += ["## #%d %s: %s" % (n["id"], n["kind"], n["text"] or "(no text)"), "",
              "%s (%d), at %.5f %.5f, zoom %.1f%s" % (n["zone"], n["zone_id"], n["u"], n["v"], zoom,
                                                     ", a painted area" if n["strokes"] else ", a point"), "",
              "![note %d](note_%d.png)" % (n["id"], n["id"]), ""]
    print("note", n["id"], n["kind"], n["zone"], "->", path, flush=True)
with open(os.path.join(outdir, "notes.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(index))
print("wrote", os.path.join(outdir, "notes.md"))
