"""
generate_patches.py — generate patch files for the 7 flagged glyphs.

For each glyph we define a corrected bitmap as a list of strings:
  '#' = 255 (full coverage)
  '.' = 0   (empty)
  '+' = 192 (partial — kept where intentional, e.g. antialiased edges)

The script diffs corrected vs Stage-2 output and writes .patch files.
Run from sabas-fonts/:
  python tools/strike/generate_patches.py
"""

from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import png
from stage4_patch import create_patch_from_diff, write_patch, patch_path

STAGE2_ROOT = Path("/tmp/sabas-strikes/stage2")
STRIKES_ROOT = Path("sources/strikes")
FAMILY = "sabas-ui"
WEIGHT = 400
RASTER_ENV = "freetype-2.x target=light interp=40 darken=on"

# Legend: '#'=255  '.'=0
CORRECTIONS: dict[tuple[int, str], list[str]] = {

    # -----------------------------------------------------------------------
    # ppem=11  H  (7×8) — snap partial stems to full, clean crossbar
    # -----------------------------------------------------------------------
    (11, "H"): [
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "#######",
        "#######",
        "##...##",
        "##...##",
    ],

    # -----------------------------------------------------------------------
    # ppem=11  a  (6×6) — clean bowl, ensure open counter
    # -----------------------------------------------------------------------
    (11, "a"): [
        "..####",
        ".#..##",
        ".#..##",
        ".#..##",
        ".#..##",
        "..####",
    ],

    # -----------------------------------------------------------------------
    # ppem=13  H  (7×10) — snap stems, clean crossbar
    # -----------------------------------------------------------------------
    (13, "H"): [
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
        "#######",
        "#######",
        "##...##",
        "##...##",
        "##...##",
    ],

    # -----------------------------------------------------------------------
    # ppem=13  a  (8×8) — clean bowl + stem, open counter
    # -----------------------------------------------------------------------
    (13, "a"): [
        "......##",
        ".....###",
        "..##.###",
        ".##..###",
        ".##..###",
        ".##..###",
        "..##.###",
        ".....###",
    ],

    # -----------------------------------------------------------------------
    # ppem=13  n  (7×8) — clean arch + stems
    # -----------------------------------------------------------------------
    (13, "n"): [
        "##.....",
        "##.####",
        "##.####",
        "##..###",
        "##...##",
        "##...##",
        "##...##",
        "##...##",
    ],

    # -----------------------------------------------------------------------
    # ppem=16  H  (9×12) — snap stems, clean crossbar
    # -----------------------------------------------------------------------
    (16, "H"): [
        "##.....##",
        "##.....##",
        "##.....##",
        "##.....##",
        "##.....##",
        "##.....##",
        "#########",
        "#########",
        "##.....##",
        "##.....##",
        "##.....##",
        "##.....##",
    ],

    # -----------------------------------------------------------------------
    # ppem=16  n  (9×9) — clean arch + stems
    # -----------------------------------------------------------------------
    (16, "n"): [
        "##.#####.",
        "##.#####.",
        "##..####.",
        "##...###.",
        "##...###.",
        "##...###.",
        "##...###.",
        "##...###.",
        "##...###.",
    ],
}


def _load_stage2(ppem: int, glyph: str) -> tuple[int, int, list[list[int]]]:
    path = STAGE2_ROOT / f"ppem{ppem:02d}" / f"{glyph}.png"
    r = png.Reader(filename=str(path))
    w, h, rows, _ = r.read()
    return w, h, [list(row) for row in rows]


def _correction_to_rows(lines: list[str]) -> list[list[int]]:
    result = []
    for line in lines:
        row = []
        for ch in line:
            if ch == "#":
                row.append(255)
            elif ch == ".":
                row.append(0)
            else:
                row.append(192)
        result.append(row)
    return result


def main() -> None:
    for (ppem, glyph), correction_lines in CORRECTIONS.items():
        w, h, stage2_rows = _load_stage2(ppem, glyph)
        corrected_rows = _correction_to_rows(correction_lines)

        # Validate dimensions match
        assert len(corrected_rows) == h, (
            f"{glyph}@{ppem}: correction has {len(corrected_rows)} rows, stage2 has {h}"
        )
        assert all(len(r) == w for r in corrected_rows), (
            f"{glyph}@{ppem}: correction row width mismatch (expected {w})"
        )

        patch = create_patch_from_diff(
            family=FAMILY,
            glyph=glyph,
            ppem=ppem,
            weight=WEIGHT,
            rows_stage2=stage2_rows,
            rows_hand=corrected_rows,
            raster_env=RASTER_ENV,
            advance=w,
        )

        out = patch_path(STRIKES_ROOT, FAMILY, WEIGHT, ppem, glyph)
        write_patch(patch, stage2_rows, out)

        changed = len(patch.edits)
        print(f"  ppem={ppem:2d}  {glyph:<6s}  {changed:3d} pixel(s) changed  → {out}")

    print(f"\nDone. {len(CORRECTIONS)} patch files written.")


if __name__ == "__main__":
    main()
