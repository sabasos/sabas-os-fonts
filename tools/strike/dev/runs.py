import importlib.util, sys
spec = importlib.util.spec_from_file_location("bt1", "tools/strike/build_t1_glyphs.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import ufoLib2
from fontTools.pens.pointInsidePen import PointInsidePen
font = ufoLib2.Font()
for d in m.LOWERCASE_DRAWERS + m.UPPERCASE_DRAWERS + m.DIGIT_DRAWERS: d(font)
m.fix_directions(font); m.union_all(font)
m.respace(font)
for fn in (m.draw_punctuation, m.draw_marks, m.draw_extra_symbols, m.draw_special_letters): fn(font)
m.fix_directions(font); m.union_all(font)

def runs(name, y, lo=-60, hi=800):
    if name not in font: return None
    g = font[name]; on = []; prev = False
    for x in range(lo, hi):
        p = PointInsidePen(font, (x + 0.5, y + 0.5)); g.draw(p)
        cur = bool(p.getResult())
        if cur and not prev: start = x
        if prev and not cur: on.append((start, x))
        prev = cur
    if prev: on.append((start, hi))
    return on

names = sys.argv[1:] or ["d"]
for n in names:
    print(f"== {n}")
    for y in range(-210, 760, 20):
        r = runs(n, y)
        if r is None: print("  MISSING"); break
        if not r: continue
        print(f"  y={y:>5}: " + "  ".join(f"{a}..{b}({b-a})" for a, b in r))
