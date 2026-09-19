"""
Extra Latin coverage for Sabas UI: Vietnamese, the Pri-African composites, and the
symbols, fractions and currency signs of Google's Latin Plus set that belong in a text
family (arrows, geometric shapes and most maths live in the Symbols family).

Accented letters are generated from their Unicode decompositions: the head letter is
peeled back to a glyph the font already has, and the marks are stacked on it one at a
time, each sitting above (or below) whatever is already there.
"""
import sys
import unicodedata
from pathlib import Path

import ufoLib2
from fontTools.pens.boundsPen import BoundsPen

sys.path.insert(0, str(Path(__file__).parent / "strike"))

MARKS = {0x300: "gravecomb", 0x301: "acutecomb", 0x302: "circumflexcomb", 0x303: "tildecomb",
         0x304: "macroncomb", 0x306: "brevecomb", 0x307: "dotaccentcomb", 0x308: "dieresiscomb",
         0x309: "hookabovecomb", 0x30A: "ringcomb", 0x30B: "hungarumlautcomb", 0x30C: "caroncomb",
         0x31B: "horncomb", 0x323: "dotbelowcomb", 0x326: "commaaccentcomb",
         0x327: "cedillacomb", 0x328: "ogonekcomb"}
BELOW = {"dotbelowcomb", "commaaccentcomb", "cedillacomb", "ogonekcomb"}
GAP = 30

VIETNAMESE = list(range(0x1EA0, 0x1EFA))
PRI_AFRICAN = [0x1E3E, 0x1E3F, 0x1E44, 0x1E45, 0x1E62, 0x1E63, 0x01F8, 0x01F9]
PINYIN = list(range(0x01CD, 0x01DD))            # Ǎ ǎ Ǐ ǐ Ǒ ǒ Ǔ ǔ Ǖ ǖ Ǘ ǘ Ǚ ǚ Ǜ ǜ
HORNED = {"ohorn": "o", "uhorn": "u", "Ohorn": "O", "Uhorn": "U"}


def _glyph_by_codepoint(font):
    return {cp: g.name for g in font for cp in g.unicodes}


def _bounds(font, g):
    p = BoundsPen(font)
    g.draw(p)
    return p.bounds


def _peel(cp, have):
    """(head codepoint, [mark glyph names]) with the head already in the font."""
    marks = []
    while cp not in have:
        d = unicodedata.decomposition(chr(cp))
        if not d or d.startswith("<"):
            return None
        parts = [int(x, 16) for x in d.split()]
        if len(parts) != 2 or parts[1] not in MARKS:
            return None
        marks.insert(0, MARKS[parts[1]])
        cp = parts[0]
    return cp, marks


def _include(font, T1, g, head):
    """Put a letter into a glyph. A letter that is itself a composite contributes its parts
    directly, so the result never holds a component of a component."""
    src = font[head]
    if src.components:
        for c in src.components:
            g.components.append(ufoLib2.objects.Component(
                baseGlyph=c.baseGlyph, transformation=c.transformation))
        for c in src.contours:
            g.appendContour(c.copy() if hasattr(c, "copy") else c)
    else:
        T1.component(g, head)


def _attach(font, T1, g, head, marks):
    """Stack `marks` on a glyph that already holds `head`: each one centred on the letter
    (not on its horn) and sitting above, or below, whatever is already there."""
    centre_of = font[HORNED[head]] if head in HORNED else g
    for m in marks:
        b = _bounds(font, g)
        cb = _bounds(font, centre_of) if centre_of is not g else b
        mb = _bounds(font, font[m])
        dx = round((cb[0] + cb[2]) / 2 - (mb[0] + mb[2]) / 2)
        dy = round(b[1] - GAP - mb[3]) if m in BELOW else round(b[3] + GAP - mb[1])
        T1.component(g, m, dx, dy)


def add_accented(font, T1, codepoints):
    have = _glyph_by_codepoint(font)
    made = 0
    for cp in sorted(codepoints):
        if cp in have:
            continue
        peeled = _peel(cp, have)
        if peeled is None:
            continue
        head_cp, marks = peeled
        if any(m not in font for m in marks):
            continue
        head = have[head_cp]
        g = T1.add_glyph(font, f"uni{cp:04X}", font[head].width, cp)
        _include(font, T1, g, head)
        _attach(font, T1, g, head, marks)
        have[cp] = g.name
        made += 1
    return made


