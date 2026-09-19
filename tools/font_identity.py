"""
The identity a shipped Sabas font carries: names, version, license and credits.

Static instances are cut from the variable font, which names every one of them after
its default (Regular). This gives each its own family and style, links Regular and
Bold as a RIBBI pair, and writes the license and credit records that a distributed
font needs. The variable font gets the same credits and its default names.
"""
from pathlib import Path

from fontTools.ttLib import TTFont

VERSION = 0.900
VENDOR_ID = "SBAS"
PROJECT_URL = "https://github.com/sabas-fonts/sabas"
LICENSE_URL = "https://openfontlicense.org"
LICENSE_TEXT = ("This Font Software is licensed under the SIL Open Font License, Version 1.1. "
                "This license is available with a FAQ at: https://openfontlicense.org")

WEIGHT_NAMES = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium",
                600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black", 1000: "Ultra"}

DESCRIPTIONS = {
    "Sabas UI": ("The interface typeface of Sabas OS: a neo-grotesque with humanist apertures, "
                 "designed for labels, menus and controls at 11 to 20 px on 1x displays."),
    "Sabas Mono": ("The monospaced typeface of Sabas OS for terminals and editors: a fixed "
                   "600-unit grid, serifed i j l r I 1, a dotted zero and texture healing."),
}


def _copyright(root=Path(__file__).resolve().parent.parent):
    return (root / "OFL.txt").read_text().splitlines()[0].strip()


def _set(name, string, name_id):
    name.removeNames(nameID=name_id)
    name.setName(string, name_id, 3, 1, 0x409)


def apply_identity(font: TTFont) -> None:
    name = font["name"]
    family = name.getDebugName(16) or name.getDebugName(1)
    static = "fvar" not in font
    weight = font["OS/2"].usWeightClass
    style = WEIGHT_NAMES.get(weight, "Regular") if static else "Regular"
    ribbi = style in ("Regular", "Bold")
    compact = family.replace(" ", "")
    ps_name = f"{compact}-{style.replace(' ', '')}"

    if ribbi:
        _set(name, family, 1)
        _set(name, style, 2)
        name.removeNames(nameID=16)
        name.removeNames(nameID=17)
    else:
        _set(name, f"{family} {style}", 1)
        _set(name, "Regular", 2)
        _set(name, family, 16)
        _set(name, style, 17)
    full = f"{family} {style}"
    _set(name, full, 4)
    _set(name, ps_name, 6)
    _set(name, f"{VERSION:.3f};{VENDOR_ID};{ps_name}", 3)
    _set(name, f"Version {VERSION:.3f}", 5)
    _set(name, _copyright(), 0)
    _set(name, "Sabas Project Authors", 8)
    _set(name, "Sabas Project Authors", 9)
    _set(name, DESCRIPTIONS.get(family, ""), 10)
    _set(name, PROJECT_URL, 11)
    _set(name, PROJECT_URL, 12)
    _set(name, LICENSE_TEXT, 13)
    _set(name, LICENSE_URL, 14)
    font["head"].fontRevision = VERSION
