import sys
from fontTools.ttLib import TTCollection
from fontTools.pens.recordingPen import RecordingPen
c = TTCollection("/System/Library/Fonts/Helvetica.ttc")
f = c.fonts[0]
gs = f.getGlyphSet()
S = 1000 / f["head"].unitsPerEm
for name in sys.argv[1:]:
    p = RecordingPen(); gs[name].draw(p)
    print(f"== {name}  adv={gs[name].width*S:.0f}")
    n = -1
    for op, args in p.value:
        if op == "moveTo": n += 1; print(f" -- contour {n}")
        pts = " ".join(f"({x*S:.0f},{y*S:.0f})" for x, y in args)
        print(f"   {op} {pts}")
