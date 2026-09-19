"""
Shape letter pairs with the font's real kerning and report pairs that end up closer
than MIN_CLEARANCE units. A kerned pair that touches is a bug in the table.

Usage: check_kerning.py [font] [min_clearance_units]
"""
import string
import sys

import freetype
import uharfbuzz as hb
from PIL import Image, ImageChops, ImageFilter

PPEM = 250
UNITS_PER_PX = 1000 / PPEM


def load(path):
    face = freetype.Face(path)
    face.set_pixel_sizes(0, PPEM)
    blob = hb.Blob.from_file_path(path)
    return face, hb.Font(hb.Face(blob))


_cache = {}


def glyph_image(face, gid):
    if gid not in _cache:
        face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING)
        bm = face.glyph.bitmap
        if bm.width == 0 or bm.rows == 0:
            _cache[gid] = None
        else:
            raw = Image.frombytes("L", (bm.pitch, bm.rows), bytes(bm.buffer)).crop((0, 0, bm.width, bm.rows))
            _cache[gid] = (raw.point(lambda v: 255 if v >= 64 else 0),
                           face.glyph.bitmap_left, face.glyph.bitmap_top)
    return _cache[gid]


def pair_distance(face, hbfont, text, limit_px):
    """Smallest r in 0..limit_px (pixels) at which the two glyphs touch; None if clear.

    Distance is Chebyshev (a square growing one pixel per step), so diagonal gaps read
    up to 40% short of Euclidean: the check errs on the side of reporting.
    """
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {})
    infos, poss = buf.glyph_infos, buf.glyph_positions
    if len(infos) != 2:
        return None
    a = glyph_image(face, infos[0].codepoint)
    b = glyph_image(face, infos[1].codepoint)
    if a is None or b is None:
        return None
    x_b = int(round(poss[0].x_advance * PPEM / 1000.0))
    ax0, ay0 = a[1], -a[2]
    bx0, by0 = x_b + b[1], -b[2]
    left = min(ax0, bx0) - 2
    top = min(ay0, by0) - 2
    right = max(ax0 + a[0].width, bx0 + b[0].width) + 2
    bottom = max(ay0 + a[0].height, by0 + b[0].height) + 2
    size = (right - left, bottom - top)
    la = Image.new("L", size, 0)
    lb = Image.new("L", size, 0)
    la.paste(a[0], (ax0 - left, ay0 - top))
    lb.paste(b[0], (bx0 - left, by0 - top))
    grown = la
    for r in range(0, limit_px + 1):
        if ImageChops.multiply(grown, lb).getbbox():
            return r
        grown = grown.filter(ImageFilter.MaxFilter(3))
    return None


def main(path="fonts/SabasUI-Regular.otf", clearance=16):
    face, hbfont = load(path)
    limit = max(1, int(round(clearance / UNITS_PER_PX)))
    letters = string.ascii_letters
    pairs = [a + b for a in letters for b in letters]
    pairs += [a + b for a in "TVWYFPrvwyAL7" for b in ".,"]
    pairs += ["ff", "fi", "fl", "ft"]
    bad = []
    for text in pairs:
        r = pair_distance(face, hbfont, text, limit)
        if r is not None:
            bad.append((r, text))
    bad.sort()
    for r, text in bad:
        print(f"  {text}: within {(r + 1) * UNITS_PER_PX:.0f} units")
    print(f"{len(pairs)} pairs checked, {len(bad)} closer than {clearance} units")
    return 1 if bad else 0


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(main(args[0] if args else "fonts/SabasUI-Regular.otf",
                  int(args[1]) if len(args) > 1 else 16))
