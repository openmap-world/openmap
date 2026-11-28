# Builds OpenMap/Data/<client>/Battlegrounds.lua: each battleground's map (Blizzard's, a uiMap the game
# has) and where the battleground's own minimap tiles lie on it, for the minimap's detail over the map
# as it zooms in (Map/Battlegrounds.lua).
#   - the battlegrounds: the Map table's PvP instances (InstanceType 3) with a uiMap placed on them
#     (UiMapAssignment); one with none (Battle for Gilneas, so far) is left out and named: the game
#     can't place the player on any map there;
#   - where the uiMap lies: its UiMapAssignment's world box (Region) and part of the map (UiMin/UiMax);
#   - the tiles: the ones the battleground's own WDT lists (MAIN: which have terrain, MAID: each one's
#     minimap texture), read from the install (tools/casc), kept where they overlap the map; each one's
#     file is checked in the install (one not there, or encrypted, is left out and named);
#   - where on the map the minimap shows (FOCUS): Blizzard's maps of them have a frame and portraits
#     round the battleground, and the minimap's tiles run on past it into land nobody reaches; the
#     minimap shows inside this part of the map only, its edges feathered (MapFeather, Stitch.lua's
#     edge mask: full from a sixth of the way in). Set by eye from the previews
#     (tools/map-preview/battlegrounds.py with OPENMAP_BG_MIX=0.5); the whole map where none is set.
# Tile (x, y) covers world Y from (32 - x) * 533.33 down and world X from (32 - y) * 533.33 down.
#
# usage: python -P tools/map-data/battlegrounds.py <cache dir> <World of Warcraft folder> [build]
#   (the tables are fetched from wago.tools into the cache; build: theirs, the client's by default)
import csv, os, struct, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "casc"))
import clients   # the client the tools build for (OPENMAP_CLIENT)
from casc import Casc

if len(sys.argv) < 3:
    sys.exit("usage: python -P tools/map-data/battlegrounds.py <cache dir> <World of Warcraft folder> [build]")
cache, wow = sys.argv[1], sys.argv[2]
BUILD = sys.argv[3] if len(sys.argv) > 3 else clients.BUILD
OUT = os.path.join(clients.DATA, "Battlegrounds.lua")
os.makedirs(cache, exist_ok=True)
UA = {"User-Agent": "openmap-tools/1"}
TILE = 1600 / 3
# [uiMapID] = u0, v0, u1, v1 (past 0 or 1: the feathered edge off the map, its full strength to the map's edge)
FOCUS = {
    1459: (0.29, -0.15, 0.67, 1.15),    # Alterac Valley: the valley, from Dun Baldar to Frostwolf Keep
    1460: (0.19, -0.15, 0.81, 1.15),    # Warsong Gulch: the gulch between the two portraits
    1461: (0.15, -0.12, 0.87, 1.12),    # Arathi Basin: the basin between the two portraits
    2524: (0.16, -0.05, 0.84, 1.15),    # Darkspear Islands: the islands, not the other isles' tiles in the corners
}


def table(name):
    path = os.path.join(cache, "%s-%s.csv" % (name, BUILD))
    # (a missing table still answers 200, with an empty or tiny body)
    if not os.path.exists(path) or os.path.getsize(path) < 100:
        url = "https://wago.tools/db2/%s/csv?build=%s" % (name, BUILD)
        print("  fetching", url, flush=True)
        open(path, "wb").write(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read())
        time.sleep(0.3)
    if os.path.getsize(path) < 100: sys.exit("empty answer for %s %s" % (name, BUILD))
    return list(csv.DictReader(open(path, encoding="utf-8")))


