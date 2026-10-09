# Cuts the map border (art-edits/border.png: the map art's frame, hand-cut from Blizzard's
# continent art, transparent inside) into nine pieces for Map/Border.lua: four corners
# kept as they are, four edges stretched to fit, so the frame fits a map of any shape.
# Writes OpenMap/Media/Textures/MapBorder/<piece>.tga (power-of-two canvases; Border.lua
# crops each to its content with texture coordinates: CORNER, EDGE_W, EDGE_H below).
# usage: python -P tools/map-art/border.py
import os
from PIL import Image

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(here, "..", "..")
src = Image.open(os.path.join(root, "art-edits", "border.png")).convert("RGBA")
out = os.path.join(root, "OpenMap", "Media", "Textures", "MapBorder")
os.makedirs(out, exist_ok=True)
W, H = src.size
CORNER = 192                    # the corners: their metal fittings and curled paper, whole
EDGE_W = 1024                   # the top / bottom edge's length once cut (from W - 2 * CORNER)

def save(img, canvas, name):
    c = Image.new("RGBA", canvas, (0, 0, 0, 0))
    c.paste(img, (0, 0))
    c.save(os.path.join(out, name + ".tga"))

C = CORNER
save(src.crop((0, 0, C, C)), (256, 256), "tl")
save(src.crop((W - C, 0, W, C)), (256, 256), "tr")
save(src.crop((0, H - C, C, H)), (256, 256), "bl")
save(src.crop((W - C, H - C, W, H)), (256, 256), "br")
save(src.crop((C, 0, W - C, C)).resize((EDGE_W, C), Image.LANCZOS), (1024, 256), "top")
save(src.crop((C, H - C, W - C, H)).resize((EDGE_W, C), Image.LANCZOS), (1024, 256), "bottom")
save(src.crop((0, C, C, H - C)), (256, 1024), "left")
save(src.crop((W - C, C, W, H - C)), (256, 1024), "right")
print("border:", W, "x", H, "corner", C, "side edge", H - 2 * C)
