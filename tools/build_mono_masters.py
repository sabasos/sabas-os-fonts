"""
Build Sabas Mono weight masters and slnt extreme from SabasM-Regular.ufo.
§5.1 Mono: wght 200–800/400, slnt 0…−9, GRAD −200…150.
Masters: Light(200), Regular(400), Bold(700) for wght axis.
         Oblique(slnt=-9) for slnt axis.
GRAD extremes derived from Regular same as UI.
"""
import shutil
from pathlib import Path
from fontTools.pens.transformPen import TransformPen
import ufoLib2

REG = Path("sources/sabas-mono/SabasM-Regular.ufo")
MONO_VSTEM = 84
SLNT_SHEAR = -0.158  # tan(9°)

MASTERS = [
    # (stylename, wght, vstem, width_scale)
    ("Light",  200, 42,  1.0),
    ("Bold",   700, 132, 1.0),   # advance stays 600 — width_scale=1 always for mono
    ("GradMin", None, 55, 1.0),  # GRAD=-200: XOPQ-=30 → vstem≈55
    ("GradMax", None, 110, 1.0), # GRAD=+150: XOPQ+=22 → vstem≈110
]


def scale_ufo(src_path, dst_path, vstem, stylename, shear=0.0):
    if dst_path.exists():
        shutil.rmtree(dst_path)

    src = ufoLib2.Font.open(src_path)
    dst = ufoLib2.Font()

    sy = vstem / MONO_VSTEM
    sx = sy

    for attr in vars(src.info.__class__):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(src.info, attr)
            if val is not None and not callable(val):
                setattr(dst.info, attr, val)
        except Exception:
            pass

    dst.info.styleName = stylename
    if src.info.postscriptBlueValues:
        dst.info.postscriptBlueValues = [round(v * sy) for v in src.info.postscriptBlueValues]
    if src.info.postscriptOtherBlues:
        dst.info.postscriptOtherBlues = [round(v * sy) for v in src.info.postscriptOtherBlues]

    dst.lib.update(src.lib)
    dst.groups.update(src.groups)
    dst.features.text = src.features.text

    if shear:
        transform = (sx, 0, shear * sy, sy, 0, 0)
    else:
        transform = (sx, 0, 0, sy, 0, 0)

    for src_g in src:
        dst_g = dst.newGlyph(src_g.name)
        dst_g.width = src_g.width   # fixed 600 always
        dst_g.unicodes = list(src_g.unicodes)

        for comp in src_g.components:
            t = comp.transformation
            dst_g.components.append(ufoLib2.objects.Component(
                baseGlyph=comp.baseGlyph,
                transformation=(t[0], t[1], t[2], t[3],
                                round(t[4]),          # x offset unchanged (mono)
                                round(t[5] * sy)),
            ))

        if src_g.contours:
            dst_pen = dst_g.getPen()
            t_pen = TransformPen(dst_pen, transform)
            src_g.draw(t_pen)

    dst.save(dst_path)
    print(f"  {dst_path.name}  vstem≈{vstem}")


def main():
    for stylename, wght, vstem, _ in MASTERS:
        dst = Path(f"sources/sabas-mono/SabasM-{stylename}.ufo")
        print(f"Building {stylename}...")
        scale_ufo(REG, dst, vstem, stylename)

    # Oblique: shear from Regular
    dst = Path("sources/sabas-mono/SabasM-Oblique.ufo")
    print("Building Oblique (slnt=-9)...")
    scale_ufo(REG, dst, MONO_VSTEM, "Oblique", shear=SLNT_SHEAR)

    print("Done.")


if __name__ == "__main__":
    main()
