# The sea chart's layout for a window of any shape (build.py; render.py mirrors the chart with it, and
# Chart.lua does the same in game: tools/offline-test/chart.py checks the two agree).
#
# All in Santiago's sheet px (his 3840 px square). The chart is a "canvas" of the window's shape, made
# round the game's map, which sits in its middle (WORLD: the box where the game's map is at least half
# there), never scaled; at least PAD of sea round it on the tighter side, more the other way. His paper
# fills it in cuts along each axis: his torn-edge strip at each end, cuts from inside his paper between,
# each cross-faded into the one before (axis()). The ornaments keep their size; where each goes is worked
# out once per window shape (place()).
import math
try:
    import numpy as np
    from scipy import ndimage as ndi
except ImportError:             # (the layout itself needs neither: tools/offline-test/chart.py runs without them)
    np = ndi = None

SIZE = 3840                     # his sheet
PAD = 480                       # least sea between the game's map and the chart's edge, on the tighter side
EDGE = 350                      # his torn edge: cuts from inside the paper keep clear of it
EDGE_CUT = 1100                 # a torn-edge strip at the chart's end: this long at most
INNER_CUT = 2600                # a cut from inside his paper: this long at most (his inside is about 3140)
SEAM = 380                      # how long two overlapping cuts cross-fade over
CLEAR = 110                     # ornaments keep this far from the game's map
ORN_GAP = 60                    # ... and from each other
EDGE_GAP = 160                  # ... and from the chart's edge (or as near as he painted them)
STEP = 160                      # how far apart the spots looked at round an ornament's home are
LEAST = 0.45                    # an ornament smaller than this is left out (it reads as a mistake, not a choice)
CORNER = 0.55                   # the ornaments in the corners (astrolabe, vignette): at most this of his size
FRAME = 0.6                     # the frame's wooden corners: this of his size, about their corner
MARGIN = 0.25                   # how much of an ornament may be in the margin round the game's map, at the last
NEAR = sorted(((x, y) for x in range(-2400, 2401, 100) for y in range(-2400, 2401, 100)
               if 0 < x * x + y * y <= 2400 ** 2), key=lambda o: o[0] ** 2 + o[1] ** 2)   # (nearest first)


def canvas_for(aspect, world):
    """The chart's size (sheet px) for a window `aspect` (width / height) round `world` (x0, y0, x1, y1)."""
    ww, wh = world[2] - world[0], world[3] - world[1]
    w, h = ww + 2 * PAD, wh + 2 * PAD
    if w / h < aspect:
        w = h * aspect
    else:
        h = w / aspect
    return w, h


def axis(n):
    """One axis of the chart, n px long: [(s0, s1, d0, d1, fade)] on his sheet and the chart. His torn-edge strip
    at each end (EDGE_CUT long at most), cuts from inside his paper between (INNER_CUT long at most, from
    [EDGE, SIZE - EDGE]); each after the first fades in over `fade` at its start, over the one before. A short
    axis: the two edge strips alone, overlapping in the middle."""
    X = min(SEAM, n / 3)
    if n <= 2 * EDGE_CUT - X:
        P = (n + X) / 2
        return [(0.0, P, 0.0, P, 0.0), (SIZE - P, float(SIZE), n - P, float(n), X)]
    k = 1
    while 2 * EDGE_CUT + k * INNER_CUT - (k + 1) * X < n:
        k += 1
    P = (n - 2 * EDGE_CUT + (k + 1) * X) / k
    out = [(0.0, float(EDGE_CUT), 0.0, float(EDGE_CUT), 0.0)]
    at = EDGE_CUT - X
    for i in range(1, k + 1):
        s0 = EDGE + (SIZE - 2 * EDGE - P) * ((i * 0.618) % 1)
        out.append((s0, s0 + P, at, at + P, X))
        at += P - X
    out.append((float(SIZE - EDGE_CUT), float(SIZE), at, at + EDGE_CUT, X))
    return out


