"""Shaping goldens for Sabas Mono: calt texture healing, marks, and the fixed grid."""
import sys

import uharfbuzz as hb

CASES = [
    ("mill",  ["m", "i.wide1", "l.wide2", "l.wide1"]),
    ("llll",  ["l.wide1", "l.wide2", "l.wide2", "l.wide1"]),
    ("ifill", ["i.wide1", "f.wide2", "i.wide2", "l.wide2", "l.wide1"]),
    ("MWMW",  ["M", "W.narrow1", "M.narrow1", "W"]),
    ("WWiWW", ["W", "W", "i", "W", "W"]),
    ("i l",   ["i", "space", "l"]),
    ("nn",    ["n", "n"]),
    ("il",    ["i.wide1", "l.wide1"]),
    ("x́", ["x", "acutecomb"]),
    ("į́", ["iogonek", "acutecomb"]),
]


def shape(font, text):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {})
    return buf


def main(path="fonts/SabasM-Regular.ttf"):
    font = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
    bad = 0
    for text, want in CASES:
        buf = shape(font, text)
        got = [font.glyph_to_string(i.codepoint) for i in buf.glyph_infos]
        advs = {p.x_advance for p in buf.glyph_positions if p.x_advance}
        clusters = [i.cluster for i in buf.glyph_infos]
        ok = got == want and advs <= {600}
        bad += not ok
        print(("ok   " if ok else "FAIL ") + f"{text!r:8} -> {got} advances {sorted(advs)}"
              + ("" if ok else f"  want {want}"))
    # Cluster preservation: healing substitutes one glyph for one glyph.
    buf = shape(font, "llll")
    ok = [i.cluster for i in buf.glyph_infos] == [0, 1, 2, 3]
    bad += not ok
    print(("ok   " if ok else "FAIL ") + "clusters stay 1:1 through healing")
    # Idempotence: shaping the healed glyphs' source text again gives the same result.
    a = [font.glyph_to_string(i.codepoint) for i in shape(font, "illi").glyph_infos]
    b = [font.glyph_to_string(i.codepoint) for i in shape(font, "illi").glyph_infos]
    ok = a == b
    bad += not ok
    print(("ok   " if ok else "FAIL ") + "shaping is deterministic")
    print("all mono feature cases pass" if not bad else f"{bad} failing")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
