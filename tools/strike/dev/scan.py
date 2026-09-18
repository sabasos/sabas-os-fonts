import importlib.util, sys
spec = importlib.util.spec_from_file_location("bt1", "tools/strike/build_t1_glyphs.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import ufoLib2
from fontTools.pens.pointInsidePen import PointInsidePen
font = ufoLib2.Font()
for d in m.LOWERCASE_DRAWERS + m.UPPERCASE_DRAWERS + m.DIGIT_DRAWERS: d(font)
print("reversed:", m.fix_directions(font), "unioned:", m.union_all(font))
m.respace(font)
for fn in (m.draw_punctuation, m.draw_marks, m.draw_extra_symbols, m.draw_special_letters): fn(font)
print("pass2 reversed:", m.fix_directions(font), "unioned:", m.union_all(font))
def runs(name, y):
    if name not in font: return print(f"  {name}: MISSING")
    g = font[name]; on = []; prev = False
    for x in range(-40, 1200):
        p = PointInsidePen(font, (x + 0.5, y + 0.5)); g.draw(p)
        cur = bool(p.getResult())
        if cur and not prev: start = x
        if prev and not cur: on.append((start, x))
        prev = cur
    if prev: on.append((start, 1200))
    print(f"  {name:>11} @y={y:>4}: " + "  ".join(f"{a}..{b} ({b-a})" for a, b in on))
print("\n-- stem widths at mid x-height --")
for n in ["b","d","p","q","a","g","o","e","c","s","n","h","u","m","i","l","t","f"]: runs(n, 270)
print("\n-- caps through the bowl --")
for n in ["B","P","R","D","O","G","Q","C","S","A","H","E"]: runs(n, 468)
for n in ["B","D","O"]: runs(n, 200)
print("\n-- derived letters --")
for n in ["Thorn","thorn","germandbls","uni1E9E","eth","Eth","ae","oe","OE","AE","Oslash","oslash","cent","Euro","sterling","copyright","ordmasculine"]: runs(n, 300)
