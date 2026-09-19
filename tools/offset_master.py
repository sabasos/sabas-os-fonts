"""
Derive a Sabas UI master from the Regular UFO by moving outline points, so every
master keeps Regular's contour and point structure and interpolates with it.

A stem is thickened by offsetting each edge along its outward normal by an
anisotropic amount: vertical stems take dx = (V - V0) / 2 per side, horizontal
stems dy = (H - H0) / 2. Corners are mitred, smooth nodes move along their normal,
and each Bezier handle moves with its anchor and is rescaled to the anchor's new
spacing so round shapes stay round.

Thickening horizontals also pushes every horizontal edge that sits on the
baseline, x-height or cap height outward, which would break the alignment zones.
A piecewise-linear vertical map, built per glyph class, pulls the zones back to
their original heights and leaves the extra weight inside the stems. Dots and
accents that float above the letter keep their bottom edge and grow upward.
"""
import copy
import math
import unicodedata

import ufoLib2

V0, H0 = 88.0, 76.0
XH, CAP, ASC = 540.0, 720.0, 750.0
SIDE_K = 1.1             # share of the extra stem width added to each side bearing
MITER_LIMIT = 3.0
SMOOTH_COS = math.cos(math.radians(6.0))


def _area(pts):
    a = 0.0
    for i, (x0, y0) in enumerate(pts):
        x1, y1 = pts[(i + 1) % len(pts)]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def _unit(vx, vy):
    n = math.hypot(vx, vy)
    return (vx / n, vy / n) if n > 1e-9 else None


def fill_is_left(font):
    """True when contours wind so that the filled side is on the left of travel."""
    pts = [(p.x, p.y) for p in font["H"].contours[0].points]
    return _area(pts) > 0


def _glyph_kind(font, g):
    """'lower' for lowercase letters, 'mark' for zero-width glyphs, else 'cap'."""
    if g.width == 0:
        return "mark"
    cps = list(g.unicodes)
    if not cps:
        base = g.name.split(".")[0]
        if base in font and font[base].unicodes:
            cps = list(font[base].unicodes)
    if cps and unicodedata.category(chr(cps[0])) == "Ll":
        return "lower"
    return "cap"


def _zone_map(P, d):
    """Vertical map that returns the offset zones (-d and P+d) to 0 and P."""
    def m(y):
        if y <= -d:
            return y + d
        if y >= P + d:
            return P + (y - P - d)
        return (y + d) * P / (P + 2 * d)
    return m


def _effective_dy(P, H_target):
    """dy such that a horizontal stem ends at H_target after the zone map."""
    return P * (H_target - H0) / (2.0 * (P - H_target))


def _offset_contour(points, dx, dy, left_fill):
    n = len(points)
    on = [i for i, p in enumerate(points) if p.type is not None]
    if not on:
        return [(p.x, p.y) for p in points]
    P = [(p.x, p.y) for p in points]

    def normal(t):
        return (t[1], -t[0]) if left_fill else (-t[1], t[0])

    def dist(nx, ny):
        return dx * nx * nx + dy * ny * ny

    shift = {}
    for k, i in enumerate(on):
        pi, ni = on[k - 1], on[(k + 1) % len(on)]

        def between(a, b):
            out, j = [], (a + 1) % n
            while j != b:
                out.append(j)
                j = (j + 1) % n
            return out

        before, after = between(pi, i), between(i, ni)
        t_in = None
        for j in reversed(before):
            t_in = _unit(P[i][0] - P[j][0], P[i][1] - P[j][1])
            if t_in:
                break
        if t_in is None:
            t_in = _unit(P[i][0] - P[pi][0], P[i][1] - P[pi][1])
        t_out = None
        for j in after:
            t_out = _unit(P[j][0] - P[i][0], P[j][1] - P[i][1])
            if t_out:
                break
        if t_out is None:
            t_out = _unit(P[ni][0] - P[i][0], P[ni][1] - P[i][1])
        if t_in is None or t_out is None:
            shift[i] = (0.0, 0.0)
            continue
        n1, n2 = normal(t_in), normal(t_out)
        if t_in[0] * t_out[0] + t_in[1] * t_out[1] >= SMOOTH_COS:
            nn = _unit(n1[0] + n2[0], n1[1] + n2[1]) or n1
            d = dist(*nn)
            shift[i] = (nn[0] * d, nn[1] * d)
            continue
        d1, d2 = dist(*n1), dist(*n2)
        det = n1[0] * n2[1] - n1[1] * n2[0]
        if abs(det) < 0.2:
            nn = _unit(n1[0] + n2[0], n1[1] + n2[1]) or n1
            d = dist(*nn)
            sx, sy = nn[0] * d, nn[1] * d
        else:
            sx = (d1 * n2[1] - d2 * n1[1]) / det
            sy = (n1[0] * d2 - n2[0] * d1) / det
        lim = MITER_LIMIT * max(abs(dx), abs(dy), 1e-9)
        m = math.hypot(sx, sy)
        if m > lim:
            sx, sy = sx * lim / m, sy * lim / m
        shift[i] = (sx, sy)

    new = list(P)
    for i in on:
        new[i] = (P[i][0] + shift[i][0], P[i][1] + shift[i][1])

    for k, i in enumerate(on):
        ni = on[(k + 1) % len(on)]
        offs, j = [], (i + 1) % n
        while j != ni:
            offs.append(j)
            j = (j + 1) % n
        if not offs:
            continue
        A, B = P[i], P[ni]
        nA, nB = new[i], new[ni]
        rx = abs(nB[0] - nA[0]) / abs(B[0] - A[0]) if abs(B[0] - A[0]) > 20 else 1.0
        ry = abs(nB[1] - nA[1]) / abs(B[1] - A[1]) if abs(B[1] - A[1]) > 20 else 1.0
        rx, ry = min(max(rx, 0.3), 3.0), min(max(ry, 0.3), 3.0)
        half = (len(offs) + 1) // 2
        for idx, j in enumerate(offs):
            if idx < half:
                anchor, na, ax, ay = P[i], nA, rx, ry
            else:
                anchor, na, ax, ay = P[ni], nB, rx, ry
            new[j] = (na[0] + (P[j][0] - anchor[0]) * ax,
                      na[1] + (P[j][1] - anchor[1]) * ay)
    return new


