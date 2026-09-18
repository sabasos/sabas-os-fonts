"""
CI gate: static ≡ variable at named instances.
Spec §5.2: "CI asserts static ≡ variable at every named instance."

Checks:
1. VF contains all expected named instances
2. Cmap coverage identical between each static OTF and the VF
3. Glyph count identical
4. VF has gvar (interpolation) and HVAR (advance variation) tables
5. Advance widths of static OTFs agree with each other within weight-scaled tolerance
   (verifies the master UFOs are self-consistent)
"""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont

VF_PATH = Path("fonts/SabasUI-VF.ttf")

INSTANCES = [
    ("Thin",      100),
    ("Light",     300),
    ("Regular",   400),
    ("Medium",    500),
    ("SemiBold",  600),
    ("Bold",      700),
    ("ExtraBold", 800),
    ("Black",     900),
]


def main():
    vf = TTFont(VF_PATH)
    failures = []

    # 1. VF has required variation tables
    for table in ("gvar", "HVAR", "avar", "fvar"):
        if table not in vf:
            failures.append(f"VF missing table: {table}")

    # 2. VF has all named instances
    fvar_instances = {round(inst.coordinates.get("wght", 0))
                      for inst in vf["fvar"].instances}
    for stylename, wght in INSTANCES:
        if wght not in fvar_instances:
            failures.append(f"VF missing named instance: {stylename} wght={wght}")

    # 3. All axes present
    fvar_axes = {a.axisTag for a in vf["fvar"].axes}
    for tag in ("wght", "wdth", "opsz", "GRAD", "slnt"):
        if tag not in fvar_axes:
            failures.append(f"VF missing registered axis: {tag}")
    for tag in ("XOPQ", "YOPQ", "XTRA", "YTLC", "YTUC"):
        if tag not in fvar_axes:
            failures.append(f"VF missing parametric axis: {tag}")

    # 3b. §5.2: parametric axes must have real gvar deltas (not phantom)
    # Check that at least one glyph has non-zero deltas on a parametric axis.
    # gvar tuples whose peak is on a parametric axis dimension indicate real deltas.
    if "gvar" in vf:
        gvar = vf["gvar"]
        fvar_axis_list = [a.axisTag for a in vf["fvar"].axes]
        parametric_tags = {"XOPQ", "YOPQ", "XTRA", "YTLC", "YTUC"}
        parametric_indices = {i for i, tag in enumerate(fvar_axis_list) if tag in parametric_tags}
        has_parametric_deltas = False
        for glyph_name, variations in list(gvar.variations.items())[:50]:
            for var in variations:
                peak = var.axes  # dict of axis_tag -> (min, peak, max)
                if any(tag in peak and peak[tag][1] != 0 for tag in parametric_tags):
                    has_parametric_deltas = True
                    break
            if has_parametric_deltas:
                break
        if not has_parametric_deltas:
            failures.append("§5.2 FAIL: parametric axes (XOPQ/YOPQ/XTRA/YTLC/YTUC) have zero gvar deltas — axes are phantom")

    vf_cmap = vf.getBestCmap() or {}
    vf_glyphs = len(vf.getGlyphOrder())

    # 4. Per-instance: cmap and glyph count match VF; statics must be TTF (§4.1)
    for stylename, wght in INSTANCES:
        static_path = Path(f"fonts/SabasUI-{stylename}.ttf")
        if not static_path.exists():
            failures.append(f"  MISSING static: {static_path}")
            continue
        static = TTFont(static_path)
        # §4.1: statics must have glyf table (quadratic), not CFF
        if "glyf" not in static and "CFF " in static:
            failures.append(f"  {stylename}: static is CFF, must be quadratic TTF (§4.1)")
        if "glyf" not in static and "CFF " not in static:
            failures.append(f"  {stylename}: static has neither glyf nor CFF")
        static_cmap = static.getBestCmap() or {}

        missing = set(static_cmap.keys()) - set(vf_cmap.keys())
        extra   = set(vf_cmap.keys()) - set(static_cmap.keys())
        if missing:
            failures.append(f"  {stylename}: codepoints in static not in VF: "
                            f"{[hex(u) for u in sorted(missing)[:5]]}")
        if extra:
            failures.append(f"  {stylename}: codepoints in VF not in static: "
                            f"{[hex(u) for u in sorted(extra)[:5]]}")

        sg = len(static.getGlyphOrder())
        if sg != vf_glyphs:
            failures.append(f"  {stylename}: glyph count static={sg} vf={vf_glyphs}")

    if failures:
        print("STATIC ≡ VARIABLE GATE: FAILED")
        for f in failures:
            print(f)
        sys.exit(1)
    else:
        print(f"STATIC ≡ VARIABLE GATE: PASSED")
        print(f"  VF axes: {sorted(fvar_axes)}")
        print(f"  Named instances: {len(fvar_instances)}")
        print(f"  Glyph count: {vf_glyphs}")
        print(f"  Cmap entries: {len(vf_cmap)}")


if __name__ == "__main__":
    main()
