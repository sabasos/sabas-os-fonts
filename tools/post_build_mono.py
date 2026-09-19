"""Post-build fixup for Sabas Mono: hhea, gasp and a STAT table matching its axes."""
import sys
from pathlib import Path

from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).parent))
from post_build_fixup import add_gasp, fix_hhea

AXES = [
    dict(tag="wght", name="Weight", values=[
        dict(nominalValue=200, name="Light",     rangeMinValue=200, rangeMaxValue=300),
        dict(value=400, name="Regular", flags=0x2, linkedValue=700),
        dict(nominalValue=500, name="Medium",    rangeMinValue=450, rangeMaxValue=550),
        dict(nominalValue=600, name="SemiBold",  rangeMinValue=550, rangeMaxValue=650),
        dict(value=700, name="Bold", linkedValue=400),
        dict(nominalValue=800, name="ExtraBold", rangeMinValue=750, rangeMaxValue=800),
    ]),
    dict(tag="slnt", name="Slant", values=[
        dict(nominalValue=0,  name="Upright", rangeMinValue=-2, rangeMaxValue=0, flags=0x2),
        dict(nominalValue=-9, name="Oblique", rangeMinValue=-9, rangeMaxValue=-2),
    ]),
    dict(tag="GRAD", name="Grade", values=[
        dict(nominalValue=-200, name="GradMin",  rangeMinValue=-200, rangeMaxValue=-100),
        dict(nominalValue=0,    name="GradNorm", rangeMinValue=-100, rangeMaxValue=75, flags=0x2),
        dict(nominalValue=150,  name="GradMax",  rangeMinValue=75,   rangeMaxValue=150),
    ]),
]


def main():
    for p in sorted(Path("fonts").glob("SabasM-*.ttf")):
        font = TTFont(str(p))
        fix_hhea(font)
        add_gasp(font)
        buildStatTable(font, AXES)
        font.save(str(p))
        print(f"  {p.name}: hhea={font['hhea'].ascent}/{font['hhea'].descent}/{font['hhea'].lineGap}")


if __name__ == "__main__":
    main()