GAP_KEEP = 0.75          # share of an original vertical gap a heavier weight keeps


def _bbox(contour):
    xs = [p.x for p in contour.points]
    ys = [p.y for p in contour.points]
    return min(xs), min(ys), max(xs), max(ys)


def _move(contour, dy):
    for p in contour.points:
        p.y = round(p.y + dy)


def _separate_stacked(g, orig, P, kind):
    """Keep stacked shapes (the bars of =, the dots of : and !) from merging.

    Offsetting shrinks every gap by the extra stroke weight. Where two contours sat
    one above the other in Regular, move them apart until they keep GAP_KEEP of the
    original gap, unless a contour is pinned to the baseline or the top zone.
    """
    if len(g.contours) < 2 or kind == "mark":
        return
    order = sorted(range(len(orig)), key=lambda i: orig[i][1])
    for lo, hi in zip(order, order[1:]):
        a, b = orig[lo], orig[hi]
        if a[3] >= b[1] or a[2] <= b[0] or b[2] <= a[0]:
            continue
        g0 = b[1] - a[3]
        na, nb = _bbox(g.contours[lo]), _bbox(g.contours[hi])
        need = GAP_KEEP * g0 - (nb[1] - na[3])
        if need <= 0:
            continue
        low_pinned = a[1] <= 15
        high_pinned = b[3] >= P - 15
        if low_pinned and high_pinned:
            continue
        if low_pinned:
            _move(g.contours[hi], need)
        elif high_pinned:
            _move(g.contours[lo], -need)
        else:
            _move(g.contours[lo], -need / 2)
            _move(g.contours[hi], need / 2)


