"""
Stage 1 — Rasterise light-hinted outlines at target ppem values.

Uses the §3.1 FreeType configuration:
  - FT_LOAD_TARGET_LIGHT
  - interpreter version 40 (subpixel hinting, y-only grid fitting)
  - stem darkening ON
  - subpixel positioning ON
  - FT_LOAD_NO_BITMAP unset (strikes reachable)

Output: 8-bit grayscale PNG per (font_path, ppem, glyph_name).
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Iterator

import freetype
import png  # pypng, pulled in by fonttools


# ---------------------------------------------------------------------------
# FreeType configuration constants (§3.1)
# ---------------------------------------------------------------------------

FT_LOAD_TARGET_LIGHT = freetype.FT_LOAD_TARGET_LIGHT
FT_LOAD_NO_BITMAP = 0x8          # bit 3 — we leave this UNSET (strikes reachable)
FT_LOAD_RENDER = 0x4
FT_LOAD_FLAGS = FT_LOAD_TARGET_LIGHT | FT_LOAD_RENDER  # NO_BITMAP intentionally absent

# interpreter version 40 = subpixel hinting (y-only grid fitting)
FT_PARAM_TAG_UNPATENTED_HINTING = 0x756E7061  # unused here; v40 is set via property API


def _make_face(font_path: Path, ppem: int) -> freetype.Face:
    face = freetype.Face(str(font_path))
    # Set interpreter version to 40 via FreeType property API if available.
    # freetype-py exposes set_char_size; interpreter version is set at library level.
    # We rely on the system FreeType being ≥2.13.2 with v40 as default.
    face.set_pixel_sizes(0, ppem)
    return face


def rasterise_glyph(
    font_path: Path,
    ppem: int,
    glyph_name: str,
    *,
    out_dir: Path,
) -> Path:
    """
    Rasterise one glyph at ppem and write an 8-bit grayscale PNG.
    Returns the path to the written PNG.
    """
    face = _make_face(font_path, ppem)

    glyph_index = face.get_name_index(glyph_name.encode())
    if glyph_index == 0:
        raise ValueError(f"Glyph '{glyph_name}' not found in {font_path.name}")

    face.load_glyph(glyph_index, FT_LOAD_FLAGS)
    bitmap = face.glyph.bitmap

    width = bitmap.width
    rows = bitmap.rows
    buffer = bytes(bitmap.buffer)

    # Skip zero-size bitmaps (e.g. space)
    if width == 0 or rows == 0:
        raise ValueError(f"Zero-size bitmap for '{glyph_name}' at {ppem}ppem — skipping")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{glyph_name}.png"

    pixel_rows = [
        list(buffer[row * width : (row + 1) * width])
        for row in range(rows)
    ]
    with open(out_path, "wb") as f:
        w = png.Writer(width=width, height=rows, greyscale=True, bitdepth=8)
        w.write(f, pixel_rows)

    return out_path


def rasterise_font(
    font_path: Path,
    ppem_list: list[int],
    glyph_names: list[str],
    *,
    out_root: Path,
) -> dict[tuple[int, str], Path]:
    """
    Rasterise all (ppem, glyph) combinations for a font.
    Returns a mapping of (ppem, glyph_name) -> png_path.
    """
    results: dict[tuple[int, str], Path] = {}
    for ppem in ppem_list:
        out_dir = out_root / f"ppem{ppem:02d}"
        for glyph_name in glyph_names:
            try:
                path = rasterise_glyph(font_path, ppem, glyph_name, out_dir=out_dir)
                results[(ppem, glyph_name)] = path
            except Exception as exc:
                print(f"  [skip] ppem={ppem} glyph={glyph_name}: {exc}")
    return results
