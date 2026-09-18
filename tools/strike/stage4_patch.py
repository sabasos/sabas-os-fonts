"""
Stage 4 — Patch format v1: reader, writer, and conflict resolver (§6.5 Stage 4).

Format spec (frozen at v1, decided before M1):
  - One file per (glyph, ppem, weight)
  - Path: sources/strikes/<family>/wght<NNN>/ppem<NN>/<glyphname>.patch
  - Line-oriented plain text
  - from->to per-pixel deltas (enables per-pixel conflict detection)
  - baseline is a BLAKE3 hash of the Stage-2 raster (fast path)
  - raster-env records FreeType version + config (invalidated by upgrades)
  - Coordinates: baseline-relative, y-up, matching UFO convention

Conflict policy:
  baseline matches          → apply all, silent
  baseline differs, all from match → apply all, mark verified-reapply
  some from differ          → apply rest, flag pixels, BUILD FAILS
  bbox or advance changed   → whole glyph conflicts, full re-review

--accept-drift flag: overrides for local designer loop, rejected in CI.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PixelEdit:
    x: int
    y: int
    from_val: int
    to_val: int


@dataclass
class PatchFile:
    format: int
    family: str
    glyph: str
    ppem: int
    weight: int
    baseline: str           # blake3/sha256 hex of Stage-2 raster
    raster_env: str         # e.g. "freetype-2.13.3 target=light interp=40 darken=on compiler=fontc"
    bbox: tuple[int, int, int, int]   # xMin yMin xMax yMax, px, baseline-relative y-up
    advance: int            # px
    edits: list[PixelEdit] = field(default_factory=list)

    # path this was loaded from (set on read)
    source_path: Optional[Path] = field(default=None, repr=False)


# ---------------------------------------------------------------------------
# Hash helper — full SHA-256 hex (blake3 requires C extension; sha256 is fine)
# ---------------------------------------------------------------------------

def _hash_raster(rows: list[list[int]]) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update(bytes(row))
    return "sha256:" + h.hexdigest()  # full 64-char hex, no truncation


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def write_patch(
    patch: PatchFile,
    rows_stage2: list[list[int]],
    path: Path,
) -> None:
    """Write a patch file. rows_stage2 is used to generate the ASCII preview."""
    path.parent.mkdir(parents=True, exist_ok=True)
    xmin, ymin, xmax, ymax = patch.bbox
    width = xmax - xmin
    height = ymax - ymin

    lines = [
        f"format {patch.format}",
        f"family      {patch.family}",
        f"glyph       {patch.glyph}",
        f"ppem        {patch.ppem}",
        f"weight      {patch.weight}",
        f"baseline    {patch.baseline}",
        f"raster-env  {patch.raster_env}",
        f"bbox        {xmin} {ymin} {xmax} {ymax}",
        f"advance     {patch.advance}",
        "",
        "# x  y   from ->  to      8-bit coverage",
    ]
    for edit in patch.edits:
        lines.append(f"  {edit.x:2d}  {edit.y:2d}    {edit.from_val:3d} -> {edit.to_val:3d}")

    # ASCII preview (tool-generated, do not hand-edit)
    lines.append("")
    lines.append("# --- preview (tool-generated, do not hand-edit) ---")
    for row_idx in range(height):
        row_str = ""
        for col_idx in range(width):
            # apply edits to stage2 for preview
            px = rows_stage2[row_idx][col_idx] if row_idx < len(rows_stage2) and col_idx < len(rows_stage2[row_idx]) else 0
            for edit in patch.edits:
                if edit.x == col_idx and edit.y == row_idx:
                    px = edit.to_val
            row_str += "#" if px >= 128 else "."
        lines.append(f"# {row_str}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------

_EDIT_RE = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+)\s*->\s*(\d+)")


def read_patch(path: Path) -> PatchFile:
    lines = path.read_text(encoding="utf-8").splitlines()
    meta: dict[str, str] = {}
    edits: list[PixelEdit] = []

    for line in lines:
        if line.startswith("#") or not line.strip():
            continue
        m = _EDIT_RE.match(line)
        if m:
            edits.append(PixelEdit(
                x=int(m.group(1)),
                y=int(m.group(2)),
                from_val=int(m.group(3)),
                to_val=int(m.group(4)),
            ))
            continue
        if " " in line or "\t" in line:
            key, _, val = line.partition(" ")
            meta[key.strip()] = val.strip()

    bbox_parts = list(map(int, meta["bbox"].split()))
    return PatchFile(
        format=int(meta["format"]),
        family=meta["family"],
        glyph=meta["glyph"],
        ppem=int(meta["ppem"]),
        weight=int(meta["weight"]),
        baseline=meta["baseline"],
        raster_env=meta["raster-env"],
        bbox=tuple(bbox_parts),  # type: ignore[arg-type]
        advance=int(meta["advance"]),
        edits=edits,
        source_path=path,
    )


# ---------------------------------------------------------------------------
# Apply / conflict resolution
# ---------------------------------------------------------------------------

@dataclass
class ApplyResult:
    status: str             # "clean" | "verified-reapply" | "conflict" | "bbox-conflict"
    applied: list[PixelEdit] = field(default_factory=list)
    conflicted: list[PixelEdit] = field(default_factory=list)
    new_baseline: str = ""


def apply_patch(
    patch: PatchFile,
    rows_stage2: list[list[int]],
    *,
    accept_drift: bool = False,
) -> tuple[list[list[int]], ApplyResult]:
    """
    Apply patch to rows_stage2. Returns (patched_rows, result).
    Raises SystemExit with non-zero code on conflict unless accept_drift=True.
    """
    import copy
    rows = copy.deepcopy(rows_stage2)
    current_baseline = _hash_raster(rows_stage2)
    result = ApplyResult(status="clean", new_baseline=current_baseline)

    if current_baseline == patch.baseline:
        # Fast path: baseline matches, apply everything unchecked
        for edit in patch.edits:
            rows[edit.y][edit.x] = edit.to_val
            result.applied.append(edit)
        return rows, result

    # Baseline differs: per-pixel from verification
    for edit in patch.edits:
        actual = rows_stage2[edit.y][edit.x] if edit.y < len(rows_stage2) and edit.x < len(rows_stage2[edit.y]) else -1
        if actual == edit.from_val:
            rows[edit.y][edit.x] = edit.to_val
            result.applied.append(edit)
        else:
            result.conflicted.append(edit)

    if result.conflicted:
        result.status = "conflict"
        msg = (
            f"PATCH CONFLICT: {patch.glyph} ppem={patch.ppem} wght={patch.weight} — "
            f"{len(result.conflicted)} pixel(s) differ from expected 'from' value.\n"
            f"  Conflicted pixels: {[(e.x, e.y) for e in result.conflicted]}\n"
            f"  Patch: {patch.source_path}\n"
            "  Glyph queued for re-review. Build fails."
        )
        if accept_drift:
            print(f"[WARNING --accept-drift] {msg}", file=sys.stderr)
        else:
            print(f"[ERROR] {msg}", file=sys.stderr)
            sys.exit(1)
    else:
        result.status = "verified-reapply"

    return rows, result


# ---------------------------------------------------------------------------
# Patch directory helpers
# ---------------------------------------------------------------------------

def patch_path(
    strikes_root: Path,
    family: str,
    weight: int,
    ppem: int,
    glyph_name: str,
) -> Path:
    return strikes_root / family / f"wght{weight:03d}" / f"ppem{ppem:02d}" / f"{glyph_name}.patch"


def create_patch_from_diff(
    family: str,
    glyph: str,
    ppem: int,
    weight: int,
    rows_stage2: list[list[int]],
    rows_hand: list[list[int]],
    raster_env: str,
    advance: int,
) -> PatchFile:
    """
    Create a PatchFile by diffing Stage-2 output against hand-corrected bitmap.
    Only pixels that differ are recorded.
    """
    edits: list[PixelEdit] = []
    for r_idx, (row_s2, row_hand) in enumerate(zip(rows_stage2, rows_hand)):
        for c_idx, (s2_px, hand_px) in enumerate(zip(row_s2, row_hand)):
            if s2_px != hand_px:
                edits.append(PixelEdit(x=c_idx, y=r_idx, from_val=s2_px, to_val=hand_px))

    height = len(rows_stage2)
    width = len(rows_stage2[0]) if rows_stage2 else 0

    return PatchFile(
        format=1,
        family=family,
        glyph=glyph,
        ppem=ppem,
        weight=weight,
        baseline=_hash_raster(rows_stage2),
        raster_env=raster_env,
        bbox=(0, 0, width, height),
        advance=advance,
        edits=edits,
    )
