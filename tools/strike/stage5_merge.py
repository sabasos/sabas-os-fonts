"""
Stage 5 — Merge corrected bitmaps into EBDT/EBLC strikes and validate (§6.5 Stage 5).

Uses fontTools TTX round-trip with the exact XML schema fontTools expects.
"""

from __future__ import annotations

from pathlib import Path
import tempfile, os

import png
from fontTools.ttLib import TTFont


# ---------------------------------------------------------------------------
# PNG helpers
# ---------------------------------------------------------------------------

def load_png(path: Path) -> tuple[int, int, list[list[int]]]:
    reader = png.Reader(filename=str(path))
    w, h, rows, _ = reader.read()
    return w, h, [list(row) for row in rows]


# ---------------------------------------------------------------------------
# EBDT/EBLC TTX builder
# ---------------------------------------------------------------------------

def _hex_rows(rows: list[list[int]]) -> str:
    return " ".join(f"{px:02X}" for row in rows for px in row)


def _build_ttx(
    ppem_list: list[int],
    glyph_id_map: dict[str, int],
    bitmap_root: Path,
    glyph_names: list[str],
    ascender: int,
) -> str:
    """
    Build a single TTX string containing both EBDT and EBLC tables.
    Uses format 6 (big metrics, byte-aligned, 8-bit grayscale).
    """
    ebdt_strikes = []
    eblc_strikes = []

    for strike_idx, ppem in enumerate(ppem_list):
        # SbitLineMetrics ascender is a signed byte (pixel value at ppem)
        # §4.2: sTypoAscender=800 UPM → scale to ppem
        asc_px = min(127, round(ascender * ppem / 1000))
        glyphs_in_strike = [
            g for g in glyph_names
            if (bitmap_root / f"ppem{ppem:02d}" / f"{g}.png").exists()
            and glyph_id_map.get(g) is not None
        ]
        if not glyphs_in_strike:
            continue

        glyph_xml = []
        for g in glyphs_in_strike:
            w, h, rows = load_png(bitmap_root / f"ppem{ppem:02d}" / f"{g}.png")
            # Hex bytes as plain text inside <rawimagedata> (fontTools _readRawImageData)
            hex_data = _hex_rows(rows)
            glyph_xml.append(f"""\
      <ebdt_bitmap_format_6 name="{g}">
        <BigGlyphMetrics>
          <height value="{h}"/>
          <width value="{w}"/>
          <horiBearingX value="0"/>
          <horiBearingY value="{h}"/>
          <horiAdvance value="{w}"/>
          <vertBearingX value="0"/>
          <vertBearingY value="0"/>
          <vertAdvance value="{h}"/>
        </BigGlyphMetrics>
        <rawimagedata>{hex_data}</rawimagedata>
      </ebdt_bitmap_format_6>""")

        ebdt_strikes.append(
            f'    <strikedata index="{strike_idx}">\n'
            + "\n".join(glyph_xml)
            + "\n    </strikedata>"
        )

        start_id = min(glyph_id_map[g] for g in glyphs_in_strike)
        end_id   = max(glyph_id_map[g] for g in glyphs_in_strike)
        glyph_locs = "\n".join(
            f'        <glyphLoc name="{g}" id="{glyph_id_map[g]}"/>'
            for g in glyphs_in_strike
        )

        eblc_strikes.append(f"""\
    <strike index="{strike_idx}">
      <bitmapSizeTable>
        <sbitLineMetrics direction="hori">
          <ascender value="{asc_px}"/>
          <descender value="0"/>
          <widthMax value="{ppem}"/>
          <caretSlopeNumerator value="0"/>
          <caretSlopeDenominator value="1"/>
          <caretOffset value="0"/>
          <minOriginSB value="0"/>
          <minAdvanceSB value="0"/>
          <maxBeforeBL value="{asc_px}"/>
          <minAfterBL value="0"/>
          <pad1 value="0"/>
          <pad2 value="0"/>
        </sbitLineMetrics>
        <sbitLineMetrics direction="vert">
          <ascender value="{asc_px}"/>
          <descender value="0"/>
          <widthMax value="{ppem}"/>
          <caretSlopeNumerator value="0"/>
          <caretSlopeDenominator value="1"/>
          <caretOffset value="0"/>
          <minOriginSB value="0"/>
          <minAdvanceSB value="0"/>
          <maxBeforeBL value="{asc_px}"/>
          <minAfterBL value="0"/>
          <pad1 value="0"/>
          <pad2 value="0"/>
        </sbitLineMetrics>
        <ppemX value="{ppem}"/>
        <ppemY value="{ppem}"/>
        <bitDepth value="8"/>
        <flags value="0x01"/>
        <startGlyphIndex value="{start_id}"/>
        <endGlyphIndex value="{end_id}"/>
        <colorRef value="0"/>
      </bitmapSizeTable>
      <eblc_index_sub_table_1 imageFormat="6" firstGlyphIndex="{start_id}" lastGlyphIndex="{end_id}">
{glyph_locs}
      </eblc_index_sub_table_1>
    </strike>""")

    ebdt_block = (
        '  <EBDT>\n'
        '    <header version="2.0"/>\n'
        + "\n".join(ebdt_strikes)
        + "\n  </EBDT>"
    )
    eblc_block = (
        '  <EBLC>\n'
        '    <header version="2.0"/>\n'
        + "\n".join(eblc_strikes)
        + "\n  </EBLC>"
    )

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<ttFont>\n"
        + ebdt_block + "\n"
        + eblc_block + "\n"
        "</ttFont>"
    )


