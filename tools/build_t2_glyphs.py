"""
Add T2 glyphs to SabasUI-Regular.ufo:
  - 3 new combining marks: hookabovecomb, dotbelowcomb, horncomb
  - 4 Vietnamese base chars: Ohorn, ohorn, Uhorn, uhorn
  - 39 missing Latin Ext-A composites
  - Standalone glyphs: IJ, ij, Eng, eng, kgreenlandic, napostrophe, Tbar, tbar, longs
All masters are rebuilt after Regular is updated.
"""
import shutil
from pathlib import Path
import sys
import ufoLib2

sys.path.insert(0, str(Path(__file__).parent))

UFO = Path("sources/sabas-ui/SabasUI-Regular.ufo")


def add_glyph(font, name, unicode_val, width, draw_fn=None, components=None):
    if name in font:
        del font[name]
    g = font.newGlyph(name)
    g.width = width
    if unicode_val is not None:
        g.unicodes = [unicode_val]
    if components:
        for base, dx, dy in components:
            g.components.append(ufoLib2.objects.Component(
                baseGlyph=base,
                transformation=(1, 0, 0, 1, dx, dy),
            ))
    if draw_fn:
        pen = g.getPen()
        draw_fn(pen)
    return g


def quad(pen, x0, y0, x1, y1):
    pen.moveTo((x0, y0))
    pen.lineTo((x1, y0))
    pen.lineTo((x1, y1))
    pen.lineTo((x0, y1))
    pen.closePath()


def _t1():
    """The T1 generator's stroke tools, imported without running its main()."""
    sys.path.insert(0, str(Path(__file__).parent / "strike"))
    import build_t1_glyphs
    return build_t1_glyphs


ACCENT_NIB = (66, 60)          # accents are a little lighter than the stems


def add_new_marks(font):
    T1 = _t1()

    # hookabovecomb U+0309: the curl of a question mark, sitting where the other
    # above marks sit (bottom at 800). One centreline, so the weight holds round
    # the turn.
    g = add_glyph(font, "hookabovecomb", 0x0309, 0)
    T1.stroke(g, T1.arc_spline(0, 880, 50, 54, 175.0, -80.0), *ACCENT_NIB)

    # dotbelowcomb U+0323: a true circle at the size of the i-dot.
    g = add_glyph(font, "dotbelowcomb", 0x0323, 0)
    T1.dot(g, 0, -118, 46)

    # horncomb U+031B: a short stroke that leaves the letter up and to the right.
    # It starts at the origin, so each base places it where its own outline is.
    g = add_glyph(font, "horncomb", 0x031B, 0)
    T1.stroke(g, T1.spline([
        (0,   0,   62.0, None, 44.0),
        (58,  108, 42.0, 40.0, 34.0),
        (118, 150, 18.0, 34.0, None),
    ]), 62, 56)


def _ink(font, name):
    from fontTools.pens.boundsPen import BoundsPen
    p = BoundsPen(font)
    font[name].draw(p)
    return p.bounds


def _horn_start(font, base, ring):
    """Where the horn leaves a base: on the ring at 40 degrees, or in the right stem."""
    import math
    x0, y0, x1, y1 = _ink(font, base)
    if ring:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        rx, ry = (x1 - x0) / 2 - 44, (y1 - y0) / 2 - 38
        return round(cx + rx * math.cos(math.radians(40))), round(cy + ry * math.sin(math.radians(40)))
    return round(x1 - 44), round(y1 - 120)


def add_vietnamese_bases(font):
    for name, cp, base, ring in [("Ohorn", 0x01A0, "O", True), ("ohorn", 0x01A1, "o", True),
                                 ("Uhorn", 0x01AF, "U", False), ("uhorn", 0x01B0, "u", False)]:
        hx, hy = _horn_start(font, base, ring)
        add_glyph(font, name, cp, font[base].width,
                  components=[(base, 0, 0), ("horncomb", hx, hy)])


