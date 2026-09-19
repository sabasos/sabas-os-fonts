"""Shape strings through HarfBuzz and assert the glyphs each Sabas UI feature picks."""
import sys

import uharfbuzz as hb

CASES = [
    # (text, features, expected glyph names)
    ("a", {}, ["a"]),
    ("a", {"ss01": True}, ["a.ss01"]),
    ("á", {"ss01": True}, ["aacute.ss01"]),
    ("l", {"ss02": True}, ["l.ss02"]),
    ("3", {"ss03": True}, ["three.ss03"]),
    ("0", {"cv01": True}, ["zero.cv01"]),
    ("1 2", {"tnum": True}, ["one.tnum", "space", "two.tnum"]),
    ("1 2", {"tnum": True, "pnum": True}, ["one", "space", "two"]),
    ("-", {"case": True}, ["hyphen.case"]),
    ("1234", {"onum": True}, ["one.onum", "two.onum", "three.onum", "four.onum"]),
    ("12", {"onum": True, "lnum": True}, ["one", "two"]),
    ("4", {"cv02": True}, ["four.cv02"]),
    ("1/2", {"frac": True}, ["one.numr", "fraction", "two.dnom"]),
    ("12/345", {"frac": True},
     ["one.numr", "two.numr", "fraction", "three.dnom", "four.dnom", "five.dnom"]),
    ("a1/2b", {"frac": True}, ["a", "one.numr", "fraction", "two.dnom", "b"]),
    ("12", {"sups": True}, ["one.sups", "two.sups"]),
    ("12", {"subs": True}, ["one.subs", "two.subs"]),
    ("12", {"numr": True}, ["one.numr", "two.numr"]),
    ("1a 2o", {"ordn": True}, ["one", "ordfeminine", "space", "two", "ordmasculine"]),
    ("a", {"ordn": True}, ["a"]),
    ("í", {}, ["iacute"]),
    ("j̈", {}, ["uni0237", "dieresiscomb"]),
    ("ị", {}, ["uni1ECB"]),
]


def shape(font, text, features):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features)
    order = font.face.glyph_order if hasattr(font.face, "glyph_order") else None
    return [font.glyph_to_string(i.codepoint) for i in buf.glyph_infos], buf


def check_marks(font):
    """Combining marks with no precomposed glyph must be moved by mark/mkmk."""
    bad = 0

    def positions(text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, {})
        return [font.glyph_to_string(i.codepoint) for i in buf.glyph_infos], buf.glyph_positions

    names, pos = positions("x\u0301")
    ok = names == ["x", "acutecomb"] and abs(pos[1].y_offset - (570 - 800)) <= 3 and pos[1].x_offset != 0
    print(("ok   " if ok else "FAIL ") + f"mark   x + acute  -> y_offset {pos[1].y_offset} x_offset {pos[1].x_offset}")
    bad += not ok

    names, pos = positions("x\u0302\u0301")
    ok = names == ["x", "circumflexcomb", "acutecomb"] and pos[2].y_offset > pos[1].y_offset + 50
    print(("ok   " if ok else "FAIL ") + f"mkmk   x + circ + acute -> y_offsets {pos[1].y_offset}, {pos[2].y_offset}")
    bad += not ok

    names, pos = positions("x\u0323")
    ok = names == ["x", "dotbelowcomb"] and pos[1].y_offset != 0
    print(("ok   " if ok else "FAIL ") + f"mark   x + dot below -> y_offset {pos[1].y_offset}")
    bad += not ok
    return bad


def check_kerning(font):
    """Class kerning, including accented and alternate glyphs that join a base's class."""
    bad = 0

    def first_advance(text, feats=None):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(font, buf, feats or {})
        return buf.glyph_positions[0].x_advance, [font.glyph_to_string(i.codepoint) for i in buf.glyph_infos]

    def plain(ch):
        buf = hb.Buffer()
        buf.add_str(ch)
        buf.guess_segment_properties()
        hb.shape(font, buf, {})
        return buf.glyph_positions[0].x_advance

    cases = [
        ("To", None, -80), ("AV", None, -60), ("LT", None, -65), ("Y.", None, -75),
        ("r.", None, -60), ("nn", None, 0), ("rn", None, 0), ("HH", None, 0),
        ("T\u00f3", None, -80),          # oacute joins the round class
        ("\u00c1V", None, -60),          # Aacute joins A
        ("Ta", {"ss01": True}, -80),      # a.ss01 joins the round class
    ]
    for text, feats, want in cases:
        adv, names = first_advance(text, feats)
        first_plain = plain(text[0]) if not feats else None
        if first_plain is None:
            # the plain advance of the first glyph, taken from a lone shaping of it
            first_plain = plain(text[0])
        got = adv - first_plain
        ok = got == want
        print(("ok   " if ok else "FAIL ") + f"kern   {text!r:8} {names} -> {got} (want {want})")
        bad += not ok
    return bad


def main(path):
    face = hb.Face(hb.Blob.from_file_path(path))
    font = hb.Font(face)
    bad = 0
    for text, feats, want in CASES:
        got, _ = shape(font, text, feats)
        ok = got == want
        bad += not ok
        print(("ok   " if ok else "FAIL ") + f"{text!r:10} {sorted(feats)} -> {got}" + ("" if ok else f"  want {want}"))
    bad += check_marks(font)
    bad += check_kerning(font)
    print("all feature cases pass" if not bad else f"{bad} failing cases")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "fonts/SabasUI-Regular.otf"))
