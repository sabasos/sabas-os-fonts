"""
Sabas UI kerning: shape classes and class-to-class values.

Kerning is class-based only (brief section 10). The classes name the *edge* that
matters: `kern1` groups are the right edge of the first glyph, `kern2` groups the
left edge of the second. Accented letters and alternates (a.ss01, aacute, ...)
join their base letter's group automatically, so a new composite never needs a
kerning entry of its own.

tools/check_kerning.py rasterises every pair the table touches and fails if two
glyphs end up closer than the minimum clearance.
"""

KERN1 = {
    "T":     ["T"],
    "FP":    ["F", "P"],
    "VWY":   ["V", "W", "Y"],
    "A":     ["A"],
    "L":     ["L"],
    "R":     ["R"],
    "K":     ["K"],
    "OC":    ["C", "D", "G", "O", "Q"],
    "r":     ["r"],
    "vwy":   ["v", "w", "y"],
    "seven": ["seven"],
    "quote": ["quoteright", "quotedblright", "quoteleft", "quotedblleft",
              "quotesingle", "quotedbl"],
}

KERN2 = {
    "round":   ["a", "c", "d", "e", "g", "o", "q", "s"],
    "Round":   ["C", "G", "O", "Q"],
    "A":       ["A"],
    "VWY":     ["V", "W", "Y"],
    "T":       ["T"],
    "vwy":     ["v", "w", "y"],
    "lowstem": ["i", "m", "n", "p", "r", "u"],
    "period":  ["period", "comma", "quotesinglbase", "quotedblbase"],
    "quote":   ["quoteright", "quotedblright", "quoteleft", "quotedblleft",
                "quotesingle", "quotedbl"],
}

# (kern1 class, kern2 class, value). Negative pulls the pair together.
PAIRS = [
    # T: arm over a following letter.
    ("T", "round", -80), ("T", "A", -75), ("T", "period", -90), ("T", "vwy", -55),
    ("T", "lowstem", -50), ("T", "Round", -25),
    # V W Y: diagonals.
    ("VWY", "round", -55), ("VWY", "A", -60), ("VWY", "period", -75),
    ("VWY", "lowstem", -30), ("VWY", "Round", -20), ("VWY", "vwy", -15),
    # F P: arm and open bowl.
    ("FP", "round", -30), ("FP", "A", -55), ("FP", "period", -80),
    # A: diagonal against a following diagonal, arm or quote.
    ("A", "VWY", -60), ("A", "T", -65), ("A", "Round", -20), ("A", "vwy", -25),
    ("A", "quote", -25),
    # L: foot leaves a hole under what follows.
    ("L", "VWY", -60), ("L", "T", -65), ("L", "Round", -20), ("L", "quote", -70),
    # R and K: a leg or arm that swings out.
    ("R", "T", -20), ("R", "VWY", -20), ("K", "round", -25), ("K", "Round", -20),
    ("K", "vwy", -25),
    # Round capitals before a diagonal or an arm.
    ("OC", "A", -20), ("OC", "VWY", -20), ("OC", "T", -15),
    # Lowercase r and the diagonals before a stop or a round.
    ("r", "period", -60), ("r", "round", -20), ("vwy", "period", -55),
    ("vwy", "round", -20),
    # Seven's bar.
    ("seven", "period", -80), ("seven", "round", -30), ("seven", "A", -50),
    # Quotes sit high; pull them into what follows.
    ("quote", "round", -30), ("quote", "A", -50),
]

# Glyph-to-glyph exceptions (no class covers them).
EXCEPTIONS = [("f", "i", -20)]


def _root(font, name, depth=0):
    """The base letter a composite or alternate is built on."""
    g = font[name]
    if g.components and depth < 4:
        first = g.components[0].baseGlyph
        if first in font:
            return _root(font, first, depth + 1)
    return name.split(".")[0] if "." in name and not name.startswith(".") else name


def _expand(font, table):
    """Class name -> member list, extended with composites and alternates."""
    owner = {}
    for cls, members in table.items():
        for m in members:
            if m in font:
                owner[m] = cls
    out = {cls: [m for m in members if m in font] for cls, members in table.items()}
    for g in font:
        if g.name in owner or g.name.endswith((".numr", ".dnom", ".sups", ".subs", ".case", ".tnum")):
            continue
        root = _root(font, g.name)
        if root in owner:
            out[owner[root]].append(g.name)
    return {k: v for k, v in out.items() if v}


def apply(font):
    """Install groups and pairs into a UFO, replacing any earlier kerning. Returns the pair count."""
    k1, k2 = _expand(font, KERN1), _expand(font, KERN2)
    groups = {n: m for n, m in font.groups.items() if not n.startswith("public.kern")}
    for cls, members in k1.items():
        groups[f"public.kern1.{cls}"] = members
    for cls, members in k2.items():
        groups[f"public.kern2.{cls}"] = members
    font.groups = groups
    kerning = {}
    for a, b, v in PAIRS:
        if a in k1 and b in k2:
            kerning[(f"public.kern1.{a}", f"public.kern2.{b}")] = v
    for a, b, v in EXCEPTIONS:
        if a in font and b in font:
            kerning[(a, b)] = v
    font.kerning = kerning
    return len(kerning)
