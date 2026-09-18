"""
Build parametric extreme masters for §5.2.

Each master sits at a parametric axis location (XOPQ/YOPQ/XTRA/YTLC/YTUC),
NOT at a registered axis location. avar2 maps registered → parametric;
these masters supply the gvar deltas that make those axes functional.

Regular defaults: XOPQ=88, YOPQ=76, XTRA=0, YTLC=540, YTUC=720
UPM=1000, x-height≈540, cap-height≈720, vstem≈88, hstem≈76
"""
import shutil
from pathlib import Path
from fontTools.pens.transformPen import TransformPen
import ufoLib2

REG = Path("sources/sabas-ui/SabasUI-Regular.ufo")

# Regular parametric defaults
XOPQ_DEF = 88
YOPQ_DEF = 76
YTLC_DEF = 540   # x-height in UPM units
YTUC_DEF = 720   # cap-height in UPM units
UPM      = 1000

# Parametric axis extremes and the geometry they encode.
# Each entry: (stylename, location_dict, sx, sy, dx_advance_frac, ytlc_scale)
#
# sx  = horizontal scale applied to contour points (XTRA effect on counters)
# sy  = vertical scale applied to contour points (YOPQ/YTLC effect)
# dx_advance_frac = fractional change to advance width (XTRA is advance-neutral
#                   for GRAD; for wdth it changes advance)
# ytlc_scale = scale applied to y-coordinates relative to baseline (YTLC effect)
#
# For XTRA: only counter space changes, not stems → use sx on x, keep y.
# For YTLC: scale y-coords so x-height hits target, cap stays fixed.
# For XOPQ/YOPQ (GRAD): scale stems, keep advance neutral via XTRA compensation.

EXTREMES = [
    # Condensed: XTRA=-100, XOPQ=80 (slight stem thinning for narrow fit)
    # Advance narrows ~15%, counters compress
    {
        "stylename": "Condensed",
        "location": {"X Transparent": -100, "X Opaque": 80},
        "sx": 0.85, "sy": 1.00,
        "advance_scale": 0.85,
        "shear": 0.0,
    },
    # Extended: XTRA=+100, XOPQ=92 (slight stem thickening)
    {
        "stylename": "Extended",
        "location": {"X Transparent": 100, "X Opaque": 92},
        "sx": 1.15, "sy": 1.00,
        "advance_scale": 1.15,
        "shear": 0.0,
    },
    # Caption: YTLC=580 (+40 from 540), XTRA=+20, YOPQ=68 (slightly lighter)
    # y-scale = 580/540 ≈ 1.074 applied to y-coords up to x-height
    # We approximate with a uniform sy that hits the YTLC target
    {
        "stylename": "Caption",
        "location": {"Y Transparent LC": 580, "X Transparent": 20, "Y Opaque": 68},
        "sx": 1.02, "sy": 580 / 540,
        "advance_scale": 1.02,
        "shear": 0.0,
    },
    # Display: YTLC=460 (-80 from 540), XTRA=-10, YOPQ=82 (slightly heavier)
    {
        "stylename": "Display",
        "location": {"Y Transparent LC": 460, "X Transparent": -10, "Y Opaque": 82},
        "sx": 0.99, "sy": 460 / 540,
        "advance_scale": 0.99,
        "shear": 0.0,
    },
    # GradMin: XOPQ=20, YOPQ=17 (very light stems), XTRA=+30 (advance-neutral)
    # Stem scale = 20/88 ≈ 0.227 for x, 17/76 ≈ 0.224 for y
    {
        "stylename": "GradMin",
        "location": {"X Opaque": 20, "Y Opaque": 17, "X Transparent": 30},
        "sx": 20 / XOPQ_DEF, "sy": 17 / YOPQ_DEF,
        "advance_scale": 1.00,   # advance-neutral: XTRA compensates
        "shear": 0.0,
    },
    # GradMax: XOPQ=200, YOPQ=172 (very heavy stems), XTRA=-60 (advance-neutral)
    {
        "stylename": "GradMax",
        "location": {"X Opaque": 200, "Y Opaque": 172, "X Transparent": -60},
        "sx": 200 / XOPQ_DEF, "sy": 172 / YOPQ_DEF,
        "advance_scale": 1.00,
        "shear": 0.0,
    },
    # Oblique: slnt=-10, no parametric axes involved — registered axis master
    {
        "stylename": "Oblique",
        "location": {"Slant": -10},
        "sx": 1.00, "sy": 1.00,
        "advance_scale": 1.00,
        "shear": -0.176,   # tan(10°)
    },
]


def build_master(src_path, dst_path, cfg):
    if dst_path.exists():
        shutil.rmtree(dst_path)

    src = ufoLib2.Font.open(src_path)
    dst = ufoLib2.Font()

    for attr in vars(src.info.__class__):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(src.info, attr)
            if val is not None and not callable(val):
                setattr(dst.info, attr, val)
        except Exception:
            pass

    dst.info.styleName = cfg["stylename"]
    dst.lib.update(src.lib)
    # Record parametric location for downstream tooling
    dst.lib["co.sabas.parametric.location"] = cfg["location"]

    sx, sy = cfg["sx"], cfg["sy"]
    shear  = cfg["shear"]
    adv_sc = cfg["advance_scale"]

    if src.info.postscriptBlueValues:
        dst.info.postscriptBlueValues = [round(v * sy) for v in src.info.postscriptBlueValues]
    if src.info.postscriptOtherBlues:
        dst.info.postscriptOtherBlues = [round(v * sy) for v in src.info.postscriptOtherBlues]

    dst.groups.update(src.groups)
    dst.kerning.update(src.kerning)
    dst.features.text = src.features.text

    # Transform: shear in x direction for oblique; scale for parametric
    if shear:
        transform = (sx, 0, shear * sy, sy, 0, 0)
    else:
        transform = (sx, 0, 0, sy, 0, 0)

    for src_g in src:
        dst_g = dst.newGlyph(src_g.name)
        dst_g.width = round(src_g.width * adv_sc)
        dst_g.unicodes = list(src_g.unicodes)

        for comp in src_g.components:
            t = comp.transformation
            dst_g.components.append(ufoLib2.objects.Component(
                baseGlyph=comp.baseGlyph,
                transformation=(t[0], t[1], t[2], t[3],
                                round(t[4] * adv_sc),
                                round(t[5] * sy)),
            ))

        if src_g.contours:
            dst_pen = dst_g.getPen()
            t_pen = TransformPen(dst_pen, transform)
            src_g.draw(t_pen)

    dst.save(dst_path)
    print(f"  {dst_path.name}  loc={cfg['location']}")


def main():
    for cfg in EXTREMES:
        dst = Path(f"sources/sabas-ui/SabasUI-{cfg['stylename']}.ufo")
        print(f"Building {cfg['stylename']}...")
        build_master(REG, dst, cfg)
    print("Done.")


if __name__ == "__main__":
    main()
