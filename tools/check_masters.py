"""Report glyphs whose contour or component structure differs between masters."""
import glob
import sys

import ufoLib2


def signature(g):
    return (
        tuple((len(c.points), tuple(p.type for p in c.points)) for c in g.contours),
        tuple(c.baseGlyph for c in g.components),
        tuple(a.name for a in g.anchors),
    )


def main(pattern="sources/sabas-ui/SabasUI-*.ufo"):
    paths = sorted(glob.glob(pattern))
    ref_path = next(p for p in paths if p.endswith("-Regular.ufo"))
    ref = ufoLib2.Font.open(ref_path)
    bad = 0
    for p in paths:
        f = ufoLib2.Font.open(p)
        diff = [g.name for g in ref if g.name not in f or signature(g) != signature(f[g.name])]
        if diff:
            bad += 1
            print(f"{p.split('-')[-1][:-4]:10} {len(diff)} differ: {diff[:10]}")
    print("all masters compatible" if not bad else f"{bad} masters incompatible")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