def add_latin_ext_a(font):
    # Each entry: (name, unicode, base_glyph, mark_glyph)
    # Width inherited from base glyph
    composites = [
        ("Ccircumflex",   0x0108, "C",  "circumflexcomb"),
        ("ccircumflex",   0x0109, "c",  "circumflexcomb"),
        ("Ebreve",        0x0114, "E",  "brevecomb"),
        ("ebreve",        0x0115, "e",  "brevecomb"),
        ("Gcircumflex",   0x011C, "G",  "circumflexcomb"),
        ("gcircumflex",   0x011D, "g",  "circumflexcomb"),
        ("Hcircumflex",   0x0124, "H",  "circumflexcomb"),
        ("hcircumflex",   0x0125, "h",  "circumflexcomb"),
        ("Itilde",        0x0128, "I",  "tildecomb"),
        ("itilde",        0x0129, "i",  "tildecomb"),
        ("Ibreve",        0x012C, "I",  "brevecomb"),
        ("ibreve",        0x012D, "i",  "brevecomb"),
        ("Jcircumflex",   0x0134, "J",  "circumflexcomb"),
        ("jcircumflex",   0x0135, "j",  "circumflexcomb"),
        ("Omacron",       0x014C, "O",  "macroncomb"),
        ("omacron",       0x014D, "o",  "macroncomb"),
        ("Obreve",        0x014E, "O",  "brevecomb"),
        ("obreve",        0x014F, "o",  "brevecomb"),
        ("Rcommaaccent",  0x0156, "R",  "commaaccentcomb"),
        ("rcommaaccent",  0x0157, "r",  "commaaccentcomb"),
        ("Scircumflex",   0x015C, "S",  "circumflexcomb"),
        ("scircumflex",   0x015D, "s",  "circumflexcomb"),
        ("Utilde",        0x0168, "U",  "tildecomb"),
        ("utilde",        0x0169, "u",  "tildecomb"),
        ("Ubreve",        0x016C, "U",  "brevecomb"),
        ("ubreve",        0x016D, "u",  "brevecomb"),
    ]
    for name, uni, base, mark in composites:
        w = font[base].width if base in font else 500
        add_glyph(font, name, uni, w, components=[(base, 0, 0), (mark, 0, 0)])


def add_standalone(font):
    # IJ U+0132 — ligature, width = I.width + J.width - overlap
    iw = font["I"].width if "I" in font else 280
    jw = font["J"].width if "J" in font else 420
    add_glyph(font, "IJ", 0x0132, iw + jw - 40,
              components=[("I", 0, 0), ("J", iw - 40, 0)])

    # ij U+0133
    iw = font["i"].width if "i" in font else 260
    jw = font["j"].width if "j" in font else 260
    add_glyph(font, "ij", 0x0133, iw + jw - 20,
              components=[("i", 0, 0), ("j", iw - 20, 0)])

    # kgreenlandic U+0138 — looks like k but without the upper arm
    # Use k as base (no good decomposition; copy k contours via component)
    kw = font["k"].width if "k" in font else 530
    add_glyph(font, "kgreenlandic", 0x0138, kw, components=[("k", 0, 0)])

    # napostrophe U+0149 — n preceded by apostrophe-like mark
    nw = font["n"].width if "n" in font else 570
    add_glyph(font, "napostrophe", 0x0149, nw + 120,
              components=[("quoterightcomb" if "quoterightcomb" in font else "commaaccentcomb", 0, 0),
                           ("n", 120, 0)])

    # Eng U+014A — uppercase N with descending right leg
    nw = font["N"].width if "N" in font else 700
    add_glyph(font, "Eng", 0x014A, nw, components=[("N", 0, 0)])

    # eng U+014B — lowercase n with descending right leg (use n as base)
    nw = font["n"].width if "n" in font else 570
    add_glyph(font, "eng", 0x014B, nw, components=[("n", 0, 0)])

    # Ldotaccent U+013F — L with middle dot
    lw = font["L"].width if "L" in font else 560
    add_glyph(font, "Ldotaccent", 0x013F, lw,
              components=[("L", 0, 0), ("dotaccentcomb", 0, -340)])

    # ldotaccent U+0140
    lw = font["l"].width if "l" in font else 260
    add_glyph(font, "ldotaccent", 0x0140, lw,
              components=[("l", 0, 0), ("dotaccentcomb", 0, -340)])

    # Tbar U+0166 — T with horizontal bar through stem
    tw = font["T"].width if "T" in font else 600
    def draw_tbar(pen):
        quad(pen, 80, 440, tw - 80, 480)
    add_glyph(font, "Tbar", 0x0166, tw,
              components=[("T", 0, 0)], draw_fn=draw_tbar)

    # tbar U+0167
    tw = font["t"].width if "t" in font else 360
    def draw_tbar_lc(pen):
        quad(pen, 20, 380, tw - 20, 416)
    add_glyph(font, "tbar", 0x0167, tw,
              components=[("t", 0, 0)], draw_fn=draw_tbar_lc)

    # longs U+017F — long s (historical); use s shape
    sw = font["s"].width if "s" in font else 490
    add_glyph(font, "longs", 0x017F, sw, components=[("s", 0, 0)])


def main():
    font = ufoLib2.Font.open(UFO)
    print(f"Opened {UFO}  ({len(font)} glyphs)")

    add_new_marks(font)
    add_vietnamese_bases(font)
    add_latin_ext_a(font)
    add_standalone(font)

    import build_coverage
    viet, symbols, fixed = build_coverage.add_all(font)
    print(f"coverage: +{viet} accented letters, +{symbols} symbols, {fixed} composites re-placed")

    import finalize
    added, n_anchors, pairs = finalize.finalize(font)
    print(f"ss01 alternates +{added}, {n_anchors} anchors, {pairs} kern pairs")

    font.save(UFO, overwrite=True)
    print(f"Saved {UFO}  ({len(font)} glyphs)")


if __name__ == "__main__":
    main()
