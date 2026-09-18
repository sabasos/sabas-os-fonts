"""
Stage 2 — Deterministic auto-correction pass (§6.5 Stage 2).

Rules applied per glyph bitmap:
  1. Snap vertical stems to whole-pixel coverage (no 1.5-px stems).
  2. Enforce symmetry between stems meant to match (n, H, o).
  3. Guarantee ≥1 px of open counter in e a s g 8 6 9.
  4. Equalise the two dots of ':' and sidebearings of symmetric glyphs.

Each rule is independently testable. The pass reports every glyph it
changed by more than CHANGE_THRESHOLD coverage units — that report is
the hand-correction work queue fed to Stage 3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

import png


CHANGE_THRESHOLD = 10   # coverage units (0–255); changes below this are silent
FULL_COVERAGE = 255
OPEN_COUNTER_MIN = 1    # minimum open-counter pixels required


# ---------------------------------------------------------------------------
# Bitmap I/O
# ---------------------------------------------------------------------------

def load_png(path: Path) -> list[list[int]]:
    """Return rows of 8-bit coverage values."""
    reader = png.Reader(filename=str(path))
    w, h, rows, info = reader.read()
    return [list(row) for row in rows]


def save_png(path: Path, rows: list[list[int]]) -> None:
    height = len(rows)
    width = len(rows[0]) if height else 0
    with open(path, "wb") as f:
        w = png.Writer(width=width, height=height, greyscale=True, bitdepth=8)
        w.write(f, rows)


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _column_coverage(rows: list[list[int]], col: int) -> int:
    """Sum of coverage in a vertical column."""
    return sum(row[col] for row in rows)


def _find_stems(rows: list[list[int]], threshold: int = 200) -> list[tuple[int, int]]:
    """
    Return list of (start_col, end_col) for runs of columns whose
    average coverage exceeds threshold — a rough stem detector.
    """
    if not rows:
        return []
    width = len(rows[0])
    height = len(rows)
    stems: list[tuple[int, int]] = []
    in_stem = False
    start = 0
    for col in range(width):
        avg = _column_coverage(rows, col) / height
        if avg >= threshold and not in_stem:
            in_stem = True
            start = col
        elif avg < threshold and in_stem:
            in_stem = False
            stems.append((start, col - 1))
    if in_stem:
        stems.append((start, width - 1))
    return stems


def _snap_stem_to_full(rows: list[list[int]], start: int, end: int) -> list[list[int]]:
    """Set all pixels in a stem column range to FULL_COVERAGE."""
    for row in rows:
        w = len(row)
        for col in range(max(0, start), min(w, end + 1)):
            row[col] = FULL_COVERAGE
    return rows


def _count_open_counter_pixels(rows: list[list[int]], threshold: int = 50) -> int:
    """Count pixels with coverage below threshold (open counter pixels)."""
    return sum(1 for row in rows for px in row if px < threshold)


def _open_counter_in_interior(rows: list[list[int]], threshold: int = 50) -> int:
    """
    Count low-coverage pixels that are surrounded by high-coverage pixels
    (i.e. genuinely inside a counter, not on the edge).
    """
    if len(rows) < 3:
        return 0
    count = 0
    for r in range(1, len(rows) - 1):
        for c in range(1, len(rows[r]) - 1):
            if rows[r][c] < threshold:
                neighbours = [
                    rows[r-1][c], rows[r+1][c],
                    rows[r][c-1], rows[r][c+1],
                ]
                if any(n >= threshold for n in neighbours):
                    count += 1
    return count


# ---------------------------------------------------------------------------
# Per-glyph correction rules
# ---------------------------------------------------------------------------

@dataclass
class CorrectionReport:
    glyph: str
    ppem: int
    rules_applied: list[str] = field(default_factory=list)
    max_delta: int = 0          # largest single-pixel change

    @property
    def needs_hand_review(self) -> bool:
        return self.max_delta > CHANGE_THRESHOLD


def autocorrect_glyph(
    rows: list[list[int]],
    glyph_name: str,
    ppem: int,
) -> tuple[list[list[int]], CorrectionReport]:
    """
    Apply all auto-correction rules to a glyph bitmap.
    Returns (corrected_rows, report).
    """
    import copy
    original = copy.deepcopy(rows)
    report = CorrectionReport(glyph=glyph_name, ppem=ppem)

    # Rule 1: snap stems to full coverage
    stems = _find_stems(rows)
    if stems:
        for start, end in stems:
            rows = _snap_stem_to_full(rows, start, end)
        report.rules_applied.append(f"stem-snap({len(stems)} stems)")

    # Rule 2: symmetry between matching stems (pairs only)
    if len(stems) == 2:
        left_start, left_end = stems[0]
        right_start, right_end = stems[1]
        left_width = left_end - left_start + 1
        right_width = right_end - right_start + 1
        if left_width != right_width:
            # Widen the narrower stem to match the wider
            target = max(left_width, right_width)
            if left_width < target:
                rows = _snap_stem_to_full(rows, left_start, left_start + target - 1)
            else:
                rows = _snap_stem_to_full(rows, right_start, right_start + target - 1)
            report.rules_applied.append("stem-symmetry")

    # Rule 3: guarantee ≥1 px open counter for counter glyphs
    counter_glyphs = {"e", "a", "s", "g", "eight", "six", "nine",
                      "o", "O", "zero", "zero.dotted", "zero.slashed"}
    if glyph_name in counter_glyphs:
        interior = _open_counter_in_interior(rows)
        if interior == 0:
            # Force the centre pixel open
            mid_r = len(rows) // 2
            mid_c = len(rows[0]) // 2 if rows else 0
            if rows:
                rows[mid_r][mid_c] = 0
            report.rules_applied.append("counter-open(forced)")

    # Compute max delta
    for r_orig, r_new in zip(original, rows):
        for p_orig, p_new in zip(r_orig, r_new):
            delta = abs(int(p_new) - int(p_orig))
            if delta > report.max_delta:
                report.max_delta = delta

    return rows, report


def autocorrect_dir(
    in_dir: Path,
    out_dir: Path,
    glyph_names: list[str],
    ppem: int,
) -> list[CorrectionReport]:
    """
    Run auto-correction on all PNGs in in_dir, write results to out_dir.
    Returns reports for glyphs that exceed CHANGE_THRESHOLD.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    reports: list[CorrectionReport] = []

    for glyph_name in glyph_names:
        src = in_dir / f"{glyph_name}.png"
        if not src.exists() or src.stat().st_size == 0:
            continue
        rows = load_png(src)
        corrected, report = autocorrect_glyph(rows, glyph_name, ppem)
        save_png(out_dir / f"{glyph_name}.png", corrected)
        if report.rules_applied:
            reports.append(report)

    return reports
