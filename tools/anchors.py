"""
Mark-attachment anchors for Sabas UI.

Bases get `top` and `bottom`, sitting ACCENT_GAP clear of the ink. Marks get the
matching `_top` / `_bottom` at their own ink edge, so an attached mark ends up
exactly where place_accent puts the same mark on a precomposed letter. Marks also
carry `top` / `bottom` past their far edge, which is what stacks a second mark on
the first (mkmk).

The compiler turns these into `mark` and `mkmk`; there is no hand-written FEA for
either. Anchors are recomputed from each master's own outlines rather than
transformed, so a heavier or slanted master gets anchors that match its ink.
"""
import unicodedata

from fontTools.pens.boundsPen import BoundsPen

ACCENT_GAP = 30
SKIP_MARKS = {"horncomb"}
# Named, not measured: a mark that grows with weight can change which side of the
# baseline its ink is centred on, and every master has to agree.
BELOW_MARKS = {"dotbelowcomb", "commaaccentcomb", "cedillacomb", "ogonekcomb"}


def _bounds(font, g):
    p = BoundsPen(font)
    g.draw(p)
    return p.bounds


def _is_letter(font, g):
    cps = list(g.unicodes)
    if not cps:
        base = g.name.split(".")[0]
        if base in font:
            cps = list(font[base].unicodes)
    return bool(cps) and unicodedata.category(chr(cps[0])).startswith("L")


def add_anchors(font, gap=ACCENT_GAP):
    """Rebuild the anchors on every base letter and combining mark. Returns the count."""
    count = 0
    for g in font:
        g.anchors.clear()
    for g in font:
        is_mark = g.name.endswith("comb") and g.width == 0
        if is_mark and g.name in SKIP_MARKS:
            continue
        if not is_mark and not (g.width and _is_letter(font, g)):
            continue
        b = _bounds(font, g)
        if b is None:
            continue
        cx = round((b[0] + b[2]) / 2)
        if is_mark:
            if g.name in BELOW_MARKS:
                g.appendAnchor({"name": "_bottom", "x": cx, "y": round(b[3])})
                g.appendAnchor({"name": "bottom", "x": cx, "y": round(b[1] - gap)})
            else:
                g.appendAnchor({"name": "_top", "x": cx, "y": round(b[1])})
                g.appendAnchor({"name": "top", "x": cx, "y": round(b[3] + gap)})
            count += 2
        else:
            g.appendAnchor({"name": "top", "x": cx, "y": round(b[3] + gap)})
            g.appendAnchor({"name": "bottom", "x": cx, "y": round(b[1] - gap)})
            count += 2
    return count