def chunks(data):
    out, i = {}, 0
    while i + 8 <= len(data):
        tag, size = data[i:i + 4][::-1].decode("latin1"), struct.unpack("<I", data[i + 4:i + 8])[0]
        out[tag] = data[i + 8:i + 8 + size]
        i += 8 + size
    return out


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main():
    casc = Casc(wow, clients.PRODUCT)

    def there(fid):
        try:
            return len(casc.read(fid)) > 0
        except Exception:
            return False

    maps = {int(r["ID"]): r for r in table("Map")}
    uimaps = {int(r["ID"]): r for r in table("UiMap")}
    assigned = {}
    for r in table("UiMapAssignment"):
        assigned.setdefault(int(r["MapID"]), []).append(r)
    out, left = [], []
    for mid in sorted(maps):
        m = maps[mid]
        if m["InstanceType"] != "3": continue
        rows = [r for r in assigned.get(mid, []) if int(r["UiMapID"]) in uimaps]
        if not rows:
            left.append("%d %s: no uiMap" % (mid, m["MapName_lang"]))
            continue
        a = min(rows, key=lambda r: int(r["OrderIndex"]))
        ui = int(a["UiMapID"])
        x0, y0, x1, y1 = (float(a["Region_%d" % i]) for i in (0, 1, 3, 4))
        u0, v0, u1, v1 = (float(a[k]) for k in ("UiMin_0", "UiMin_1", "UiMax_0", "UiMax_1"))
        wdt = int(m["WdtFileDataID"])
        try:
            c = chunks(casc.read(wdt))
        except Exception as e:
            left.append("%d %s: WDT %d not readable (%s)" % (mid, m["MapName_lang"], wdt, e))
            continue
        tiles, missing = {}, []
        for n in range(64 * 64):
            ty, tx = divmod(n, 64)                                  # (both chunks run row by row: y, then x)
            if not struct.unpack_from("<I", c["MAIN"], n * 8)[0] & 1: continue
            mini = struct.unpack_from("<8I", c["MAID"], n * 32)[7] if "MAID" in c else 0
            if not mini: continue
            # (the tile's world box: Y from (32 - x) * TILE down, X from (32 - y) * TILE down)
            ty0, ty1 = (32 - tx - 1) * TILE, (32 - tx) * TILE
            tx0, tx1 = (32 - ty - 1) * TILE, (32 - ty) * TILE
            if ty1 <= y0 or ty0 >= y1 or tx1 <= x0 or tx0 >= x1: continue
            if there(mini): tiles[tx * 64 + ty] = mini
            else: missing.append(mini)
        if missing:
            left.append("%d %s: %d minimap tiles not in the install (%s)" % (mid, m["MapName_lang"], len(missing),
                        ", ".join(map(str, missing[:6]))))
        out.append((ui, mid, m["MapName_lang"], (x0, y0, x1, y1), (u0, v0, u1, v1), tiles, FOCUS.get(ui, (0, 0, 1, 1))))
        print("%d %s: uiMap %d, %d tiles" % (mid, m["MapName_lang"], ui, len(tiles)))

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("-- Battlegrounds' maps (Blizzard's) and the battleground's own minimap tiles on them, for the\n")
        f.write("-- minimap's detail as the map zooms in (Map/Battlegrounds.lua):\n")
        f.write("--   [uiMapID] = { game map ID, name (the tables', English), { minX, minY, maxX, maxY: the world box\n")
        f.write("--     the map shows, yards }, { u0, v0, u1, v1: the part of the map it covers },\n")
        f.write("--     { [x * 64 + y] = minimap tile file ID (x runs east, y south; 533.33 yards each) },\n")
        f.write("--     { u0, v0, u1, v1: where on the map the minimap shows, its edges feathered } }\n")
        f.write("-- Generated by tools/map-data/battlegrounds.py from build %s's tables and the install's files;\n" % BUILD)
        f.write("-- regenerate rather than edit.\n\nlocal _, ns = ...\n\nns.MapBattlegrounds = {\n")
        for ui, mid, name, box, part, tiles, focus in out:
            f.write("\t[%d] = { %d, %s, { %s }, { %s }, {\n" % (ui, mid, lua_str(name),
                    ", ".join("%.2f" % v for v in box), ", ".join("%g" % v for v in part)))
            items = sorted(tiles.items())
            for i in range(0, len(items), 8):
                f.write("\t\t" + " ".join("[%d] = %d," % kv for kv in items[i:i + 8]) + "\n")
            f.write("\t}, { %s } },\n" % ", ".join("%g" % v for v in focus))
        f.write("}\n")
    for line in left: print("left out:", line)


main()
