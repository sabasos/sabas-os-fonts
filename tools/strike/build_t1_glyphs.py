"""
build_t1_glyphs.py — generate T1 Core UFO glyphs programmatically.

Strategy:
  - Base glyphs: drawn with correct §4.3 metrics (x-height 540, cap 720,
    vertical stem 88, horizontal stem 76, advance from spec table)
  - Accented glyphs: components referencing base + combining mark anchor
  - Combining marks: drawn as standalone glyphs
  - Symbols/punctuation: drawn directly

Run from sabas-fonts/:
  python tools/strike/build_t1_glyphs.py
"""

from __future__ import annotations
import warnings, os, sys
warnings.filterwarnings("ignore")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))

from pathlib import Path
import math
import unicodedata
import ufoLib2

UFO_PATH = Path("sources/sabas-ui/SabasUI-Regular.ufo")

# §4.3 metrics
UPM       = 1000
XHEIGHT   = 540
CAPHEIGHT = 720
VSTEM     = 88    # vertical stem
HSTEM     = 76    # horizontal stem
ASCENDER  = 750
DESCENDER = -205

# Optical corrections.
#
# OVS — overshoot. Round forms must exceed the flat ones at top and bottom or
# the eye reads them as smaller. Applied to *both* the outer and inner radius of
# a round form so the stroke thickness at the apex stays at HSTEM.
OVS       = 10

# Curve handles. A circle wants 0.5523 in both directions, but a type 'o' drawn
# that way looks weak: the apex is too pointed and the shoulders too empty.
# Lengthening the horizontal handle at the top/bottom extrema flattens the apex
# and fills the shoulders, which is what makes a drawn 'o' read as round.
K_CIRCLE  = 0.5523        # true circle — dots, and anything genuinely circular
K_FLAT    = 0.62          # horizontal handle leaving a top/bottom extremum
K_SIDE    = 0.55          # vertical handle leaving a left/right extremum

# Stem compensation. A stem enclosed by other stems reads darker than an
# isolated one, and the side of a curve reads thinner than a straight stem of
# the same measure. Drawing every stem at exactly VSTEM produces uneven colour,
# so dense letters come in slightly lighter and curve sides slightly heavier.
VSTEM_TIGHT = VSTEM - 4   # 84 — middle stems of m, and n/u/h shoulders' partners
CSTEM       = HSTEM + 4   # 80 — thickest point of a round stroke's side
DSTEM       = VSTEM - 4   # 84 — diagonals, measured square to the stroke
JOIN        = 20

# DSTEM — a diagonal at full stem weight reads heavy, partly because two of them
# meet and darken the join, so the diagonals come in a little under VSTEM. It is
# a *perpendicular* measure: the horizontal width of the stroke is larger, by
# 1/cos of its angle, and that horizontal width is what a coordinate names.

# JOIN — how far a bowl reaches into the stem it springs from. A bowl that stops
# exactly on the stem's face leaves a coincident edge: the rasteriser shows a
# seam along it, the autohinter reads two stems where there is one, and the
# boolean union either refuses to merge the pieces or mangles the counter.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def glyph_name(cp: int) -> str:
    """Canonical glyph name for a codepoint."""
    try:
        n = unicodedata.name(chr(cp)).lower()
        n = n.replace(" ", "_").replace("-", "_")
        return n
    except ValueError:
        return f"uni{cp:04X}"


def uni_name(cp: int) -> str:
    return f"uni{cp:04X}"


def add_glyph(font: ufoLib2.Font, name: str, width: int, unicode_val: int | None = None) -> ufoLib2.Glyph:
    if name in font:
        g = font[name]
    else:
        font.newGlyph(name)
        g = font[name]
    g.width = width
    if unicode_val is not None:
        g.unicodes = [unicode_val]
    g.clearContours()
    g.clearComponents()
    return g


def rect(g: ufoLib2.Glyph, x0: int, y0: int, x1: int, y1: int) -> None:
    """Add a filled rectangle contour from two opposite corners."""
    if x1 <= x0 or y1 <= y0:
        raise ValueError(
            f"rect({x0}, {y0}, {x1}, {y1}) on {g.name!r} is empty or inverted. "
            f"rect() takes absolute corners; use rectwh() for x/y/width/height."
        )
    pen = g.getPen()
    pen.moveTo((x0, y0))
    pen.lineTo((x1, y0))
    pen.lineTo((x1, y1))
    pen.lineTo((x0, y1))
    pen.closePath()


def rectwh(g: ufoLib2.Glyph, x: int, y: int, w: int, h: int) -> None:
    """Add a filled rectangle from an origin plus a width and height."""
    rect(g, x, y, x + w, y + h)


def oval(g: ufoLib2.Glyph, cx: int, cy: int, rx: int, ry: int, clockwise: bool = False,
         kflat: float = K_FLAT, kside: float = K_SIDE) -> None:
    """Add an optically corrected oval contour.

    kflat governs the horizontal handle leaving the top and bottom extrema, and
    kside the vertical handle leaving the left and right extrema. The defaults
    flatten the apex and fill the shoulders; pass kflat=kside=K_CIRCLE for a
    true circle (dots, and anything that should be geometrically circular).
    """
    k = int(kflat * rx)
    kv = int(kside * ry)
    pen = g.getPen()
    if not clockwise:
        pen.moveTo((cx, cy - ry))
        pen.curveTo((cx + k, cy - ry), (cx + rx, cy - kv), (cx + rx, cy))
        pen.curveTo((cx + rx, cy + kv), (cx + k, cy + ry), (cx, cy + ry))
        pen.curveTo((cx - k, cy + ry), (cx - rx, cy + kv), (cx - rx, cy))
        pen.curveTo((cx - rx, cy - kv), (cx - k, cy - ry), (cx, cy - ry))
    else:
        pen.moveTo((cx, cy - ry))
        pen.curveTo((cx - k, cy - ry), (cx - rx, cy - kv), (cx - rx, cy))
        pen.curveTo((cx - rx, cy + kv), (cx - k, cy + ry), (cx, cy + ry))
        pen.curveTo((cx + k, cy + ry), (cx + rx, cy + kv), (cx + rx, cy))
        pen.curveTo((cx + rx, cy - kv), (cx + k, cy - ry), (cx, cy - ry))
    pen.closePath()


def _arc(cx: float, cy: float, rx: float, ry: float, a0: float, a1: float
         ) -> list[tuple[tuple[float, float], ...]]:
    """Cubic segments along an elliptical arc, from angle a0 to a1 in degrees.

    Angles run counterclockwise from 3 o'clock, so a1 > a0 sweeps the same way an
    outer contour does. Each piece gets the exact circular handle length,
    4/3·tan(Δ/4), scaled by the same optical correction oval() applies: longest
    where the tangent is horizontal, at the top and bottom of the form, shortest
    at its sides.

    The arc is cut *on* the multiples of 90° it crosses, not into equal pieces:
    those four angles are the ellipse's extremes, and an extreme the outline only
    passes near is one the hinter cannot snap to and one where the overshoot is no
    longer exactly OVS. A 306° sweep split four ways evenly — which is what c and
    e used to get — misses all four of them.

    Returns a list of (p1, p2, p3) triples to feed to curveTo; the caller is
    responsible for being at the arc's first point already.
    """
    import math
    step = 90 if a1 >= a0 else -90
    cuts = [a0]
    q = math.floor(a0 / 90) * 90 + (90 if step > 0 else 0)
    while (q - a1) * step < -1e-9:
        if abs(q - cuts[-1]) > 1e-9:
            cuts.append(q)
        q += step
    if abs(a1 - cuts[-1]) > 1e-9:
        cuts.append(a1)
    out = []
    for c0, c1 in zip(cuts, cuts[1:]):
        b0, b1 = math.radians(c0), math.radians(c1)
        k = 4 / 3 * math.tan((b1 - b0) / 4)

        def optical(t: float) -> float:
            # |sin| is 1 at the top and bottom of the form, 0 at its sides
            s = abs(math.sin(t))
            return (K_SIDE + (K_FLAT - K_SIDE) * s) / K_CIRCLE

        def point(t):
            return (cx + rx * math.cos(t), cy + ry * math.sin(t))

        def tangent(t):
            return (-rx * math.sin(t), ry * math.cos(t))

        p0, p3 = point(b0), point(b1)
        t0, t3 = tangent(b0), tangent(b1)
        f0, f3 = k * optical(b0), k * optical(b1)
        out.append(((p0[0] + f0 * t0[0], p0[1] + f0 * t0[1]),
                    (p3[0] - f3 * t3[0], p3[1] - f3 * t3[1]),
                    p3))
    return out


def arc_stroke(g: ufoLib2.Glyph, cx: float, cy: float, rx: float, ry: float,
               wx: float, wy: float, a0: float, a1: float) -> None:
    """A stroke that follows an elliptical arc: c's bow, e's ring, S's bowls.

    The outer edge runs from a0 to a1, a flat cut crosses the end, the inner edge
    comes back and a second cut closes the start. ``wx`` and ``wy`` are the wall
    thickness at the sides and at the top/bottom — a round stroke's side has to
    be the heavier of the two or the form looks pinched.

    Terminals are placed by angle rather than by trimming a quadrant to a
    convenient number, so a stroke can stop anywhere without the arc that
    remains being a different ellipse from the one it was drawn on.
    """
    import math
    pen = g.getPen()
    start = (cx + rx * math.cos(math.radians(a0)), cy + ry * math.sin(math.radians(a0)))
    pen.moveTo(start)
    for seg in _arc(cx, cy, rx, ry, a0, a1):
        pen.curveTo(*seg)
    inner_end = (cx + (rx - wx) * math.cos(math.radians(a1)),
                 cy + (ry - wy) * math.sin(math.radians(a1)))
    pen.lineTo(inner_end)
    for seg in _arc(cx, cy, rx - wx, ry - wy, a1, a0):
        pen.curveTo(*seg)
    pen.closePath()


