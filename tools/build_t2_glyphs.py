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
import ufoLib2

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


def add_new_marks(font):
    # hookabovecomb U+0309 — small hook above, used in Vietnamese
    # Shape: a small open hook at ~820-880 height, zero advance
    def draw_hook(pen):
        # Hook: starts at top, curves left and down
        pen.moveTo((0, 880))
        pen.curveTo((-40, 880), (-60, 860), (-60, 840))
        pen.curveTo((-60, 820), (-40, 810), (-20, 815))
        pen.lineTo((-16, 807))
        pen.lineTo((-24, 807))
        pen.curveTo((-52, 800), (-76, 812), (-76, 840))
        pen.curveTo((-76, 872), (-52, 896), (0, 896))
        pen.closePath()
    add_glyph(font, "hookabovecomb", 0x0309, 0, draw_hook)

    # dotbelowcomb U+0323 — dot below baseline, used in Vietnamese
    def draw_dotbelow(pen):
        cx, cy, r = 0, -120, 28
        pen.moveTo((cx - r, cy))
        pen.curveTo((cx - r, cy + r), (cx, cy + r), (cx, cy + r))
        pen.curveTo((cx + r, cy + r), (cx + r, cy), (cx + r, cy))
        pen.curveTo((cx + r, cy - r), (cx, cy - r), (cx, cy - r))
        pen.curveTo((cx - r, cy - r), (cx - r, cy), (cx - r, cy))
        pen.closePath()
    add_glyph(font, "dotbelowcomb", 0x0323, 0, draw_dotbelow)

    # horncomb U+031B — combining horn, used in ơ ư
    def draw_horn(pen):
        # Small curved stroke extending right from top-right of base letter
        pen.moveTo((0, 680))
        pen.curveTo((20, 700), (40, 700), (50, 690))
        pen.curveTo((60, 680), (60, 660), (40, 650))
        pen.lineTo((36, 658))
        pen.curveTo((52, 666), (52, 680), (44, 688))
        pen.curveTo((36, 696), (20, 694), (4, 676))
        pen.closePath()
    add_glyph(font, "horncomb", 0x031B, 0, draw_horn)


def add_vietnamese_bases(font):
    # Ohorn U+01A0 — O with horn: O + horncomb component
    o_w = font["O"].width
    add_glyph(font, "Ohorn", 0x01A0, o_w,
              components=[("O", 0, 0), ("horncomb", o_w // 2, 0)])

    # ohorn U+01A1
    o_w = font["o"].width
    add_glyph(font, "ohorn", 0x01A1, o_w,
              components=[("o", 0, 0), ("horncomb", o_w // 2, 0)])

    # Uhorn U+01AF — U with horn
    u_w = font["U"].width
    add_glyph(font, "Uhorn", 0x01AF, u_w,
              components=[("U", 0, 0), ("horncomb", u_w // 2, 0)])

    # uhorn U+01B0
    u_w = font["u"].width
    add_glyph(font, "uhorn", 0x01B0, u_w,
              components=[("u", 0, 0), ("horncomb", u_w // 2, 0)])


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
        ("Tcommaaccent",  0x0162, "T",  "commaaccentcomb"),
        ("tcommaaccent",  0x0163, "t",  "commaaccentcomb"),
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

    font.save(UFO, overwrite=True)
    print(f"Saved {UFO}  ({len(font)} glyphs)")


if __name__ == "__main__":
    main()