def replace_origin_marks(font, T1):
    """Composites whose marks were left at (0, 0) get them placed.

    A composite is one glyph: no shaper runs mark attachment inside it, so a mark left at
    the origin stays at the origin. Returns the number of glyphs fixed.
    """
    fixed = 0
    for g in list(font):
        comps = list(g.components)
        if len(comps) < 2:
            continue
        head, rest = comps[0], comps[1:]
        is_mark = lambda n: n.endswith("comb") and font[n].width == 0
        if is_mark(head.baseGlyph) or not all(is_mark(c.baseGlyph) for c in rest):
            continue
        if any(tuple(c.transformation[4:]) != (0, 0) for c in rest):
            continue
        marks = [c.baseGlyph for c in rest]
        g.components.clear()
        g.width = font[head.baseGlyph].width
        _include(font, T1, g, head.baseGlyph)
        _attach(font, T1, g, head.baseGlyph, marks)
        fixed += 1
    return fixed


def add_symbols(font, T1):
    from build_t1_glyphs import (CAPHEIGHT, HSTEM, VSTEM, XHEIGHT, SMALL_FIG_SCALE, band, dot,
                                 oval, rect, copy_outline, component, ink, FIG_NAMES)
    made = []

    def new(name, cp, width):
        made.append(name)
        return T1.add_glyph(font, name, width, cp)

    MID = CAPHEIGHT // 2
    top_dy = CAPHEIGHT * (1 - SMALL_FIG_SCALE)

    g = new("plusminus", 0x00B1, 580)
    rect(g, 40, MID + 30, 540, MID + 30 + HSTEM)
    rect(g, 290 - HSTEM // 2, MID - 110, 290 + HSTEM // 2, MID + 200)
    rect(g, 40, MID - 150, 540, MID - 150 + HSTEM)

    g = new("brokenbar", 0x00A6, 280)
    rect(g, 96, -60, 184, MID - 50)
    rect(g, 96, MID + 50, 184, CAPHEIGHT + 20)

    g = new("logicalnot", 0x00AC, 580)
    rect(g, 40, MID, 540, MID + HSTEM)
    rect(g, 540 - VSTEM, MID - 190, 540, MID + HSTEM)

    g = new("dblverticalbar", 0x2016, 380)
    rect(g, 70, 0, 158, CAPHEIGHT)
    rect(g, 222, 0, 310, CAPHEIGHT)

    g = new("dagger", 0x2020, 460)
    rect(g, 230 - VSTEM // 2, -120, 230 + VSTEM // 2, CAPHEIGHT)
    rect(g, 50, CAPHEIGHT - 190, 410, CAPHEIGHT - 190 + HSTEM)
    g = new("daggerdbl", 0x2021, 460)
    rect(g, 230 - VSTEM // 2, -120, 230 + VSTEM // 2, CAPHEIGHT)
    rect(g, 50, CAPHEIGHT - 190, 410, CAPHEIGHT - 190 + HSTEM)
    rect(g, 50, 60, 410, 60 + HSTEM)

    g = new("minute", 0x2032, 200)
    band(g, 130, CAPHEIGHT, 80, CAPHEIGHT - 190, weight=64)
    g = new("second", 0x2033, 320)
    band(g, 130, CAPHEIGHT, 80, CAPHEIGHT - 190, weight=64)
    band(g, 250, CAPHEIGHT, 200, CAPHEIGHT - 190, weight=64)

    if "percent" in font:
        g = new("perthousand", 0x2030, 1000)
        copy_outline(font, g, "percent")
        dot(g, 850, 140, 140)
        dot(g, 850, 140, 72, clockwise=True)

    if "u" in font:
        g = new("mu", 0x00B5, font["u"].width)
        copy_outline(font, g, "u")
        b = ink(font, "u")
        rect(g, round(b[0]), -205, round(b[0] + VSTEM), 10)

    g = new("pi", 0x03C0, 600)
    rect(g, 50, XHEIGHT - HSTEM, 550, XHEIGHT)
    rect(g, 170, 0, 170 + VSTEM, XHEIGHT - 20)
    rect(g, 380, 0, 380 + VSTEM, XHEIGHT - 20)

    for cp, sup, sub_ in [(0x2074, "four", 0x2084), (0x2075, "five", 0x2085), (0x2076, "six", 0x2086),
                          (0x2077, "seven", 0x2087), (0x2078, "eight", 0x2088), (0x2079, "nine", 0x2089),
                          (None, "one", 0x2081), (None, "two", 0x2082), (None, "three", 0x2083)]:
        w = round(font[sup].width * SMALL_FIG_SCALE)
        if cp:
            g = new(f"{sup}superior", cp, w)
            component(g, sup, 0, top_dy, SMALL_FIG_SCALE)
        g = new(f"{sup}inferior", sub_, w)
        component(g, sup, 0, -110, SMALL_FIG_SCALE)

    frac_w = font["fraction"].width if "fraction" in font else 130
    for name, cp, n, d in [("onethird", 0x2153, "one", "three"), ("twothirds", 0x2154, "two", "three")]:
        wn = round(font[n].width * SMALL_FIG_SCALE)
        wd = round(font[d].width * SMALL_FIG_SCALE)
        g = new(name, cp, wn + frac_w + wd)
        component(g, n, 0, top_dy, SMALL_FIG_SCALE)
        component(g, "fraction", wn, 0)
        component(g, d, wn + frac_w, 0, SMALL_FIG_SCALE)

    # Currency: a capital with its bars, built from the capital's own outline.
    def barred(name, cp, base, bars, vertical=()):
        b = ink(font, base)
        g = new(name, cp, font[base].width)
        copy_outline(font, g, base)
        for y in bars:
            rect(g, round(b[0] - 30), round(y), round(b[2] + 30), round(y + 62))
        for x, y0, y1 in vertical:
            rect(g, round(x), y0, round(x + 62), y1)

    cx = lambda n: (ink(font, n)[0] + ink(font, n)[2]) / 2 - 31
    barred("naira", 0x20A6, "N", [MID - 20, MID + 70])
    barred("won", 0x20A9, "W", [MID - 20, MID + 70])
    barred("peso", 0x20B1, "P", [MID - 30, MID + 50])
    barred("tugrik", 0x20AE, "T", [CAPHEIGHT * 0.45, CAPHEIGHT * 0.30])
    barred("tenge", 0x20B8, "T", [CAPHEIGHT * 0.50, CAPHEIGHT * 0.35])
    barred("kip", 0x20AD, "K", [MID - 31])
    barred("ruble", 0x20BD, "P", [CAPHEIGHT * 0.30])
    barred("cedi", 0x20B5, "C", [], [(cx("C"), -70, CAPHEIGHT + 70)])
    barred("baht", 0x0E3F, "B", [], [(cx("B"), -70, 110), (cx("B"), CAPHEIGHT - 110, CAPHEIGHT + 70)])
    barred("bitcoin", 0x20BF, "B", [], [(cx("B") - 55, -80, 110), (cx("B") + 55, -80, 110),
                                         (cx("B") - 55, CAPHEIGHT - 110, CAPHEIGHT + 80),
                                         (cx("B") + 55, CAPHEIGHT - 110, CAPHEIGHT + 80)])
    if "dcroat" in font:
        b = ink(font, "dcroat")
        g = new("dong", 0x20AB, font["dcroat"].width)
        copy_outline(font, g, "dcroat")
        rect(g, round(b[0]), -130, round(b[2]), -130 + 62)
    if "C" in font:
        b = ink(font, "C")
        g = new("colonsign", 0x20A1, font["C"].width)
        copy_outline(font, g, "C")
        band(g, b[0] + 60, -50, b[2] - 60, CAPHEIGHT + 50, weight=62)
    if "R" in font and "s" in font:
        wr, ws = font["R"].width, font["s"].width
        g = new("rupee", 0x20A8, wr + ws)
        component(g, "R")
        component(g, "s", wr, 0)

    # Modifier apostrophes, and the open o, which is a c read the other way round.
    for name, cp, base in [("uni02BB", 0x02BB, "quoteleft"), ("uni02BC", 0x02BC, "quoteright")]:
        if base in font:
            g = new(name, cp, font[base].width)
            component(g, base)
    from build_t1_glyphs import flip_x
    for name, cp, base in [("Oopen", 0x0186, "C"), ("oopen", 0x0254, "c")]:
        if base in font:
            g = new(name, cp, font[base].width)
            copy_outline(font, g, base)
            flip_x(g, font[base].width / 2)

    # Arithmetic on the = < > and ~ already in the font.
    if "equal" in font:
        g = new("notequal", 0x2260, 580)
        copy_outline(font, g, "equal")
        band(g, 170, MID - 150, 410, MID + 150, weight=HSTEM * 0.9)
    for name, cp, base in [("lessequal", 0x2264, "less"), ("greaterequal", 0x2265, "greater")]:
        if base in font:
            g = new(name, cp, 580)
            copy_outline(font, g, base, dy=60)
            rect(g, 40, MID - 190, 540, MID - 190 + HSTEM)
    if "asciitilde" in font:
        g = new("approxequal", 0x2248, font["asciitilde"].width)
        copy_outline(font, g, "asciitilde", dy=70)
        copy_outline(font, g, "asciitilde", dy=-70)
    return made


def add_all(font):
    import build_t1_glyphs as T1
    # Start from a clean slate: the accented letters this module generates are rebuilt
    # every run, so a change to the stacking rules reaches all of them.
    for cp in VIETNAMESE + PRI_AFRICAN + PINYIN:
        name = f"uni{cp:04X}"
        if name in font:
            del font[name]
    fixed = replace_origin_marks(font, T1)
    v = add_accented(font, T1, VIETNAMESE + PRI_AFRICAN + PINYIN)
    s = add_symbols(font, T1)
    return v, len(s), fixed