def _build_master(src_path, dst_path, style, V, H, weight_class=None,
                 x_scale=1.0, neutral_advance=False, xh_target=None,
                 shear=0.0, location=None, tracking=0, fit_cell=None):
    """Write a derived master to dst_path.

    V, H            target vertical / horizontal stem thickness
    x_scale         horizontal scale applied before the offset (wdth masters)
    neutral_advance keep every advance unchanged (GRAD masters)
    xh_target       lowercase x-height, cap height and ascender stay fixed (opsz)
    tracking        units added to every advance, split between the two side bearings
    fit_cell        squeeze any glyph whose ink is wider than this, about its centre
    """
    import shutil
    from pathlib import Path
    dst_path = Path(dst_path)
    if dst_path.exists():
        shutil.rmtree(dst_path)
    src = ufoLib2.Font.open(src_path)
    dst = ufoLib2.Font()
    for attr in vars(src.info.__class__):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(src.info, attr)
            if val is not None and not callable(val):
                setattr(dst.info, attr, val)
        except Exception:
            pass
    dst.info.styleName = style
    if weight_class:
        dst.info.openTypeOS2WeightClass = weight_class
    dst.groups.update(src.groups)
    for pair, val in src.kerning.items():
        dst.kerning[pair] = round(val * x_scale)
    dst.features.text = src.features.text
    dst.lib.update(src.lib)
    if location:
        dst.lib["co.sabas.master.location"] = location

    left = fill_is_left(src)
    dx = (V - V0 * x_scale) / 2.0
    side = (0.0 if neutral_advance else SIDE_K * dx) + tracking / 2.0
    dy_thick = (H - H0) / 2.0

    def q_map(y):
        if xh_target is None:
            return y
        if y <= 0:
            return y
        if y <= XH:
            return y * xh_target / XH
        if y <= ASC:
            return xh_target + (y - XH) * (ASC - xh_target) / (ASC - XH)
        return y

    for sg in src:
        g = copy.deepcopy(sg)
        kind = _glyph_kind(src, sg)
        P = XH if kind == "lower" else CAP
        d_eff = _effective_dy(P, H) if abs(H - H0) > 1e-6 else 0.0
        zmap = _zone_map(P, d_eff) if d_eff else (lambda y: y)
        _ = dy_thick

        orig_boxes = []
        for c in g.contours:
            xs = [p.x * x_scale for p in c.points]
            ys = [p.y for p in c.points]
            orig_boxes.append((min(xs), min(ys), max(xs), max(ys)))
        for c in g.contours:
            src_pts = [(p.x * x_scale, p.y) for p in c.points]
            for p, (x, y) in zip(c.points, src_pts):
                p.x, p.y = x, y
            ymin_orig = min(y for _, y in src_pts)
            floating = (kind == "mark") or (kind == "lower" and ymin_orig >= P + 20)
            new = _offset_contour(c.points, dx, d_eff, left)
            if floating:
                shift_y = ymin_orig - min(y for _, y in new)
                new = [(x, y + shift_y) for x, y in new]
            else:
                new = [(x, zmap(y)) for x, y in new]
            if kind == "lower" and not floating:
                new = [(x, q_map(y)) for x, y in new]
            for p, (x, y) in zip(c.points, new):
                p.x = round(x + (side if g.width else 0))
                p.y = round(y)

        _separate_stacked(g, orig_boxes, P, kind)

        for a in g.anchors:
            a.x = round(a.x * x_scale + (side if g.width else 0))
            a.y = round(zmap(a.y))

        for comp in g.components:
            base = src[comp.baseGlyph]
            t = comp.transformation
            ox = t[4] * x_scale
            if base.width:
                ox += side * (1 - t[0])
            else:
                ox += side
            comp.transformation = type(t)(t[0], t[1], t[2], t[3], round(ox), t[5])

        g.width = round(sg.width * x_scale + (2 * side if sg.width else 0))
        if fit_cell and g.width and g.contours:
            from fontTools.pens.boundsPen import BoundsPen
            bp = BoundsPen(None)
            for c in g.contours:
                c.draw(bp)
            if bp.bounds:
                cx = (bp.bounds[0] + bp.bounds[2]) / 2
                k = min(1.0, fit_cell / (bp.bounds[2] - bp.bounds[0]))
                # Squeeze to fit, then sit the ink in the middle of the advance.
                for c in g.contours:
                    for p in c.points:
                        p.x = round(g.width / 2 + (p.x - cx) * k)
        if shear:
            for c in g.contours:
                for p in c.points:
                    p.x = round(p.x + shear * p.y)
            for a in g.anchors:
                a.x = round(a.x + shear * a.y)
            for comp in g.components:
                t = comp.transformation
                comp.transformation = type(t)(t[0], t[1], t[2], t[3],
                                              round(t[4] + shear * t[5]), t[5])
        dst.addGlyph(g)

    from anchors import add_anchors
    add_anchors(dst)
    dst.save(dst_path)
    return dst


def build_master(*args, zones=None, base_stems=None, **kwargs):
    """_build_master with the source family's metrics: zones=(x-height, cap, ascender)
    and base_stems=(vertical, horizontal) of the font being derived from."""
    global V0, H0, XH, CAP, ASC
    saved = (V0, H0, XH, CAP, ASC)
    try:
        if zones:
            XH, CAP, ASC = zones
        if base_stems:
            V0, H0 = base_stems
        return _build_master(*args, **kwargs)
    finally:
        V0, H0, XH, CAP, ASC = saved
