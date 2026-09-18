"""
Build SabasM-Regular.ufo — Sabas Mono Regular master.
§4.3 Mono metrics: 1000 UPM, advance=600 fixed, x-height=525, cap=700,
vstem=84, hstem=72, ascender=750, descender=-205, opsz default=13.
Strategy: derive from SabasUI-Regular.ufo, rescale all contours to fit
600-unit advance, adjust vertical metrics.
"""
import shutil
from pathlib import Path
from fontTools.pens.transformPen import TransformPen
import ufoLib2

SRC = Path("sources/sabas-ui/SabasUI-Regular.ufo")
DST = Path("sources/sabas-mono/SabasM-Regular.ufo")

# §4.3 Mono vs UI metrics
MONO_ADVANCE   = 600
UI_XHEIGHT     = 540;  MONO_XHEIGHT  = 525
UI_CAP         = 720;  MONO_CAP      = 700
UI_VSTEM       = 88;   MONO_VSTEM    = 84
UI_HSTEM       = 76;   MONO_HSTEM    = 72
UI_ASCENDER    = 750;  MONO_ASCENDER = 750
UI_DESCENDER   = -205; MONO_DESCENDER= -205

# Vertical scale: x-height ratio
SY = MONO_XHEIGHT / UI_XHEIGHT   # ≈ 0.972


def build_mono_ufo():
    if DST.exists():
        shutil.rmtree(DST)

    src = ufoLib2.Font.open(SRC)
    dst = ufoLib2.Font()

    # ── fontinfo ──────────────────────────────────────────────────────
    for attr in vars(src.info.__class__):
        if attr.startswith("_"):
            continue
        try:
            val = getattr(src.info, attr)
            if val is not None and not callable(val):
                setattr(dst.info, attr, val)
        except Exception:
            pass

    dst.info.familyName          = "Sabas Mono"
    dst.info.styleMapFamilyName  = "Sabas Mono"
    dst.info.styleName           = "Regular"
    dst.info.openTypeOS2WeightClass = 400
    dst.info.xHeight             = MONO_XHEIGHT
    dst.info.capHeight           = MONO_CAP
    dst.info.ascender            = MONO_ASCENDER
    dst.info.descender           = MONO_DESCENDER
    dst.info.postscriptSlantAngle = 0

    # Blue zones: baseline, x-height, cap, ascender overshoot
    dst.info.postscriptBlueValues = [
        -12, 0,                          # baseline
        MONO_XHEIGHT - 10, MONO_XHEIGHT + 10,  # x-height
        MONO_CAP - 10,     MONO_CAP + 10,       # cap
        MONO_ASCENDER - 10, MONO_ASCENDER + 10, # ascender
    ]
    dst.info.postscriptOtherBlues = [MONO_DESCENDER - 10, MONO_DESCENDER]

    # OS/2 metrics
    dst.info.openTypeOS2TypoAscender  = 800
    dst.info.openTypeOS2TypoDescender = -200
    dst.info.openTypeOS2TypoLineGap   = 200
    dst.info.openTypeHheaAscender     = 800
    dst.info.openTypeHheaDescender    = -200
    dst.info.openTypeHheaLineGap      = 200
    dst.info.openTypeOS2WinAscent     = 1010
    dst.info.openTypeOS2WinDescent    = 300

    # lib
    dst.lib.update(src.lib)
    dst.lib["public.postscriptNames"] = {}

    dst.groups.update(src.groups)
    dst.features.text = ""   # features written separately

    # ── Glyphs ────────────────────────────────────────────────────────
    for src_g in src:
        dst_g = dst.newGlyph(src_g.name)
        dst_g.unicodes = list(src_g.unicodes)

        # All glyphs get fixed 600-unit advance (except .notdef which keeps 500)
        if src_g.name == ".notdef":
            dst_g.width = 500
        else:
            dst_g.width = MONO_ADVANCE

        # Components: scale offsets to fit 600-unit grid
        for comp in src_g.components:
            t = comp.transformation
            # x offset: scale by MONO_ADVANCE / src_g.width (center in cell)
            src_w = src_g.width if src_g.width > 0 else MONO_ADVANCE
            x_scale = MONO_ADVANCE / src_w
            dst_g.components.append(ufoLib2.objects.Component(
                baseGlyph=comp.baseGlyph,
                transformation=(
                    t[0], t[1], t[2], t[3],
                    round(t[4] * x_scale),
                    round(t[5] * SY),
                ),
            ))

        if src_g.contours:
            src_w = src_g.width if src_g.width > 0 else MONO_ADVANCE
            # Center contours horizontally in the 600-unit cell
            x_scale = MONO_ADVANCE / src_w
            x_offset = 0  # already centered by scaling
            transform = (x_scale, 0, 0, SY, x_offset, 0)
            dst_pen = dst_g.getPen()
            t_pen = TransformPen(dst_pen, transform)
            src_g.draw(t_pen)

    # Update glyph order
    order = list(src.lib.get("public.glyphOrder", []))
    dst.lib["public.glyphOrder"] = order

    dst.save(DST)
    print(f"Saved {DST}  ({len(dst)} glyphs, advance={MONO_ADVANCE})")


if __name__ == "__main__":
    build_mono_ufo()
