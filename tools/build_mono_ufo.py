"""
Sabas Mono Regular, derived from the current Sabas UI Regular.

Brief 4.3: 1000 UPM, advance 600 fixed, x-height 525, cap 700, vertical stem 84,
horizontal stem 72. Each glyph is centred in the 600 cell. A glyph whose ink is wider
than the cell allows (m, w, M, W, ...) is compressed and its stems offset back to 84,
rather than stretching narrow glyphs to fill the cell. Accented letters are rebuilt
from the mono bases and marks with the mark anchors.

Mono's letterforms differ from UI's where a fixed grid needs it: serifed i, j, l, r, I
and 1 so they fill their cells and stay distinct, and a dotted zero.
"""
import copy
import sys
from pathlib import Path

import ufoLib2
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "strike"))
import anchors
import kerning
import offset_master as om

SRC = Path("sources/sabas-ui/SabasUI-Regular.ufo")
DST = Path("sources/sabas-mono/SabasM-Regular.ufo")

CELL, MIN_SB = 600, 30
V, H = 84, 72
XH_M, CAP_M, ASC_M, DESC_M = 525, 700, 750, -205
SRC_XH, SRC_CAP, SRC_ASC = 540, 720, 750
FEATURES = "include(../features/mono/features.fea);\n"


def _is_mark(font, name):
    """A combining mark that is attached by anchor. The horn and the caron tick belong
    to their letter's outline instead: they are folded in, so the letter is compressed
    with them and stays inside its cell."""
    g = font[name]
    return name.endswith("comb") and name != "horncomb" and g.width == 0


# Alternates that only the UI features reach. Mono has its own feature set, so these
# would be glyphs no feature can select.
UI_ONLY_SUFFIXES = (".ss01", ".ss02", ".ss03", ".cv01", ".cv02", ".numr", ".dnom",
                    ".sups", ".subs", ".onum", ".tnum", ".case")


def _draw_decomposed(font, name, pen):
    """Draw a glyph with every component except combining marks folded in."""
    g = font[name]
    for c in g.contours:
        c.draw(pen)
    for comp in g.components:
        if _is_mark(font, comp.baseGlyph):
            continue
        _draw_decomposed(font, comp.baseGlyph, TransformPen(pen, comp.transformation))


def _bounds(font, glyph):
    p = BoundsPen(font)
    glyph.draw(p)
    return p.bounds


def _lower_map(y):
    if y <= 0:
        return y
    if y <= SRC_XH:
        return y * XH_M / SRC_XH
    if y <= SRC_ASC:
        return XH_M + (y - SRC_XH) * (ASC_M - XH_M) / (SRC_ASC - SRC_XH)
    return y


def _cap_map(y):
    return y * CAP_M / SRC_CAP if y > 0 else y