def frame_place(box, cw, ch, scale=1.0):
    """A frame piece (its box on his sheet) pinned to its corner of a cw x ch chart, at `scale` about it."""
    x0, y0, x1, y1 = box
    right, bottom = (x0 + x1) / 2 > SIZE / 2, (y0 + y1) / 2 > SIZE / 2
    cx, cy = (SIZE if right else 0), (SIZE if bottom else 0)
    x0, x1 = cx + (x0 - cx) * scale, cx + (x1 - cx) * scale
    y0, y1 = cy + (y0 - cy) * scale, cy + (y1 - cy) * scale
    dx = cw - SIZE if right else 0
    dy = ch - SIZE if bottom else 0
    return (x0 + dx, y0 + dy, x1 + dx, y1 + dy)


# ------------------------------------------------------------------------------------------- ornaments

def filled(alpha):
    """An ornament's shape, holes filled: nothing goes inside a ring or a vignette's frame."""
    a = ndi.binary_closing(np.pad(alpha > 0.1, 8), iterations=8)
    return ndi.binary_fill_holes(a)[8:-8, 8:-8]


def grow(m, r):
    return ndi.distance_transform_edt(~m) <= r if m.any() else m


def gap(b, w):
    """How far apart two boxes are (negative: overlapping)."""
    return max(w[0] - b[2], b[0] - w[2], w[1] - b[3], b[1] - w[3])


