"""Where each continent's land hides what's drawn under it: Data/<client>/Cover.lua, for Stitch.lua's Live.Clip.

    python covergrid.py <OpenMap folder> [--write] [--map]

Under a continent's land (MapLand/<continent>, drawn through MapFeatherWide once the zones' zoom is
reached) Stitch.lua draws a dozen layers the size of the view: the sea's colours and mottling, the
world's and the continent's own art, the wave strokes. Where that land is opaque none of them can be
seen. This notes, for each continent, the cells of its art's rectangle where it is: the land texture
and the feather both fully opaque (their alpha 255), and so are the eight cells round each (the game
draws both smoothed, bilinear: a point's colour comes from the texels round it). Stitch.lua clips
those layers to the part of the view outside these cells.

Cells are the textures' own texels (256 a side over the continent's art, both textures the same
size), so no resampling comes between this and what the game draws.

The table is stamped with the addon's version (the toc's): Stitch.lua clips by it on that version only,
so an OpenMap whose textures may have changed since never clips by an old table. Run this again after
an update (or wherever MapLand is baked) to stamp the new one.

It also measures where the world's sea colour hides what's under it (the sea's outer colour and
mottling): MapSeaField/947, which has no alpha, drawn over the whole world through MapFeatherWide,
which is fully opaque from some way in from each edge. That distance (two texels further in, for the
smoothing) is the table's `world`. If the sea colour ever has an alpha, `world` is left out and
Stitch.lua clips nothing by it.

Standard library only (plain TGA files).
"""
import math, os, re, struct, sys


def tga(path):
    """an uncompressed TGA: width, height, bytes a pixel, rows top-down"""
    with open(path, "rb") as f:
        data = f.read()
    idlen, cmap, kind = data[0], data[1], data[2]
    w, h, depth, desc = struct.unpack_from("<HHBB", data, 12)
    if kind not in (2, 3) or cmap: raise ValueError(path + ": not a plain TGA")
    bpp = depth // 8
    at = 18 + idlen
    rows = [data[at + y * w * bpp: at + (y + 1) * w * bpp] for y in range(h)]
    if not desc & 0x20: rows.reverse()      # (stored bottom-up)
    return w, h, bpp, rows


def alpha(rows, bpp, x, y):
    return rows[y][x * bpp + bpp - 1] if bpp in (2, 4) else 255


def feather_full(path):
    """how far in from each edge the mask is opaque throughout, in texels, and its size (it's square)"""
    w, h, bpp, rows = tga(path)
    if w != h: raise ValueError(path + ": not square")
    for inset in range(0, w // 2):
        if all(alpha(rows, bpp, x, y) == 255 for y in range(inset, h - inset) for x in range(inset, w - inset)):
            return inset, w
    return None, w


def land_cover(tex, cont):
    """rows (top-down) of booleans: the continent's texels where its land hides what's under it"""
    w, h, bpp, rows = tga(os.path.join(tex, "MapLand", "%d.tga" % cont))
    fw, fh, fbpp, frows = tga(os.path.join(tex, "MapFeatherWide.tga"))
    if (w, h) != (fw, fh) or w != h: raise ValueError("MapLand/%d and MapFeatherWide differ in size, or aren't square" % cont)
    if bpp != 4: raise ValueError("MapLand/%d has no alpha" % cont)
    ok = [[alpha(rows, bpp, x, y) == 255 and alpha(frows, fbpp, x, y) == 255 for x in range(w)] for y in range(h)]
    safe = [[all(0 <= y + dy < h and 0 <= x + dx < w and ok[y + dy][x + dx] for dy in (-1, 0, 1) for dx in (-1, 0, 1))
             for x in range(w)] for y in range(h)]
    return safe, w


def hex_row(row):
    """a row as hex digits, four cells a digit (the first cell the digit's 8), trailing zeros dropped"""
    digits = []
    for k in range(0, len(row), 4):
        v = 0
        for b in range(4):
            if k + b < len(row) and row[k + b]: v |= 8 >> b
        digits.append("%x" % v)
    return "".join(digits).rstrip("0")


def main():
    args = sys.argv[1:]
    if not args: sys.exit(__doc__)
    addon, client, conts = args[0], "Forever", (1414, 1415)
    tex = os.path.join(addon, "Media", "Textures", client)
    inset, fsize = feather_full(os.path.join(tex, "MapFeatherWide.tga"))
    _, _, bpp, _ = tga(os.path.join(tex, "MapSeaField", "947.tga"))
    # (two texels further in than the first opaque one: the game smooths between texels; rounded up)
    world = math.ceil((inset + 2) / fsize * 1000) / 1000 if inset is not None and bpp == 3 else None
    print("MapFeatherWide: opaque from texel %s of %d in from each edge; MapSeaField/947: %s; the world's sea colour hides what's under it from %s of the world in"
          % (inset, fsize, "no alpha" if bpp == 3 else "HAS ALPHA", world))
    with open(os.path.join(addon, "OpenMap.toc"), encoding="utf-8") as f:
        version = re.search(r"^## Version:\s*(\S+)", f.read(), re.M).group(1)
    grids, size = {}, None
    for cont in conts:
        grid, size = land_cover(tex, cont)
        grids[cont] = grid
        n = sum(sum(r) for r in grid)
        print("MapLand/%d: %d x %d cells, %d of them hide what's under (%.1f%% of the continent's art)" % (cont, size, size, n, 100.0 * n / (size * size)))
        if "--map" in args:
            for row in grid[::6]:
                print("  " + "".join("#" if any(row[k:k + 3]) else "." for k in range(0, size, 3)))
    if "--write" in args:
        lines = ["-- Where each continent's land hides what's drawn under it (Stitch.lua's Live.Clip): [continent's map] =",
                 "-- rows from the top of its art's rectangle, `size` cells a side; each row hex digits, four cells a digit",
                 "-- (the first cell the digit's 8; cells past a row's end: none). A cell is here when the continent's land",
                 "-- texture (MapLand) and the feather it's drawn through (MapFeatherWide) are both fully opaque there and",
                 "-- in the eight cells round it: the cells are their texels, and the game draws them smoothed.",
                 "-- Generated by covergrid.py from Media/Textures/%s; regenerate with those textures rather than edit." % client,
                 "-- `world`: how far in from each edge of the world (a share of its size) the world's sea colour, drawn",
                 "-- through the same feather, hides the sea's outer colour and mottling under it.",
                 "-- `built`: the OpenMap version whose textures it was read from; Stitch.lua clips by it on that version only.",
                 "", "local _, ns = ...", "", "ns.MapCover = {",
                 "\tsize = %d, built = \"%s\",%s" % (size, version, " world = %s," % world if world else "")]
        for cont in conts:
            lines.append("\t[%d] = {" % cont)
            for row in grids[cont]:
                lines.append('\t\t"%s",' % hex_row(row))
            lines.append("\t},")
        lines.append("}")
        out = os.path.join(addon, "Data", client, "Cover.lua")
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        print("wrote %s (%d bytes)" % (out, os.path.getsize(out)))


if __name__ == "__main__":
    main()
