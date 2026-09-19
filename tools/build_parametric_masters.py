"""
Masters for the registered wdth, opsz, GRAD and slnt axes, derived from Regular.

Each one sits on its own axis extreme in SabasUI.designspace.

  wdth  Condensed / Extended  x-scale the outline, then offset the stems back to
                              80 / 92 so narrow cuts do not clog (brief §5.2).
  opsz  Caption / Display     lowercase x-height 580 / 460, hairlines 82 / 70 and
                              tracking +30 / -16; cap height and ascender unchanged,
                              so the size series loosens and lifts as it shrinks.
  GRAD  GradMin / GradMax     stems 68/59 and 100/87 with every advance unchanged,
                              which is what makes grade reflow-free (brief §5.1).
  slnt  Oblique               10 degree shear, leaning right.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from offset_master import build_master

REG = Path("sources/sabas-ui/SabasUI-Regular.ufo")
OUT = Path("sources/sabas-ui")

MASTERS = [
    dict(style="Condensed", V=80,  H=76, x_scale=0.85, location={"wdth": 75}),
    dict(style="Extended",  V=92,  H=76, x_scale=1.15, location={"wdth": 125}),
    dict(style="Caption",   V=88,  H=82, xh_target=580, tracking=30, location={"opsz": 10}),
    dict(style="Display",   V=88,  H=70, xh_target=460, tracking=-16, location={"opsz": 32}),
    dict(style="GradMin",   V=68,  H=59, neutral_advance=True, location={"GRAD": -200}),
    dict(style="GradMax",   V=100, H=87, neutral_advance=True, location={"GRAD": 150}),
    dict(style="Oblique",   V=88,  H=76, shear=0.1763, location={"slnt": -10}),
]


def main():
    for cfg in MASTERS:
        cfg = dict(cfg)
        style = cfg.pop("style")
        V, H = cfg.pop("V"), cfg.pop("H")
        print(f"Building {style}...")
        build_master(REG, OUT / f"SabasUI-{style}.ufo", style, V, H, **cfg)
    print("Done.")


if __name__ == "__main__":
    main()