class Placer:
    """Where the ornaments go on a chart of a given shape. Works at `k` working px per sheet px.
    ornaments: [{"box": (x0, y0, x1, y1) on his sheet, "alpha": its alpha (h, w) at k}]
    middle: the game's map's alpha on his sheet at k (SIZE * k square), world: its box (sheet px)."""

    def __init__(self, ornaments, middle, world, k):
        self.o, self.world, self.k = ornaments, world, k
        self.middle = middle > 0.3
        n = middle.shape[0]
        own = [self.stamp(o["alpha"], o["box"][0], o["box"][1], (n, n)) for o in ornaments]
        grown = [grow(m, self.s(ORN_GAP)) for m in own]
        self.orig = []   # how much each already overlaps the others' margins in his own layout
        for i, m in enumerate(own):
            others = np.zeros_like(m)
            for j, g in enumerate(grown):
                if j != i:
                    others |= g
            self.orig.append((m & others).sum() / max(1, m.sum()))
        self.cache = {}

    def s(self, v):
        return int(round(v * self.k))

    def stamp(self, alpha, x, y, shape, shape_fn=filled):
        m = np.zeros(shape, bool)
        a = shape_fn(alpha)
        X, Y = self.s(x), self.s(y)
        h, w = a.shape
        x0, y0, x1, y1 = max(0, X), max(0, Y), min(shape[1], X + w), min(shape[0], Y + h)
        if x0 < x1 and y0 < y1:
            m[y0:y1, x0:x1] = a[y0 - Y:y1 - Y, x0 - X:x1 - X]
        return m

    def shape(self, i, sc):
        key = (i, round(sc, 3))
        if key not in self.cache:
            a = self.o[i]["alpha"]
            if sc < 0.999:
                h, w = a.shape
                a = ndi.zoom(a, (max(1, int(h * sc)) / h, max(1, int(w * sc)) / w), order=1)
            self.cache[key] = filled(a)
        return self.cache[key]

    def place(self, aspect):
        """[(scale, x0, y0)] per ornament (sheet px on the chart), and the chart's size."""
        world = self.world
        cw, ch = canvas_for(aspect, world)
        ww, wh = world[2] - world[0], world[3] - world[1]
        wx0, wy0 = (cw - ww) / 2, (ch - wh) / 2
        new_world = (wx0, wy0, wx0 + ww, wy0 + wh)
        sizes = (cw, ch)
        CW, CH = self.s(cw) + 1, self.s(ch) + 1
        zone = np.zeros((CH, CW), bool)
        n = self.middle.shape[0]
        X, Y = self.s(wx0 - world[0]), self.s(wy0 - world[1])
        x0, y0, x1, y1 = max(0, X), max(0, Y), min(CW, X + n), min(CH, Y + n)
        zone[y0:y1, x0:x1] = self.middle[y0 - Y:y1 - Y, x0 - X:x1 - X]
        zone = grow(zone, self.s(CLEAR))
        taken = np.zeros_like(zone)

        def over(m, x, y, z):
            h, w = m.shape
            X, Y = self.s(x), self.s(y)
            a0, b0, a1, b1 = max(0, X), max(0, Y), min(CW, X + w), min(CH, Y + h)
            if a0 >= a1 or b0 >= b1:
                return 1.0
            return (m[b0 - Y:b1 - Y, a0 - X:a1 - X] & z[b0:b1, a0:a1]).sum() / max(1, m.sum())

        def margins(a, b):
            return min(a, EDGE_GAP), min(SIZE - b, EDGE_GAP)

        def clamp(v, size, a, b, ax):
            m0, m1 = margins(a, b)
            return min(max(v, m0), sizes[ax] - m1 - size)

        def home(a, b, ax, size):
            """In the middle's span: with it. In a band: its share of the band's room."""
            o0, o1, n0, n1 = world[ax], world[ax + 2], new_world[ax], new_world[ax + 2]
            c = (a + b) / 2
            if o0 <= c <= o1:
                return a - o0 + n0 + ((b - a) - size) / 2, "world"
            m0, m1 = margins(a, b)
            if c < o0:
                R0, R1, N0, N1 = m0, o0 - CLEAR, m0, n0 - CLEAR
            else:
                R0, R1, N0, N1 = o1 + CLEAR, SIZE - m1, n1 + CLEAR, sizes[ax] - m1
            free, freen = (R1 - R0) - (b - a), (N1 - N0) - size
            r = min(max((a - R0) / free, 0), 1) if free > 0 else 0.5
            return (N0 + r * freen if freen >= 0 else (N1 - size if c < o0 else N0)), "band"

        def hops(a, b, ax, a2, b2, size):
            """No room beside the middle: the band above or below it (left or right), as near it as it was."""
            o = 1 - ax
            before = (a2 + b2) / 2 < (world[o] + world[o + 2]) / 2
            left = (a + b) / 2 < world[ax]
            band_old = (world[ax] if left else SIZE - world[ax + 2]) - CLEAR
            near = min(1, max(0, ((world[ax] - b) if left else (a - world[ax + 2])) - CLEAR) / max(1, band_old))
            m0, m1 = margins(a2, b2)
            N0, N1 = (m0, new_world[o] - CLEAR) if before else (new_world[o + 2] + CLEAR, sizes[o] - m1)
            room = max(0, N1 - N0 - size[o])
            v = (a + b) / 2 / SIZE * sizes[ax] - size[ax] / 2
            for out in (near, near + 0.35, near + 0.7):
                out = min(out, 1)
                v2 = (N1 - size[o] - out * room) if before else (N0 + out * room)
                for kk in (0, 1, -1, 2, -2, 3, -3, 4, -4, 6, -6, 8, -8):
                    yield v + kk * STEP, v2

        def tries(i, stage):
            bx0, by0, bx1, by1 = self.o[i]["box"]
            w, h = bx1 - bx0, by1 - by0
            pins = (bx0 < 250, by0 < 250, SIZE - bx1 < 250, SIZE - by1 < 250)
            if any(pins):
                pl, pt, pr, pb = pins

                def corner(sc):
                    W_, H_ = w * sc, h * sc
                    nx = bx0 if pl else (cw - (SIZE - bx1) - W_ if pr else clamp(home(bx0, bx1, 0, W_)[0], W_, bx0, bx1, 0))
                    ny = by0 if pt else (ch - (SIZE - by1) - H_ if pb else clamp(home(by0, by1, 1, H_)[0], H_, by0, by1, 1))
                    return sc, nx, ny
                if stage == 0:
                    for sc in (1.0, 0.95, 0.9, 0.85, 0.8):
                        yield corner(sc * CORNER)
                    return

                def along(sc):   # along an edge, away from its corner
                    _, nx, ny = corner(sc)
                    for kk in range(1, 16):
                        if pt or pb:
                            yield sc, clamp(nx + (kk if pl else -kk) * STEP, w * sc, bx0, bx1, 0), ny
                        if pl or pr:
                            yield sc, nx, clamp(ny + (kk if pt else -kk) * STEP, h * sc, by0, by1, 1)
                if stage == 1:
                    for sc in (1.0, 0.9, 0.8):
                        yield from along(sc * CORNER)
                    for sc in np.arange(0.78 * CORNER, LEAST - 0.001, -0.02):
                        yield corner(float(sc))
                    return
                for sc in np.arange(0.7 * CORNER, LEAST - 0.001, -0.025):
                    yield corner(float(sc))
                    yield from along(float(sc))
                return

            def at_home(sc):
                W_, H_ = w * sc, h * sc
                (nx, kx), (ny, ky) = home(bx0, bx1, 0, W_), home(by0, by1, 1, H_)
                return (sc, clamp(nx, W_, bx0, bx1, 0), clamp(ny, H_, by0, by1, 1)), kx, ky

            def hopped(sc):
                W_, H_ = w * sc, h * sc
                _, kx, ky = at_home(sc)
                if kx == "band" and ky == "world":
                    for nx, ny in hops(bx0, bx1, 0, by0, by1, (W_, H_)):
                        yield sc, clamp(nx, W_, bx0, bx1, 0), clamp(ny, H_, by0, by1, 1)
                elif ky == "band" and kx == "world":
                    for ny, nx in hops(by0, by1, 1, bx0, bx1, (W_, H_)):
                        yield sc, clamp(nx, W_, bx0, bx1, 0), clamp(ny, H_, by0, by1, 1)

            def slid(sc):
                W_, H_ = w * sc, h * sc
                (_, nx, ny), _, _ = at_home(sc)
                for ox, oy in NEAR:
                    yield sc, clamp(nx + ox, W_, bx0, bx1, 0), clamp(ny + oy, H_, by0, by1, 1)

            if stage == 0:
                for sc in (1.0, 0.95, 0.9, 0.85, 0.8):
                    yield at_home(sc)[0]
                return
            if stage == 1:
                for sc in (1.0, 0.9):
                    yield from slid(sc)
                for sc in (1.0, 0.9, 0.8):
                    yield from hopped(sc)
                for sc in np.arange(0.76, LEAST - 0.001, -0.04):
                    yield at_home(float(sc))[0]
                    yield from hopped(float(sc))
                return
            for sc in np.arange(0.7, LEAST - 0.001, -0.1):
                yield at_home(float(sc))[0]
                yield from slid(float(sc))

        def pinned(i):
            bx0, by0, bx1, by1 = self.o[i]["box"]
            return bx0 < 250 or by0 < 250 or SIZE - bx1 < 250 or SIZE - by1 < 250

        order = sorted(range(len(self.o)), key=lambda i: (not pinned(i), -self.o[i]["alpha"].size))
        where = {}
        # stage 0: at home, a little smaller at most; 1: anywhere near, or smaller; 2 (what's left): smaller
        # still, and into the margin round the game's map (never on it: the margin's CLEAR wide)
        # (the corner pieces through all three first: they've nowhere else to go)
        steps = [(stage, i) for i in order if pinned(i) for stage in (0, 1, 2)]
        steps += [(stage, i) for stage in (0, 1, 2) for i in order if not pinned(i)]
        for stage, i in steps:
            if i in where:
                continue
            for sc, nx, ny in tries(i, stage):
                m = self.shape(i, sc)
                if over(m, nx, ny, zone) <= (0.02 if stage < 2 else MARGIN) and over(m, nx, ny, taken) <= self.orig[i] + 0.02:
                    where[i] = (sc, nx, ny)
                    break
            if i not in where and stage == 2:
                where[i] = (0.0, 0.0, 0.0)   # nowhere at all: left out
            if i in where and where[i][0] > 0:
                sc, nx, ny = where[i]
                m = self.shape(i, sc)
                taken |= grow(self.stamp_mask(m, nx, ny, (CH, CW)), self.s(ORN_GAP))
        return [where[i] for i in range(len(self.o))], (cw, ch)

    def stamp_mask(self, m, x, y, shape):
        out = np.zeros(shape, bool)
        X, Y = self.s(x), self.s(y)
        h, w = m.shape
        x0, y0, x1, y1 = max(0, X), max(0, Y), min(shape[1], X + w), min(shape[0], Y + h)
        if x0 < x1 and y0 < y1:
            out[y0:y1, x0:x1] = m[y0 - Y:y1 - Y, x0 - X:x1 - X]
        return out


