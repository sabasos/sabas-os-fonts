"""
Strike pipeline CLI — runs §6.5 stages 1–5.

Usage:
  python pipeline.py --font path/to/SabasUI-Regular.otf \
                     --family sabas-ui \
                     --weight 400 \
                     --ppem 11 13 16 \
                     --glyphs space H a n o \
                     [--accept-drift] \
                     [--golden tests/raster/sabas-ui] \
                     [--out fonts/SabasUI-Regular-strikes.otf]

Stages:
  1  Rasterise outlines via FreeType (§3.1 config)
  2  Auto-correct (stem snap, symmetry, counter openness)
  4  Apply patch overlays if present (§6.5 Stage 4 format)
  5  Embed EBDT/EBLC into font + validate golden diff
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running from tools/strike/ directly
sys.path.insert(0, str(Path(__file__).parent))

from stage1_rasterise import rasterise_font
from stage2_autocorrect import autocorrect_dir
import png as _png
from stage4_patch import apply_patch, patch_path, read_patch
from stage5_merge import embed_strikes, validate_golden_diff, validate_counter_openness

# §6.1 counter glyphs that must retain open counters
COUNTER_GLYPHS = ["e", "a", "s", "g", "o", "zero", "eight", "six", "nine"]


def run(args: argparse.Namespace) -> int:
    font_path = Path(args.font)
    out_root = Path(args.work_dir)
    strikes_root = Path(args.strikes_root)
    family = args.family
    weight = args.weight
    ppem_list: list[int] = args.ppem
    glyph_names: list[str] = args.glyphs
    accept_drift: bool = args.accept_drift

    stage1_dir = out_root / "stage1"
    stage2_dir = out_root / "stage2"
    stage4_dir = out_root / "stage4"

    # -----------------------------------------------------------------------
    # Stage 1 — Rasterise
    # -----------------------------------------------------------------------
    print("\n=== Stage 1: Rasterise ===")
    rasterise_font(font_path, ppem_list, glyph_names, out_root=stage1_dir)
    print(f"  Output → {stage1_dir}")

    # -----------------------------------------------------------------------
    # Stage 2 — Auto-correct
    # -----------------------------------------------------------------------
    print("\n=== Stage 2: Auto-correct ===")
    all_reports = []
    for ppem in ppem_list:
        reports = autocorrect_dir(
            in_dir=stage1_dir / f"ppem{ppem:02d}",
            out_dir=stage2_dir / f"ppem{ppem:02d}",
            glyph_names=glyph_names,
            ppem=ppem,
        )
        all_reports.extend(reports)

    review_queue = [r for r in all_reports if r.needs_hand_review]
    if review_queue:
        print(f"\n  Hand-correction work queue ({len(review_queue)} glyphs):")
        for r in review_queue:
            print(f"    ppem={r.ppem:2d}  {r.glyph:<20s}  rules={r.rules_applied}  max_delta={r.max_delta}")
    else:
        print("  No glyphs exceed hand-correction threshold.")

    # -----------------------------------------------------------------------
    # Stage 4 — Apply patch overlays
    # -----------------------------------------------------------------------
    print("\n=== Stage 4: Apply patches ===")
    import shutil
    for ppem in ppem_list:
        src_dir = stage2_dir / f"ppem{ppem:02d}"
        dst_dir = stage4_dir / f"ppem{ppem:02d}"
        dst_dir.mkdir(parents=True, exist_ok=True)

        for glyph_name in glyph_names:
            src_png = src_dir / f"{glyph_name}.png"
            dst_png = dst_dir / f"{glyph_name}.png"
            patch_file = patch_path(strikes_root, family, weight, ppem, glyph_name)

            if not src_png.exists():
                continue

            # Load stage2 rows
            import png as _png
            reader = _png.Reader(filename=str(src_png))
            w, h, rows_iter, _ = reader.read()
            rows = [list(row) for row in rows_iter]

            if patch_file.exists():
                patch = read_patch(patch_file)
                rows, result = apply_patch(patch, rows, accept_drift=accept_drift)
                print(f"  ppem={ppem:2d}  {glyph_name:<20s}  patch={result.status}")
            else:
                # No patch: copy stage2 output as-is
                shutil.copy2(src_png, dst_png)
                continue

            # Write patched PNG
            with open(dst_png, "wb") as f:
                writer = _png.Writer(width=w, height=h, greyscale=True, bitdepth=8)
                writer.write(f, rows)

    # -----------------------------------------------------------------------
    # Stage 5 — Embed strikes + validate
    # -----------------------------------------------------------------------
    print("\n=== Stage 5: Embed strikes ===")
    out_font = Path(args.out) if args.out else font_path.with_stem(font_path.stem + "-strikes")
    embed_strikes(
        font_path=font_path,
        bitmap_root=stage4_dir,
        ppem_list=ppem_list,
        weight=weight,
        glyph_names=glyph_names,
        out_path=out_font,
    )

    # Validate golden diff
    failures: list[str] = []
    if args.golden:
        golden_dir = Path(args.golden)
        print(f"\n  Validating golden diff against {golden_dir} ...")
        failures += validate_golden_diff(stage4_dir, golden_dir, ppem_list, glyph_names)

    # Validate counter openness
    counter_in_run = [g for g in glyph_names if g in COUNTER_GLYPHS]
    if counter_in_run:
        failures += validate_counter_openness(stage4_dir, ppem_list, counter_in_run)

    if failures:
        print("\n  VALIDATION FAILURES:")
        for f in failures:
            print(f"    {f}")
        return 1

    print("\n  All validation checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Sabas strike pipeline (§6.5 stages 1–5)")
    parser.add_argument("--font", required=True, help="Path to compiled .otf/.ttf")
    parser.add_argument("--family", required=True, help="Family name, e.g. sabas-ui")
    parser.add_argument("--weight", type=int, default=400, help="Weight value, e.g. 400")
    parser.add_argument("--ppem", type=int, nargs="+", default=[11, 13, 16],
                        help="ppem values to process")
    parser.add_argument("--glyphs", nargs="+", default=["space", "H", "a", "n", "o"],
                        help="Glyph names to process")
    parser.add_argument("--work-dir", default="/tmp/sabas-strikes",
                        help="Working directory for intermediate files")
    parser.add_argument("--strikes-root", default="sources/strikes",
                        help="Root of patch overlay files")
    parser.add_argument("--golden", default=None,
                        help="Directory of golden PNGs for diff validation")
    parser.add_argument("--out", default=None,
                        help="Output font path (default: <input>-strikes.otf)")
    parser.add_argument("--accept-drift", action="store_true",
                        help="Override patch conflicts (local loop only, rejected in CI)")
    args = parser.parse_args()
    sys.exit(run(args))


if __name__ == "__main__":
    main()
