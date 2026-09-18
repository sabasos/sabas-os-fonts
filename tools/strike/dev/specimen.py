import importlib.util, sys, os
spec = importlib.util.spec_from_file_location("b", "tools/strike/build_t1_glyphs.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import ufoLib2
font = ufoLib2.Font()
font.info.unitsPerEm = m.UPM
font.info.ascender = m.ASCENDER
font.info.descender = m.DESCENDER
font.info.xHeight = m.XHEIGHT
font.info.capHeight = m.CAPHEIGHT
font.info.familyName = "SabasSpec"; font.info.styleName = "Regular"
for group in (m.LOWERCASE_DRAWERS, m.UPPERCASE_DRAWERS, m.DIGIT_DRAWERS):
    for d in group: d(font)
m.fix_directions(font); m.union_all(font); m.respace(font)
m.draw_punctuation(font); m.draw_marks(font)
m.draw_extra_symbols(font); m.draw_special_letters(font)
m.fix_directions(font); m.union_all(font)
m.draw_accented(font); m.draw_accented2(font)
m.set_kerning(font)
if ".notdef" not in font:
    g = font.newGlyph(".notdef"); g.width = 500

from ufo2ft import compileTTF
tt = compileTTF(font, useProductionNames=False)
tt.save("/tmp/spec.ttf")
print("compiled", len(tt.getGlyphOrder()), "glyphs")
