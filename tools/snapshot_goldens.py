"""Snapshot golden PNGs for all strike weights from their stage4 output."""
import shutil, os
from pathlib import Path

GOLDEN_GLYPHS = ["H", "a", "n", "o"]
PPEM_SIZES    = [11, 12, 13, 14, 16, 18, 20]
GOLDEN_ROOT   = Path("tests/raster/sabas-ui")

WEIGHTS = [
    (400, "/tmp/sabas-strikes-400/stage4"),
    (600, "/tmp/sabas-strikes-600/stage4"),
    (700, "/tmp/sabas-strikes-700/stage4"),
]

for wght, stage4 in WEIGHTS:
    for ppem in PPEM_SIZES:
        gdir = GOLDEN_ROOT / f"wght{wght}" / f"ppem{ppem:02d}"
        gdir.mkdir(parents=True, exist_ok=True)
        for glyph in GOLDEN_GLYPHS:
            src = Path(stage4) / f"ppem{ppem:02d}" / f"{glyph}.png"
            if not src.exists():
                src = Path(stage4) / f"ppem{ppem}" / f"{glyph}.png"
            dst = gdir / f"{glyph}.png"
            if src.exists():
                shutil.copy2(src, dst)
                print(f"  golden wght{wght}/ppem{ppem}/{glyph}.png")
            else:
                print(f"  MISSING {src}")

print("Done.")
