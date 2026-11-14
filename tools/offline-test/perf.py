"""Offline performance test: the stitched map's work per frame while zooming out (Lua 5.1).

Usage:  python -P tools/offline-test/perf.py [--table]      (OPENMAP_CLIENT: the client, tools/clients.py)
Needs:  pip install lupa

The game's map tables (UiMap*, wago.tools) aren't in the repo, so world.py can't run without them. This
builds a world of its own from what is: the zones in Grade.lua laid out in a grid over two continents,
each with the art IDs of Reveal.lua (its overlays), so the numbers of zones, tiles and overlays are the
real map's order (about 40 zones, 480 base tiles, 800 overlays, against a player's 49 / 516 / 937).
Positions and file IDs are made up: it counts the work, it doesn't see art.

A frame's cost in game is mostly the regions drawn and the regions the client lays out again, not Lua.
So per step of a zoom out (the same calls WorldMap.lua makes on a wheel notch: S.SetZoom, S.SetView,
then a few frames of the file loader) this counts:
  drawn      textures shown with every frame above them shown (the fill the GPU draws)
  placed     textures anchored to something (hidden or not: the client lays them out each frame)
  made       regions created in the step (a font string is one: lettering built in one frame is a hitch)
  calls      calls that change a region (SetPoint, ClearAllPoints, SetAlpha, SetShown, SetTexCoord,
             SetTexture, SetVertexColor, SetDesaturation, SetSize): what a step makes the client do
  lua ms     the Lua CPU time of the step, and kb of garbage it left
It can't give frames per second: fill and layout cost are the game's. /openmap bench does that in game.
The budgets in BUDGETS are what the code does now, measured here: a change that makes a zoom out
draw, place or touch more regions than that fails (lower them when a change takes work away).
"""
import os, re, sys, time, unittest
import lupa.lua51 as lupa

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "OpenMap"))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import clients
import world

# (the world is the Forever client's whatever OPENMAP_CLIENT is: its tables stand in for the game's, and the
# retail build has its own real ones, which this test's made-up maps would fight)
# (the zoom a player's view starts at in the report, and the steps down to the whole world: a wheel
# notch is about x0.8 in OpenMap's zoom)
START_ZOOM = 12.87
NOTCH = 0.8


def read(path, encoding="utf-8"):
    with open(path, encoding=encoding) as f:
        return f.read()


