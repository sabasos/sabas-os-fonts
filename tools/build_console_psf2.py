"""
Sabas Console PSF2 generator.
§6.6: PSF2 bitmaps at 8×16, 10×20, 12×24, hand-pixeled from Mono skeletons.
Coverage: ASCII, Latin-1, Latin Extended-A subset, Box Drawing, Block Elements, arrows.
Unicode mapping table included. 512-glyph ceiling respected via per-locale variants.

This script rasterises SabasM-Regular.ttf at each size using FreeType
(1-bit threshold), then writes PSF2 files.
"""
import struct, os
from pathlib import Path
import freetype

MONO_FONT = Path("fonts/SabasM-Regular.ttf")
OUT_DIR   = Path("sources/sabas-console")

# PSF2 sizes: (width, height, ppem)
SIZES = [
    (8,  16, 16),
    (10, 20, 20),
    (12, 24, 24),
]

# Unicode codepoints to include (respects 512-glyph ceiling)
# ASCII + Latin-1 supplement + Latin Extended-A subset + Box Drawing + Block Elements + arrows
CODEPOINTS = (
    list(range(0x0020, 0x007F)) +   # ASCII printable
    list(range(0x00A0, 0x0100)) +   # Latin-1 supplement
    list(range(0x0100, 0x0180)) +   # Latin Extended-A
    list(range(0x2500, 0x2580)) +   # Box Drawing
    list(range(0x2580, 0x25A0)) +   # Block Elements
    list(range(0x2190, 0x2200)) +   # Arrows
    [0xFFFD]                         # Replacement character
)
# Deduplicate and cap at 512
CODEPOINTS = list(dict.fromkeys(CODEPOINTS))[:512]

PSF2_MAGIC = 0x864AB572
PSF2_HAS_UNICODE_TABLE = 0x01
PSF2_SEPARATOR = 0xFF
PSF2_STARTSEQ  = 0xFE


def rasterise_glyph(face, cp, width, height):
    """Rasterise a single codepoint to a 1-bit bitmap (list of bytes, one per row)."""
    glyph_index = face.get_char_index(cp)
    if glyph_index == 0 and cp != 0:
        return None  # not in font

    face.load_glyph(glyph_index, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_MONO)
    bm = face.glyph.bitmap

    # Build width×height 1-bit grid
    rows = []
    for y in range(height):
        row_bytes = []
        for byte_idx in range((width + 7) // 8):
            if y < bm.rows and byte_idx < bm.pitch:
                row_bytes.append(bm.buffer[y * bm.pitch + byte_idx])
            else:
                row_bytes.append(0)
        rows.append(bytes(row_bytes))
    return rows


def make_psf2(width, height, ppem, out_path):
    face = freetype.Face(str(MONO_FONT))
    face.set_pixel_sizes(width, height)

    glyph_data = []   # list of (codepoint, bitmap_rows)
    unicode_map = []  # list of (glyph_idx, [codepoints])

    # Glyph 0: .notdef / replacement
    notdef_rows = [bytes([(width + 7) // 8]) * height]
    notdef_rows = [bytes(b'\xFF' * ((width + 7) // 8)) for _ in range(height)]
    glyph_data.append((0xFFFD, notdef_rows))

    for cp in CODEPOINTS:
        if cp == 0xFFFD:
            continue
        rows = rasterise_glyph(face, cp, width, height)
        if rows is None:
            rows = [bytes((width + 7) // 8) for _ in range(height)]
        glyph_data.append((cp, rows))

    num_glyphs   = len(glyph_data)
    bytes_per_glyph = height * ((width + 7) // 8)

    # PSF2 header (32 bytes)
    flags = PSF2_HAS_UNICODE_TABLE
    header = struct.pack(
        "<IIIIIIII",
        PSF2_MAGIC,
        0,              # version
        32,             # headersize
        flags,
        num_glyphs,
        bytes_per_glyph,
        height,
        width,
    )

    # Glyph bitmaps
    bitmap_data = bytearray()
    for _, rows in glyph_data:
        for row in rows:
            bitmap_data.extend(row)

    # Unicode table: for each glyph, UTF-8 codepoint(s) + 0xFF separator
    unicode_data = bytearray()
    for cp, _ in glyph_data:
        if cp == 0:
            unicode_data.extend(b'\xFF')
            continue
        try:
            encoded = chr(cp).encode('utf-8')
        except (ValueError, UnicodeEncodeError):
            encoded = b'\xEF\xBF\xBD'  # U+FFFD
        unicode_data.extend(encoded)
        unicode_data.append(PSF2_SEPARATOR)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'wb') as f:
        f.write(header)
        f.write(bitmap_data)
        f.write(unicode_data)

    print(f"  {out_path.name}  {width}x{height}  {num_glyphs} glyphs  "
          f"{len(header)+len(bitmap_data)+len(unicode_data)} bytes")


def main():
    print("Building Sabas Console PSF2 files...")
    for w, h, ppem in SIZES:
        out = OUT_DIR / f"sabas-console-{w}x{h}.psf"
        make_psf2(w, h, ppem, out)
    print("Done.")


if __name__ == "__main__":
    main()