def pick(chart, aspect):
    """The worked-out layout nearest a window `aspect` (by ratio)."""
    best = min(chart["layouts"], key=lambda row: abs(math.log(row[0] / aspect)))
    return best[1:]


def ops(chart, aspect):
    """What the chart draws for a window `aspect`, as Chart.lua does: every piece's place on the chart
    (sheet px, the chart's top-left at 0, 0), with the part of its texture it shows.
      canvas: (cw, ch); shift: (dx, dy), his sheet's place on the chart (the middle's offset)
      paper: [(src box on his sheet, dst box, fade x, fade y, level)]   (fade: the cut's cross-fade at its start)
      web, rays, ornaments, frame: [(texture name, dst box, u1, v1)]"""
    world = chart["world"]
    cw, ch = canvas_for(aspect, world)
    ww, wh = world[2] - world[0], world[3] - world[1]
    wx0, wy0 = (cw - ww) / 2, (ch - wh) / 2
    dx, dy = wx0 - world[0], wy0 - world[1]
    xs, ys = axis(cw), axis(ch)
    paper = []
    major_x = len(xs) >= len(ys)
    for i, (sx0, sx1, dx0, dx1, fx) in enumerate(xs):
        for j, (sy0, sy1, dy0, dy1, fy) in enumerate(ys):
            level = i * len(ys) + j if major_x else j * len(xs) + i
            paper.append(((sx0, sy0, sx1, sy1), (dx0, dy0, dx1, dy1), fx, fy, level))
    out = {"canvas": (cw, ch), "shift": (dx, dy), "paper": paper}
    out["web"] = [("Web", (dx, dy, dx + SIZE, dy + SIZE)) + tuple(chart["web"])]
    places = pick(chart, aspect)
    orn, moved = [], {}
    for k, (o, p) in enumerate(zip(chart["ornaments"], places), 1):
        x0, y0, x1, y1, u1, v1 = o
        sc = p[4]
        if sc <= 0:   # (no room for it on a chart this shape)
            continue
        x, y = unanchor(p[:4], cw, ch, world)
        orn.append(("Ornament%d" % k, (x, y, x + (x1 - x0) * sc, y + (y1 - y0) * sc), u1, v1))
        moved[k] = (x, y, sc, x0, y0)
    rays = []
    for k, (r, rose) in enumerate(zip(chart["rays"], chart["roses"]), 1):
        x0, y0, x1, y1, u1, v1 = r
        orn_k, rx, ry = rose
        if orn_k not in moved:
            continue
        nx, ny, sc, ox, oy = moved[orn_k]
        # the rose's centre, where its rays meet, carried with it (the rays keep their own size)
        mx, my = nx + (rx - ox) * sc - rx, ny + (ry - oy) * sc - ry
        rays.append(("Rays%d" % k, (x0 + mx, y0 + my, x1 + mx, y1 + my), u1, v1))
    out["rays"], out["ornaments"] = rays, orn
    out["frame"] = [("Frame%d" % k, frame_place(f[:4], cw, ch, f[6]), f[4], f[5]) for k, f in enumerate(chart["frame"], 1)]
    return out


