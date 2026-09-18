"""
Generate Medium(500) UFO by interpolating 50% between Regular(400) and SemiBold(600).
Uses fontTools MathGlyph for correct point-by-point interpolation including curves.
"""
import shutil
from pathlib import Path
import ufoLib2
from fontTools.pens.recordingPen import RecordingPen
from fontTools.misc.roundTools import noRound

REG = Path("sources/sabas-ui/SabasUI-Regular.ufo")
SB  = Path("sources/sabas-ui/SabasUI-SemiBold.ufo")
DST = Path("sources/sabas-ui/SabasUI-Medium.ufo")
T   = 0.5


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_pt(a, b, t):
    return (round(lerp(a[0], b[0], t)), round(lerp(a[1], b[1], t)))


def interp_recording(rec_a, rec_b, t, dst_pen):
    """Replay interpolated version of two compatible RecordingPen recordings."""
    ops_a = rec_a.value
    ops_b = rec_b.value
    if len(ops_a) != len(ops_b):
        # incompatible — replay rec_a as-is
        rec_a.replay(dst_pen)
        return
    for (op_a, args_a), (op_b, args_b) in zip(ops_a, ops_b):
        if op_a != op_b:
            rec_a.replay(dst_pen)
            return
        if op_a in ("moveTo", "lineTo"):
            pts = tuple(lerp_pt(a, b, t) for a, b in zip(args_a[0] if isinstance(args_a[0], (list, tuple)) and not isinstance(args_a[0][0], (int, float)) else [args_a[0]], [args_b[0]] if not isinstance(args_b[0], (list, tuple)) or isinstance(args_b[0][0], (int, float)) else args_b[0]))
            getattr(dst_pen, op_a)(pts[0])
        elif op_a in ("curveTo", "qCurveTo"):
            pts = tuple(lerp_pt(a, b, t) for a, b in zip(args_a, args_b))
            getattr(dst_pen, op_a)(*pts)
        elif op_a == "closePath":
            dst_pen.closePath()
        elif op_a == "endPath":
            dst_pen.endPath()
        elif op_a == "addComponent":
            # components: (baseGlyph, transformation)
            bg_a, tr_a = args_a
            bg_b, tr_b = args_b
            tr = tuple(round(lerp(a, b, t)) if i >= 4 else lerp(a, b, t)
                       for i, (a, b) in enumerate(zip(tr_a, tr_b)))
            dst_pen.addComponent(bg_a, tr)


def main():
    if DST.exists():
        shutil.rmtree(DST)

    reg = ufoLib2.Font.open(REG)
    sb  = ufoLib2.Font.open(SB)
    dst = ufoLib2.Font()

    # Interpolate fontinfo
    for attr in vars(reg.info.__class__):
        if attr.startswith("_"):
            continue
        try:
            rv = getattr(reg.info, attr)
            sv = getattr(sb.info, attr)
            if rv is None or callable(rv):
                continue
            if isinstance(rv, (int, float)) and isinstance(sv, (int, float)):
                setattr(dst.info, attr, type(rv)(round(lerp(rv, sv, T))))
            else:
                setattr(dst.info, attr, rv)
        except Exception:
            pass

    dst.info.styleName = "Medium"
    dst.info.openTypeOS2WeightClass = 500

    if reg.info.postscriptBlueValues and sb.info.postscriptBlueValues:
        dst.info.postscriptBlueValues = [
            round(lerp(r, s, T))
            for r, s in zip(reg.info.postscriptBlueValues,
                            sb.info.postscriptBlueValues)
        ]

    dst.groups.update(reg.groups)
    dst.kerning.update(reg.kerning)
    dst.features.text = reg.features.text
    dst.lib.update(reg.lib)

    for reg_g in reg:
        if reg_g.name not in sb:
            continue
        sb_g = sb[reg_g.name]
        dst_g = dst.newGlyph(reg_g.name)
        dst_g.width = round(lerp(reg_g.width, sb_g.width, T))
        dst_g.unicodes = list(reg_g.unicodes)

        rec_a, rec_b = RecordingPen(), RecordingPen()
        reg_g.draw(rec_a)
        sb_g.draw(rec_b)
        interp_recording(rec_a, rec_b, T, dst_g.getPen())

    dst.save(DST)
    print(f"Saved {DST}  ({len(dst)} glyphs)")


if __name__ == "__main__":
    main()
