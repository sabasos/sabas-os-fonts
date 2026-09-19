"""Invariants for Sabas Mono: fixed 600 advance, no kerning, ink inside the cell, zones held."""
import glob
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

CELL = 600


def check(path):
    f = TTFont(path)
    gs = f.getGlyphSet()
    hmtx = f["hmtx"]
    problems = []
    bad_adv = [g for g in f.getGlyphOrder() if hmtx[g][0] not in (0, CELL)]
    if bad_adv:
        problems.append(f"{len(bad_adv)} glyphs with an advance other than 0/{CELL}: {bad_adv[:6]}")
    if "kern" in f or ("GPOS" in f and "kern" in {r.FeatureTag for r in f["GPOS"].table.FeatureList.FeatureRecord}):
        problems.append("has a kern feature")
    overflow = []
    for g in f.getGlyphOrder():
        if hmtx[g][0] != CELL:
            continue
        p = BoundsPen(gs)
        gs[g].draw(p)
        if p.bounds and (p.bounds[0] < -4 or p.bounds[2] > CELL + 4):
            overflow.append(g)
    if overflow:
        problems.append(f"{len(overflow)} glyphs whose ink leaves the cell: {overflow[:6]}")
    if "fvar" not in f:
        def top(name):
            p = BoundsPen(gs)
            gs[name].draw(p)
            return p.bounds[3]
        if abs(top("x") - 525) > 3 or abs(top("H") - 700) > 3:
            problems.append(f"zones drifted: x {top('x')} H {top('H')}")
    return problems


def main(pattern="fonts/SabasM-*.ttf"):
    total = 0
    for path in sorted(glob.glob(pattern)):
        problems = check(path)
        print(("ok   " if not problems else "FAIL ") + path.split("/")[-1])
        for pr in problems:
            print("       " + pr)
        total += bool(problems)
    print("all mono checks pass" if not total else f"{total} fonts failing")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