def ovalwh(g: ufoLib2.Glyph, x: int, y: int, w: int, h: int, clockwise: bool = False,
           **kw) -> None:
    """Add an oval from a bounding box: origin plus width and height.

    oval() takes a centre and two radii. Passing box coordinates to it silently
    produces a shape four times too big in the wrong place, so anything that
    thinks in bounding boxes goes through here instead.
    """
    oval(g, x + w // 2, y + h // 2, w // 2, h // 2, clockwise, **kw)


def dot(g: ufoLib2.Glyph, cx: int, cy: int, r: int, clockwise: bool = False) -> None:
    """A true circle — for dots, which should not be optically flattened."""
    oval(g, cx, cy, r, r, clockwise, kflat=K_CIRCLE, kside=K_CIRCLE)


def _hspan(x0: float, y0: float, x1: float, y1: float, weight: float) -> float:
    """Horizontal width of a diagonal whose perpendicular weight is ``weight``."""
    import math
    return weight * math.hypot(x1 - x0, y1 - y0) / abs(y1 - y0)


def band(g: ufoLib2.Glyph, x0: float, y0: float, x1: float, y1: float,
         weight: float = DSTEM, cut: str = "hh") -> None:
    """A straight diagonal of even weight, between two points on its centre line.

    Both long edges are generated from the one slope, so the stroke cannot taper.
    Tracing a diagonal's two edges to separately chosen corners — the obvious way
    to draw an A — gives them slightly different slopes and the stroke loses a
    third of its weight on the way to the vertex.

    ``cut`` finishes each end: "h" cuts it square across x, the usual finish at a
    baseline or an x-height; "v" cuts it square across y, which is how an end is
    hidden inside the stem it springs from.
    """
    import math
    dx, dy = x1 - x0, y1 - y0
    length = math.hypot(dx, dy)
    sign = 1.0 if dx * dy > 0 else -1.0

    def offset(kind: str) -> tuple[float, float]:
        if kind == "h":
            return (weight * length / abs(dy) / 2, 0.0)
        # A vertical cut leans the other way from a horizontal one: moving along
        # +x on a rising stroke is the same as moving along -y.
        return (0.0, -sign * weight * length / abs(dx) / 2)

    o0, o1 = offset(cut[0]), offset(cut[1])
    pts = [(x0 - o0[0], y0 - o0[1]), (x0 + o0[0], y0 + o0[1]),
           (x1 + o1[0], y1 + o1[1]), (x1 - o1[0], y1 - o1[1])]
    pen = g.getPen()
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()


def vee(g: ufoLib2.Glyph, ax: float, ay: float, bx: float, by: float,
        cx: float, cy: float, weight: float = DSTEM) -> None:
    """Two even-weight diagonals meeting at a point: A, V, v, M, and W's halves.

    ``(ax, ay)`` is the left arm's open end and ``(cx, cy)`` the right arm's,
    both given as the *outer* corner — the one further from the other arm. The
    outer edges meet exactly at the vertex ``(bx, by)``, giving a clean point,
    and each inner edge runs parallel to its own outer edge, so an arm carries
    its weight all the way into the join. The notch where the two inner edges
    cross is solved for rather than guessed.
    """
    wl = _hspan(ax, ay, bx, by, weight)
    wr = _hspan(cx, cy, bx, by, weight)
    sl = (bx - ax) / (by - ay)          # x per y along the left arm
    sr = (bx - cx) / (by - cy)
    # inner edges: x = (ax + wl) + sl·(y - ay) and x = (cx - wr) + sr·(y - cy)
    ny = ((cx - wr - sr * cy) - (ax + wl - sl * ay)) / (sl - sr)
    nx = ax + wl + sl * (ny - ay)
    pen = g.getPen()
    pen.moveTo((ax, ay))
    for p in [(ax + wl, ay), (nx, ny), (cx - wr, cy), (cx, cy), (bx, by)]:
        pen.lineTo(p)
    pen.closePath()


# ---------------------------------------------------------------------------
# A centreline stroker
# ---------------------------------------------------------------------------
#
# Everything above draws a shape by describing its outline. That is the right way
# to draw a rectangle or a ring, and it stops being the right way the moment a
# stroke has to change direction while holding an even weight — an s's spine, a
# g's tail, a 5's bowl, an ampersand. Traced by hand, the two edges of such a
# stroke drift apart and it swells, or they cross and the fill cancels itself to
# a hairline. Both of those happened here, in exactly those letters.
#
# So those letters are drawn the way they are written, as one centre line, and
# this code lays the weight on afterwards. The nib is an ellipse, wider than it
# is tall, which is what makes a curved stroke heavy where it runs vertically and
# light where it runs horizontally without anyone choosing those two numbers
# twice: the offset of an elliptical nib along a unit normal is exactly
# hypot(ax·nx, ay·ny), so the modulation falls out of the nib instead of being a
# correction applied on top of a circle.
#
# The offset of a cubic is not a cubic, so each stretch is sampled and refitted.
# Endpoints and end tangents are taken from the offset curve itself and only the
# two handle lengths are solved for, by least squares over the samples. Keeping
# the endpoints and tangents fixed is the point: a fitter free to move them would
# leave a kink at every segment boundary, and a kink in a letter's outline is a
# bright dot in a hinted raster.

def _bez_pt(s, t: float) -> tuple[float, float]:
    """Point at parameter ``t`` on the cubic ``s`` = (p0, p1, p2, p3)."""
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = s
    u = 1.0 - t
    w0, w1, w2, w3 = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
    return (w0 * ax + w1 * bx + w2 * cx + w3 * dx,
            w0 * ay + w1 * by + w2 * cy + w3 * dy)


def _bez_dir(s, t: float) -> tuple[float, float]:
    """Unit tangent at ``t``, falling back to the chord at a degenerate handle."""
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = s
    u = 1.0 - t
    vx = 3 * (u * u * (bx - ax) + 2 * u * t * (cx - bx) + t * t * (dx - cx))
    vy = 3 * (u * u * (by - ay) + 2 * u * t * (cy - by) + t * t * (dy - cy))
    n = math.hypot(vx, vy)
    if n < 1e-9:
        vx, vy = dx - ax, dy - ay
        n = math.hypot(vx, vy) or 1.0
    return (vx / n, vy / n)


def lseg(p0, p1):
    """A straight centreline stretch, as a cubic with collinear handles."""
    return (tuple(p0),
            (p0[0] + (p1[0] - p0[0]) / 3.0, p0[1] + (p1[1] - p0[1]) / 3.0),
            (p0[0] + (p1[0] - p0[0]) * 2 / 3.0, p0[1] + (p1[1] - p0[1]) * 2 / 3.0),
            tuple(p1))


def spline(nodes) -> list:
    """Cubic chain through ``nodes``, each ``(x, y, degrees, h_in, h_out)``.

    The direction is the tangent the curve must have at that node, so two
    stretches meeting there are tangent-continuous by construction rather than by
    the two sets of handles happening to line up. ``h_in``/``h_out`` are handle
    lengths in units; None takes a third of the chord, which is the right answer
    for a gentle bend and too short for a quarter turn.
    """
    segs = []
    for (x0, y0, a0, _, h0), (x1, y1, a1, h1, _) in zip(nodes, nodes[1:]):
        chord = math.hypot(x1 - x0, y1 - y0)
        f0 = chord / 3.0 if h0 is None else h0
        f1 = chord / 3.0 if h1 is None else h1
        d0 = (math.cos(math.radians(a0)), math.sin(math.radians(a0)))
        d1 = (math.cos(math.radians(a1)), math.sin(math.radians(a1)))
        segs.append(((x0, y0),
                     (x0 + f0 * d0[0], y0 + f0 * d0[1]),
                     (x1 - f1 * d1[0], y1 - f1 * d1[1]),
                     (x1, y1)))
    return segs


def arc_spline(cx: float, cy: float, rx: float, ry: float,
               a0: float, a1: float) -> list:
    """An exact elliptical arc as a centreline chain, for stroke() to walk."""
    start = (cx + rx * math.cos(math.radians(a0)), cy + ry * math.sin(math.radians(a0)))
    segs, p0 = [], start
    for c1, c2, p3 in _arc(cx, cy, rx, ry, a0, a1):
        segs.append((p0, c1, c2, p3))
        p0 = p3
    return segs


def _fit_cubic(pts, t0, t1):
    """Least-squares cubic through ``pts`` with fixed ends and end tangents.

    Solves only for the two handle lengths, over a chord-length parameterisation
    of the samples. Returns a (p0, c1, c2, p3) tuple.
    """
    p0, p3 = pts[0], pts[-1]
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = d[-1]
    if total < 1e-9:
        return (p0, p0, p3, p3)
    c11 = c12 = c22 = r1 = r2 = 0.0
    for dist, p in zip(d, pts):
        u = dist / total
        v = 1.0 - u
        b1, b2 = 3 * v * v * u, 3 * v * u * u
        a1 = (b1 * t0[0], b1 * t0[1])
        a2 = (-b2 * t1[0], -b2 * t1[1])
        ex = p[0] - (v ** 3 + b1) * p0[0] - (b2 + u ** 3) * p3[0]
        ey = p[1] - (v ** 3 + b1) * p0[1] - (b2 + u ** 3) * p3[1]
        c11 += a1[0] * a1[0] + a1[1] * a1[1]
        c12 += a1[0] * a2[0] + a1[1] * a2[1]
        c22 += a2[0] * a2[0] + a2[1] * a2[1]
        r1 += a1[0] * ex + a1[1] * ey
        r2 += a2[0] * ex + a2[1] * ey
    det = c11 * c22 - c12 * c12
    if abs(det) < 1e-9:
        f0 = f1 = total / 3.0
    else:
        f0 = (r1 * c22 - r2 * c12) / det
        f1 = (r2 * c11 - r1 * c12) / det
    lo, hi = total * 0.02, total * 1.2
    f0 = min(max(f0, lo), hi)
    f1 = min(max(f1, lo), hi)
    return (p0, (p0[0] + f0 * t0[0], p0[1] + f0 * t0[1]),
            (p3[0] - f1 * t1[0], p3[1] - f1 * t1[1]), p3)


def _slide(cub, end: int, through, direction: float):
    """Move a fitted cubic's terminal point along its own tangent onto a cut.

    ``through`` is a point on the cut and ``direction`` its angle, so a terminal
    can be finished square to the baseline however obliquely the stroke arrives.
    The adjacent handle moves with the point, which leaves the tangent — and so
    the smoothness of the join behind it — untouched.
    """
    p = cub[3] if end else cub[0]
    h = cub[2] if end else cub[1]
    tx, ty = p[0] - h[0], p[1] - h[1]
    dx, dy = math.cos(math.radians(direction)), math.sin(math.radians(direction))
    cross = tx * dy - ty * dx
    if abs(cross) < 1e-6:
        return cub
    s = ((through[0] - p[0]) * dy - (through[1] - p[1]) * dx) / cross
    off = (s * tx, s * ty)
    moved = ((p[0] + off[0], p[1] + off[1]), (h[0] + off[0], h[1] + off[1]))
    return (cub[0], cub[1], moved[1], moved[0]) if end else \
           (moved[0], moved[1], cub[2], cub[3])


def stroke(g: ufoLib2.Glyph, segs, wx: float, wy: float,
           cap0: float | None = None, cap1: float | None = None,
           samples: int = 24) -> None:
    """Lay an elliptical nib of width ``wx`` and height ``wy`` along a centreline.

    ``segs`` is a continuous open chain of cubics, from spline() or arc_spline().
    ``cap0``/``cap1`` are the angles at which to cut the two ends — 0 for a cut
    parallel to the baseline, 90 for one square to it, None to leave the end cut
    square to the stroke itself. An end that disappears inside a stem needs no
    cap at all; the union pass swallows it.
    """
    ax, ay = wx / 2.0, wy / 2.0
    centres, dirs, keys = [], [], [0]
    for i, s in enumerate(segs):
        d0, d1 = _bez_dir(s, 0.0), _bez_dir(s, 1.0)
        turn = math.degrees(math.acos(max(-1.0, min(1.0, d0[0] * d1[0] + d0[1] * d1[1]))))
        pieces = max(1, math.ceil(turn / 40.0))
        n = samples * pieces
        start = keys[-1]
        for j in range(0 if i == 0 else 1, n + 1):
            t = j / n
            centres.append(_bez_pt(s, t))
            dirs.append(_bez_dir(s, t))
        end = len(centres) - 1
        for k in range(1, pieces + 1):
            keys.append(start + (end - start) * k // pieces)

    def edge(side: int) -> list:
        pts = []
        for (px, py), (tx, ty) in zip(centres, dirs):
            nx, ny = -ty, tx
            d = math.hypot(ax * nx, ay * ny) * side
            pts.append((px + d * nx, py + d * ny))
        tans = []
        for i in range(len(pts)):
            a = pts[max(0, i - 1)]
            b = pts[min(len(pts) - 1, i + 1)]
            vx, vy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(vx, vy) or 1.0
            tans.append((vx / n, vy / n))
        cubs = [_fit_cubic(pts[a:b + 1], tans[a], tans[b]) for a, b in zip(keys, keys[1:])]
        if cap0 is not None:
            cubs[0] = _slide(cubs[0], 0, centres[0], cap0)
        if cap1 is not None:
            cubs[-1] = _slide(cubs[-1], 1, centres[-1], cap1)
        return cubs

    left, right = edge(1), edge(-1)
    pen = g.getPen()
    pen.moveTo(left[0][0])
    for c in left:
        pen.curveTo(c[1], c[2], c[3])
    pen.lineTo(right[-1][3])
    for c in reversed(right):
        pen.curveTo(c[2], c[1], c[0])
    pen.closePath()


def comma_shape(g: ufoLib2.Glyph, cx: int, cy: int, r: int = 55,
                drop: int = 240) -> float:
    """A comma: a round bowl with a tail sweeping down and to the left.

    ``cy`` is the centre of the bowl and ``drop`` how far below it the tail
    reaches. The bowl and the tail are separate contours that overlap inside the
    bowl; the union pass in main() merges them into one outline.

    Returns the mark's vertical centre, which is the axis to mirror about when
    turning a closing quote into an opening one.
    """
    dot(g, cx, cy, r)
    tail = cy - drop
    pen = g.getPen()
    pen.moveTo((cx + int(r * 0.62), cy + 10))
    pen.curveTo((cx + int(r * 0.80), cy - 60), (cx + int(r * 0.55), cy - 130),
                (cx - int(r * 0.29), tail))
    pen.lineTo((cx - r - 1, tail + 40))
    pen.curveTo((cx - int(r * 0.29), cy - 120), (cx - int(r * 0.36), cy - 40),
                (cx - int(r * 0.55), cy + 10))
    pen.closePath()
    return (cy + r + tail) / 2


def rotate180(g: ufoLib2.Glyph, cx: float, cy: float) -> None:
    """Turn a glyph's contours through 180° about (cx, cy), in place."""
    flip_y(g, cy)
    flip_x(g, cx)


def shift_x(g: ufoLib2.Glyph, dx: float) -> None:
    """Move a glyph's contours horizontally, in place."""
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.transformPen import TransformPen
    rec = RecordingPen()
    g.draw(rec)
    g.clearContours()
    rec.replay(TransformPen(g.getPen(), (1, 0, 0, 1, dx, 0)))


# Target sidebearings, as (left, right). The advance is recomputed from the ink
# width, so these two numbers fix both where the outline sits and how wide the
# glyph is. Only glyphs the drawing code got wrong are listed; everything else
# already lands within a few units of its neighbours.
SIDEBEARINGS: dict[str, tuple[int, int]] = {
    # The diagonals were drawn hard against the origin — zero sidebearings on
    # both sides, so Av, xv, VA and every similar pair collided outright.
    "v": (26, 26), "w": (22, 22), "x": (24, 24), "y": (24, 22),
    "A": (18, 18), "V": (18, 18), "W": (14, 14), "X": (20, 20), "Y": (18, 18),
    # i and j were spaced as though they were as wide as n.
    "i": (60, 60), "j": (40, 60),
    # Flat-sided forms whose arms or terminals nearly touched the advance.
    "c": (48, 40), "f": (60, 30), "E": (60, 50), "F": (60, 50), "L": (60, 40),
    # Bowls widened above; give them all the same sidebearings as O.
    "B": (60, 60), "D": (60, 60), "P": (60, 60), "R": (60, 60), "G": (60, 60),
    "J": (56, 60),
    # Tabular figures keep the 580-unit advance and centre their ink in it.
    # Only the figures whose ink width divides evenly into 580 belong here, since
    # respace sets the advance to lsb + ink + rsb: one (174 wide) and four (440).
    # three and five had (85, 85) here, which quietly set their advances to 570
    # and broke the tabular column; they are centred by construction instead.
    "one": (188, 188), "four": (70, 70),
}


def respace(font: ufoLib2.Font, targets: dict[str, tuple[int, int]] = SIDEBEARINGS) -> None:
    """Move outlines and set advances so each glyph hits its target sidebearings.

    Must run before the accented letters are composed: place_accent centres each
    mark on the base's ink, so the bases have to be in their final positions.
    """
    from fontTools.pens.boundsPen import BoundsPen
    for name, (lsb, rsb) in targets.items():
        if name not in font:
            continue
        g = font[name]
        if g.components:
            continue          # composites follow their bases
        p = BoundsPen(font)
        g.draw(p)
        if p.bounds is None:
            continue
        x0, _, x1, _ = p.bounds
        if lsb != x0:
            shift_x(g, lsb - x0)
        g.width = round(lsb + (x1 - x0) + rsb)


def union_all(font: ufoLib2.Font) -> int:
    """Merge overlapping contours glyph by glyph.

    Several letters are built from pieces that overlap on purpose — the comma's
    bowl and tail, a's bowl and stem, the accents' components. Overlaps left in
    the outline show up as seams when the rasteriser fills them and they confuse
    the autohinter, so they are unioned away once everything is drawn.
    """
    from booleanOperations import union
    from fontTools.pens.recordingPen import RecordingPointPen
    merged = 0
    for g in font:
        if g.components or len(g.contours) < 2:
            continue
        rec = RecordingPointPen()          # booleanOperations emits point-pen calls
        try:
            union(list(g.contours), rec)
        except Exception:
            continue          # leave anything the boolean engine chokes on alone
        if not rec.value:
            continue
        before = len(g.contours)
        g.clearContours()
        rec.replay(g.getPointPen())
        if len(g.contours) != before:
            merged += 1
    return merged


def flip_y(g: ufoLib2.Glyph, axis: float) -> None:
    """Mirror a glyph's contours vertically about y=axis, in place.

    Used to derive u from n and so on, which guarantees the two letters share
    exactly the same shoulder weight and curvature.
    """
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.transformPen import TransformPen
    rec = RecordingPen()
    g.draw(rec)
    g.clearContours()
    tp = TransformPen(g.getPen(), (1, 0, 0, -1, 0, 2 * axis))
    rec.replay(tp)


def flip_x(g: ufoLib2.Glyph, axis: float) -> None:
    """Mirror a glyph's contours horizontally about x=axis, in place."""
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.transformPen import TransformPen
    rec = RecordingPen()
    g.draw(rec)
    g.clearContours()
    tp = TransformPen(g.getPen(), (-1, 0, 0, 1, 2 * axis, 0))
    rec.replay(tp)


# Shoulder geometry, shared by n m h r u and their derivatives.
#
# The naive construction — one cubic from stem to stem with both handles at the
# x-height — peaks at only three quarters of the intended rise, leaving an apex
# about a quarter of HSTEM deep. These letters are therefore drawn as a single
# contour whose outer edge genuinely reaches the x-height and whose counter is
# offset from it by HSTEM, so the shoulder carries the same weight as the stems.

SHOULDER_FLAT = 0.38   # fraction of the run that stays flat at the apex
SHOULDER_H    = 0.55   # horizontal handle, as a fraction of the run
SHOULDER_V    = 0.45   # vertical handle, as a fraction of the drop
SHOULDER_KNEE = 0.574  # height at which the shoulder has become a plain stem


def apex_end(x_from: int, x_to: int) -> int:
    """The x at which a flat apex gives way to the descending curve."""
    return x_from + int((x_to - x_from) * SHOULDER_FLAT)


def curve_down(pen, x_from: int, y_top: int, x_to: int, y_knee: int) -> None:
    """Shoulder edge descending from a flat apex into a stem."""
    pen.curveTo((x_from + int((x_to - x_from) * SHOULDER_H), y_top),
                (x_to, y_top - int((y_top - y_knee) * SHOULDER_V)),
                (x_to, y_knee))


def curve_up(pen, x_from: int, y_knee: int, x_to: int, y_top: int) -> None:
    """Shoulder edge rising out of a stem into a flat apex (reverse of above)."""
    pen.curveTo((x_from, y_top - int((y_top - y_knee) * SHOULDER_V)),
                (x_to + int((x_from - x_to) * SHOULDER_H), y_top),
                (x_to, y_top))


def n_shape(g: ufoLib2.Glyph, x0: int, x3: int, y_top: int,
            stem: int = VSTEM, thick: int = HSTEM) -> None:
    """The n-form: two stems joined by a shoulder, as one contour.

    Drawn as a single contour so the shoulder and the stems are continuous ink
    rather than three abutting pieces meeting on coincident edges. The counter
    is an excursion up from the baseline between the two stems.
    """
    x1, x2 = x0 + stem, x3 - stem       # inner edges of the two stems
    knee = int(y_top * SHOULDER_KNEE)   # where the shoulder is a plain stem
    y_in = y_top - thick                # apex of the counter
    ax = apex_end(x1, x2)
    pen = g.getPen()
    pen.moveTo((x0, 0))
    pen.lineTo((x1, 0))
    pen.lineTo((x1, y_in))
    pen.lineTo((ax, y_in))
    curve_down(pen, ax, y_in, x2, knee)
    pen.lineTo((x2, 0))
    pen.lineTo((x3, 0))
    pen.lineTo((x3, knee))
    curve_up(pen, x3, knee, ax, y_top)
    pen.lineTo((x0, y_top))
    pen.closePath()


def component(g: ufoLib2.Glyph, base: str, dx: int = 0, dy: int = 0,
              scale: float = 1.0) -> None:
    pen = g.getPen()
    pen.addComponent(base, (scale, 0, 0, scale, dx, dy))


def ink(font: ufoLib2.Font, name: str):
    """Bounding box of a glyph's drawn ink, or None if it is blank."""
    from fontTools.pens.boundsPen import BoundsPen
    if name not in font:
        return None
    p = BoundsPen(font)
    font[name].draw(p)
    return p.bounds


def copy_outline(font: ufoLib2.Font, g: ufoLib2.Glyph, src: str, dx: float = 0,
                 dy: float = 0, sx: float = 1.0, sy: float = 1.0, keep=None) -> None:
    """Copy another glyph's contours into g, optionally moved and scaled.

    Stroked and ligated letters are built this way rather than from components,
    because the added stroke has to be merged with the base outline by the union
    pass and a component cannot take part in that.

    ``keep`` is an optional predicate on a contour's bounds, used to take part of
    a glyph — the stem of i without its dot, say.
    """
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.pens.boundsPen import BoundsPen
    if src not in font:
        return
    out = TransformPen(g.getPen(), (sx, 0, 0, sy, dx, dy))
    for c in font[src].contours:
        if keep is not None:
            b = BoundsPen(None)
            c.draw(b)
            if b.bounds is None or not keep(b.bounds):
                continue
        rec = RecordingPen()
        c.draw(rec)
        rec.replay(out)


def _interior_points(contour, want: int = 32) -> list[tuple[float, float]]:
    """Sample points strictly inside a contour, for nesting tests.

    The candidates are deliberately off round numbers: coordinates that land
    exactly on another contour's edge — which happens wherever a bowl meets a
    stem — give an undefined inside/outside answer.

    A whole grid row is always finished before the sample is trimmed, and the
    trim takes every k-th hit rather than the first ``want`` of them. Returning
    as soon as ``want`` points were found instead would hand back a sample drawn
    entirely from the contour's left edge, and a D-bowl judged by its left edge
    alone sits inside its own counter.
    """
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.pointInsidePen import PointInsidePen
    b = BoundsPen(None)
    contour.draw(b)
    if b.bounds is None:
        return []
    x0, y0, x1, y1 = b.bounds
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return []
    # The sample has to spread over the whole contour, not cluster in the
    # middle: a bowl's centre is all inside its own counter, and judging the
    # bowl by those points alone reads it as a hole.
    found = []
    for n in (9, 17):
        for i in range(1, n):
            for j in range(1, n):
                p = (x0 + (x1 - x0) * i / n + 0.317, y0 + (y1 - y0) * j / n + 0.211)
                pip = PointInsidePen(None, p, evenOdd=True)
                contour.draw(pip)
                if pip.getResult():
                    found.append(p)
        if found:
            break
    if len(found) > want:
        step = len(found) / want
        found = [found[int(i * step)] for i in range(want)]
    return found


def _contains(contour, point) -> bool:
    from fontTools.pens.pointInsidePen import PointInsidePen
    pip = PointInsidePen(None, point, evenOdd=True)
    contour.draw(pip)
    return bool(pip.getResult())


def half_bowl(g: ufoLib2.Glyph, x_stem: int, y0: int, y1: int, right: int) -> None:
    """A D-shaped bowl springing from the right of a stem whose face is x_stem.

    Two contours — the outline and its counter — reaching JOIN units into the
    stem, the way B and P are built.
    """
    pen = g.getPen()
    mid = (y0 + y1) // 2
    rx = right - x_stem
    ry = (y1 - y0) // 2
    k = int(K_FLAT * rx)
    kv = int(K_SIDE * ry)
    pen.moveTo((x_stem - JOIN, y0))
    pen.lineTo((x_stem + rx - k, y0))
    pen.curveTo((right, y0), (right + k // 2, mid - kv), (right + k // 2, mid))
    pen.curveTo((right + k // 2, mid + kv), (right, y1), (x_stem + rx - k, y1))
    pen.lineTo((x_stem - JOIN, y1))
    pen.closePath()
    pen.moveTo((x_stem + HSTEM, y0 + HSTEM))
    pen.lineTo((x_stem + rx - k, y0 + HSTEM))
    pen.curveTo((right - HSTEM, y0 + HSTEM), (right + k // 2 - CSTEM, mid - kv + 20),
                (right + k // 2 - CSTEM, mid))
    pen.curveTo((right + k // 2 - CSTEM, mid + kv - 20), (right - HSTEM, y1 - HSTEM),
                (x_stem + rx - k, y1 - HSTEM))
    pen.lineTo((x_stem - JOIN // 2, y1 - HSTEM))
    pen.lineTo((x_stem - JOIN // 2, y0 + HSTEM))
    pen.closePath()


def bowl(g: ufoLib2.Glyph, x_stem: float, far: float, cy: float, ry: float,
         wstem: float = VSTEM, wbar: float = HSTEM) -> None:
    """The bowl of b, d, p, q and g: an oval that runs into a stem.

    ``x_stem`` is the stem face the bowl springs from, ``far`` the bowl's outer
    edge, and (``cy``, ``ry``) its vertical centre and half height including
    overshoot. Which way the bowl points is read off the two x's.

    The shape is an ellipse *wider* than the bowl looks, cut off by the stem, and
    the width is solved so that the cut lands exactly at the counter's top and
    bottom — the same place Helvetica joins them. That single constraint is what
    makes the letter hold together:

      - Draw the bowl as a whole o and overlap a stem on it, and the o's wall
        leaves the stem again above and below the overlap. What is left is a
        hairline of ink between the counter and the open bay at the top right,
        23 units of it at y=410 on the old d — half a pixel at 24px, which the
        rasteriser renders as a broken letter.
      - Cut the ellipse at its own vertical extremes instead (the obvious D
        shape) and the bowl's overshoot runs flat into the stem, so the bowl's
        foot ends up as a slab 10 units below the baseline beside the stem.

    Cutting at the counter's extremes puts the join where the bowl's wall is
    still travelling nearly straight up, and leaves the overshoot out in the
    middle of the bowl where it belongs. The cut itself is JOIN units inside the
    stem so the union has something to bite on.
    """
    sgn = 1 if far > x_stem else -1            # which way the bowl points
    width = abs(far - x_stem)
    half = ry - wbar                           # the counter's half height
    ct = math.sqrt(max(0.0, 1 - (half / ry) ** 2))
    rx = width / (1 + ct)                      # ... solved from the join height
    cx = far - sgn * rx
    cut = x_stem - sgn * JOIN                  # JOIN units into the stem
    srx = -sgn * rx                            # signed so 0° faces the stem
    a = math.degrees(math.acos(max(-1.0, min(1.0, (cut - cx) / srx))))

    def at(t: float) -> tuple[float, float]:
        return (cx + srx * math.cos(math.radians(t)), cy + ry * math.sin(math.radians(t)))

    pen = g.getPen()
    pen.moveTo(at(-a))
    # Split at the extremes so every one of them is an on-curve point: an
    # extremum the outline only passes near is an extremum the hinter cannot
    # align, and the overshoot stops being exactly OVS.
    for lo, hi in ((-a, -90), (-90, -180), (-180, -270), (-270, a - 360)):
        for seg in _arc(cx, cy, srx, ry, lo, hi):
            pen.curveTo(*seg)
    pen.closePath()                            # back down the cut, inside the stem

    # The counter is a free oval, like o's, reaching JOIN//2 past the stem's face
    # so the stem — not the counter's own wall — is what closes it on that side.
    c_far = far - sgn * wstem
    c_near = x_stem - sgn * (JOIN // 2)
    oval(g, round((c_far + c_near) / 2), round(cy), round(abs(c_near - c_far) / 2),
         round(half), clockwise=True)


def fix_directions(font: ufoLib2.Font) -> int:
    """Make outer contours run counterclockwise and counters clockwise.

    That is the PostScript convention the UFO sources are expected to use, and
    ufo2ft reverses it when compiling to TrueType. Two things depend on getting
    it right: a counter wound the same way as its outer contour fills in solid
    under a nonzero rasteriser, and booleanOperations reads a reversed contour as
    a hole, so the union pass silently does nothing to those glyphs.
    """
    from fontTools.pens.areaPen import AreaPen
    from fontTools.pens.pointInsidePen import PointInsidePen
    from fontTools.pens.recordingPen import RecordingPen
    from fontTools.pens.reverseContourPen import ReverseContourPen
    fixed = 0
    for g in font:
        if len(g.contours) == 0:
            continue
        contours = list(g.contours)
        recs, flip = [], []
        for i, c in enumerate(contours):
            rec = RecordingPen()
            c.draw(rec)
            recs.append(rec)
            a = AreaPen()
            c.draw(a)
            points = _interior_points(c, want=24)
            if not points or a.value == 0:
                flip.append(False)
                continue
            # One contour encloses another only if *every* point of the inner one
            # falls inside it. Testing a single point instead would read two
            # merely overlapping strokes — the bars of #, the arms of x — as
            # nested, and reverse one of them.
            depth = sum(
                1 for j, other in enumerate(contours)
                if j != i and all(_contains(other, p) for p in points)
            )
            want_positive = depth % 2 == 0
            flip.append(want_positive != (a.value > 0))
        if not any(flip):
            continue
        g.clearContours()
        pen = g.getPen()
        for rec, needs_flip in zip(recs, flip):
            rec.replay(ReverseContourPen(pen) if needs_flip else pen)
        fixed += 1
    return fixed


# ---------------------------------------------------------------------------
# Base lowercase
# ---------------------------------------------------------------------------

def draw_a(font: ufoLib2.Font) -> None:
    """Double-storey a: a hooked stem with a bowl hung off its lower half.

    Three overlapping pieces the union merges — the arch, the stem and the bowl.
    The single-storey form is kept as a.ss01, which is where §10 puts it.
    """
    g = add_glyph(font, "a", 520, 0x0061)
    x0, x1 = 370, 458                         # the stem's two faces
    xc = (x0 + x1) / 2
    TOP = XHEIGHT + OVS - HSTEM / 2           # centre line at the top of the arch
    SHOULDER = 400                            # where the stem turns into the arch
    # Stem and arch are one stroke, not a rectangle with a curve stuck on top. Two
    # pieces would meet along the stem's right face, and a coincident edge there
    # leaves either a seam or — since the arch's edge curves away from it — a step
    # at the top right of the letter.
    stroke(g, spline([
        (xc,  0,        90.0,  None, None),
        (xc,  SHOULDER, 90.0,  None, K_CIRCLE * (TOP - SHOULDER)),
        (250, TOP,      180.0, K_CIRCLE * (xc - 250), 75.0),
        (110, 425,      238.0, 60.0, None),
    ]), VSTEM, HSTEM, cap0=0.0)
    # The bowl is two ovals, the way b and d's are, rather than a half ellipse cut
    # flat against the stem: a flat-sided bowl puts its overshoot at the stem's
    # face, where the stem's own flat foot then cuts across it and leaves a tab
    # hanging below the baseline. Rounded, the overshoot sits at the bowl's middle
    # where it belongs, and the bowl has met the baseline again by the time it
    # reaches the stem.
    oval(g, 215, 155, 175, 165)
    oval(g, 254, 155, 126, 89, clockwise=True)


def draw_a_ss01(font: ufoLib2.Font) -> None:
    """Single-storey a — §10's ss01 alternate, drawn from the same parts as d."""
    g = add_glyph(font, "a.ss01", 540, None)
    rect(g, 402, 0, 490, XHEIGHT)
    oval(g, 250, 270, 200, 270 + OVS)
    oval(g, 275, 270, 137, 194 + OVS, clockwise=True)


def draw_b(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "b", 570, 0x0062)
    rect(g, 60, 0, 148, ASCENDER)
    bowl(g, 148, 510, 270, 270 + OVS)


def draw_c(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "c", 510, 0x0063)
    # Terminals 27° above and below the waist. The old pair sat at 12°, which
    # closed the aperture up so far that the letter read as an o at text sizes.
    arc_stroke(g, 280, 270, 230, XHEIGHT // 2 + OVS, VSTEM, HSTEM, 27, 333)


def draw_d(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "d", 570, 0x0064)
    rect(g, 422, 0, 510, ASCENDER)
    bowl(g, 422, 60, 270, 270 + OVS)


def draw_e(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "e", 540, 0x0065)
    # The old e closed its contour straight across the middle, so the counter was
    # never cut out at all and the letter filled in solid above the crossbar.
    #
    # Built instead as a ring with a gap in its right side plus a crossbar laid
    # across the mouth of that gap: the bar seals the top of the bay into a real
    # counter and what is left below it is the aperture. The union pass merges the
    # two pieces and derives the counter, so there is no hand-traced hole to get
    # wrong. Both ends of the bar stop inside the ring's walls — an end flush with
    # the outline would leave a coincident edge for the rasteriser to seam.
    cx, cy, rx, ry = 270, 270, 220, XHEIGHT // 2 + OVS
    BAR = 292                           # centre of the crossbar
    # The ring is cut at the bar's underside, not at its centre, and the bar runs
    # out to meet the ring's outer edge there. Cut anywhere else and the two
    # disagree about where the right hand side of the letter is: the bar's end
    # stops short of the outer edge and the ring's terminal juts past it, leaving a
    # spur pointing out of the letter at exactly the height the eye reads the bar.
    lo = BAR - HSTEM // 2
    a = math.degrees(math.asin((lo - cy) / ry))
    arc_stroke(g, cx, cy, rx, ry, VSTEM, HSTEM, a, 360 - 32)
    rect(g, cx - rx + 50, lo, cx + rx * math.cos(math.radians(a)), BAR + HSTEM // 2)


def draw_f(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "f", 340, 0x0066)
    pen = g.getPen()
    x0, x1 = 120, 120 + VSTEM
    HTOP = ASCENDER + OVS     # the hook's apex is a curve, so it overshoots
    TERM_Y = 620              # where the hook's terminal is cut off
    SHOULDER = ASCENDER - 110  # where the stem turns into the hook
    pen.moveTo((x0, 0))
    pen.lineTo((x0, SHOULDER))
    pen.curveTo((x0, HTOP - 40), (x0 + 40, HTOP), (215, HTOP))
    pen.curveTo((265, HTOP), (300, HTOP - 40), (305, TERM_Y))
    pen.lineTo((305 - HSTEM + 14, TERM_Y))
    pen.curveTo((241, TERM_Y + 40), (250, HTOP - HSTEM), (215, HTOP - HSTEM))
    pen.curveTo((211, HTOP - HSTEM), (x1, HTOP - 100), (x1, SHOULDER))
    pen.lineTo((x1, 0))
    pen.closePath()
    rect(g, 60, XHEIGHT - HSTEM // 2, 310, XHEIGHT + HSTEM // 2)


def draw_g(font: ufoLib2.Font) -> None:
    # Single storey, as the brief asks: q's bowl and stem, and then the stem keeps
    # going and swings left into a tail. The old g had the stem run all the way to
    # the descender with a separate closed tail hung off the bottom, which read as
    # a q with a loop — the tail was a second form rather than the end of the stem.
    #
    # Bowl and stem are identical to d's and q's, to the unit. The tail is one
    # stroked centreline starting inside the stem, so where it leaves the stem its
    # walls *are* the stem's walls: the nib is VSTEM wide and the centreline is
    # still vertical there, which puts the two edges at 422 and 510 exactly.
    g = add_glyph(font, "g", 570, 0x0067)
    bowl(g, 422, 60, 270, 270 + OVS)
    # Stem and tail are one stroke with no rect under it. Drawn as a rect plus a
    # curve, the curve has to start below the rect's foot, and the turn then has
    # so little room left above the descender that it begins with a radius of 103
    # against the straight stem's infinity — which rasterises as a corner on the
    # outside of the tail, about 50 units under the baseline.
    #
    # Instead the turn is an exact quarter circle of radius 200 that starts 33
    # *above* the baseline, where Helvetica starts its own. Constant radius all
    # the way round means the only curvature break left is straight-to-200 at the
    # top, gentle enough that the eye reads the stem as running smoothly into the
    # tail. The tail then has to sweep far enough left and rise far enough back up
    # to read as a hook rather than a blob: it ends under the bowl's left wall,
    # only 65 below the baseline, cut flat because by then the stroke is
    # travelling almost straight up and a flat cut is very nearly a square one.
    LOW = DESCENDER + HSTEM / 2               # the tail's lowest centreline
    R = 200.0
    stroke(g, spline([
        (466, XHEIGHT,  270.0, None, None),   # flat top, level with the bowl's
        (466, LOW + R,  270.0, None, K_CIRCLE * R),
        (466 - R, LOW,  180.0, K_CIRCLE * R, 67.7),
        (120, -65,       97.0, 67.7, None),   # up under the bowl
    ]), VSTEM, HSTEM, cap0=0.0, cap1=0.0)


def draw_h(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "h", 570, 0x0068)
    # As n, but the left stem carries on to the ascender.
    knee = int(XHEIGHT * SHOULDER_KNEE)
    y_in = XHEIGHT - HSTEM
    ax = apex_end(148, 422)
    pen = g.getPen()
    pen.moveTo((60, 0))
    pen.lineTo((148, 0))
    pen.lineTo((148, y_in))
    pen.lineTo((ax, y_in))
    curve_down(pen, ax, y_in, 422, knee)
    pen.lineTo((422, 0))
    pen.lineTo((510, 0))
    pen.lineTo((510, knee))
    curve_up(pen, 510, knee, ax, XHEIGHT)
    pen.lineTo((148, XHEIGHT))
    pen.lineTo((148, ASCENDER))
    pen.lineTo((60, ASCENDER))
    pen.closePath()


def draw_i(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "i", 260, 0x0069)
    rect(g, 86, 0, 174, XHEIGHT)
    oval(g, 130, XHEIGHT + 80, 44, 44)


def draw_j(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "j", 260, 0x006A)
    pen = g.getPen()
    pen.moveTo((86, XHEIGHT))
    pen.lineTo((174, XHEIGHT))
    pen.lineTo((174, DESCENDER + 80))
    pen.curveTo((174, DESCENDER), (86, DESCENDER), (40, DESCENDER + 40))
    pen.lineTo((40 + HSTEM, DESCENDER + 40 + HSTEM))
    pen.curveTo((86, DESCENDER + HSTEM), (86, DESCENDER + HSTEM), (86, DESCENDER + 80))
    pen.lineTo((86, XHEIGHT))
    pen.closePath()
    oval(g, 130, XHEIGHT + 80, 44, 44)


def draw_k(font: ufoLib2.Font) -> None:
    # Both diagonals used to start inside the stem, 40 units apart, so the white
    # wedge between them drove its point into the stem and the two strokes met
    # there at a single point with no mass behind the junction. In a grotesque the
    # leg springs off the arm, not off the stem: the arm's underside and the leg's
    # top meet at one vertex out at 0.52 of the advance, and the junction lands on
    # the stem over a 109-unit stretch — wider than the stem itself. Coordinates
    # below are Helvetica's, fitted to this font's stem, x-height and advance.
    #
    # The leg is 92 units thick against the arm's 77. It is the steeper of the
    # two, so it wants a weight nearer the vertical stem's than the horizontal
    # bar's, and drawing both the same makes the leg look starved.
    g = add_glyph(font, "k", 530, 0x006B)
    pen = g.getPen()
    pen.moveTo((60, ASCENDER))
    pen.lineTo((148, ASCENDER))
    pen.lineTo((148, 311))          # stem's right edge, down to the arm
    pen.lineTo((361, XHEIGHT))      # arm, upper edge
    pen.lineTo((467, XHEIGHT))      # its level terminal
    pen.lineTo((278, 338))          # back down the arm's underside, to the vertex
    pen.lineTo((477, 0))            # leg, upper edge
    pen.lineTo((371, 0))            # its level terminal
    pen.lineTo((210, 273))          # back up the leg's underside
    pen.lineTo((148, 202))          # and into the stem, well below the arm
    pen.lineTo((148, 0))
    pen.lineTo((60, 0))
    pen.closePath()


def draw_l(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "l", 280, 0x006C)
    # A bare stem makes l indistinguishable from I and from the vertical bar at
    # UI sizes, which is the one confusion a system font cannot afford. A tail
    # curving out to the right settles it; the same move keeps l apart from the
    # digit one, which has its flag on the left.
    #
    # Stem and tail are one stroke on a centreline. Hand-traced, the two edges of
    # the turn were written independently and the inner one ran all the way back
    # to the stem's left edge, so it ate the foot of the stem from below and what
    # was left of the tail was a wisp that thinned to nothing at the tip. Offset
    # from a centreline the tail cannot thin: the width is the nib's.
    LOW = HSTEM / 2                  # the tail's centreline, half a stroke up
    R = 110.0                        # radius of the turn, measured on the centreline
    stroke(g, spline([
        (104, ASCENDER, 270.0, None, None),          # down the stem
        (104, LOW + R,  270.0, None, K_CIRCLE * R),  # into the turn
        (104 + R, LOW,    0.0, K_CIRCLE * R, None),  # out of it, running level
        (236, LOW,        0.0, None, None),          # to the tip
    ]), VSTEM, HSTEM, cap0=0.0, cap1=90.0)


def draw_m(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "m", 860, 0x006D)
    # Three stems, two shoulders, one contour. The middle stem is drawn slightly
    # narrower than the outer two: enclosed on both sides, it would otherwise
    # read darker than they do.
    knee = int(XHEIGHT * SHOULDER_KNEE)
    y_in = XHEIGHT - HSTEM
    mid_l = 430 - VSTEM_TIGHT // 2      # 388
    mid_r = 430 + VSTEM_TIGHT // 2      # 472
    a1, a2 = apex_end(148, mid_l), apex_end(mid_r, 712)
    pen = g.getPen()
    pen.moveTo((60, 0))
    pen.lineTo((148, 0))
    pen.lineTo((148, y_in))
    pen.lineTo((a1, y_in))
    curve_down(pen, a1, y_in, mid_l, knee)
    pen.lineTo((mid_l, 0))
    pen.lineTo((mid_r, 0))
    pen.lineTo((mid_r, y_in))
    pen.lineTo((a2, y_in))
    curve_down(pen, a2, y_in, 712, knee)
    pen.lineTo((712, 0))
    pen.lineTo((800, 0))
    pen.lineTo((800, knee))
    curve_up(pen, 800, knee, a2, XHEIGHT)
    pen.lineTo((60, XHEIGHT))
    pen.closePath()


def draw_n(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "n", 570, 0x006E)
    n_shape(g, 60, 510, XHEIGHT)


def draw_o(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "o", 560, 0x006F)
    oval(g, 280, 270, 220, 270 + OVS)
    oval(g, 280, 270, 132, 194 + OVS, clockwise=True)


def draw_p(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "p", 570, 0x0070)
    rect(g, 60, DESCENDER, 148, XHEIGHT)
    bowl(g, 148, 510, 270, 270 + OVS)


def draw_q(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "q", 570, 0x0071)
    rect(g, 422, DESCENDER, 510, XHEIGHT)
    bowl(g, 422, 60, 270, 270 + OVS)


def draw_r(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "r", 360, 0x0072)
    # Stem plus a shoulder that stops instead of returning to the baseline. The
    # arm ends in a vertical terminal exactly HSTEM deep.
    y_in = XHEIGHT - HSTEM
    tip = 320
    ax = apex_end(148, 422)          # same apex as n, so r and n agree
    pen = g.getPen()
    pen.moveTo((60, 0))
    pen.lineTo((148, 0))
    pen.lineTo((148, y_in))
    curve_down(pen, 148, y_in, tip, y_in - 80)
    pen.lineTo((tip, y_in - 80 + HSTEM))
    curve_up(pen, tip, y_in - 80 + HSTEM, ax, XHEIGHT)
    pen.lineTo((60, XHEIGHT))
    pen.closePath()


def ess(g: ufoLib2.Glyph, cx: float, cy: float, halfw: float, halfh: float,
        wx: float, wy: float, term: float = 108.0, waist: float = 315.0,
        shoulder: float = 0.46, tx: float = 0.97, ty: float = 0.60) -> None:
    """s and S: one written centre line, stroked with an elliptical nib.

    Two earlier attempts failed in the same place, the waist. Traced as one
    outline, the inner and outer edges crossed there and the fill cancelled to a
    hairline. Built from two arcs plus a straight band, the band had to be shallow
    enough to reach both bowls and the letter grew a horizontal bar through its
    middle. Neither is how an s is made: an s is a single stroke that starts at
    the top right, goes up over the top, down the left of the upper bowl, crosses
    the waist, and comes round the bottom to a terminal at the lower left. Drawn
    that way there is no waist to get wrong — it is just the one place where the
    line stops curving one way and starts curving the other.

    The whole lower half is the upper half turned 180° about ``(cx, cy)``, which
    is the symmetry an s is built on, so only half the numbers exist. ``term`` is
    the direction the stroke leaves its top terminal in, ``waist`` the direction
    it crosses the middle in, and ``shoulder`` how far above the middle the upper
    bowl's widest point sits, as a fraction of the half height.

    The one number that has to be watched is the handle out of the shoulder plus
    the handle back into the waist: if together they cover more than the vertical
    distance between those two nodes, the centre line bulges out to the left on
    its way down and the stroke grows a lump. ``shoulder`` is what buys the room.
    """
    hb = halfh * shoulder
    ktop = K_CIRCLE * halfw               # handle across the top of a bowl
    karch = K_CIRCLE * (halfh - hb)       # and up the bowl's side to that top
    kside = 0.42 * (halfh - hb)           # out of the bowl's side into the waist
    kw = 0.45 * halfw                     # and back out of the waist
    if kside + abs(math.cos(math.radians(waist))) * kw > hb:
        raise ValueError(f"ess on {g.name!r}: shoulder {shoulder} leaves no room "
                         f"between the bowl's side and the waist; the centre line "
                         f"would bulge.")
    nodes = [
        (cx + halfw * tx, cy + halfh * ty, term, None, 0.42 * (halfh - hb)),
        (cx,              cy + halfh,      180.0, 0.48 * halfw, ktop),
        (cx - halfw,      cy + hb,         270.0, karch, kside),
        (cx,              cy,              waist, kw, kw),
        (cx + halfw,      cy - hb,         270.0, kside, karch),
        (cx,              cy - halfh,      180.0, ktop, 0.48 * halfw),
        (cx - halfw * tx, cy - halfh * ty, term, 0.42 * (halfh - hb), None),
    ]
    # Both terminals cut square to the stroke. Cut flat to the baseline instead
    # and the corner where the cut meets the outer edge closes to 60°, which turns
    # the end of the stroke into a beak pointing out of the letter.
    stroke(g, spline(nodes), wx, wy)


def draw_s(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "s", 490, 0x0073)
    # Ink 41–449 wide against o's 60–500: an s is drawn narrower than an o. The
    # centre line's box is the ink's box less half the nib in each direction, so
    # the overshoot is put in here rather than left to be discovered later.
    WX, WY = VSTEM - 2, HSTEM - 2
    ess(g, 226, XHEIGHT // 2, 142, XHEIGHT // 2 + OVS - WY / 2, WX, WY)


def draw_t(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "t", 360, 0x0074)
    # A grotesque t has a foot: the stem turns right at the baseline and stops in
    # a vertical cut, which is what keeps it from reading as a plus sign and what
    # stops the pair "tt" from looking like a fence. It had none.
    stroke(g, spline([
        (180, ASCENDER - 60, 270.0, None, None),
        (180, 110,           270.0, None, K_CIRCLE * 72),
        (300, 38,              0.0, K_CIRCLE * 120, None),
    ]), VSTEM, HSTEM, cap0=0.0, cap1=90.0)
    # The crossbar hangs *below* x-height, its top on the line, not straddling it.
    rect(g, 40, XHEIGHT - HSTEM, 316, XHEIGHT)


def draw_u(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "u", 570, 0x0075)
    # u is n rotated 180°, which is the classic relationship and guarantees the
    # two letters carry identical shoulder weight and curvature. Rotating rather
    # than only mirroring vertically keeps the straight stem on the right, where
    # u wants it.
    n_shape(g, 60, 510, XHEIGHT)
    flip_y(g, XHEIGHT / 2)
    flip_x(g, 570 / 2)


def draw_v(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "v", 530, 0x0076)
    # The vertex is a point, so it overshoots the baseline for the same reason a
    # round form does: a shape that comes to a point looks short if it stops on
    # the line.
    vee(g, 0, XHEIGHT, 265, -OVS, 530, XHEIGHT)


def draw_w(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "w", 740, 0x0077)
    # Two v's overlapping across the middle apex. They have to overlap rather
    # than touch: two shapes meeting at a single point give the union nothing to
    # merge, and the rasteriser draws a pinhole there.
    vee(g, 0, XHEIGHT, 185, -OVS, 390, XHEIGHT)
    vee(g, 350, XHEIGHT, 555, -OVS, 740, XHEIGHT)


def draw_x(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "x", 510, 0x0078)
    band(g, 55, 0, 455, XHEIGHT)
    band(g, 455, 0, 55, XHEIGHT)


def draw_y(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "y", 510, 0x0079)
    # A v whose vertex is buried in the descender stem, so the join is covered.
    vee(g, 0, XHEIGHT, 255, 44, 510, XHEIGHT)
    pen = g.getPen()
    pen.moveTo((299, 120))
    pen.lineTo((299, DESCENDER))
    pen.curveTo((299, DESCENDER - 40), (200, DESCENDER - 60), (130, DESCENDER - 20))
    pen.lineTo((130, DESCENDER - 20 + HSTEM))
    pen.curveTo((190, DESCENDER - 20 + HSTEM), (211, DESCENDER + HSTEM), (211, DESCENDER))
    pen.lineTo((211, 120))
    pen.closePath()


def draw_z(font: ufoLib2.Font) -> None:
    g = add_glyph(font, "z", 490, 0x007A)
    rect(g, 40, XHEIGHT - HSTEM, 450, XHEIGHT)
    rect(g, 40, 0, 450, HSTEM)
    # The diagonal's square ends are cut half way up each bar, where the bar
    # covers them.
    band(g, 90, HSTEM // 2, 400, XHEIGHT - HSTEM // 2)


LOWERCASE_DRAWERS = [
    draw_a, draw_a_ss01, draw_b, draw_c, draw_d, draw_e, draw_f, draw_g,
    draw_h, draw_i, draw_j, draw_k, draw_l, draw_m, draw_n,
    draw_o, draw_p, draw_q, draw_r, draw_s, draw_t, draw_u,
    draw_v, draw_w, draw_x, draw_y, draw_z,
]


# ---------------------------------------------------------------------------
# Base uppercase
# ---------------------------------------------------------------------------

def draw_A(font):
    g = add_glyph(font, "A", 680, 0x0041)
    vee(g, 0, 0, 340, CAPHEIGHT, 680, 0)
    # The crossbar starts inside the diagonals rather than on their edges: its
    # ends have to stay covered at the *top* of the bar, where the diagonals
    # have moved furthest inward.
    rect(g, 170, 260, 510, 336)

def draw_B(font):
    g = add_glyph(font, "B", 640, 0x0042)
    rect(g, 60, 0, 148, CAPHEIGHT)
    pen = g.getPen()
    for y0, y1, cx in [(0, CAPHEIGHT//2, 520), (CAPHEIGHT//2, CAPHEIGHT, 496)]:
        mid = (y0 + y1) // 2
        rx = cx - 148; ry = (y1 - y0) // 2
        k = int(K_FLAT * rx); kv = int(K_SIDE * ry)
        pen.moveTo((148 - JOIN, y0)); pen.lineTo((cx - rx, y0))
        pen.curveTo((cx - rx + k, y0), (cx, mid - kv), (cx, mid))
        pen.curveTo((cx, mid + kv), (cx - rx + k, y1), (cx - rx, y1))
        pen.lineTo((148 - JOIN, y1)); pen.closePath()
        pen.moveTo((148 - JOIN // 2, y0 + HSTEM)); pen.lineTo((cx - rx, y0 + HSTEM))
        pen.curveTo((cx - rx + k, y0 + HSTEM), (cx - HSTEM, mid - kv + 20), (cx - HSTEM, mid))
        pen.curveTo((cx - HSTEM, mid + kv - 20), (cx - rx + k, y1 - HSTEM), (cx - rx, y1 - HSTEM))
        pen.lineTo((148 - JOIN // 2, y1 - HSTEM)); pen.closePath()

def draw_C(font):
    g = add_glyph(font, "C", 620, 0x0043)
    pen = g.getPen()
    cx, cy, rx, ry = 310, CAPHEIGHT//2, 250, CAPHEIGHT//2 + OVS
    k = int(K_FLAT * rx); kv = int(K_SIDE * ry)
    pen.moveTo((cx+rx, cy+80))
    pen.curveTo((cx+rx, cy+kv),(cx+k, cy+ry),(cx, cy+ry))
    pen.curveTo((cx-k, cy+ry),(cx-rx, cy+kv),(cx-rx, cy))
    pen.curveTo((cx-rx, cy-kv),(cx-k, cy-ry),(cx, cy-ry))
    pen.curveTo((cx+k, cy-ry),(cx+rx, cy-kv),(cx+rx, cy-80))
    pen.lineTo((cx+rx-HSTEM, cy-80))
    pen.curveTo((cx+rx-HSTEM, cy-kv+40),(cx+k, cy-ry+HSTEM),(cx, cy-ry+HSTEM))
    pen.curveTo((cx-k, cy-ry+HSTEM),(cx-rx+HSTEM, cy-kv),(cx-rx+HSTEM, cy))
    pen.curveTo((cx-rx+HSTEM, cy+kv),(cx-k, cy+ry-HSTEM),(cx, cy+ry-HSTEM))
    pen.curveTo((cx+k, cy+ry-HSTEM),(cx+rx-HSTEM, cy+kv-40),(cx+rx-HSTEM, cy+80))
    pen.closePath()

def draw_D(font):
    g = add_glyph(font, "D", 680, 0x0044)
    rect(g, 60, 0, 148, CAPHEIGHT)
    pen = g.getPen()
    cx, cy = 148, CAPHEIGHT//2; rx = 345; ry = CAPHEIGHT//2 + OVS
    k = int(K_FLAT * rx); kv = int(K_SIDE * ry)
    pen.moveTo((148 - JOIN, 0)); pen.lineTo((148+rx-k, 0))
    pen.curveTo((148+rx, 0),(148+rx+k//2, cy-kv),(148+rx+k//2, cy))
    pen.curveTo((148+rx+k//2, cy+kv),(148+rx, CAPHEIGHT),(148+rx-k, CAPHEIGHT))
    pen.lineTo((148 - JOIN, CAPHEIGHT)); pen.closePath()
    pen.moveTo((148 - JOIN // 2, HSTEM)); pen.lineTo((148+rx-k, HSTEM))
    pen.curveTo((148+rx-HSTEM, HSTEM),(148+rx+k//2-HSTEM, cy-kv+20),(148+rx+k//2-HSTEM, cy))
    pen.curveTo((148+rx+k//2-HSTEM, cy+kv-20),(148+rx-HSTEM, CAPHEIGHT-HSTEM),(148+rx-k, CAPHEIGHT-HSTEM))
    pen.lineTo((148 - JOIN // 2, CAPHEIGHT-HSTEM)); pen.closePath()

def draw_E(font):
    g = add_glyph(font, "E", 600, 0x0045)
    rect(g, 60, 0, 148, CAPHEIGHT)
    rect(g, 148, CAPHEIGHT-HSTEM, 580, CAPHEIGHT)
    rect(g, 148, CAPHEIGHT//2-HSTEM//2, 520, CAPHEIGHT//2+HSTEM//2)
    rect(g, 148, 0, 580, HSTEM)

def draw_F(font):
    g = add_glyph(font, "F", 580, 0x0046)
    rect(g, 60, 0, 148, CAPHEIGHT)
    rect(g, 148, CAPHEIGHT-HSTEM, 560, CAPHEIGHT)
    rect(g, 148, CAPHEIGHT//2-HSTEM//2, 500, CAPHEIGHT//2+HSTEM//2)

def draw_G(font):
    g = add_glyph(font, "G", 660, 0x0047)
    pen = g.getPen()
    cx, cy, rx, ry = 310, CAPHEIGHT//2, 250, CAPHEIGHT//2 + OVS
    k = int(K_FLAT * rx); kv = int(K_SIDE * ry)
    pen.moveTo((cx+rx, cy+80))
    pen.curveTo((cx+rx, cy+kv),(cx+k, cy+ry),(cx, cy+ry))
    pen.curveTo((cx-k, cy+ry),(cx-rx, cy+kv),(cx-rx, cy))
    pen.curveTo((cx-rx, cy-kv),(cx-k, cy-ry),(cx, cy-ry))
    pen.curveTo((cx+k, cy-ry),(cx+rx, cy-kv),(cx+rx, cy-80))
    pen.lineTo((cx+rx-HSTEM, cy-80))
    pen.curveTo((cx+rx-HSTEM, cy-kv+40),(cx+k, cy-ry+HSTEM),(cx, cy-ry+HSTEM))
    pen.curveTo((cx-k, cy-ry+HSTEM),(cx-rx+HSTEM, cy-kv),(cx-rx+HSTEM, cy))
    pen.curveTo((cx-rx+HSTEM, cy+kv),(cx-k, cy+ry-HSTEM),(cx, cy+ry-HSTEM))
    pen.curveTo((cx+k, cy+ry-HSTEM),(cx+rx-HSTEM, cy+kv-40),(cx+rx-HSTEM, cy+80))
    pen.closePath()
    rect(g, cx, cy-HSTEM//2, cx+rx, cy+HSTEM//2)

def draw_H(font):
    g = add_glyph(font, "H", 680, 0x0048)
    rect(g, 80, 0, 168, CAPHEIGHT)
    rect(g, 512, 0, 600, CAPHEIGHT)
    rect(g, 168, CAPHEIGHT//2-HSTEM//2, 512, CAPHEIGHT//2+HSTEM//2)

def draw_I(font):
    g = add_glyph(font, "I", 320, 0x0049)
    # Crossbars top and bottom. Without them I is the same rectangle as the
    # vertical bar and as a tail-less l; with them the three are never confused.
    # They are kept short so I still reads as a sans-serif capital.
    rect(g, 116, 0, 204, CAPHEIGHT)
    rect(g, 56, 0, 264, HSTEM)
    rect(g, 56, CAPHEIGHT-HSTEM, 264, CAPHEIGHT)

def draw_J(font):
    g = add_glyph(font, "J", 420, 0x004A)
    # Helvetica's J: a deep narrow turn off the stem, then a broad sweep back up
    # to the left ending in a flat cut at a third of the cap height. Drawn as one
    # centreline, so the hook carries the same weight all the way round instead
    # of pinching to nothing where a traced inner edge would come back.
    BOT = -OVS + HSTEM / 2              # the hook's centreline at its lowest
    STEM = 288 - VSTEM / 2              # the stem's centreline
    RX_R, RY_R = 76.0, 160.0            # the turn off the stem
    RX_L, RY_L = 150.0, 200.0           # the sweep up to the terminal
    stroke(g, spline([
        (STEM, CAPHEIGHT,  270.0, None, None),
        (STEM, BOT + RY_R, 270.0, None, K_CIRCLE * RY_R),
        (STEM - RX_R, BOT, 180.0, K_CIRCLE * RX_R, K_CIRCLE * RX_L),
        (STEM - RX_R - RX_L, BOT + RY_L, 90.0, K_CIRCLE * RY_L, None),
    ]), VSTEM, HSTEM)

def draw_K(font):
    g = add_glyph(font, "K", 640, 0x004B)
    rect(g, 60, 0, 148, CAPHEIGHT)
    # Arm and leg start inside the stem, cut vertically so the stem hides the
    # cut; their two cuts overlap in there, which is what joins them.
    band(g, 100, 380, 560, CAPHEIGHT, cut="vh")
    band(g, 100, 330, 560, 0, cut="vh")

def draw_L(font):
    g = add_glyph(font, "L", 560, 0x004C)
    rect(g, 60, 0, 148, CAPHEIGHT)
    rect(g, 148, 0, 540, HSTEM)

def draw_M(font):
    g = add_glyph(font, "M", 800, 0x004D)
    rect(g, 60, 0, 148, CAPHEIGHT)
    rect(g, 652, 0, 740, CAPHEIGHT)
    # The diagonals' outer edges continue the stems' outer edges, and they run
    # all the way to the baseline: an M whose vertex stops short reads as a wide
    # N with a dent in it.
    vee(g, 60, CAPHEIGHT, 400, -OVS, 740, CAPHEIGHT)

def draw_N(font):
    g = add_glyph(font, "N", 680, 0x004E)
    rect(g, 60, 0, 148, CAPHEIGHT)
    rect(g, 532, 0, 620, CAPHEIGHT)
    # The diagonal is a touch wider than the stem where it is cut, so it juts a
    # few units past it at each end. That wedge is how the letter is built: it
    # is what keeps the diagonal at its own weight instead of the stem's.
    band(g, 110, CAPHEIGHT, 570, 0)

def draw_O(font):
    g = add_glyph(font, "O", 720, 0x004F)
    oval(g, 360, CAPHEIGHT//2, 300, CAPHEIGHT//2 + OVS)
    oval(g, 360, CAPHEIGHT//2, 212, CAPHEIGHT//2-HSTEM + OVS, clockwise=True)

def draw_P(font):
    g = add_glyph(font, "P", 620, 0x0050)
    rect(g, 60, 0, 148, CAPHEIGHT)
    pen = g.getPen()
    cx = 148; cy = int(CAPHEIGHT*0.65); rx = 270; ry = int(CAPHEIGHT*0.35)
    k = int(K_FLAT * rx); kv = int(K_SIDE * ry)
    pen.moveTo((148 - JOIN, cy-ry)); pen.lineTo((148+rx-k, cy-ry))
    pen.curveTo((148+rx, cy-ry),(148+rx+k//2, cy-kv),(148+rx+k//2, cy))
    pen.curveTo((148+rx+k//2, cy+kv),(148+rx, cy+ry),(148+rx-k, cy+ry))
    pen.lineTo((148 - JOIN, cy+ry)); pen.closePath()
    pen.moveTo((148 - JOIN // 2, cy-ry+HSTEM)); pen.lineTo((148+rx-k, cy-ry+HSTEM))
    pen.curveTo((148+rx-HSTEM, cy-ry+HSTEM),(148+rx+k//2-HSTEM, cy-kv+20),(148+rx+k//2-HSTEM, cy))
    pen.curveTo((148+rx+k//2-HSTEM, cy+kv-20),(148+rx-HSTEM, cy+ry-HSTEM),(148+rx-k, cy+ry-HSTEM))
    pen.lineTo((148 - JOIN // 2, cy+ry-HSTEM)); pen.closePath()

def draw_Q(font):
    g = add_glyph(font, "Q", 720, 0x0051)
    oval(g, 360, CAPHEIGHT//2, 300, CAPHEIGHT//2 + OVS)
    oval(g, 360, CAPHEIGHT//2, 212, CAPHEIGHT//2-HSTEM + OVS, clockwise=True)
    pen = g.getPen()
    pen.moveTo((400, 160)); pen.lineTo((560, 0))
    pen.lineTo((480, 0)); pen.lineTo((320, 160)); pen.closePath()

def draw_R(font):
    g = add_glyph(font, "R", 640, 0x0052)
    rect(g, 60, 0, 148, CAPHEIGHT)
    pen = g.getPen()
    cx = 148; cy = int(CAPHEIGHT*0.65); rx = 270; ry = int(CAPHEIGHT*0.35)
    k = int(K_FLAT * rx); kv = int(K_SIDE * ry)
    pen.moveTo((148 - JOIN, cy-ry)); pen.lineTo((148+rx-k, cy-ry))
    pen.curveTo((148+rx, cy-ry),(148+rx+k//2, cy-kv),(148+rx+k//2, cy))
    pen.curveTo((148+rx+k//2, cy+kv),(148+rx, cy+ry),(148+rx-k, cy+ry))
    pen.lineTo((148 - JOIN, cy+ry)); pen.closePath()
    pen.moveTo((148 - JOIN // 2, cy-ry+HSTEM)); pen.lineTo((148+rx-k, cy-ry+HSTEM))
    pen.curveTo((148+rx-HSTEM, cy-ry+HSTEM),(148+rx+k//2-HSTEM, cy-kv+20),(148+rx+k//2-HSTEM, cy))
    pen.curveTo((148+rx+k//2-HSTEM, cy+kv-20),(148+rx-HSTEM, cy+ry-HSTEM),(148+rx-k, cy+ry-HSTEM))
    pen.lineTo((148 - JOIN // 2, cy+ry-HSTEM)); pen.closePath()
    # The leg's upper end is cut half way into the bowl's bottom stroke.
    band(g, 290, cy - ry + HSTEM // 2, 545, 0)

def draw_S(font):
    g = add_glyph(font, "S", 580, 0x0053)
    # Same skeleton as s, at cap size. Ink 40–580 against O's 40–616.
    ess(g, 310, CAPHEIGHT // 2, 226, CAPHEIGHT // 2 + OVS - HSTEM / 2, VSTEM, HSTEM)

def draw_T(font):
    g = add_glyph(font, "T", 600, 0x0054)
    rect(g, 256, 0, 344, CAPHEIGHT)
    rect(g, 40, CAPHEIGHT-HSTEM, 560, CAPHEIGHT)

def draw_U(font):
    g = add_glyph(font, "U", 680, 0x0055)
    # One centreline from cap height down, round the bottom and back up, so the
    # two joins that a stem-plus-bowl U needs do not exist to crack open. The
    # nib is VSTEM wide and HSTEM tall, which thins the turn exactly as much as
    # Helvetica thins its own (85 against a 99 stem, the same 0.86).
    L, R = 124.0, 556.0                 # the stems' centrelines
    BOT = -OVS + HSTEM / 2              # the turn's centreline at its lowest
    TURN = 285.0                        # where the sides stop running straight
    RX, RY = (R - L) / 2, TURN - BOT
    stroke(g, spline([
        (L, CAPHEIGHT, 270.0, None, None),
        (L, TURN,      270.0, None, K_CIRCLE * RY),
        (L + RX, BOT,    0.0, K_CIRCLE * RX, K_CIRCLE * RX),
        (R, TURN,       90.0, K_CIRCLE * RY, None),
        (R, CAPHEIGHT,  90.0, None, None),
    ]), VSTEM, HSTEM)

def draw_V(font):
    g = add_glyph(font, "V", 660, 0x0056)
    vee(g, 0, CAPHEIGHT, 330, -OVS, 660, CAPHEIGHT)

def draw_W(font):
    g = add_glyph(font, "W", 900, 0x0057)
    vee(g, 0, CAPHEIGHT, 225, -OVS, 470, CAPHEIGHT)
    vee(g, 430, CAPHEIGHT, 675, -OVS, 900, CAPHEIGHT)

def draw_X(font):
    g = add_glyph(font, "X", 640, 0x0058)
    band(g, 55, 0, 585, CAPHEIGHT)
    band(g, 585, 0, 55, CAPHEIGHT)

def draw_Y(font):
    g = add_glyph(font, "Y", 620, 0x0059)
    vee(g, 0, CAPHEIGHT, 310, 300, 620, CAPHEIGHT)
    rect(g, 266, 0, 354, 330)   # the stem swallows the vertex and its notch

def draw_Z(font):
    g = add_glyph(font, "Z", 600, 0x005A)
    rect(g, 40, CAPHEIGHT - HSTEM, 560, CAPHEIGHT)
    rect(g, 40, 0, 560, HSTEM)
    band(g, 90, HSTEM // 2, 510, CAPHEIGHT - HSTEM // 2)

UPPERCASE_DRAWERS = [
    draw_A, draw_B, draw_C, draw_D, draw_E, draw_F, draw_G,
    draw_H, draw_I, draw_J, draw_K, draw_L, draw_M, draw_N,
    draw_O, draw_P, draw_Q, draw_R, draw_S, draw_T, draw_U,
    draw_V, draw_W, draw_X, draw_Y, draw_Z,
]


# ---------------------------------------------------------------------------
# Digits
# ---------------------------------------------------------------------------

def draw_zero(font):
    g = add_glyph(font, "zero", 580, 0x0030)
    oval(g, 290, CAPHEIGHT//2, 230, CAPHEIGHT//2 + OVS)
    oval(g, 290, CAPHEIGHT//2, 142, CAPHEIGHT//2-HSTEM + OVS, clockwise=True)

def draw_one(font):
    # The flag was a right triangle with its point on the left, which reads as a
    # stub: it carries no weight at the tip, so at text sizes it drops out and the
    # one looks like a bare stem. A grotesque flag is a wedge with a blunt tip —
    # Helvetica's is a 69-unit vertical edge at 0.17 of the advance, a level
    # underside at 0.71 of the cap, and a top that leaves the tip almost flat and
    # steepens into the stem. The curve below is Helvetica's own, mapped onto this
    # font's tip and cap.
    g = add_glyph(font, "one", 580, 0x0031)
    rect(g, 246, 0, 334, CAPHEIGHT)
    pen = g.getPen()
    pen.moveTo((130, 512))
    pen.lineTo((130, 582))
    pen.curveTo((184, 589), (221, 600), (242, 614))
    pen.curveTo((263, 629), (279, 661), (290, 716))   # ends inside the stem
    pen.lineTo((290, 512))
    pen.closePath()

def draw_two(font):
    g = add_glyph(font, "two", 580, 0x0032)
    L, R = 80, 500
    TOP = CAPHEIGHT + OVS
    cx, cy = (L + R) // 2, 470          # centre of the arch's ellipse
    rx, ry = (R - L) // 2, TOP - 470
    RX, RY = rx - HSTEM, ry - HSTEM     # the arch's inner ellipse
    STRAIGHT = 380                      # the right side runs down to here
    pen = g.getPen()
    # the arch: left terminal cut flat at the ellipse's widest point, over the
    # top, down the right side and on down a short straight run
    pen.moveTo((cx - rx, cy))
    pen.curveTo((cx - rx, cy + int(K_SIDE * ry)), (cx - int(K_FLAT * rx), TOP), (cx, TOP))
    pen.curveTo((cx + int(K_FLAT * rx), TOP), (cx + rx, cy + int(K_SIDE * ry)), (cx + rx, cy))
    pen.lineTo((cx + rx, STRAIGHT))
    pen.lineTo((cx + RX, STRAIGHT))
    pen.lineTo((cx + RX, cy))
    pen.curveTo((cx + RX, cy + int(K_SIDE * RY)), (cx + int(K_FLAT * RX), TOP - HSTEM), (cx, TOP - HSTEM))
    pen.curveTo((cx - int(K_FLAT * RX), TOP - HSTEM), (cx - RX, cy + int(K_SIDE * RY)), (cx - RX, cy))
    pen.closePath()
    # the diagonal, cut vertically inside the arch's right side and flat inside
    # the foot bar
    band(g, cx + rx - 40, cy, L + 70, HSTEM // 2, cut="vh")
    rect(g, L, 0, R, HSTEM)

def draw_three(font):
    # Two bowls, the lower one the wider, sweeping past each other so that they
    # merge into one stroke through the waist. The old three drew each bowl as a
    # closed shape with a hand-written curve back to a terminal on the left, and
    # the two shapes met without overlapping: the join showed as a notch on the
    # right of the waist and the terminals came out as vertical stubs.
    #
    # The radii are solved, not chosen. With the ink fixed top and bottom, the
    # ink left in the waist is
    #     (top - bottom) - 2·(ry_upper + ry_lower) + 2·HSTEM
    # so asking for a waist exactly one horizontal stroke thick fixes the sum of
    # the two radii at 408; the split between them is what makes the lower bowl
    # the larger of the two, as it has to be for the digit not to look top-heavy.
    # The waist is a bar, not a crossing. Running the two bowls past each other
    # and letting them merge cannot work: with the waist one stroke thick the
    # upper bowl's counter edge and the lower bowl's outer edge are tangent at
    # the centre and never cross, so neither bowl's cut can be hidden inside the
    # other and both show as spurs. Helvetica does not cross them either — its
    # three is a single contour whose waist ends in a blunt vertical cut at 0.39
    # of the ink width. So each bowl stops at its own extreme, where its cut is
    # vertical, and a short bar spans the two cuts and reaches past them to form
    # the blunt end. The bar is 2 units taller than the bowls at their extremes,
    # which keeps every edge crossing transversal instead of tangent; 2 units is
    # 0.05 px at 24 px, and it also lets the waist read a hair sturdier.
    g = add_glyph(font, "three", 580, 0x0033)
    TOP, BOT = CAPHEIGHT + OVS, -OVS
    ry_up, ry_lo = 193, 215                   # 408 between them: see above
    cy_up, cy_lo = TOP - ry_up, BOT + ry_lo
    # Terminals at 200° and -184°, both a touch past the bowls' left extremes,
    # which is where Helvetica cuts its own: 0.67 of the figure height for the
    # upper one and just above the lower bowl's centre for the other.
    arc_stroke(g, 290, cy_up, 190, ry_up, VSTEM, HSTEM, 200, -90)
    arc_stroke(g, 290, cy_lo, 210, ry_lo, VSTEM, HSTEM, 90, -184)
    # 244 puts the blunt end 0.39 of the way across the ink, where Helvetica's is.
    rect(g, 244, cy_up - ry_up - 2, 330, cy_lo + ry_lo + 2)

def draw_four(font):
    g = add_glyph(font, "four", 580, 0x0034)
    BAR = CAPHEIGHT // 3
    rect(g, 372, 0, 460, CAPHEIGHT)                              # stem
    rect(g, 60, BAR - HSTEM // 2, 500, BAR + HSTEM // 2)         # crossbar
    band(g, 416, CAPHEIGHT, 115, BAR)                            # diagonal

def draw_five(font):
    # Flat top bar, a short stem hanging from its left end, and a bowl swinging
    # off the stem's foot. The old five drew the bowl as two hand-written closed
    # contours that had to meet each other twice; they did not, so the mouth of
    # the bowl came out as a wedge and the top edge of the bowl and the foot of
    # the stem crossed at a coincident edge.
    #
    # It is one stroke on a centreline now. The bowl's arc starts at 135° — up
    # and to the left, inside the stem — and sweeps clockwise round through the
    # bottom to -170°, just past due left, so the upper terminal is buried and
    # only the lower one is visible. Both cuts are horizontal, which is what
    # Helvetica does: its bowl terminal is a flat cut, not a radial one.
    g = add_glyph(font, "five", 580, 0x0035)
    rect(g, 100, CAPHEIGHT - HSTEM, 490, CAPHEIGHT)   # the top bar
    # The bowl is nearly as wide as the whole advance — its outer edge runs from
    # 60 to 520, the same as zero's. A five whose bowl is only as wide as its bar
    # looks starved, and that is what the first attempt at this glyph did: the
    # bowl has to out-reach the bar by a good margin on both sides, as it does in
    # every grotesque. Helvetica's is 503 units wide against a 379-unit bar.
    # The end that meets the stem gets a butt cap, square to the stroke, not the
    # level cut the terminal gets. A level cut there is 121 units long against an
    # 82-unit stroke, because the stroke is climbing at 45°, and squaring it off
    # means sliding each corner 45 units along its own tangent — further than the
    # inner edge travels in the same stretch. The refitted inner edge then doubles
    # back on itself and opens a hairline crack at the corner, which is exactly
    # what the first version of this glyph did. Square to the stroke slides
    # nothing, and at 140° the cut lands inside the stem with room on both sides.
    stroke(g, arc_spline(290, 230, 186, 202, 140, -168), VSTEM, HSTEM, cap1=0.0)
    # 326 is 8 units under the cut's lower corner, so the whole cut is buried; a
    # stem stopping flush on it would leave a coincident edge, which the union and
    # the autohinter both read badly.
    rect(g, 100, 326, 100 + VSTEM, CAPHEIGHT - HSTEM + 4)

def draw_six(font):
    g = add_glyph(font, "six", 580, 0x0036)
    pen = g.getPen()
    cx, cy = 290, CAPHEIGHT//4; rx = 230; ry = CAPHEIGHT//4
    oval(g, cx, cy, rx, ry + OVS)
    oval(g, cx, cy, rx-HSTEM, ry-HSTEM + OVS, clockwise=True)
    # Spine: springs off the left of the bowl and rises to a terminal at the top
    # right. The old version put its control points above the end point, so the
    # stroke turned over early and topped out well short of the cap line.
    pen.moveTo((cx-rx, cy))
    pen.curveTo((cx-rx, cy+300),(cx-70, CAPHEIGHT),(cx+120, CAPHEIGHT))
    pen.lineTo((cx+120, CAPHEIGHT-HSTEM))
    pen.curveTo((cx-40, CAPHEIGHT-HSTEM),(cx-rx+HSTEM, cy+280),(cx-rx+HSTEM, cy))
    pen.closePath()

def draw_seven(font):
    g = add_glyph(font, "seven", 580, 0x0037)
    pen = g.getPen()
    pen.moveTo((80, CAPHEIGHT)); pen.lineTo((500, CAPHEIGHT))
    pen.lineTo((500, CAPHEIGHT-HSTEM)); pen.lineTo((240, 0))
    pen.lineTo((152, 0)); pen.lineTo((412, CAPHEIGHT-HSTEM))
    pen.lineTo((80, CAPHEIGHT-HSTEM)); pen.closePath()

def draw_eight(font):
    g = add_glyph(font, "eight", 580, 0x0038)
    top = int(CAPHEIGHT*0.28)
    for cy, ry in [(CAPHEIGHT - top, top + OVS), (top, top + OVS)]:
        oval(g, 290, cy, 200, ry)
        oval(g, 290, cy, 200-HSTEM, ry-HSTEM + OVS, clockwise=True)

def draw_nine(font):
    g = add_glyph(font, "nine", 580, 0x0039)
    cx, cy = 290, int(CAPHEIGHT*0.75); rx = 230; ry = int(CAPHEIGHT*0.25)
    oval(g, cx, cy, rx, ry + OVS)
    oval(g, cx, cy, rx-HSTEM, ry-HSTEM + OVS, clockwise=True)
    pen = g.getPen()
    # Spine, the 180° counterpart of six's: down to a terminal at the bottom left.
    pen.moveTo((cx+rx, cy))
    pen.curveTo((cx+rx, cy-300),(cx+70, 0),(cx-120, 0))
    pen.lineTo((cx-120, HSTEM))
    pen.curveTo((cx+40, HSTEM),(cx+rx-HSTEM, cy-280),(cx+rx-HSTEM, cy))
    pen.closePath()

DIGIT_DRAWERS = [
    draw_zero, draw_one, draw_two, draw_three, draw_four,
    draw_five, draw_six, draw_seven, draw_eight, draw_nine,
]

# ---------------------------------------------------------------------------
# Punctuation and symbols
# ---------------------------------------------------------------------------

def draw_punctuation(font):
    # space
    g = add_glyph(font, "space", 250, 0x0020)

    # period
    g = add_glyph(font, "period", 280, 0x002E)
    dot(g, 140, 60, 55)

    # comma
    g = add_glyph(font, "comma", 280, 0x002C)
    comma_shape(g, 140, 100)

    # colon
    g = add_glyph(font, "colon", 280, 0x003A)
    dot(g, 140, 60, 50)
    dot(g, 140, XHEIGHT-60, 50)

    # semicolon
    g = add_glyph(font, "semicolon", 280, 0x003B)
    comma_shape(g, 140, 100, r=50)
    dot(g, 140, XHEIGHT-60, 50)

    # exclamation
    g = add_glyph(font, "exclam", 280, 0x0021)
    rect(g, 96, 160, 184, CAPHEIGHT)
    dot(g, 140, 60, 55)

    # question
    g = add_glyph(font, "question", 520, 0x003F)
    oval(g, 260, 60, 55, 55)
    pen = g.getPen()
    pen.moveTo((216, 220)); pen.lineTo((216, 300))
    pen.curveTo((216, 380),(160, 420),(160, 500))
    pen.curveTo((160, 580),(220, CAPHEIGHT),(320, CAPHEIGHT))
    pen.curveTo((420, CAPHEIGHT),(480, 580),(480, 500))
    pen.curveTo((480, 440),(440, 400),(380, 380))
    pen.lineTo((380, 300)); pen.lineTo((304, 300)); pen.lineTo((304, 380))
    pen.curveTo((340, 396),(392, 420),(392, 500))
    pen.curveTo((392, 560),(360, CAPHEIGHT-HSTEM),(320, CAPHEIGHT-HSTEM))
    pen.curveTo((280, CAPHEIGHT-HSTEM),(248, 560),(248, 500))
    pen.curveTo((248, 440),(304, 400),(304, 300))
    pen.lineTo((304, 220)); pen.closePath()

    # hyphen-minus
    g = add_glyph(font, "hyphen", 340, 0x002D)
    rect(g, 60, XHEIGHT//2-HSTEM//2, 280, XHEIGHT//2+HSTEM//2)

    # underscore
    g = add_glyph(font, "underscore", 500, 0x005F)
    rect(g, 0, -120, 500, -120+HSTEM)

    # slash
    g = add_glyph(font, "slash", 400, 0x002F)
    band(g, 120, -DESCENDER // 2, 280, CAPHEIGHT)

    # backslash
    g = add_glyph(font, "backslash", 400, 0x005C)
    band(g, 120, CAPHEIGHT, 280, -DESCENDER // 2)

    # parens. The old pair was 133 units thick at the waist on a 105-unit bow —
    # thicker than a cap stem and barely curved, which is why they read as C and
    # D. Redrawn on a 180-unit bow with an 88-unit waist and 34-unit terminals,
    # and run from below the baseline to above the cap line as parens should.
    # The right one is a mirror of the left rather than a sign-flipped redraw, so
    # the two cannot drift apart.
    PAREN_TOP, PAREN_BOT = CAPHEIGHT + 60, -60
    for name, cp, mirror in [("parenleft",0x0028,False),("parenright",0x0029,True)]:
        g = add_glyph(font, name, 340, cp)
        pen = g.getPen()
        # The terminals were 34 units across against 88 at the middle, so both
        # parens tapered to a hair and dropped out at text sizes. Helvetica's are
        # 61 across the tip and 93 at the middle; these are 62 and 88, and the
        # outer control moves to x=0 so the bow is as deep as the aperture wants.
        x_out, x_in = 260, 198           # terminal, outer and inner edge
        xc_out, xc_in = 0, 138           # control x: sets the mid-height weight
        ky = int((PAREN_TOP - PAREN_BOT) * 0.30)
        pen.moveTo((x_out, PAREN_TOP))
        pen.curveTo((xc_out, PAREN_TOP - ky), (xc_out, PAREN_BOT + ky), (x_out, PAREN_BOT))
        pen.lineTo((x_in, PAREN_BOT))
        pen.curveTo((xc_in, PAREN_BOT + ky), (xc_in, PAREN_TOP - ky), (x_in, PAREN_TOP))
        pen.closePath()
        if mirror:
            flip_x(g, 170)

    # brackets. Previously both arms extended to the right whatever the sign, so
    # bracketleft and bracketright were byte-identical.
    for name, cp, mirror in [("bracketleft",0x005B,False),("bracketright",0x005D,True)]:
        g = add_glyph(font, name, 340, cp)
        rect(g, 80, PAREN_BOT, 80+HSTEM, PAREN_TOP)
        rect(g, 80, PAREN_BOT, 80+HSTEM+110, PAREN_BOT+HSTEM)
        rect(g, 80, PAREN_TOP-HSTEM, 80+HSTEM+110, PAREN_TOP)
        if mirror:
            flip_x(g, 170)

    # braces. Same story as the brackets: the sign flipped the arm positions but
    # not the HSTEM offsets, so braceright's stroke was measured outward instead
    # of inward. Drawn once and mirrored.
    for name, cp, mirror in [("braceleft",0x007B,False),("braceright",0x007D,True)]:
        g = add_glyph(font, name, 340, cp)
        cx = 170
        pen = g.getPen()
        TOP, BOT = PAREN_TOP, PAREN_BOT
        mid = (TOP + BOT) // 2
        pen.moveTo((cx+100, TOP))
        pen.curveTo((cx+40, TOP),(cx-20, TOP-60),(cx-20, TOP-120))
        pen.lineTo((cx-20, mid+60))
        pen.curveTo((cx-20, mid+20),(cx-80, mid),(cx-120, mid))
        pen.curveTo((cx-80, mid),(cx-20, mid-20),(cx-20, mid-60))
        pen.lineTo((cx-20, BOT+120))
        pen.curveTo((cx-20, BOT+60),(cx+40, BOT),(cx+100, BOT))
        pen.lineTo((cx+100, BOT+HSTEM))
        pen.curveTo((cx+60, BOT+HSTEM),(cx-20+HSTEM, BOT+80),(cx-20+HSTEM, BOT+120))
        pen.lineTo((cx-20+HSTEM, mid-60))
        pen.curveTo((cx-20+HSTEM, mid-30),(cx-60, mid),(cx-100, mid))
        pen.curveTo((cx-60, mid),(cx-20+HSTEM, mid+30),(cx-20+HSTEM, mid+60))
        pen.lineTo((cx-20+HSTEM, TOP-120))
        pen.curveTo((cx-20+HSTEM, TOP-80),(cx+60, TOP-HSTEM),(cx+100, TOP-HSTEM))
        pen.closePath()
        if mirror:
            flip_x(g, 170)

    # quotation marks
    for name, cp, dx in [("quotedbl",0x0022,80),("quotesingle",0x0027,0)]:
        g = add_glyph(font, name, 300 if dx else 200, cp)
        for x in ([80, 80+dx] if dx else [100]):
            rect(g, x, CAPHEIGHT-160, x+HSTEM, CAPHEIGHT)

    # grave / acute
    for name, cp, slant in [("grave",0x0060,-1),("acute",0x00B4,1)]:
        g = add_glyph(font, name, 400, cp)
        pen = g.getPen()
        bx = 200 - slant*60
        y0, y1 = XHEIGHT + 80, XHEIGHT + 160
        pen.moveTo((bx, y0)); pen.lineTo((bx+slant*80, y1))
        pen.lineTo((bx+slant*80+HSTEM, y1))
        pen.lineTo((bx+HSTEM, y0)); pen.closePath()

    # at sign
    g = add_glyph(font, "at", 860, 0x0040)
    # The inner form has to be a legible a, not a dot. Helvetica's is 0.41 of the
    # advance wide with a 214-unit counter; mine was 0.33 with a 120-unit counter,
    # which closes up below about 20 px and leaves a blob inside a ring.
    CY = CAPHEIGHT // 2
    oval(g, 430, CY, 380, CY)
    oval(g, 430, CY, 380 - 70, CY - 70, clockwise=True)
    oval(g, 400, CY, 175, 185)
    oval(g, 400, CY, 175 - 72, 185 - 72, clockwise=True)
    rect(g, 400 + 175 - 72, CY - 190, 400 + 175, CY + 150)

    # hash
    g = add_glyph(font, "numbersign", 580, 0x0023)
    rect(g, 160, 0, 160+HSTEM, CAPHEIGHT)
    rect(g, 340, 0, 340+HSTEM, CAPHEIGHT)
    rect(g, 60, CAPHEIGHT//3*2-HSTEM//2, 520, CAPHEIGHT//3*2+HSTEM//2)
    rect(g, 60, CAPHEIGHT//3-HSTEM//2, 520, CAPHEIGHT//3+HSTEM//2)

    # dollar
    g = add_glyph(font, "dollar", 580, 0x0024)
    pen = g.getPen()
    cx, cy = 290, CAPHEIGHT//2
    ry = CAPHEIGHT//2 + OVS
    pen.moveTo((cx+200, cy+100))
    pen.curveTo((cx+200, cy+220),(cx+80, cy+260),(cx, cy+260))
    pen.curveTo((cx-100, cy+260),(cx-200, cy+180),(cx-200, cy+80))
    pen.curveTo((cx-200, cy),(cx-80, cy-40),(cx, cy-40))
    pen.curveTo((cx+80, cy-40),(cx+200, cy-80),(cx+200, cy-160))
    pen.curveTo((cx+200, cy-260),(cx+80, cy-260),(cx, cy-260))
    pen.curveTo((cx-100, cy-260),(cx-200, cy-220),(cx-200, cy-100))
    pen.lineTo((cx-200+HSTEM, cy-100))
    pen.curveTo((cx-200+HSTEM, cy-200),(cx-60, cy-260+HSTEM),(cx, cy-260+HSTEM))
    pen.curveTo((cx+80, cy-260+HSTEM),(cx+200-HSTEM, cy-200),(cx+200-HSTEM, cy-160))
    pen.curveTo((cx+200-HSTEM, cy-60),(cx+60, cy-HSTEM),(cx, cy-HSTEM))
    pen.curveTo((cx-80, cy-HSTEM),(cx-200+HSTEM, cy+20),(cx-200+HSTEM, cy+80))
    pen.curveTo((cx-200+HSTEM, cy+160),(cx-60, cy+260-HSTEM),(cx, cy+260-HSTEM))
    pen.curveTo((cx+80, cy+260-HSTEM),(cx+200-HSTEM, cy+200),(cx+200-HSTEM, cy+100))
    pen.closePath()
    rect(g, cx-HSTEM//2, -60, cx+HSTEM//2, CAPHEIGHT+60)

    # percent
    # The rings were r=120 outside and r=44 inside, so each counter was 88 units
    # across — a tenth of an em, which fills in solid below 24 px and leaves two
    # dots. Helvetica's are 340 across the outside and 200 across the counter, a
    # 0.59 ratio; these follow it. The slash was also a full stem thick; Helvetica
    # cuts its percent slash to 0.59 of a stem, so it does here too.
    g = add_glyph(font, "percent", 740, 0x0025)
    RO, RI = 140, 72
    for cx, cy in ((180, 540), (560, 140)):
        oval(g, cx, cy, RO, RO)
        oval(g, cx, cy, RI, RI, clockwise=True)
    pen = g.getPen()
    pen.moveTo((600, CAPHEIGHT)); pen.lineTo((660, CAPHEIGHT))
    pen.lineTo((140, -OVS)); pen.lineTo((80, -OVS)); pen.closePath()

    # ampersand. The old one was an oval with two straight bars laid across it and
    # read as a script p-with-a-flourish. This is the grotesque construction: a
    # closed loop up top, a large bowl below it open at the upper right, a thick
    # diagonal from the loop down into the leg, and a leg cut flat at both ends.
    # The bowl and the diagonal both die inside the leg, so the only joins are
    # buried and there is no edge for the rasteriser to split.
    g = add_glyph(font, "ampersand", 700, 0x0026)
    oval(g, 300, 545, 158, 166)
    oval(g, 300, 545, 158 - 80, 166 - 76, clockwise=True)
    stroke(g, spline([                            # the bowl
        (250, 430, 240.0, None, None),
        (120, 250, 270.0, None, K_CIRCLE * 220),
        (300,  30,   0.0, K_CIRCLE * 180, K_CIRCLE * 200),
        (500, 180,  65.0, K_CIRCLE * 150, None),
    ]), VSTEM, HSTEM)
    stroke(g, spline([                            # the diagonal
        (330, 420, -50.0, None, None),
        (490, 215, -60.0, None, None),
    ]), VSTEM, HSTEM)
    stroke(g, spline([                            # the leg
        (505, 340, 255.0, None, None),
        (585,   0, 285.0, None, None),
    ]), VSTEM, HSTEM, cap0=0.0, cap1=0.0)

    # asterisk. This was three identical rectangles plus three shapes whose corner
    # arithmetic used abs(int(sin)), which is 0 or 1, so it drew a blob. A real
    # five-pointed star: arms 145 long and 56 wide, the valley between two arms
    # falling out of the geometry as h/sin(36 degrees) rather than being guessed.
    g = add_glyph(font, "asterisk", 380, 0x002A)
    cx, cy, R, h = 190.0, 573.0, 145.0, 28.0
    rho = h / math.sin(math.radians(36.0))
    pts = []
    for k in range(5):
        th = 90.0 + 72.0 * k
        u = (math.cos(math.radians(th)), math.sin(math.radians(th)))
        for side in (-90.0, 90.0):                # the arm's two tip corners
            n = (math.cos(math.radians(th + side)), math.sin(math.radians(th + side)))
            pts.append((cx + R * u[0] + h * n[0], cy + R * u[1] + h * n[1]))
        v = math.radians(th + 36.0)               # and the valley after it
        pts.append((cx + rho * math.cos(v), cy + rho * math.sin(v)))
    pen = g.getPen()
    pen.moveTo(pts[0])
    for p in pts[1:]:
        pen.lineTo(p)
    pen.closePath()

    # plus
    g = add_glyph(font, "plus", 580, 0x002B)
    rect(g, 40, CAPHEIGHT//2-HSTEM//2, 540, CAPHEIGHT//2+HSTEM//2)
    rect(g, 290-HSTEM//2, 100, 290+HSTEM//2, CAPHEIGHT-100)

    # equals
    g = add_glyph(font, "equal", 580, 0x003D)
    rect(g, 60, CAPHEIGHT//2+40, 520, CAPHEIGHT//2+40+HSTEM)
    rect(g, 60, CAPHEIGHT//2-40-HSTEM, 520, CAPHEIGHT//2-40)

    # less / greater. The sign arithmetic flipped the arms but not the HSTEM
    # offsets, so greater's inner edge landed outside the glyph; mirrored instead.
    for name, cp, mirror in [("less",0x003C,False),("greater",0x003E,True)]:
        g = add_glyph(font, name, 580, cp)
        pen = g.getPen()
        # Offsetting the arm ends by HSTEM *horizontally* on a 34-degree arm left
        # only 42 units perpendicular — half a stem — so both signs came out
        # hairline thin and needle-pointed. Both ends and the vertex are cut
        # vertically instead, with the 88-unit cut height chosen so the arm
        # measures a stem across it.
        MID = CAPHEIGHT // 2
        pen.moveTo((40, MID + 41))
        for p in [(540, MID+232), (540, MID+144), (131, MID),
                  (540, MID-143), (540, MID-231), (40, MID-40)]:
            pen.lineTo(p)
        pen.closePath()
        if mirror:
            flip_x(g, 290)

    # vertical bar
    g = add_glyph(font, "bar", 280, 0x007C)
    rect(g, 96, 0, 184, CAPHEIGHT)

    # tilde
    g = add_glyph(font, "asciitilde", 580, 0x007E)
    pen = g.getPen()
    pen.moveTo((60, XHEIGHT//2-20))
    pen.curveTo((100, XHEIGHT//2+80),(200, XHEIGHT//2+80),(290, XHEIGHT//2))
    pen.curveTo((380, XHEIGHT//2-80),(480, XHEIGHT//2-80),(520, XHEIGHT//2+20))
    pen.lineTo((520, XHEIGHT//2+20+HSTEM))
    pen.curveTo((480, XHEIGHT//2-80+HSTEM),(380, XHEIGHT//2-80+HSTEM),(290, XHEIGHT//2+HSTEM))
    pen.curveTo((200, XHEIGHT//2+80+HSTEM),(100, XHEIGHT//2+80+HSTEM),(60, XHEIGHT//2-20+HSTEM))
    pen.closePath()

    # circumflex
    g = add_glyph(font, "asciicircum", 580, 0x005E)
    pen = g.getPen()
    pen.moveTo((60, XHEIGHT))
    pen.lineTo((290-HSTEM//2, CAPHEIGHT))
    pen.lineTo((290+HSTEM//2, CAPHEIGHT))
    pen.lineTo((520, XHEIGHT))
    pen.lineTo((520-HSTEM, XHEIGHT))
    pen.lineTo((290, CAPHEIGHT-80))
    pen.lineTo((60+HSTEM, XHEIGHT))
    pen.closePath()


# ---------------------------------------------------------------------------
# Combining marks and spacing accents
# ---------------------------------------------------------------------------

def draw_marks(font):
    # Combining marks (zero-width). The kind numbers select the shape drawn
    # below; they were previously shifted by one from acutecomb onward, so every
    # mark from acute to caron drew its predecessor's shape — acutecomb came out
    # as a grave, tildecomb as a circumflex, caroncomb as a double acute, and no
    # glyph in the font was actually a caron.
    marks = [
        ("gravecomb",    0x0300, -1,  0),
        ("acutecomb",    0x0301,  1,  1),
        ("circumflexcomb",0x0302, 0,  2),
        ("tildecomb",    0x0303,  0,  3),
        ("macroncomb",   0x0304,  0,  4),
        ("brevecomb",    0x0306,  0,  5),
        ("dotaccentcomb",0x0307,  0,  6),
        ("dieresiscomb", 0x0308,  0,  7),
        ("ringcomb",     0x030A,  0,  8),
        ("hungarumlautcomb",0x030B,0, 9),
        ("caroncomb",    0x030C,  0, 13),
        ("commaaccentcomb",0x0326,0, 10),
        ("cedillacomb",  0x0327,  0, 11),
        ("ogonekcomb",   0x0328,  0, 12),
    ]
    for name, cp, slant, kind in marks:
        g = add_glyph(font, name, 0, cp)
        cx = 0  # zero-width, centred at 0
        if kind == 0:  # grave
            # The acute mirrored in x: high at the left, low at the right. As
            # written before it rose to the right, so A-grave and A-acute were
            # the same glyph.
            pen = g.getPen()
            pen.moveTo((0, CAPHEIGHT+80)); pen.lineTo((-80, CAPHEIGHT+160))
            pen.lineTo((-80-HSTEM, CAPHEIGHT+160)); pen.lineTo((-HSTEM, CAPHEIGHT+80))
            pen.closePath()
        elif kind == 1:  # acute
            pen = g.getPen()
            pen.moveTo((0, CAPHEIGHT+80)); pen.lineTo((80, CAPHEIGHT+160))
            pen.lineTo((80+HSTEM, CAPHEIGHT+160)); pen.lineTo((HSTEM, CAPHEIGHT+80))
            pen.closePath()
        elif kind == 2:  # circumflex
            pen = g.getPen()
            pen.moveTo((-80, CAPHEIGHT+80)); pen.lineTo((0, CAPHEIGHT+160))
            pen.lineTo((80, CAPHEIGHT+80)); pen.lineTo((80-HSTEM, CAPHEIGHT+80))
            pen.lineTo((0, CAPHEIGHT+160-HSTEM)); pen.lineTo((-80+HSTEM, CAPHEIGHT+80))
            pen.closePath()
        elif kind == 3:  # tilde
            # A wave, not an arch: it was drawn as a single hump, which is a
            # breve, so A-tilde and A-breve were indistinguishable. Stroked with
            # a flat nib so the crest and trough thin and the diagonal between
            # them carries the weight, the way a grotesque tilde does.
            # Helvetica's tilde is 341 wide and 115 tall against a 63-thick
            # stroke: it is the width, not the amplitude, that makes a wave read
            # as a wave. 300 x 108 here, on the same near-3:1 footing.
            MID = CAPHEIGHT + 130
            stroke(g, spline([
                (-108, MID - 20,  40.0, None, None),
                ( -54, MID + 26,   0.0, None, None),
                (   0, MID,      -28.0, None, None),
                (  54, MID - 26,   0.0, None, None),
                ( 108, MID + 20,  40.0, None, None),
            ]), 84, 56)
        elif kind == 4:  # macron
            rect(g, -80, CAPHEIGHT+100, 80, CAPHEIGHT+100+HSTEM)
        elif kind == 5:  # breve
            pen = g.getPen()
            pen.moveTo((-80, CAPHEIGHT+160))
            pen.curveTo((-80, CAPHEIGHT+80),(80, CAPHEIGHT+80),(80, CAPHEIGHT+160))
            pen.lineTo((80, CAPHEIGHT+160+HSTEM))
            pen.curveTo((80, CAPHEIGHT+80+HSTEM),(-80, CAPHEIGHT+80+HSTEM),(-80, CAPHEIGHT+160+HSTEM))
            pen.closePath()
        elif kind == 6:  # dot above
            oval(g, 0, CAPHEIGHT+120, 44, 44)
        elif kind == 7:  # diaeresis
            oval(g, -60, CAPHEIGHT+120, 40, 40)
            oval(g, 60, CAPHEIGHT+120, 40, 40)
        elif kind == 8:  # ring above
            oval(g, 0, CAPHEIGHT+140, 55, 55)
            oval(g, 0, CAPHEIGHT+140, 20, 20, clockwise=True)
        elif kind == 9:  # double acute
            for dx in [-50, 50]:
                pen = g.getPen()
                pen.moveTo((dx, CAPHEIGHT+80)); pen.lineTo((dx+60, CAPHEIGHT+160))
                pen.lineTo((dx+60+HSTEM, CAPHEIGHT+160)); pen.lineTo((dx+HSTEM, CAPHEIGHT+80))
                pen.closePath()
        elif kind == 10:  # comma below
            pen = g.getPen()
            pen.moveTo((0, -60)); pen.lineTo((40, 0))
            pen.lineTo((0, 0)); pen.lineTo((-40, -60)); pen.closePath()
        elif kind == 11:  # cedilla
            pen = g.getPen()
            pen.moveTo((0, 0)); pen.lineTo((60, -60))
            pen.curveTo((60, -120),(-60, -120),(-60, -60))
            pen.lineTo((-60+HSTEM, -60))
            pen.curveTo((-60+HSTEM, -120+HSTEM),(60-HSTEM, -120+HSTEM),(60-HSTEM, -60))
            pen.lineTo((HSTEM, 0)); pen.closePath()
        elif kind == 13:  # caron — an inverted circumflex
            pen = g.getPen()
            pen.moveTo((-80, CAPHEIGHT+160)); pen.lineTo((0, CAPHEIGHT+80))
            pen.lineTo((80, CAPHEIGHT+160)); pen.lineTo((80-HSTEM, CAPHEIGHT+160))
            pen.lineTo((0, CAPHEIGHT+80+HSTEM)); pen.lineTo((-80+HSTEM, CAPHEIGHT+160))
            pen.closePath()
        elif kind == 12:  # ogonek
            pen = g.getPen()
            pen.moveTo((0, 0)); pen.lineTo((0, -40))
            pen.curveTo((0, -120),(80, -120),(80, -60))
            pen.lineTo((80-HSTEM, -60))
            pen.curveTo((80-HSTEM, -120+HSTEM),(HSTEM, -80),(HSTEM, -40))
            pen.lineTo((HSTEM, 0)); pen.closePath()

    # spacing accents (non-zero width)
    spacing = [
        ("dieresis",  0x00A8, 7),
        ("macron",    0x00AF, 4),
        ("breve",     0x02D8, 5),
        ("dotaccent", 0x02D9, 6),
        ("ring",      0x02DA, 8),
        ("hungarumlaut",0x02DD, 9),
        ("caron",     0x02C7, 13),
        ("circumflex",0x02C6, 2),
        ("tilde",     0x02DC, 3),
        ("cedilla",   0x00B8, 11),
        ("ogonek",    0x02DB, 12),
    ]
    marks_map = {0:"gravecomb", 1:"acutecomb", 2:"circumflexcomb", 3:"tildecomb",
                 4:"macroncomb", 5:"brevecomb", 6:"dotaccentcomb", 7:"dieresiscomb",
                 8:"ringcomb", 9:"hungarumlautcomb", 11:"cedillacomb",
                 12:"ogonekcomb", 13:"caroncomb"}
    for name, cp, kind in spacing:
        g = add_glyph(font, name, 400, cp)
        src = marks_map.get(kind)
        if src and src in font:
            # Reuse the combining shape, moved to the centre of the advance. The
            # above-marks come down to where they would sit over a lowercase
            # letter; the below-marks are already at the baseline and stay put.
            below = kind in (10, 11, 12)
            component(g, src, 200, 0 if below else XHEIGHT - CAPHEIGHT)


# ---------------------------------------------------------------------------
# Accented letters — built as components
# ---------------------------------------------------------------------------

# Map: glyph_name -> (unicode, base_glyph, mark_glyph, mark_dx, mark_dy)
# mark_dy is relative to baseline; we compute shift so mark sits above base
ACCENTED: list[tuple[str,int,str,str]] = [
    # uppercase A
    ("Agrave",   0x00C0, "A", "gravecomb"),
    ("Aacute",   0x00C1, "A", "acutecomb"),
    ("Acircumflex",0x00C2,"A","circumflexcomb"),
    ("Atilde",   0x00C3, "A", "tildecomb"),
    ("Adieresis",0x00C4, "A", "dieresiscomb"),
    ("Aring",    0x00C5, "A", "ringcomb"),
    # C
    ("Ccedilla", 0x00C7, "C", "cedillacomb"),
    # E
    ("Egrave",   0x00C8, "E", "gravecomb"),
    ("Eacute",   0x00C9, "E", "acutecomb"),
    ("Ecircumflex",0x00CA,"E","circumflexcomb"),
    ("Edieresis",0x00CB, "E", "dieresiscomb"),
    # I
    ("Igrave",   0x00CC, "I", "gravecomb"),
    ("Iacute",   0x00CD, "I", "acutecomb"),
    ("Icircumflex",0x00CE,"I","circumflexcomb"),
    ("Idieresis",0x00CF, "I", "dieresiscomb"),
    # N
    ("Ntilde",   0x00D1, "N", "tildecomb"),
    # O
    ("Ograve",   0x00D2, "O", "gravecomb"),
    ("Oacute",   0x00D3, "O", "acutecomb"),
    ("Ocircumflex",0x00D4,"O","circumflexcomb"),
    ("Otilde",   0x00D5, "O", "tildecomb"),
    ("Odieresis",0x00D6, "O", "dieresiscomb"),
    # U
    ("Ugrave",   0x00D9, "U", "gravecomb"),
    ("Uacute",   0x00DA, "U", "acutecomb"),
    ("Ucircumflex",0x00DB,"U","circumflexcomb"),
    ("Udieresis",0x00DC, "U", "dieresiscomb"),
    # Y
    ("Yacute",   0x00DD, "Y", "acutecomb"),
    # lowercase a
    ("agrave",   0x00E0, "a", "gravecomb"),
    ("aacute",   0x00E1, "a", "acutecomb"),
    ("acircumflex",0x00E2,"a","circumflexcomb"),
    ("atilde",   0x00E3, "a", "tildecomb"),
    ("adieresis",0x00E4, "a", "dieresiscomb"),
    ("aring",    0x00E5, "a", "ringcomb"),
    # c
    ("ccedilla", 0x00E7, "c", "cedillacomb"),
    # e
    ("egrave",   0x00E8, "e", "gravecomb"),
    ("eacute",   0x00E9, "e", "acutecomb"),
    ("ecircumflex",0x00EA,"e","circumflexcomb"),
    ("edieresis",0x00EB, "e", "dieresiscomb"),
    # i
    ("igrave",   0x00EC, "i", "gravecomb"),
    ("iacute",   0x00ED, "i", "acutecomb"),
    ("icircumflex",0x00EE,"i","circumflexcomb"),
    ("idieresis",0x00EF, "i", "dieresiscomb"),
    # n
    ("ntilde",   0x00F1, "n", "tildecomb"),
    # o
    ("ograve",   0x00F2, "o", "gravecomb"),
    ("oacute",   0x00F3, "o", "acutecomb"),
    ("ocircumflex",0x00F4,"o","circumflexcomb"),
    ("otilde",   0x00F5, "o", "tildecomb"),
    ("odieresis",0x00F6, "o", "dieresiscomb"),
    # u
    ("ugrave",   0x00F9, "u", "gravecomb"),
    ("uacute",   0x00FA, "u", "acutecomb"),
    ("ucircumflex",0x00FB,"u","circumflexcomb"),
    ("udieresis",0x00FC, "u", "dieresiscomb"),
    # y
    ("yacute",   0x00FD, "y", "acutecomb"),
    ("ydieresis",0x00FF, "y", "dieresiscomb"),
    # Latin Ext-A sample
    ("Amacron",  0x0100, "A", "macroncomb"),
    ("amacron",  0x0101, "a", "macroncomb"),
    ("Abreve",   0x0102, "A", "brevecomb"),
    ("abreve",   0x0103, "a", "brevecomb"),
    ("Aogonek",  0x0104, "A", "ogonekcomb"),
    ("aogonek",  0x0105, "a", "ogonekcomb"),
    ("Cacute",   0x0106, "C", "acutecomb"),
    ("cacute",   0x0107, "c", "acutecomb"),
    ("Ccaron",   0x010C, "C", "caroncomb"),
    ("ccaron",   0x010D, "c", "caroncomb"),
    ("Emacron",  0x0112, "E", "macroncomb"),
    ("emacron",  0x0113, "e", "macroncomb"),
    ("Eogonek",  0x0118, "E", "ogonekcomb"),
    ("eogonek",  0x0119, "e", "ogonekcomb"),
    ("Ecaron",   0x011A, "E", "caroncomb"),
    ("ecaron",   0x011B, "e", "caroncomb"),
    ("Nacute",   0x0143, "N", "acutecomb"),
    ("nacute",   0x0144, "n", "acutecomb"),
    ("Ncaron",   0x0147, "N", "caroncomb"),
    ("ncaron",   0x0148, "n", "caroncomb"),
    ("Oacute",   0x00D3, "O", "acutecomb"),
    ("Odblacute",0x0150, "O", "hungarumlautcomb"),
    ("odblacute",0x0151, "o", "hungarumlautcomb"),
    ("Racute",   0x0154, "R", "acutecomb"),
    ("racute",   0x0155, "r", "acutecomb"),
    ("Rcaron",   0x0158, "R", "caroncomb"),
    ("rcaron",   0x0159, "r", "caroncomb"),
    ("Sacute",   0x015A, "S", "acutecomb"),
    ("sacute",   0x015B, "s", "acutecomb"),
    ("Scaron",   0x0160, "S", "caroncomb"),
    ("scaron",   0x0161, "s", "caroncomb"),
    ("Tcaron",   0x0164, "T", "caroncomb"),
    ("tcaron",   0x0165, "t", "caroncomb"),
    ("Umacron",  0x016A, "U", "macroncomb"),
    ("umacron",  0x016B, "u", "macroncomb"),
    ("Uring",    0x016E, "U", "ringcomb"),
    ("uring",    0x016F, "u", "ringcomb"),
    ("Udblacute",0x0170, "U", "hungarumlautcomb"),
    ("udblacute",0x0171, "u", "hungarumlautcomb"),
    ("Uogonek",  0x0172, "U", "ogonekcomb"),
    ("uogonek",  0x0173, "u", "ogonekcomb"),
    ("Zcacute",  0x0179, "Z", "acutecomb"),
    ("zacute",   0x017A, "z", "acutecomb"),
    ("Zdotaccent",0x017B,"Z", "dotaccentcomb"),
    ("zdotaccent",0x017C,"z","dotaccentcomb"),
    ("Zcaron",   0x017D, "Z", "caroncomb"),
    ("zcaron",   0x017E, "z", "caroncomb"),
    # Romanian comma-below
    ("Scommaaccent",0x0218,"S","commaaccentcomb"),
    ("scommaaccent",0x0219,"s","commaaccentcomb"),
    ("Tcommaaccent",0x021A,"T","commaaccentcomb"),
    ("tcommaaccent",0x021B,"t","commaaccentcomb"),
]


# How much clear air to leave between a base letter and its mark.
ACCENT_GAP = 30


def place_accent(font, name, cp, base, mark):
    """Compose an accented letter, positioning the mark over (or under) the base.

    The combining marks are drawn centred on x=0 and sitting above the cap line.
    Dropping them at (0, 0) — which is what this used to do — left every accent
    hanging off the left edge of its base and floating at cap-accent height even
    over an x-height letter. The mark is now centred on the base's ink and moved
    vertically to clear it by ACCENT_GAP; marks that belong below the letter are
    measured down from the base's foot instead.
    """
    from fontTools.pens.boundsPen import BoundsPen

    def ink(g):
        p = BoundsPen(font)
        g.draw(p)
        return p.bounds

    if mark not in font:
        return
    mark_g = font[mark]
    mb = ink(mark_g)
    below = mb is not None and (mb[1] + mb[3]) / 2 < 0

    # An accent above i or j replaces the dot rather than stacking on top of it.
    if not below:
        dotless = {"i": "dotlessi", "j": "dotlessj"}.get(base)
        if dotless and dotless in font:
            base = dotless
    if base not in font:
        return

    base_g = font[base]
    bb = ink(base_g)
    g = add_glyph(font, name, base_g.width, cp)
    component(g, base)
    if bb is None or mb is None:
        component(g, mark, 0, 0)
        return
    dx = round((bb[0] + bb[2]) / 2 - (mb[0] + mb[2]) / 2)
    if below:
        dy = round(bb[1] - ACCENT_GAP - mb[3])
    else:
        dy = round(bb[3] + ACCENT_GAP - mb[1])
    component(g, mark, dx, dy)


def draw_accented(font):
    for name, cp, base, mark in ACCENTED:
        place_accent(font, name, cp, base, mark)



# ── Extra symbols / punctuation ──────────────────────────────────────────────

def draw_extra_symbols(font):
    W = 600
    # non-breaking space (same width as space, no contours)
    g = add_glyph(font, "nbspace", font["space"].width if "space" in font else 250, 0x00A0)

    # inverted exclamation  ¡
    g = add_glyph(font, "exclamdown", 280, 0x00A1)
    rectwh(g, 110, -200, 60, 340)   # stem (below baseline)
    rectwh(g, 95,  160,  90,  90)   # dot

    # inverted question  ¿
    g = add_glyph(font, "questiondown", 480, 0x00BF)
    rectwh(g, 190, -200, 100, 60)   # bottom stem
    rectwh(g, 190, -140, 100, 140)  # left arc stub
    rectwh(g, 290, -60,  100, 60)   # bottom arc
    rectwh(g, 290,  60,  100, 100)  # right arc
    rectwh(g, 190,  160, 100, 60)   # top stub
    rectwh(g, 195,  230,  90,  90)  # dot

    # guillemets  « »
    g = add_glyph(font, "guillemotleft", 480, 0x00AB)
    rectwh(g,  60, 160, 80, 200)
    rectwh(g, 160, 160, 80, 200)
    rectwh(g,  60, 260, 80, 100)
    rectwh(g, 160, 260, 80, 100)

    g = add_glyph(font, "guillemotright", 480, 0x00BB)
    rectwh(g, 240, 160, 80, 200)
    rectwh(g, 340, 160, 80, 200)
    rectwh(g, 240, 260, 80, 100)
    rectwh(g, 340, 260, 80, 100)

    # single guillemets  ‹ ›
    g = add_glyph(font, "guilsinglleft",  320, 0x2039)
    rectwh(g,  60, 160, 80, 200)
    rectwh(g,  60, 260, 80, 100)

    g = add_glyph(font, "guilsinglright", 320, 0x203A)
    rectwh(g, 180, 160, 80, 200)
    rectwh(g, 180, 260, 80, 100)

    # middle dot  ·
    g = add_glyph(font, "periodcentered", 280, 0x00B7)
    rectwh(g, 95, 240, 90, 90)

    # section sign  §  — two S-curves stacked. Rather than approximate the
    # curves, take the real S and use a squashed copy for each half, the lower
    # one turned through 180°, overlapping in the middle where they join.
    g = add_glyph(font, "section", 520, 0x00A7)
    sb = ink(font, "S")
    if sb:
        sx = 300 / (sb[2] - sb[0])
        sy = 430 / (sb[3] - sb[1])
        left, half_h = 110, 215
        # Upper half, sitting high.
        copy_outline(font, g, "S", dx=left - sb[0] * sx, dy=330 - sb[1] * sy, sx=sx, sy=sy)
        # Lower half: the same curve turned through 180° so the two bends mirror
        # each other, dropped so the two halves overlap where they join.
        scratch = add_glyph(font, "_section.tmp", 0)
        copy_outline(font, scratch, "S", dx=left - sb[0] * sx, dy=-30 - sb[1] * sy,
                     sx=sx, sy=sy)
        rotate180(scratch, left + 150, -30 + half_h)
        copy_outline(font, g, "_section.tmp")
        del font["_section.tmp"]

    # copyright  ©  and registered  ®  — a ring with a small letter inside.
    # The letter is a scaled component of the real C or R, so it cannot drift
    # away from the design as the masters change.
    for name, cp, letter in [("copyright", 0x00A9, "C"), ("registered", 0x00AE, "R")]:
        g = add_glyph(font, name, 720, cp)   # ring 60..660, so 60 each side
        cx = cy = 360
        r_out, ring = 300, 56
        dot(g, cx, cy, r_out)
        dot(g, cx, cy, r_out - ring, clockwise=True)
        lb = ink(font, letter)
        if lb:
            # Large enough that the letter's own strokes still read at 16 px:
            # a smaller ring letter goes grey before the ring does.
            scale = 400 / (lb[3] - lb[1])
            component(g, letter, cx - (lb[0] + lb[2]) / 2 * scale,
                      cy - (lb[1] + lb[3]) / 2 * scale, scale)

    # degree  °
    g = add_glyph(font, "degree", 340, 0x00B0)
    dot(g, 170, CAPHEIGHT - 130, 110)
    dot(g, 170, CAPHEIGHT - 130, 110 - 52, clockwise=True)

    # pilcrow  ¶  — a filled bowl at cap height with two stems below it
    g = add_glyph(font, "paragraph", 560, 0x00B6)
    P_BOWL = int(CAPHEIGHT * 0.42)          # how far down the solid bowl reaches
    rect(g, 300, DESCENDER + 40, 300 + HSTEM, CAPHEIGHT)
    rect(g, 430, DESCENDER + 40, 430 + HSTEM, CAPHEIGHT)
    rect(g, 180, P_BOWL, 460, CAPHEIGHT)    # the bowl's flat right part
    oval(g, 180, (P_BOWL + CAPHEIGHT) // 2, 130,
         (CAPHEIGHT - P_BOWL) // 2 + OVS)   # its round left side

    # multiplication  ×
    g = add_glyph(font, "multiply", 560, 0x00D7)
    pen = g.getPen()
    pen.moveTo((80, 160)); pen.lineTo((160, 160)); pen.lineTo((280, 300))
    pen.lineTo((400, 160)); pen.lineTo((480, 160)); pen.lineTo((480, 240))
    pen.lineTo((360, 380)); pen.lineTo((480, 520)); pen.lineTo((480, 600))
    pen.lineTo((400, 600)); pen.lineTo((280, 460)); pen.lineTo((160, 600))
    pen.lineTo((80, 600));  pen.lineTo((80, 520));  pen.lineTo((200, 380))
    pen.lineTo((80, 240));  pen.closePath()

    # division  ÷
    g = add_glyph(font, "divide", 560, 0x00F7)
    rectwh(g, 80, 340, 400, 80)    # bar
    rectwh(g, 235, 460, 90, 90)    # top dot
    rectwh(g, 235, 210, 90, 90)    # bottom dot

    # bullet  •
    g = add_glyph(font, "bullet", 400, 0x2022)
    dot(g, 200, XHEIGHT//2, 92)

    # ellipsis  …  — three periods on the period's own advance, so that
    # "a..." and "a…" set to the same width.
    g = add_glyph(font, "ellipsis", 840, 0x2026)
    for x in (140, 420, 700):
        dot(g, x, 60, 55)

    # en dash / em dash / minus. All three were being drawn 230 units thick and
    # centred at y=185 because a width/height pair was passed to a corner-pair
    # signature. The dashes take the hyphen's weight and height so that a run of
    # hyphens and dashes sits on one line; minus is centred on the maths axis
    # instead, level with the bar of plus and equal.
    DASH_Y = XHEIGHT//2
    g = add_glyph(font, "endash", 500, 0x2013)
    rect(g, 40, DASH_Y-HSTEM//2, 460, DASH_Y+HSTEM//2)

    g = add_glyph(font, "emdash", 1000, 0x2014)
    rect(g, 0, DASH_Y-HSTEM//2, 1000, DASH_Y+HSTEM//2)

    g = add_glyph(font, "minus", 580, 0x2212)
    rect(g, 40, CAPHEIGHT//2-HSTEM//2, 540, CAPHEIGHT//2+HSTEM//2)

    # Curly quotes. These were four flat blocks stacked into an L; they are now
    # real comma shapes. The opening forms are the closing forms turned through
    # 180°, which is the only difference between ‘ and ’.
    QUOTE_R = 52
    QUOTE_TOP = CAPHEIGHT
    for name, cp, opening, base in [
        ("quoteright",     0x2019, False, False),
        ("quoteleft",      0x2018, True,  False),
        ("quotesinglbase", 0x201A, False, True),
    ]:
        g = add_glyph(font, name, 280, cp)
        cy = (QUOTE_R + 60) if base else (QUOTE_TOP - QUOTE_R)
        axis = comma_shape(g, 140, cy, r=QUOTE_R, drop=170)
        if opening:
            rotate180(g, 140, axis)

    for name, cp, opening in [("quotedblright", 0x201D, False),
                              ("quotedblleft",  0x201C, True),
                              ("quotedblbase",  0x201E, False)]:
        g = add_glyph(font, name, 440, cp)
        cy = (QUOTE_R + 60) if "base" in name else (QUOTE_TOP - QUOTE_R)
        for x in (130, 310):
            axis = comma_shape(g, x, cy, r=QUOTE_R, drop=170)
        # Rotate once, about the midpoint of the pair, so the two marks swap
        # places as well as turning over.
        if opening:
            rotate180(g, 220, axis)

    # trade mark  ™
    g = add_glyph(font, "trademark", 740, 0x2122)
    # T
    rectwh(g, 60,  480, 220, 60)
    rectwh(g, 150, 300, 60, 180)
    # M
    rectwh(g, 320, 300, 60, 240)
    rectwh(g, 620, 300, 60, 240)
    pen = g.getPen()
    pen.moveTo((380,540)); pen.lineTo((490,300)); pen.lineTo((560,300))
    pen.lineTo((560,540)); pen.lineTo((500,540)); pen.lineTo((490,420))
    pen.lineTo((440,540)); pen.closePath()

    # euro  €  — the real C with two bars across it. Drawing another C here by
    # hand would only be a worse C; the two bars are a touch lighter than a
    # crossbar so they do not choke the counter at text sizes.
    g = add_glyph(font, "Euro", 620, 0x20AC)
    cb = ink(font, "C")
    if cb:
        copy_outline(font, g, "C", dx=100 - cb[0])
        bar_w = cb[2] - cb[0]
        BAR = HSTEM - 10
        for y in (int(CAPHEIGHT * 0.38), int(CAPHEIGHT * 0.56)):
            rect(g, 40, y, 100 + bar_w - 120, y + BAR)

    # cent  ¢  — c with a stroke through it, rising and falling clear of the bowl
    g = add_glyph(font, "cent", 560, 0x00A2)
    cb = ink(font, "c")
    if cb:
        copy_outline(font, g, "c", dx=60 - cb[0])
        mid = 60 + (cb[2] - cb[0]) / 2
        rect(g, round(mid - CSTEM / 2), -80, round(mid + CSTEM / 2), XHEIGHT + 80)

    # pound  £  — an f-like hook at the top, a stem, a foot and a crossbar
    g = add_glyph(font, "sterling", 600, 0x00A3)
    pen = g.getPen()
    sx0, sx1 = 200, 200 + VSTEM
    HOOK_TOP = CAPHEIGHT + OVS
    pen.moveTo((sx0, 0))
    pen.lineTo((sx0, CAPHEIGHT - 150))
    pen.curveTo((sx0, HOOK_TOP - 50), (sx0 + 60, HOOK_TOP), (330, HOOK_TOP))
    pen.curveTo((410, HOOK_TOP), (466, HOOK_TOP - 60), (470, CAPHEIGHT - 200))
    pen.lineTo((470 - HSTEM, CAPHEIGHT - 200))
    pen.curveTo((466 - HSTEM, HOOK_TOP - 110), (400, HOOK_TOP - HSTEM), (330, HOOK_TOP - HSTEM))
    pen.curveTo((sx1 + 30, HOOK_TOP - HSTEM), (sx1, HOOK_TOP - 130), (sx1, CAPHEIGHT - 150))
    pen.lineTo((sx1, 0))
    pen.closePath()
    rect(g, 60, 0, 540, HSTEM)                       # foot
    rect(g, 90, 300, 420, 300 + HSTEM - 10)          # crossbar

    # yen  ¥
    g = add_glyph(font, "yen", 600, 0x00A5)
    pen = g.getPen()
    pen.moveTo((60,720)); pen.lineTo((160,720)); pen.lineTo((300,480))
    pen.lineTo((440,720)); pen.lineTo((540,720)); pen.lineTo((360,400))
    pen.lineTo((420,400)); pen.lineTo((420,330)); pen.lineTo((360,330))
    pen.lineTo((360,260)); pen.lineTo((420,260)); pen.lineTo((420,190))
    pen.lineTo((180,190)); pen.lineTo((180,260)); pen.lineTo((240,260))
    pen.lineTo((240,330)); pen.lineTo((180,330)); pen.lineTo((180,400))
    pen.lineTo((240,400)); pen.closePath()

    # rupee  ₹
    g = add_glyph(font, "rupee", 600, 0x20B9)
    rectwh(g, 100, 620, 400, 80)   # top bar
    rectwh(g, 100, 460, 400, 80)   # second bar
    rectwh(g, 100, 460, 80, 260)   # left stem top
    rectwh(g, 100, 0,   80, 460)   # left stem bottom
    pen = g.getPen()
    pen.moveTo((180,540)); pen.lineTo((460,540)); pen.lineTo((460,460))
    pen.lineTo((180,460)); pen.closePath()
    # diagonal
    pen.moveTo((200,460)); pen.lineTo((460,0)); pen.lineTo((380,0))
    pen.lineTo((140,420)); pen.closePath()

    # feminine/masculine ordinals  ª º  — a raised, scaled a or o over a rule
    for name, cp, letter in [("ordfeminine", 0x00AA, "a"), ("ordmasculine", 0x00BA, "o")]:
        lb = ink(font, letter)
        if not lb:
            continue
        scale = 0.62
        w = round((lb[2] - lb[0]) * scale)
        g = add_glyph(font, name, w + 120, cp)
        dy = CAPHEIGHT - 60 - lb[3] * scale
        copy_outline(font, g, letter, dx=60 - lb[0] * scale,
                     dy=dy, sx=scale, sy=scale)
        # The rule hangs below the letter, not across it: measure from the
        # letter's own scaled foot rather than guessing from the cap height.
        foot = round(lb[1] * scale + dy)
        rect(g, 40, foot - 74, w + 80, foot - 34)



# ── Special letters (ligatures, stroked, dotless, etc.) ──────────────────────

def draw_special_letters(font):
    """Ligatures, stroked letters and the dotless forms.

    These are all built from the letters already drawn above rather than from
    fresh ovals and rectangles: a stroked D has to be exactly the D, and a
    ligature has to carry the same stems and bowls as the letters it joins.
    Outlines are copied rather than referenced as components so that the added
    stroke can be merged with the base by the union pass.
    """
    # Æ  — the left diagonal of A joined to E
    E = ink(font, "E")
    if E:
        e_w = E[2] - E[0]
        apex = 330                      # where the diagonal meets the top bar
        g = add_glyph(font, "AE", round(apex + e_w + 100), 0x00C6)
        band(g, 72, 0, apex + 20, CAPHEIGHT)
        copy_outline(font, g, "E", dx=apex - E[0])
        # the A-part crossbar, tucked under E's middle arm
        rect(g, 150, int(CAPHEIGHT * 0.30), apex + 40, int(CAPHEIGHT * 0.30) + HSTEM)

    # æ  — a and e sharing a stem
    a, e = ink(font, "a"), ink(font, "e")
    if a and e:
        join = (a[2] - a[0]) - VSTEM - JOIN
        g = add_glyph(font, "ae", round(60 + join + (e[2] - e[0]) + 50), 0x00E6)
        copy_outline(font, g, "a", dx=60 - a[0])
        copy_outline(font, g, "e", dx=60 + join - e[0])

    # Œ œ  — O and o with E and e hung off the right side
    O, E = ink(font, "O"), ink(font, "E")
    if O and E:
        join = (O[2] - O[0]) - VSTEM - JOIN
        g = add_glyph(font, "OE", round(60 + join + (E[2] - E[0]) + 60), 0x0152)
        copy_outline(font, g, "O", dx=60 - O[0])
        copy_outline(font, g, "E", dx=60 + join - E[0])
    o, e = ink(font, "o"), ink(font, "e")
    if o and e:
        join = (o[2] - o[0]) - VSTEM - JOIN
        g = add_glyph(font, "oe", round(60 + join + (e[2] - e[0]) + 50), 0x0153)
        copy_outline(font, g, "o", dx=60 - o[0])
        copy_outline(font, g, "e", dx=60 + join - e[0])

    # Ð Đ  — D with a stroke through its stem. Both letters are the same shape.
    D = ink(font, "D")
    if D:
        for name, cp in [("Eth", 0x00D0), ("Dcroat", 0x0110)]:
            g = add_glyph(font, name, font["D"].width, cp)
            copy_outline(font, g, "D")
            y = CAPHEIGHT // 2
            rect(g, round(D[0] - 44), y - (HSTEM - 10) // 2,
                 round(D[0] + VSTEM + 70), y + (HSTEM - 10) // 2)

    # ð đ  — d with a stroke across the ascender
    d = ink(font, "d")
    if d:
        stem_x1 = d[2]
        for name, cp in [("eth", 0x00F0), ("dcroat", 0x0111)]:
            g = add_glyph(font, name, font["d"].width, cp)
            copy_outline(font, g, "d")
            y = ASCENDER - 130
            rect(g, round(stem_x1 - VSTEM - 66), y, round(stem_x1 + 44), y + HSTEM - 14)

    # Þ  — a stem with a bowl in the middle of the cap band
    g = add_glyph(font, "Thorn", 600, 0x00DE)
    rect(g, 60, 0, 148, CAPHEIGHT)
    half_bowl(g, 148, int(CAPHEIGHT * 0.16), int(CAPHEIGHT * 0.84), 418)

    # þ  — p with the stem carried up to the ascender
    p = ink(font, "p")
    if p:
        g = add_glyph(font, "thorn", font["p"].width, 0x00FE)
        copy_outline(font, g, "p")
        rect(g, round(p[0]), XHEIGHT - 100, round(p[0] + VSTEM), ASCENDER)

    # Ø ø  — O and o with a diagonal through them
    for name, cp, base, over in [("Oslash", 0x00D8, "O", 30), ("oslash", 0x00F8, "o", 26)]:
        b = ink(font, base)
        if not b:
            continue
        g = add_glyph(font, name, font[base].width, cp)
        copy_outline(font, g, base)
        pen = g.getPen()
        x0, y0, x1, y1 = b[0] - over, b[1] - over, b[2] + over, b[3] + over
        t = CSTEM * 0.8
        pen.moveTo((x0, y0 + t)); pen.lineTo((x0 + t, y0))
        pen.lineTo((x1, y1 - t)); pen.lineTo((x1 - t, y1))
        pen.closePath()

    # Ł ł  — L and l with a diagonal stroke across the stem
    for name, cp, base, y in [("Lslash", 0x0141, "L", int(CAPHEIGHT * 0.42)),
                              ("lslash", 0x0142, "l", int(XHEIGHT * 0.72))]:
        b = ink(font, base)
        if not b:
            continue
        g = add_glyph(font, name, font[base].width, cp)
        copy_outline(font, g, base)
        pen = g.getPen()
        x0 = b[0] - 46
        x1 = b[0] + VSTEM + 56
        rise = 90
        pen.moveTo((x0, y)); pen.lineTo((x1, y + rise))
        pen.lineTo((x1, y + rise - (HSTEM - 10))); pen.lineTo((x0, y - (HSTEM - 10)))
        pen.closePath()

    # Ħ ħ  — H and h with a bar. On Ħ it crosses both stems, on ħ only the
    # ascender, which is what distinguishes it from a lowercase h with a macron.
    H = ink(font, "H")
    if H:
        g = add_glyph(font, "Hbar", font["H"].width, 0x0126)
        copy_outline(font, g, "H")
        y = CAPHEIGHT - 150
        rect(g, round(H[0] - 40), y, round(H[2] + 40), y + HSTEM - 10)
    h = ink(font, "h")
    if h:
        g = add_glyph(font, "hbar", font["h"].width, 0x0127)
        copy_outline(font, g, "h")
        y = ASCENDER - 130
        rect(g, round(h[0] - 46), y, round(h[0] + VSTEM + 56), y + HSTEM - 14)

    # ß ẞ  — a hooked left stem with two bowls on the right
    for name, cp, top, bar in [("germandbls", 0x00DF, ASCENDER, XHEIGHT),
                               ("uni1E9E", 0x1E9E, CAPHEIGHT, CAPHEIGHT)]:
        g = add_glyph(font, name, 620, cp)
        x0, x1 = 60, 60 + VSTEM
        if name == "germandbls":
            # the long-s hook, the same shape as f's
            pen = g.getPen()
            HTOP = top + OVS
            pen.moveTo((x0, 0))
            pen.lineTo((x0, top - 110))
            pen.curveTo((x0, HTOP - 40), (x0 + 40, HTOP), (155, HTOP))
            pen.curveTo((205, HTOP), (240, HTOP - 40), (245, top - 130))
            pen.lineTo((245 - HSTEM + 14, top - 130))
            pen.curveTo((181, top - 90), (190, HTOP - HSTEM), (155, HTOP - HSTEM))
            pen.curveTo((151, HTOP - HSTEM), (x1, HTOP - 100), (x1, top - 110))
            pen.lineTo((x1, 0))
            pen.closePath()
        else:
            rect(g, x0, 0, x1, top)
        # Two bowls as on a B, the lower one wider, overlapping in the middle so
        # they merge into one outline.
        half_bowl(g, x1, bar // 2 - 20, bar + OVS, x1 + 230)
        half_bowl(g, x1, -OVS, bar // 2 + 20, x1 + 270)
        # the outstroke at the foot, which is what keeps ß from reading as a B
        rect(g, x1 + 210, 0, x1 + 330, HSTEM)

    # ı ȷ  — the dotless forms, taken from i and j minus the dot
    no_dot = lambda b: b[3] < XHEIGHT + 40
    for name, cp, base in [("dotlessi", 0x0131, "i"), ("uni0237", 0x0237, "j")]:
        if base not in font:
            continue
        g = add_glyph(font, name, font[base].width, cp)
        copy_outline(font, g, base, keep=no_dot)

    # İ  — I with a dot above
    if "I" in font and "dotaccentcomb" in font:
        place_accent(font, "Idotaccent", 0x0130, "I", "dotaccentcomb")



# ── Missing accented letters (component-based) ────────────────────────────────

ACCENTED2 = [
    # dot above
    ("Cdotaccent",  0x010A, "C", "dotaccentcomb"),
    ("cdotaccent",  0x010B, "c", "dotaccentcomb"),
    ("Edotaccent",  0x0116, "E", "dotaccentcomb"),
    ("edotaccent",  0x0117, "e", "dotaccentcomb"),
    ("Gdotaccent",  0x0120, "G", "dotaccentcomb"),
    ("gdotaccent",  0x0121, "g", "dotaccentcomb"),
    ("Zdotaccent",  0x017B, "Z", "dotaccentcomb"),
    ("zdotaccent",  0x017C, "z", "dotaccentcomb"),
    # caron
    ("Dcaron",      0x010E, "D", "caroncomb"),
    ("dcaron",      0x010F, "d", "caroncomb"),
    ("Gcaron",      0x01E6, "G", "caroncomb"),  # not in missing but safe
    # breve
    ("Gbreve",      0x011E, "G", "brevecomb"),
    ("gbreve",      0x011F, "g", "brevecomb"),
    # cedilla
    ("Gcedilla",    0x0122, "G", "cedillacomb"),
    ("gcedilla",    0x0123, "g", "cedillacomb"),
    ("Kcedilla",    0x0136, "K", "cedillacomb"),
    ("kcedilla",    0x0137, "k", "cedillacomb"),
    ("Lcedilla",    0x013B, "L", "cedillacomb"),
    ("lcedilla",    0x013C, "l", "cedillacomb"),
    ("Ncedilla",    0x0145, "N", "cedillacomb"),
    ("ncedilla",    0x0146, "n", "cedillacomb"),
    ("Scedilla",    0x015E, "S", "cedillacomb"),
    ("scedilla",    0x015F, "s", "cedillacomb"),
    # T-cedilla was missing while its S partner was present, so locl's Romanian
    # rule "sub tcedilla by tcommaaccent" referenced a glyph the font did not
    # have and the whole feature file refused to compile.
    ("Tcedilla",    0x0162, "T", "cedillacomb"),
    ("tcedilla",    0x0163, "t", "cedillacomb"),
    # acute
    ("Lacute",      0x0139, "L", "acutecomb"),
    ("lacute",      0x013A, "l", "acutecomb"),
    # caron
    ("Lcaron",      0x013D, "L", "caroncomb"),
    ("lcaron",      0x013E, "l", "caroncomb"),
    # macron
    ("Imacron",     0x012A, "I", "macroncomb"),
    ("imacron",     0x012B, "i", "macroncomb"),
    # ogonek
    ("Iogonek",     0x012E, "I", "ogonekcomb"),
    ("iogonek",     0x012F, "i", "ogonekcomb"),
    # circumflex
    ("Wcircumflex", 0x0174, "W", "circumflexcomb"),
    ("wcircumflex", 0x0175, "w", "circumflexcomb"),
    ("Ycircumflex", 0x0176, "Y", "circumflexcomb"),
    ("ycircumflex", 0x0177, "y", "circumflexcomb"),
    # diaeresis
    ("Ydieresis",   0x0178, "Y", "dieresiscomb"),
    # grave
    ("Wgrave",      0x1E80, "W", "gravecomb"),
    ("wgrave",      0x1E81, "w", "gravecomb"),
    ("Ygrave",      0x1EF2, "Y", "gravecomb"),
    ("ygrave",      0x1EF3, "y", "gravecomb"),
    # acute
    ("Wacute",      0x1E82, "W", "acutecomb"),
    ("wacute",      0x1E83, "w", "acutecomb"),
    # diaeresis
    ("Wdieresis",   0x1E84, "W", "dieresiscomb"),
    ("wdieresis",   0x1E85, "w", "dieresiscomb"),
]


def draw_accented2(font):
    for name, cp, base, mark in ACCENTED2:
        if name in font:
            continue
        place_accent(font, name, cp, base, mark)



# Starter kerning. This is not a finished kerning set — it covers the pairs that
# are visibly wrong at text sizes with no kerning at all: open shapes against
# flat stems, and the round/diagonal terminals that leave a hole above the
# baseline. Left groups are the closing side of a pair, right groups the opening
# side, following the UFO3 public.kern1/public.kern2 convention.
KERN_GROUPS: dict[str, list[str]] = {
    "public.kern1.T":      ["T"],
    "public.kern1.VWY":    ["V", "W", "Y"],
    "public.kern1.FP":     ["F", "P"],
    "public.kern1.r":      ["r"],
    "public.kern1.y":      ["v", "w", "y"],
    "public.kern1.quote":  ["quoteright", "quotedblright", "quoteleft", "quotedblleft"],
    "public.kern1.A":      ["A"],
    "public.kern1.L":      ["L"],
    # A glyph may sit in only one kern2 group, so there is no separate "round"
    # group: o, e and c are already here, and the pairs that want them use this.
    "public.kern2.a":      ["a", "c", "d", "e", "g", "o", "q", "s"],
    "public.kern2.period": ["period", "comma", "quotesinglbase", "quotedblbase"],
    "public.kern2.A":      ["A"],
    "public.kern2.VWY":    ["V", "W", "Y"],
    "public.kern2.T":      ["T"],
}

KERN_PAIRS: dict[tuple[str, str], int] = {
    # Capitals with an overhanging arm or diagonal over a following round.
    ("public.kern1.T",     "public.kern2.a"):      -70,
    ("public.kern1.T",     "public.kern2.A"):      -60,
    ("public.kern1.T",     "public.kern2.period"): -80,
    ("public.kern1.VWY",   "public.kern2.a"):      -50,
    ("public.kern1.VWY",   "public.kern2.A"):      -55,
    ("public.kern1.VWY",   "public.kern2.period"): -70,
    ("public.kern1.FP",    "public.kern2.a"):      -30,
    ("public.kern1.FP",    "public.kern2.A"):      -50,
    ("public.kern1.FP",    "public.kern2.period"): -70,
    ("public.kern1.A",     "public.kern2.VWY"):    -55,
    ("public.kern1.A",     "public.kern2.T"):      -60,
    # L's foot leaves a hole under a following diagonal or T arm. These two were
    # only in the hand-written kern.fea, which ufo2ft was discarding wholesale
    # because it had no insertion marker; they belong in kerning.plist with the
    # rest so there is one source of truth.
    ("public.kern1.L",     "public.kern2.VWY"):    -60,
    ("public.kern1.L",     "public.kern2.T"):      -60,
    ("f",                  "i"):                   -20,
    # Lowercase r and the diagonals leave a gap before a full stop or comma.
    ("public.kern1.r",     "public.kern2.period"): -60,
    ("public.kern1.y",     "public.kern2.period"): -55,
    ("public.kern1.r",     "public.kern2.a"):      -20,
    # Quotes sit high; pull them into the following letter.
    ("public.kern1.quote", "public.kern2.a"):      -30,
    ("public.kern1.quote", "public.kern2.A"):      -50,
}


def set_kerning(font: ufoLib2.Font) -> int:
    """Install the starter kerning groups and pairs, dropping absent glyphs."""
    groups = dict(font.groups)
    for name, members in KERN_GROUPS.items():
        present = [m for m in members if m in font]
        if present:
            groups[name] = present
    font.groups = groups

    kerning = dict(font.kerning)
    for (first, second), value in KERN_PAIRS.items():
        # A pair whose group ended up empty would compile to a dangling
        # reference, so only keep pairs both of whose sides survived.
        if first.startswith("public.kern") and first not in groups:
            continue
        if second.startswith("public.kern") and second not in groups:
            continue
        kerning[(first, second)] = value
    font.kerning = kerning
    return len(kerning)


def main():
    import os, sys, subprocess
    ufo_path = "sources/sabas-ui/SabasUI-Regular.ufo"
    font = ufoLib2.Font.open(ufo_path)

    for draw in LOWERCASE_DRAWERS:
        draw(font)
    for draw in UPPERCASE_DRAWERS:
        draw(font)
    for draw in DIGIT_DRAWERS:
        draw(font)
    # The letters have to be finished — wound the right way, free of overlaps
    # and in their final positions — before anything is derived from them: the
    # symbols and ligatures copy their outlines, and the accented letters are
    # composed from their ink bounds.
    turned = fix_directions(font)
    merged = union_all(font)
    respace(font)

    draw_punctuation(font)
    draw_marks(font)
    draw_extra_symbols(font)
    draw_special_letters(font)

    turned += fix_directions(font)
    merged += union_all(font)

    draw_accented(font)
    draw_accented2(font)
    pairs = set_kerning(font)
    print(f"Reversed contours in {turned} glyphs, unioned {merged}, {pairs} kern pairs")

    order = list(font.lib.get("public.glyphOrder", []))
    for g in font:
        if g.name not in order:
            order.append(g.name)
    font.lib["public.glyphOrder"] = order

    font.save(ufo_path, overwrite=True)
    print(f"Saved {len(font)} glyphs to {ufo_path}")

    # fontmake lives in the venv this script is run from, not necessarily on PATH;
    # calling it by bare name failed with FileNotFoundError after a clean save.
    fontmake = os.path.join(os.path.dirname(sys.executable), "fontmake")
    if not os.path.exists(fontmake):
        fontmake = "fontmake"
    r = subprocess.run(
        [fontmake, "-u", ufo_path, "-o", "otf", "--output-dir", "fonts/"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        print(r.stderr); sys.exit(1)
    print("Compiled OK →", "fonts/SabasUI-Regular.otf")


if __name__ == "__main__":
    main()