def _derive(src):
    """Contour-only mono glyphs from the UI glyphs, plus the mark placements to redo."""
    dst = ufoLib2.Font()
    left = om.fill_is_left(src)
    mark_plan = {}
    for sg in src:
        if sg.name.endswith(UI_ONLY_SUFFIXES) or sg.name == "caronalt":
            continue
        ng = dst.newGlyph(sg.name)
        ng.unicodes = list(sg.unicodes)
        if sg.width == 0:
            ng.width = 0
            for c in sg.contours:
                ng.appendContour(copy.deepcopy(c))
            continue
        marks = [c for c in sg.components if _is_mark(src, c.baseGlyph)]
        if marks:
            mark_plan[sg.name] = [(m.baseGlyph, m.transformation) for m in marks]
        _draw_decomposed(src, sg.name, ng.getPen())
        ng.width = CELL
        b = _bounds(dst, ng)
        if b is None:
            continue
        kind = om._glyph_kind(src, sg)
        P = SRC_XH if kind == "lower" else SRC_CAP
        xs = min(1.0, (CELL - 2 * MIN_SB) / (b[2] - b[0]))
        dx = (V - om.V0 * xs) / 2.0
        d_eff = om._effective_dy(P, H)
        zmap = om._zone_map(P, d_eff)
        orig = []
        for c in ng.contours:
            xs_pts = [p.x * xs for p in c.points]
            ys_pts = [p.y for p in c.points]
            orig.append((min(xs_pts), min(ys_pts), max(xs_pts), max(ys_pts)))
        for c in ng.contours:
            for p in c.points:
                p.x *= xs
            ymin = min(p.y for p in c.points)
            floating = kind == "lower" and ymin >= P + 20
            new = om._offset_safe(c.points, dx, d_eff, left)
            if floating:
                shift = ymin - min(y for _, y in new)
                new = [(x, y + shift) for x, y in new]
            else:
                new = [(x, zmap(y)) for x, y in new]
            ymap = _lower_map if kind == "lower" and not floating else _cap_map if kind != "lower" else (lambda y: y)
            for p, (x, y) in zip(c.points, new):
                p.x, p.y = x, ymap(y)
        om._separate_stacked(ng, orig, P, kind)
        b2 = _bounds(dst, ng)
        shift = CELL / 2 - (b2[0] + b2[2]) / 2
        for c in ng.contours:
            for p in c.points:
                p.x = round(p.x + shift)
                p.y = round(p.y)
    return dst, mark_plan


def _stem_contour(g, touching):
    """Bounds of the contour that holds the stem: the one touching y <= touching."""
    best = None
    for c in g.contours:
        ys = [p.y for p in c.points]
        if min(ys) <= touching:
            xs = [p.x for p in c.points]
            if best is None or min(ys) < best[0]:
                best = (min(ys), min(xs), max(xs))
    return best


