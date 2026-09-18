"""
Generate weight masters for SabasUI from the Regular UFO.
Uses fontTools TransformPen to scale contours correctly (preserves curves).
Masters: Thin(100), Light(300), SemiBold(600), Bold(700), ExtraBold(800), Black(900)
"""
import shutil
from pathlib import Path
from fontTools.pens.transformPen import TransformPen
import ufoLib2

REGULAR_UFO = Path("sources/sabas-ui/SabasUI-Regular.ufo")
REG_VSTEM = 88

# (stylename, wght, vstem, width_scale)
MASTERS = [
    ("Thin",      100,  28, 0.92),
    ("Light",     300,  60, 0.96),
    ("SemiBold",  600, 112, 1.02),
    ("Bold",      700, 132, 1.04),
    ("ExtraBold", 800, 152, 1.06),
    ("Black",     900, 180, 1.08),
]


def scale_ufo(src_path, dst_path, vstem, width_scale, stylename, wght):
    if dst_path.exists():
        shutil.rmtree(dst_path)

    src = ufoLib2.Font.open(src_path)
    dst = ufoLib2.Font()

    # Copy fontinfo attrs
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
    dst.info.openTypeOS2WeightClass = wght

    sy = vstem / REG_VSTEM
    sx = sy  # isotropic contour scale; advance scaled separately

    if src.info.postscriptBlueValues:
        dst.info.postscriptBlueValues = [round(v * sy) for v in src.info.postscriptBlueValues]
    if src.info.postscriptOtherBlues:
        dst.info.postscriptOtherBlues = [round(v * sy) for v in src.info.postscriptOtherBlues]

    dst.groups.update(src.groups)
    dst.kerning.update(src.kerning)
    dst.features.text = src.features.text
    dst.lib.update(src.lib)

    for src_g in src:
        dst_g = dst.newGlyph(src_g.name)
        dst_g.width = round(src_g.width * width_scale)
        dst_g.unicodes = list(src_g.unicodes)

        # Scale components
        for comp in src_g.components:
            t = comp.transformation  # (xx, xy, yx, yy, dx, dy)
            dst_g.components.append(ufoLib2.objects.Component(
                baseGlyph=comp.baseGlyph,
                transformation=(t[0], t[1], t[2], t[3],
                                round(t[4] * width_scale),
                                round(t[5] * sy)),
            ))

        # Scale contours via TransformPen
        if src_g.contours:
            dst_pen = dst_g.getPen()
            t_pen = TransformPen(dst_pen, (sx, 0, 0, sy, 0, 0))
            src_g.draw(t_pen)

    dst.save(dst_path)
    print(f"  {dst_path.name}  glyphs={len(dst)}  vstem≈{vstem}")


def main():
    for stylename, wght, vstem, width_scale in MASTERS:
        dst = Path(f"sources/sabas-ui/SabasUI-{stylename}.ufo")
        print(f"Building {stylename} (wght={wght})...")
        scale_ufo(REGULAR_UFO, dst, vstem, width_scale, stylename, wght)
    print("Done.")


if __name__ == "__main__":
    main()
