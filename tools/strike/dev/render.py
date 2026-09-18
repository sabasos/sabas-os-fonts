import freetype, uharfbuzz as hb
from PIL import Image, ImageDraw

import os, sys
# Defaults to the compiled OTF; pass a path or set SABAS_FONT to look at the
# in-memory preview build from dev/specimen.py (/tmp/spec.ttf) instead.
PATH = os.environ.get("SABAS_FONT") or "fonts/SabasUI-Regular.otf"
blob = hb.Blob.from_file_path(PATH)
hbface = hb.Face(blob)
face = freetype.Face(PATH)

def shape(text, px):
    hbfont = hb.Font(hbface)
    hbfont.scale = (px * 64, px * 64)
    hb.ot_font_set_funcs(hbfont)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hbfont, buf, {"kern": True, "liga": True})
    return list(zip(buf.glyph_infos, buf.glyph_positions))

def draw_line(img, text, px, x, y, gray=False):
    face.set_pixel_sizes(0, px)
    pen = x
    d = ImageDraw.Draw(img)
    for info, pos in shape(text, px):
        face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER |
                        (freetype.FT_LOAD_TARGET_LIGHT if gray else freetype.FT_LOAD_DEFAULT))
        bm = face.glyph.bitmap
        gx = pen + face.glyph.bitmap_left + pos.x_offset // 64
        gy = y - face.glyph.bitmap_top - pos.y_offset // 64
        if bm.width and bm.rows:
            buf = bytes(bytearray(bm.buffer))
            rows = [buf[r * bm.pitch:r * bm.pitch + bm.width] for r in range(bm.rows)]
            glyph = Image.frombytes("L", (bm.width, bm.rows), b"".join(rows))
            img.paste(Image.new("L", glyph.size, 0), (gx, gy), glyph)
        pen += pos.x_advance // 64
    return pen

LINES = [
 (96, "Sabas"),
 (48, "Hamburgefonstiv 0123456789"),
 (32, "The quick brown fox jumps over"),
 (24, "ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
 (24, "abcdefghijklmnopqrstuvwxyz"),
 (24, "0123456789 !?&@#$%*()[]{}"),
 (24, ".,;:'\"-–—/\\|~^+=<>"),
 (24, "Handgloves VAWY Tokyo raffle"),
 (24, "ÆÐØÞßŒæðøþœ ÀÉÎÕÜ àéîõü ÇçŁłĐđ"),
 (18, "The quick brown fox jumps over the lazy dog, 0123456789."),
 (16, "The quick brown fox jumps over the lazy dog, 0123456789."),
 (14, "The quick brown fox jumps over the lazy dog, 0123456789."),
 (12, "The quick brown fox jumps over the lazy dog, 0123456789."),
 (24, "Illlii1 0Oo rn m cl d 8B 5S 2Z"),
]
W = 1500
H = sum(int(px * 1.9) + 14 for px, _ in LINES) + 60
img = Image.new("L", (W, H), 255)
y = 20
for px, text in LINES:
    y += int(px * 1.25)
    draw_line(img, text, px, 24, y)
    y += int(px * 0.65) + 14
OUT = os.environ.get("SABAS_OUT", "/tmp/specimen.png")
img.save(OUT)
print("wrote", OUT, img.size)
