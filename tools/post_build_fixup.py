"""
Post-build fixup applied to every compiled TTF (VF + statics).

Fixes:
  §4.2  hhea ascent=800 descent=-200 lineGap=200  (mirror sTypo*)
  §4.2  gasp table: gridfit+grayscale at all ppem, symmetric rendering flag
  §13   STAT AxisValues: format-2 weight ranges, format-3 linked values
"""
from __future__ import annotations
import sys
from pathlib import Path
from fontTools.ttLib import TTFont


# ---------------------------------------------------------------------------
# hhea
# ---------------------------------------------------------------------------

def fix_hhea(font: TTFont) -> None:
    hhea = font["hhea"]
    os2  = font["OS/2"]
    hhea.ascent  = os2.sTypoAscender   # 800
    hhea.descent = os2.sTypoDescender  # -200
    hhea.lineGap = os2.sTypoLineGap    # 200


# ---------------------------------------------------------------------------
# gasp
# ---------------------------------------------------------------------------

def add_gasp(font: TTFont) -> None:
    from fontTools.ttLib.tables._g_a_s_p import table__g_a_s_p
    gasp = table__g_a_s_p()
    # GASP_GRIDFIT=0x0001, GASP_DOGRAY=0x0002, GASP_SYMMETRIC_GRIDFIT=0x0004,
    # GASP_SYMMETRIC_SMOOTHING=0x0008
    # All ppem: gridfit + grayscale + symmetric variants
    gasp.gaspRange = {0xFFFF: 0x000F}
    gasp.version = 1
    font["gasp"] = gasp


# ---------------------------------------------------------------------------
# STAT AxisValues
# ---------------------------------------------------------------------------

def add_stat_axis_values(font: TTFont) -> None:
    """Rebuild STAT using fontTools.otlLib.builder.buildStatTable.

    Format 2 (range) for the weight/wdth/opsz/slnt/GRAD values, one axis per fvar axis.
    Format 3 (linked) for Regular↔Bold style linking.
    """
    from fontTools.otlLib.builder import buildStatTable

    axes = [
        dict(tag="wght", name="Weight", values=[
            dict(nominalValue=100,  name="Thin",      rangeMinValue=1,    rangeMaxValue=200),
            dict(nominalValue=300,  name="Light",     rangeMinValue=200,  rangeMaxValue=350),
            dict(value=400, name="Regular",   flags=0x2, linkedValue=700),   # F3: linked to Bold
            dict(nominalValue=500,  name="Medium",    rangeMinValue=450,  rangeMaxValue=550),
            dict(nominalValue=600,  name="SemiBold",  rangeMinValue=550,  rangeMaxValue=650),
            dict(value=700, name="Bold",      linkedValue=400),              # F3: linked to Regular
            dict(nominalValue=800,  name="ExtraBold", rangeMinValue=750,  rangeMaxValue=850),
            dict(nominalValue=900,  name="Black",     rangeMinValue=850,  rangeMaxValue=950),
            dict(nominalValue=1000, name="Ultra",     rangeMinValue=950,  rangeMaxValue=1000),
        ]),
        dict(tag="wdth", name="Width", values=[
            dict(nominalValue=75,  name="Condensed", rangeMinValue=50,    rangeMaxValue=87.5),
            dict(nominalValue=100, name="Normal",    rangeMinValue=87.5,  rangeMaxValue=112.5, flags=0x2),
            dict(nominalValue=125, name="Extended",  rangeMinValue=112.5, rangeMaxValue=150),
        ]),
        dict(tag="opsz", name="Optical Size", values=[
            dict(nominalValue=10, name="Caption", rangeMinValue=6,  rangeMaxValue=13),
            dict(nominalValue=16, name="Text",    rangeMinValue=13, rangeMaxValue=20, flags=0x2),
            dict(nominalValue=32, name="Display", rangeMinValue=20, rangeMaxValue=72),
        ]),
        dict(tag="slnt", name="Slant", values=[
            dict(nominalValue=0,   name="Upright", rangeMinValue=-2,  rangeMaxValue=2,  flags=0x2),
            dict(nominalValue=-10, name="Oblique", rangeMinValue=-20, rangeMaxValue=-2),
        ]),
        dict(tag="GRAD", name="Grade", values=[
            dict(nominalValue=-200, name="GradMin",  rangeMinValue=-200, rangeMaxValue=-100),
            dict(nominalValue=0,    name="GradNorm", rangeMinValue=-100, rangeMaxValue=75,  flags=0x2),
            dict(nominalValue=150,  name="GradMax",  rangeMinValue=75,   rangeMaxValue=150),
        ]),
    ]

    buildStatTable(font, axes)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fixup(path: Path) -> None:
    font = TTFont(str(path))
    fix_hhea(font)
    add_gasp(font)
    add_stat_axis_values(font)
    font.save(str(path))
    hhea = font["hhea"]
    stat = font["STAT"].table if "STAT" in font else None
    av_count = stat.AxisValueCount if stat and hasattr(stat, "AxisValueCount") else 0
    print(f"  {path.name}: hhea={hhea.ascent}/{hhea.descent}/{hhea.lineGap}"
          f"  gasp={'yes' if 'gasp' in font else 'no'}"
          f"  STAT AxisValues={av_count}")


def main() -> None:
    targets = list(Path("fonts").glob("SabasUI-*.ttf")) + [Path("fonts/SabasUI-VF.ttf")]
    targets = [p for p in targets if p.exists()]
    if not targets:
        print("No TTF files found in fonts/")
        sys.exit(1)
    for p in sorted(set(targets)):
        fixup(p)
    print("Done.")


if __name__ == "__main__":
    main()