def draw(out, chart, aspect, to_px, texture, under_middle=None):
    """Draws the chart's ops onto `out` (h, w, 3 float, 0..1): to_px(x, y) gives output px for a chart point
    (sheet px); texture(name) the texture as (h, w, 4) floats, straight alpha. The Lua draws the same:
    the dark ground, the paper's cuts (each fading in over the one before through SeamX / SeamY: a mask
    over its fade, its edge carried on past it), then the line web and each rose's rays (soft at the
    chart's edge: MapFeather), the ornaments and the frame. `under_middle`: called between the paper's
    layers and the rest (the middle's own layers go over all of it anyway; for render.py)."""
    o = ops(chart, aspect)
    cw, ch = o["canvas"]
    H, W = out.shape[:2]

    def region(box):
        x0, y0 = to_px(box[0], box[1])
        x1, y1 = to_px(box[2], box[3])
        return x0, y0, x1, y1

    def blit(img, box, mask=None):
        """img over the output box (output px), cut to the output; mask(xs, ys) -> alpha factor (output px)."""
        x0, y0, x1, y1 = region(box)
        if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H or x1 - x0 < 0.5 or y1 - y0 < 0.5:
            return
        X0, Y0, X1, Y1 = max(0, int(math.floor(x0))), max(0, int(math.floor(y0))), min(W, int(math.ceil(x1))), min(H, int(math.ceil(y1)))
        if X1 <= X0 or Y1 <= Y0:
            return
        ys = (np.arange(Y0, Y1) + 0.5 - y0) / (y1 - y0) * img.shape[0] - 0.5
        xs = (np.arange(X0, X1) + 0.5 - x0) / (x1 - x0) * img.shape[1] - 0.5
        yy, xx = np.meshgrid(ys, xs, indexing="ij")
        pm = img.copy()
        pm[..., :3] *= pm[..., 3:4]
        s = np.dstack([ndi.map_coordinates(pm[..., c], [yy, xx], order=1, mode="nearest") for c in range(4)])
        a = s[..., 3:4]
        if mask is not None:
            m = mask(np.arange(X0, X1) + 0.5, np.arange(Y0, Y1) + 0.5)[..., None]
            s, a = s * m, a * m
        dst = out[Y0:Y1, X0:X1]
        dst[:] = s[..., :3] + dst * (1 - a)

    def part(name, u0, v0, u1, v1):
        t = texture(name)
        h, w = t.shape[:2]
        return t[int(round(v0 * h)):max(int(round(v0 * h)) + 1, int(round(v1 * h))), int(round(u0 * w)):max(int(round(u0 * w)) + 1, int(round(u1 * w)))]

    # the dark ground: Backdrop, tiled every 1024 sheet px
    bd = texture("Backdrop")
    x0, y0, x1, y1 = region((0, 0, cw, ch))
    X0, Y0, X1, Y1 = max(0, int(x0)), max(0, int(y0)), min(W, int(math.ceil(x1))), min(H, int(math.ceil(y1)))
    if X1 > X0 and Y1 > Y0:
        k = (x1 - x0) / cw
        tx = ((np.arange(X0, X1) + 0.5 - x0) / k / 1024) % 1 * bd.shape[1]
        ty = ((np.arange(Y0, Y1) + 0.5 - y0) / k / 1024) % 1 * bd.shape[0]
        out[Y0:Y1, X0:X1] = bd[ty.astype(int).clip(0, bd.shape[0] - 1)][:, tx.astype(int).clip(0, bd.shape[1] - 1), :3]
    pu, pv = chart["paper"]
    seam_x, seam_y = texture("SeamX")[..., 3], texture("SeamY")[..., 3]

    def seam_mask(dbox, fx, fy):
        ox0, oy0, ox1, oy1 = region(dbox)
        fxp = fx * (ox1 - ox0) / max(1e-6, dbox[2] - dbox[0])
        fyp = fy * (oy1 - oy0) / max(1e-6, dbox[3] - dbox[1])

        def m(xs, ys):
            out_ = np.ones((len(ys), len(xs)), np.float32)
            if fx > 0:   # SeamX over [x0, x0 + fade] x the piece's height, its edge carried on (CLAMP)
                u = np.clip((xs - ox0) / fxp, 0, 1) * (seam_x.shape[1] - 1)
                v = np.clip((ys - oy0) / (oy1 - oy0), 0, 1) * (seam_x.shape[0] - 1)
                out_ *= ndi.map_coordinates(seam_x, np.meshgrid(v, u, indexing="ij"), order=1)
            if fy > 0:
                u = np.clip((xs - ox0) / (ox1 - ox0), 0, 1) * (seam_y.shape[1] - 1)
                v = np.clip((ys - oy0) / fyp, 0, 1) * (seam_y.shape[0] - 1)
                out_ *= ndi.map_coordinates(seam_y, np.meshgrid(v, u, indexing="ij"), order=1)
            return out_
        return m

    for sbox, dbox, fx, fy, level in sorted(o["paper"], key=lambda p: p[4]):
        img = part("Paper", sbox[0] / SIZE * pu, sbox[1] / SIZE * pv, sbox[2] / SIZE * pu, sbox[3] / SIZE * pv)
        blit(img, dbox, seam_mask(dbox, fx, fy) if (fx > 0 or fy > 0) else None)
    if under_middle:
        under_middle()
    # the lines soft at the chart's edge: MapFeather over the whole chart
    feather = texture("MapFeather")[..., 3]
    fx0, fy0, fx1, fy1 = region((0, 0, cw, ch))

    def edge(xs, ys):
        u = np.clip((xs - fx0) / (fx1 - fx0), 0, 1) * (feather.shape[1] - 1)
        v = np.clip((ys - fy0) / (fy1 - fy0), 0, 1) * (feather.shape[0] - 1)
        return ndi.map_coordinates(feather, np.meshgrid(v, u, indexing="ij"), order=1)
    for name, box, u1, v1 in o["web"] + o["rays"]:
        blit(part(name, 0, 0, u1, v1), box, edge)
    for name, box, u1, v1 in o["ornaments"] + o["frame"]:
        blit(part(name, 0, 0, u1, v1), box)
    return o


