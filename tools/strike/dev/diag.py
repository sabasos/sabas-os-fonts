import importlib.util, math, sys
spec = importlib.util.spec_from_file_location("b", "tools/strike/build_t1_glyphs.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
import ufoLib2
font = ufoLib2.Font()
font.info.unitsPerEm = 1000
for group in (m.LOWERCASE_DRAWERS, m.UPPERCASE_DRAWERS, m.DIGIT_DRAWERS):
    for d in group: d(font)
t = m.fix_directions(font); u = m.union_all(font)
m.respace(font)
m.draw_punctuation(font); m.draw_marks(font)
m.draw_extra_symbols(font); m.draw_special_letters(font)
m.fix_directions(font); m.union_all(font)
print("reversed", t, "unioned", u)

from fontTools.pens.pointInsidePen import PointInsidePen
def runs(g, y, x0=-300, x1=1100, step=1):
    inside, out, start = False, [], None
    for x in range(x0, x1, step):
        pip = PointInsidePen(None, (x + .5, y + .5))
        g.draw(pip)
        v = bool(pip.getResult())
        if v and not inside: start, inside = x, True
        elif not v and inside: out.append((start, x)); inside = False
    if inside: out.append((start, x1))
    return out

def perp(name, ys):
    g = font[name]
    rows = [(y, runs(g, y)) for y in ys]
    out = []
    for i in range(len(rows) - 1):
        (y0, r0), (y1, r1) = rows[i], rows[i+1]
        if len(r0) != len(r1): continue
        for a, b in zip(r0, r1):
            w0, w1 = a[1]-a[0], b[1]-b[0]
            slope = ((b[0]+b[1])/2 - (a[0]+a[1])/2) / (y1 - y0)
            p = w0 / math.hypot(1, slope)
            out.append(f"{p:5.1f}(w{w0:3d}{'/' if w1!=w0 else '='}{w1:3d})")
    print(f"{name:>10}: " + "  ".join(out))

for n, ys in [("v",(200,260)),("w",(200,260)),("x",(150,210)),("y",(300,360)),
              ("z",(200,260)),("k",(380,440)),
              ("A",(200,260)),("V",(300,360)),("W",(300,360)),("X",(200,260)),
              ("Y",(560,620)),("Z",(300,360)),("K",(560,620)),("N",(300,360)),
              ("M",(300,360)),("R",(100,160)),("AE",(200,260)),
              ("one",(400,460)),("two",(200,260)),("four",(200,260)),("seven",(200,260)),
              ("slash",(300,360)),("backslash",(300,360))]:
    try: perp(n, ys)
    except Exception as e: print(n, "ERR", e)

print("-- second pass --")
for n, ys in [("four",(400,460)),("A",(400,460)),("w",(300,360)),("x",(300,360)),
              ("AE",(400,460)),("two",(150,210)),("k",(120,180)),("K",(120,180)),
              ("Y",(400,460)),("M",(500,560)),("W",(500,560)),("v",(400,460))]:
    try: perp(n, ys)
    except Exception as e: print(n, "ERR", e)