def _mono_shapes(font, roots, T1, plain_excluded=()):
    """Serifs and the dotted zero, applied to every glyph built on those letters."""
    for g in list(font):
        if not g.width or g.name.endswith("comb"):
            continue
        # Only the letter itself and its accented forms: fractions and small figures
        # are built from a `one` too, but must not grow its foot.
        if g.name in plain_excluded:
            continue
        root = roots.get(g.name, g.name.split(".")[0])
        rect = lambda x0, y0, x1, y1: T1.rect(g, round(x0), round(y0), round(x1), round(y1))
        if root in ("i", "dotlessi"):
            s = _stem_contour(g, 5)
            if s:
                x0, x1 = s[1], s[2]
                rect(x0 - 72, XH_M - H, x0 + 10, XH_M)
                rect(x0 - 84, 0, x1 + 84, H)
        elif root in ("j", "uni0237"):
            s = _stem_contour(g, -5)
            if s:
                x1 = s[2]
                rect(x1 - V - 72, XH_M - H, x1 - V + 10, XH_M)
        elif root == "l":
            s = _stem_contour(g, 5)
            if s:
                rect(s[1] - 72, ASC_M - H, s[1] + 10, ASC_M)
        elif root == "r":
            s = _stem_contour(g, 5)
            if s:
                rect(s[1] - 70, 0, s[1] + V + 70, H)
        elif root == "I":
            g.clearContours()
            rect(150, 0, 450, H)
            rect(150, CAP_M - H, 450, CAP_M)
            rect(CELL / 2 - V / 2, 0, CELL / 2 + V / 2, CAP_M)
        elif root == "one":
            b = _bounds(font, g)
            if b:
                cx = b[2] - V / 2
                rect(cx - 130, 0, cx + 130, H)
        elif root == "zero":
            T1.dot(g, CELL // 2, CAP_M // 2, 46)


def _place_marks(font, src, mark_plan):
    """Attach each mark to its base with the anchors, stacking marks on marks."""
    BELOW = anchors.BELOW_MARKS
    anchors.add_anchors(font)
    for name, marks in mark_plan.items():
        g = font[name]
        run = {a.name: (a.x, a.y) for a in g.anchors}
        for m, t in marks:
            ma = {a.name: (a.x, a.y) for a in font[m].anchors}
            side = "bottom" if m in BELOW else "top"
            if side in run and "_" + side in ma:
                dx = round(run[side][0] - ma["_" + side][0])
                dy = round(run[side][1] - ma["_" + side][1])
                if side in ma:
                    run[side] = (ma[side][0] + dx, ma[side][1] + dy)
            else:
                # A spacing accent has no base letter to anchor to: keep its offset
                # from the UI glyph, re-centred in the cell.
                dx = round(t[4] + (CELL - src[name].width) / 2)
                dy = round(t[5] * CAP_M / SRC_CAP)
            g.components.append(ufoLib2.objects.Component(
                baseGlyph=m, transformation=(1, 0, 0, 1, dx, dy)))


# Texture healing (brief section 8): on a fixed grid narrow letters leave holes and wide
# ones crowd. calt swaps a glyph for a wider or narrower drawing of itself, chosen by its
# neighbours, and never changes an advance.
NARROW_VARIANTS = ["i", "j", "l", "t", "f", "r", "I", "one"]
NARROW_CONTEXT = NARROW_VARIANTS + [
    "period", "comma", "semicolon", "colon", "quotesingle", "quotedbl", "grave", "exclam",
    "bar", "parenleft", "parenright", "bracketleft", "bracketright", "braceleft",
    "braceright", "slash", "backslash"]
WIDE_VARIANTS = ["m", "w", "M", "W", "at", "percent", "ampersand"]
WIDTH_FACTORS = {"wide1": 1.12, "wide2": 1.24, "narrow1": 0.92}


def _restyled(font, name, factor, left_fill):
    """A copy of a glyph stretched about the cell's centre, its stems offset back to V."""
    g = font.newGlyph(f"{name}.{'narrow1' if factor < 1 else 'wide1' if factor < 1.2 else 'wide2'}")
    g.width = CELL
    src = font[name]
    for c in src.contours:
        xs, ys = [p.x for p in c.points], [p.y for p in c.points]
        if max(xs) - min(xs) < 6 or max(ys) - min(ys) < 6:
            continue                     # a stroke-end sliver, not part of the letter
        pts = copy.deepcopy(c)
        for p in pts.points:
            p.x = CELL / 2 + (p.x - CELL / 2) * factor
        new = om._offset_contour(pts.points, (V - V * factor) / 2.0, 0.0, left_fill)
        for p, (x, y) in zip(pts.points, new):
            p.x, p.y = round(x), round(y)
        g.appendContour(pts)
    return g


def add_healing_variants(font, left_fill):
    made = {}
    for name in NARROW_VARIANTS:
        if name in font:
            made[name] = [_restyled(font, name, WIDTH_FACTORS["wide1"], left_fill).name,
                          _restyled(font, name, WIDTH_FACTORS["wide2"], left_fill).name]
    for name in WIDE_VARIANTS:
        if name in font:
            made[name] = [_restyled(font, name, WIDTH_FACTORS["narrow1"], left_fill).name]
    return made


def write_healing_fea(font, made, path="sources/features/mono/healing.fea"):
    """calt rules: one single-glyph input each, so clusters stay one to one."""
    nv = [n for n in NARROW_VARIANTS if n in made]
    ctx = [n for n in NARROW_CONTEXT if n in font]
    wv = [n for n in WIDE_VARIANTS if n in made]
    wide_ctx = [n for n in WIDE_VARIANTS if n in font]
    lines = ["# healing.fea - generated by tools/build_mono_ufo.py, do not edit.",
             "# Backtrack and lookahead classes include the variants, so a decision made on the",
             "# original neighbours is the same after they have been substituted.",
             "@NARROW_V = [" + " ".join(nv) + "];",
             "@NARROW_V_W1 = [" + " ".join(f"{n}.wide1" for n in nv) + "];",
             "@NARROW_V_W2 = [" + " ".join(f"{n}.wide2" for n in nv) + "];",
             "@NARROW_ALL = [" + " ".join(ctx) + " @NARROW_V_W1 @NARROW_V_W2];",
             "@WIDE_V = [" + " ".join(wv) + "];",
             "@WIDE_V_N1 = [" + " ".join(f"{n}.narrow1" for n in wv) + "];",
             "@WIDE_ALL = [" + " ".join(wide_ctx) + " @WIDE_V_N1];",
             "",
             "lookup healing {",
             "    sub @NARROW_ALL @NARROW_V' @NARROW_ALL by @NARROW_V_W2;",
             "    sub @NARROW_ALL @NARROW_V' by @NARROW_V_W1;",
             "    sub @NARROW_V' @NARROW_ALL by @NARROW_V_W1;",
             "    sub @WIDE_ALL @WIDE_V' @WIDE_ALL by @WIDE_V_N1;",
             "} healing;",
             "",
             "feature calt { lookup healing; } calt;",
             ""]
    with open(path, "w") as fh:
        fh.write("\n".join(lines))


def build():
    import shutil
    import build_t1_glyphs as T1
    src = ufoLib2.Font.open(SRC)
    roots = {g.name: kerning._root(src, g.name) for g in src}
    font, mark_plan = _derive(src)

    for attr in vars(src.info.__class__):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(src.info, attr)
            if val is not None and not callable(val):
                setattr(font.info, attr, val)
        except Exception:
            pass
    info = font.info
    info.familyName = info.styleMapFamilyName = "Sabas Mono"
    info.styleName = "Regular"
    info.openTypeOS2WeightClass = 400
    info.xHeight, info.capHeight = XH_M, CAP_M
    info.ascender, info.descender = ASC_M, DESC_M
    info.postscriptSlantAngle = 0
    info.postscriptBlueValues = [-12, 0, XH_M - 10, XH_M + 10, CAP_M - 10, CAP_M + 10,
                                 ASC_M - 10, ASC_M + 10]
    info.postscriptOtherBlues = [DESC_M - 10, DESC_M]
    info.openTypeOS2TypoAscender, info.openTypeOS2TypoDescender, info.openTypeOS2TypoLineGap = 800, -200, 200
    info.openTypeHheaAscender, info.openTypeHheaDescender, info.openTypeHheaLineGap = 800, -200, 200
    info.openTypeOS2WinAscent, info.openTypeOS2WinDescent = 1120, 360
    info.openTypeNamePreferredFamilyName = "Sabas Mono"
    info.openTypeNamePreferredSubfamilyName = "Regular"
    info.postscriptFontName = "SabasMono-Regular"
    info.postscriptFullName = "Sabas Mono Regular"
    info.openTypeNameUniqueID = "SabasMono-Regular"
    info.postscriptIsFixedPitch = True
    # PANOSE: sans-serif, book weight, monospaced.
    info.openTypeOS2Panose = [2, 11, 5, 9, 2, 2, 3, 2, 2, 4]
    font.lib["public.glyphOrder"] = [n for n in src.lib.get("public.glyphOrder", []) if n in font] + \
        [g.name for g in font if g.name not in src.lib.get("public.glyphOrder", [])]
    font.features.text = FEATURES
    font.kerning.clear()
    font.groups.clear()

    excluded = {g.name for g in src
                if any(not _is_mark(src, c.baseGlyph) for c in g.components)
                or g.name.endswith((".numr", ".dnom", ".sups", ".subs", ".onum", ".case"))}
    _mono_shapes(font, roots, T1, excluded)
    T1.fix_directions(font)
    T1.union_all(font)
    _place_marks(font, src, mark_plan)
    made = add_healing_variants(font, om.fill_is_left(src))
    write_healing_fea(font, made)
    T1.tidy_contours(font)
    anchors.add_anchors(font)
    import finalize
    finalize.mark_categories(font)

    if DST.exists():
        shutil.rmtree(DST)
    DST.parent.mkdir(parents=True, exist_ok=True)
    font.save(DST)
    print(f"Saved {DST}  ({len(font)} glyphs, advance={CELL})")


if __name__ == "__main__":
    build()
