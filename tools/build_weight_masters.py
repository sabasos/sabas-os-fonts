"""
Weight masters for Sabas UI, derived from the Regular UFO by outline offsetting.

Every master keeps Regular's contour and point structure (see offset_master.py),
so the set interpolates. Medium is built separately by build_medium_master.py.
Stems follow the brief's 1 : 0.864 vertical-to-horizontal ratio.
"""
from pathlib import Path

from offset_master import build_master

REGULAR_UFO = Path("sources/sabas-ui/SabasUI-Regular.ufo")

# (stylename, wght, vertical stem, horizontal stem)
MASTERS = [
    ("Thin",       100,  28,  24),
    ("Light",      300,  60,  52),
    ("SemiBold",   600, 112,  97),
    ("Bold",       700, 126, 109),
    ("ExtraBold",  800, 140, 121),
    ("Black",      900, 154, 133),
    ("Ultra",     1000, 168, 145),
]


def main():
    for stylename, wght, v, h in MASTERS:
        dst = Path(f"sources/sabas-ui/SabasUI-{stylename}.ufo")
        print(f"Building {stylename} (wght={wght}, stems {v}/{h})...")
        build_master(REGULAR_UFO, dst, stylename, v, h, weight_class=wght)
    print("Done.")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    main()