def synthetic_maps():
    grade = read(os.path.join(ROOT, "Data", "Forever", "Grade.lua"), "utf-8")
    zones = [int(x) for x in re.findall(r"\[(\d+)\]\s*=", grade) if int(x) < 2000]
    reveal = read(os.path.join(ROOT, "Data", "Forever", "Reveal.lua"), "utf-8")
    arts = [int(x) for x in re.findall(r"^\t\[(\d+)\] = \{", reveal, re.M)]

    def art(i):
        base = 900000 + i * 20
        return [1002, 668, 256, 256, arts[i % len(arts)]], [base + k for k in range(12)]

    maps = {947: {"name": "Azeroth", "type": 1, "parent": 0, "rect": (0, 1, 0, 1)}}
    maps[947]["art"], maps[947]["files"] = art(0)
    conts = {1414: (0.05, 0.45, 0.2, 0.9), 1415: (0.55, 0.95, 0.15, 0.85)}
    for i, (c, r) in enumerate(conts.items()):
        maps[c] = {"name": "Continent %d" % c, "type": 2, "parent": 947, "rect": r}
        maps[c]["art"], maps[c]["files"] = art(100 + i)
        # (game map 1 is Kalimdor, 0 the Eastern Kingdoms; yards across the continent's box)
        maps[c]["asg"] = [1 - i, 0, 0, 1, 1, -10000, -10000, 10000, 10000]
    half = len(zones) // 2
    cols = 5
    for n, z in enumerate(zones):
        c = 1414 if n < half else 1415
        k = n if n < half else n - half
        cl, cr, ct, cb = conts[c]
        w, h = (cr - cl) / cols, (cb - ct) / (-(-half // cols))
        l, t = cl + (k % cols) * w, ct + (k // cols) * h
        maps[z] = {"name": "Zone %d" % z, "type": 3, "parent": c, "rect": (l, l + w * 1.1, t, t + h * 1.1)}
        maps[z]["art"], maps[z]["files"] = art(n)
    return maps


# the counting: a wrapper round each region method that changes something
PROBE = r'''
CALLS = { n = 0, by = {} }
do
	local mt = getmetatable(CreateFrame("Frame"))
	local index = mt.__index
	local counted = {}
	for _, name in ipairs({ "SetPoint", "ClearAllPoints", "SetAlpha", "SetTexCoord", "SetTexture", "SetVertexColor",
		"SetDesaturation", "SetSize", "SetWidth", "SetHeight", "SetAllPoints", "SetScale" }) do counted[name] = true end
	local wrapped = {}      -- (one wrapper a method: a closure a call would be garbage of the test's own)
	local function tally(name)
		CALLS.n = CALLS.n + 1
		CALLS.by[name] = (CALLS.by[name] or 0) + 1
	end
	mt.__index = function(t, k)
		local f = index(t, k)
		if type(f) ~= "function" then return f end
		local w = wrapped[f]
		if w then return w end
		if counted[k] then
			w = function(...) tally(k) return f(...) end
		elseif k == "Show" then   -- (a shown state that changes: Show / Hide to what it already is cost nothing)
			w = function(self, ...) if not self.__shown then tally("Show") end return f(self, ...) end
		elseif k == "Hide" then
			w = function(self, ...) if self.__shown then tally("Hide") end return f(self, ...) end
		else
			return f
		end
		wrapped[f] = w
		return w
	end
end

function PERF(ns, zooms, start, unexplored)
	local S = ns.MapStitch
	local out = { rows = {} }
	local view = CreateFrame("Frame", nil, UIParent)
	local canvas = CreateFrame("Frame", nil, view)
	if not S.Build(canvas, 100, 80, 2000) then return { built = false } end
	local st = S.stats
	out.stats = { zones = st.zones, tiles = st.tiles, overlays = st.overlays, pins = st.pins, frames = #FRAMES }
	S.Layout(S.WORLD)
	S.ApplyGrade(1, 0.1, unexplored or "show")
	local parts = S.Parts()[1][2]
	-- (the game's root is the host canvas's scale times Layout's k: about the zoom, in screen px per world
	-- unit. The stub has no scale: this is what decides when the baked tiles hand over to the live layers)
	local zNow = 1
	parts[1].GetEffectiveScale = function() return 1.08 * zNow end
	local function shown(r)
		while r do
			if not r.__shown then return false end
			r = r.__parent
		end
		return true
	end
	local function under(r, top)
		while r do if r == top then return true end r = r.__parent end
		return false
	end
	local function census()
		local drawn, placed, icons = 0, 0, 0
		for _, f in ipairs(FRAMES) do
			if f.__kind == "Texture" then
				if under(f, parts[2]) then
					if shown(f) then icons = icons + 1 end
				elseif under(f, parts[1]) then
					if shown(f) then drawn = drawn + 1 end
					if #f.__points > 0 then placed = placed + 1 end
				end
			end
		end
		return drawn, placed, icons
	end
	local k = ns.ClientMaps and ns.ClientMaps.zoom or 1
	-- the view's centre: a zone's middle, so a zoom out starts in one zone and ends on the whole world
	local l, r, t, b = S.Rect(start)
	local cu, cv = (l + r) / 2, (t + b) / 2
	local function step(z, frames)
		zNow = z
		local before, made0 = collectgarbage("count"), #FRAMES
		CALLS.n, CALLS.by = 0, {}
		local t0 = os.clock()
		S.SetZoom(z / k, z)
		S.SetView(cu, cv, 0.5 / z, 0.5 / z, z / k, z / k)
		for _ = 1, frames do NOW = NOW + 0.016 RunOnUpdate(0.016) end   -- (the stub's clock moves with the frames: files fade in by it)
		local ms = (os.clock() - t0) * 1000
		local calls, by = CALLS.n, CALLS.by
		local kb = collectgarbage("count") - before
		local drawn, placed, icons = census()
		return { zoom = z, drawn = drawn, placed = placed, icons = icons, calls = calls, ms = ms, kb = kb, by = by, made = #FRAMES - made0 }
	end
	-- the map open at the first zoom (settled: its files in), then the zoom out
	step(zooms[1], 120)
	for i = 1, #zooms do
		out.rows[#out.rows + 1] = step(zooms[i], 4)
	end
	return out
end
'''


def zooms():
    z, out = START_ZOOM, []
    while z > 1:
        out.append(round(z, 3))
        z *= NOTCH
    out.append(1)
    return out


def load_runtime():
    L = lupa.LuaRuntime(unpack_returned_tuples=True)
    L.execute(read(os.path.join(HERE, "stub.lua"), "utf-8"))
    L.execute("MAPS = " + world.lua_val(synthetic_maps()))
    L.execute(world.C_MAP)
    ns = L.eval("{}")
    load = L.eval("""function(src, name, ns)
        local fn, err = loadstring(src, "@" .. name)
        if not fn then return false, err end
        local ok, e = xpcall(function() return fn("OpenMap", ns) end, function(m) return tostring(m) .. "\\n" .. debug.traceback() end)
        return ok, e
    end""")

    def expand(rel):
        if not rel.endswith(".xml"): return [rel]
        base = os.path.dirname(rel)
        src = re.sub(r"<!--.*?-->", "", read(os.path.join(ROOT, rel), "utf-8"), flags=re.S)
        return [f for m in re.finditer(r'<(Script|Include)\s+file="([^"]+)"', src)
                for f in expand(os.path.join(base, m.group(2).replace("\\", os.sep)))]
    files = []
    for line in read(clients.toc("forever")).splitlines():
        line = line.strip()
        if line and not line.startswith("#"): files += expand(line.split(" [")[0].replace("\\", os.sep))
    for rel in files:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path): continue     # (a locale the toc lists by condition)
        ok, err = load(read(path, "utf-8-sig"), rel, ns)
        if not ok: raise RuntimeError("LOAD ERROR %s\n%s" % (rel, err))
    L.execute('FireEvent("ADDON_LOADED", "OpenMap") FireEvent("PLAYER_LOGIN") RunTimers(2)')
    L.execute(PROBE)
    return L, ns


def run(unexplored="show"):
    """the zoom out's rows: [{zoom, drawn, placed, icons, calls, ms, kb, by}]; unexplored: Options' setting (hide: the live art throughout)"""
    L, ns = load_runtime()
    res = L.eval("PERF")(ns, L.table_from(zooms()), 1429, unexplored)
    if res["built"] is False: raise RuntimeError("the world did not build")
    rows = []
    for i in range(1, len(res["rows"]) + 1):
        r = res["rows"][i]
        rows.append({k: r[k] for k in ("zoom", "drawn", "placed", "icons", "calls", "ms", "kb", "made")})
        rows[-1]["by"] = {k: v for k, v in r["by"].items()}
    errs = L.eval("ERRORS")
    stats = {k: res["stats"][k] for k in ("zones", "tiles", "overlays", "pins", "frames")}
    return rows, stats, [errs[i] for i in range(1, len(errs) + 1)]


def table(rows):
    lines = ["  zoom  drawn placed icons  calls   made   lua ms     kb"]
    for r in rows:
        lines.append("%6.2f %6d %6d %5d %6d %6d %8.2f %6.0f" % (r["zoom"], r["drawn"], r["placed"], r["icons"], r["calls"], r["made"], r["ms"], r["kb"]))
    return "\n".join(lines)


# What the code does now, measured here (the worst step of the zoom out, 10% over), per setting: "show"
# draws the zones from the baked tiles; "hide" (Options' Unexplored areas, also Classic) and a client that
# isn't English draw them live, hundreds of masked textures, which is why it has far higher budgets.
# Lua time and garbage aren't budgeted: they're the machine's noise, and /openmap bench measures them in game.
BUDGETS = {
    "show": {"drawn": 460, "placed": 1120, "calls": 1330, "made": 160},
    "hide": {"drawn": 735, "placed": 1020, "calls": 4100, "made": 160},
}


class ZoomOut(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {u: run(u) for u in BUDGETS}

    def test_no_lua_errors(self):
        for u, (rows, stats, errors) in self.runs.items():
            self.assertEqual(errors, [], u)

    def test_world_is_the_real_maps_size(self):
        # (a stand-in world that drifts from the real one makes the budgets meaningless)
        stats = self.runs["show"][1]
        self.assertTrue(30 <= stats["zones"] <= 60, stats)
        self.assertTrue(400 <= stats["tiles"] <= 600, stats)
        self.assertTrue(600 <= stats["overlays"] <= 1000, stats)

    def test_budgets(self):
        for u, limits in BUDGETS.items():
            rows = self.runs[u][0]
            for key, limit in limits.items():
                worst = max(r[key] for r in rows)
                self.assertLessEqual(worst, limit, "%s, %s: %s in one step of a zoom out, budget %s\n%s" % (u, key, worst, limit, table(rows)))

    def test_a_settled_view_costs_nothing(self):
        # (the same view again: nothing in it changed, so nothing should be touched)
        L, ns = load_runtime()
        res = L.eval("PERF")(ns, L.table_from([START_ZOOM] * 4), 1429, "show")
        self.assertEqual(res["rows"][4]["calls"], 0)


if __name__ == "__main__":
    if "--table" in sys.argv:
        bad = False
        for u in BUDGETS:
            rows, stats, errs = run(u)
            print("unexplored areas %s (%s):" % (u, "baked zone tiles" if u == "show" else "live zone art"), stats)
            print(table(rows))
            for e in errs: print("ERROR:", e[:1500])
            print("worst:", {k: round(max(r[k] for r in rows), 1) for k in ("drawn", "placed", "calls", "made", "ms", "kb")}, "\n")
            bad = bad or bool(errs)
        sys.exit(1 if bad else 0)
    unittest.main()
