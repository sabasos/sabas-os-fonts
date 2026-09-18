"""
Add texture healing variants and programming ligature glyphs to SabasM-Regular.ufo.
Healing variants: .wide1 (+8%), .wide2 (+16%), .narrow1 (-12%) of each base glyph.
Ligature glyphs: single 600-unit glyphs drawn for each programming ligature.
Also writes sources/sabas-mono/SabasM-Regular.ufo/features.fea.
"""
import shutil
from pathlib import Path
from fontTools.pens.transformPen import TransformPen
import ufoLib2

UFO = Path("sources/sabas-mono/SabasM-Regular.ufo")
W = 600

NARROW_BASES = [
    "i", "j", "l", "t", "f", "r", "I", "one",
    "period", "comma", "semicolon", "colon",
    "quotesingle", "quotedbl", "grave", "exclam", "bar",
    "parenleft", "parenright", "bracketleft", "bracketright",
    "braceleft", "braceright", "slash", "backslash",
]
WIDE_BASES = ["m", "w", "M", "W", "at", "percent", "ampersand"]

WIDE1_SCALE  = 1.08
WIDE2_SCALE  = 1.16
NARROW1_SCALE = 0.88


def add_variant(font, base_name, suffix, x_scale):
    """Add a scaled variant of base_name as base_name.suffix."""
    var_name = f"{base_name}.{suffix}"
    if var_name in font:
        return
    if base_name not in font:
        return
    base = font[base_name]
    g = font.newGlyph(var_name)
    g.width = W   # advance NEVER changes
    g.unicodes = []  # variants have no unicode

    # Scale contours horizontally around cell centre
    cx = W / 2
    # transform: scale x around cx, keep y
    # x' = cx + (x - cx) * sx = x*sx + cx*(1-sx)
    sx = x_scale
    dx = cx * (1 - sx)
    transform = (sx, 0, 0, 1.0, dx, 0)

    for comp in base.components:
        t = comp.transformation
        g.components.append(ufoLib2.objects.Component(
            baseGlyph=comp.baseGlyph,
            transformation=(t[0]*sx, t[1], t[2], t[3],
                            t[4]*sx + dx, t[5]),
        ))

    if base.contours:
        pen = g.getPen()
        t_pen = TransformPen(pen, transform)
        base.draw(t_pen)


def add_ligature_glyph(font, name, sequence_hint):
    """Add a placeholder ligature glyph (two-char sequence drawn as text-like shape)."""
    if name in font:
        return
    g = font.newGlyph(name)
    g.width = W
    g.unicodes = []
    # Draw a simple representative shape — a horizontal bar with serifs
    # Real artwork would be hand-drawn; this is a buildable placeholder
    pen = g.getPen()
    pen.moveTo((60, 360)); pen.lineTo((540, 360))
    pen.lineTo((540, 420)); pen.lineTo((60, 420)); pen.closePath()


def build_variants(font):
    for base in NARROW_BASES:
        add_variant(font, base, "wide1",  WIDE1_SCALE)
        add_variant(font, base, "wide2",  WIDE2_SCALE)
    for base in WIDE_BASES:
        add_variant(font, base, "narrow1", NARROW1_SCALE)
    # hyphen.nolig for token-boundary breaker
    if "hyphen" in font and "hyphen.nolig" not in font:
        base = font["hyphen"]
        g = font.newGlyph("hyphen.nolig")
        g.width = W
        g.unicodes = []
        base.draw(g.getPen())


LIG_GLYPHS = [
    "arrowdblright", "arrowright_eq", "arrowleft_eq",
    "greaterequal_lig", "arrowleftright", "bar_greater", "less_bar",
    "notequal", "notequal_strict", "equal_equal", "equal_strict",
    "coloncolon", "coloncolon_eq",
    "slashslash", "slashasterisk", "asteriskslash", "asteriskasterisk",
    "barbar", "ampersandampersand",
]


def build_ligatures(font):
    for name in LIG_GLYPHS:
        add_ligature_glyph(font, name, name)


FEATURES_FEA = """\
# Sabas Mono features
# Include order enforces lookup index ordering: ccmp < ss01 < calt

include(../features/mono/ss01_ligatures.fea);
include(../features/mono/calt_healing.fea);

feature zero {
    sub zero by zero.slash;
} zero;
"""


def write_features(ufo_path):
    fea_path = ufo_path / "features.fea"
    fea_path.write_text(FEATURES_FEA)
    print(f"  Wrote {fea_path}")


def main():
    font = ufoLib2.Font.open(UFO)
    before = len(font)

    build_variants(font)
    build_ligatures(font)

    # zero.slash variant for zero feature
    if "zero" in font and "zero.slash" not in font:
        base = font["zero"]
        g = font.newGlyph("zero.slash")
        g.width = W
        g.unicodes = []
        base.draw(g.getPen())
        # add diagonal slash
        pen = g.getPen()
        pen.moveTo((160, 160)); pen.lineTo((220, 100))
        pen.lineTo((440, 540)); pen.lineTo((380, 600)); pen.closePath()

    order = list(font.lib.get("public.glyphOrder", []))
    for g in font:
        if g.name not in order:
            order.append(g.name)
    font.lib["public.glyphOrder"] = order

    font.save(UFO, overwrite=True)
    write_features(UFO)
    print(f"Added {len(font) - before} variant/lig glyphs ({len(font)} total)")


if __name__ == "__main__":
    main()
