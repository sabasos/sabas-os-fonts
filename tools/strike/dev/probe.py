import importlib.util, sys
spec = importlib.util.spec_from_file_location("b", "tools/strike/build_t1_glyphs.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import ufoLib2
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.pointInsidePen import PointInsidePen

def build(stage):
    font = ufoLib2.Font(); font.info.unitsPerEm = 1000
    for group in (m.LOWERCASE_DRAWERS, m.UPPERCASE_DRAWERS, m.DIGIT_DRAWERS):
        for d in group: d(font)
    if stage == "raw": return font
    m.fix_directions(font)
    if stage == "wound": return font
    m.union_all(font); m.respace(font)
    m.draw_punctuation(font); m.draw_marks(font)
    m.draw_extra_symbols(font); m.draw_special_letters(font)
    m.fix_directions(font); m.union_all(font)
    return font

def runs(g, y):
    inside, out, start = False, [], None
    for x in range(-200, 1200):
        pip = PointInsidePen(None, (x + .5, y + .5)); g.draw(pip)
        v = bool(pip.getResult())
        if v and not inside: start, inside = x, True
        elif not v and inside: out.append((start, x)); inside = False
    return out

for stage in ("raw", "wound", "full"):
    font = build(stage)
    print("=== stage", stage)
    for n in ("e", "s", "S", "c"):
        if n not in font: continue
        g = font[n]
        info = []
        for c in g.contours:
            a = AreaPen(); c.draw(a)
            b = BoundsPen(None); c.draw(b)
            info.append(f"area={a.value:9.0f} bounds={tuple(int(v) for v in b.bounds)}")
        print(f"  {n}: {len(g.contours)} contour(s)")
        for i in info: print("     ", i)
        for y in (150, 270, 420):
            print(f"      y={y}: {runs(g, y)}")