def embed_strikes(
    font_path: Path,
    bitmap_root: Path,
    ppem_list: list[int],
    weight: int,
    glyph_names: list[str],
    out_path: Path,
) -> None:
    from fontTools.ttLib.tables import E_B_L_C_, E_B_D_T_

    font = TTFont(str(font_path))
    glyph_order = font.getGlyphOrder()
    glyph_id_map = {name: idx for idx, name in enumerate(glyph_order)}
    ascender = font["OS/2"].sTypoAscender if "OS/2" in font else 800

    ttx = _build_ttx(ppem_list, glyph_id_map, bitmap_root, glyph_names, ascender)

    with tempfile.TemporaryDirectory() as tmp:
        ttx_path = os.path.join(tmp, "strikes.ttx")
        with open(ttx_path, "w") as f:
            f.write(ttx)
        # Import into a fresh TTFont to avoid table-replacement issues,
        # then copy the populated EBLC/EBDT into the real font.
        fresh = TTFont()
        fresh.importXML(ttx_path)
        font["EBLC"] = fresh["EBLC"]
        font["EBDT"] = fresh["EBDT"]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(out_path))
    print(f"[stage5] Saved font with strikes \u2192 {out_path}")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_golden_diff(
    bitmap_dir: Path,
    golden_dir: Path,
    ppem_list: list[int],
    glyph_names: list[str],
) -> list[str]:
    failures: list[str] = []
    for ppem in ppem_list:
        for glyph_name in glyph_names:
            current = bitmap_dir / f"ppem{ppem:02d}" / f"{glyph_name}.png"
            golden  = golden_dir  / f"ppem{ppem:02d}" / f"{glyph_name}.png"
            if not current.exists() or not golden.exists():
                continue
            _, _, cur_rows = load_png(current)
            _, _, gld_rows = load_png(golden)
            diff = sum(
                1
                for rc, rg in zip(cur_rows, gld_rows)
                for pc, pg in zip(rc, rg)
                if pc != pg
            )
            if diff:
                failures.append(
                    f"GOLDEN DIFF FAIL: ppem={ppem} glyph={glyph_name} — {diff} differing pixel(s)"
                )
    return failures


def validate_counter_openness(
    bitmap_dir: Path,
    ppem_list: list[int],
    counter_glyphs: list[str],
    min_open_pixels: int = 1,
) -> list[str]:
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from stage2_autocorrect import _open_counter_in_interior
    failures: list[str] = []
    for ppem in ppem_list:
        for glyph_name in counter_glyphs:
            path = bitmap_dir / f"ppem{ppem:02d}" / f"{glyph_name}.png"
            if not path.exists():
                continue
            _, _, rows = load_png(path)
            open_px = _open_counter_in_interior(rows)
            if open_px < min_open_pixels:
                failures.append(
                    f"COUNTER CLOSED: ppem={ppem} glyph={glyph_name} — "
                    f"{open_px} open pixel(s) (need ≥{min_open_pixels})"
                )
    return failures
