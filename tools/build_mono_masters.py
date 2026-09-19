"""
Sabas Mono masters, derived from SabasM-Regular.ufo with the offset engine.

The advance is 600 in every master (a fixed grid), so each master keeps the cell and
thickens or thins the strokes inside it.

  wght  Light 200 (48/41), Bold 800 (140/120)
  GRAD  GradMin -200 (64/55), GradMax +150 (104/89)
  slnt  Oblique -9, a 9 degree shear leaning right
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from offset_master import build_master

REG = Path("sources/sabas-mono/SabasM-Regular.ufo")
OUT = Path("sources/sabas-mono")
ZONES = (525, 700, 750)
STEMS = (84, 72)

MASTERS = [
    dict(style="Light",   V=48,  H=41,  weight_class=200),
    dict(style="Bold",    V=140, H=120, weight_class=800),
    dict(style="GradMin", V=64,  H=55),
    dict(style="GradMax", V=104, H=89),
    dict(style="Oblique", V=84,  H=72, shear=0.1584),
]


def main():
    for cfg in MASTERS:
        cfg = dict(cfg)
        style = cfg.pop("style")
        V, H = cfg.pop("V"), cfg.pop("H")
        print(f"Building {style}...")
        build_master(REG, OUT / f"SabasM-{style}.ufo", style, V, H, neutral_advance=True,
                     zones=ZONES, base_stems=STEMS, fit_cell=586, **cfg)
    print("Done.")


if __name__ == "__main__":
    main()