def load_chart(path):
    """Data/Chart.lua as Python (lists from 1-based tables)."""
    from lupa.lua51 import LuaRuntime
    lua = LuaRuntime(unpack_returned_tuples=True)
    ns = lua.eval("{}")
    lua.execute("function _load(src, ns) local f = assert(loadstring(src)) return f('OpenMap', ns) end")
    with open(path, encoding="utf-8") as f:
        lua.globals()._load(f.read(), ns)

    def py(v):
        if hasattr(v, "keys"):
            keys = list(v.keys())
            if keys and all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
                return [py(v[k]) for k in range(1, len(keys) + 1)]
            return {k: py(v[k]) for k in keys}
        return v
    return py(ns.MapChart)


def anchored(box, cw, ch, world):
    """An ornament's place as Chart.lua keeps it: per axis, which edge it's measured from (0: the chart's
    near edge, 1: the middle's near edge, 2: the chart's far edge) and how far."""
    ww, wh = world[2] - world[0], world[3] - world[1]
    wx0, wy0 = (cw - ww) / 2, (ch - wh) / 2
    out = []
    for a, b, w0, w1, n in ((box[0], box[2], wx0, wx0 + ww, cw), (box[1], box[3], wy0, wy0 + wh, ch)):
        c = (a + b) / 2
        if c < w0:
            out += [0, a]
        elif c > w1:
            out += [2, n - a]
        else:
            out += [1, a - w0]
    return out


def unanchor(anchor, cw, ch, world):
    """The inverse: an ornament's left and top on a cw x ch chart."""
    ww, wh = world[2] - world[0], world[3] - world[1]
    wx0, wy0 = (cw - ww) / 2, (ch - wh) / 2
    ax, ox, ay, oy = anchor
    x = ox if ax == 0 else (wx0 + ox if ax == 1 else cw - ox)
    y = oy if ay == 0 else (wy0 + oy if ay == 1 else ch - oy)
    return x, y
