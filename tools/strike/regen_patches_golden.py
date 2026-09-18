"""Regenerate patches and golden PNGs from current stage1/stage2 output."""
import os, hashlib, shutil
from PIL import Image

STRIKES = "sources/strikes/sabas-ui"
GOLDEN  = "tests/raster/sabas-ui"
STAGE1  = "/tmp/sabas-strikes/stage1"
STAGE2  = "/tmp/sabas-strikes/stage2"

PATCH_GLYPHS  = {11: ["H", "a"], 13: ["H", "a", "n"], 16: ["H", "n"]}
GOLDEN_GLYPHS = {11: ["H", "a", "n", "o"], 13: ["H", "a", "n", "o"], 16: ["H", "a", "n", "o"]}

RASTER_ENV = "freetype-2.13.3 target=light interp=40 darken=on"


def _hash_raster(path):
    import hashlib
    img = Image.open(path)
    px = list(img.getdata())
    w, h = img.size
    hh = hashlib.sha256()
    for y in range(h):
        hh.update(bytes(px[y*w:(y+1)*w]))
    return "sha256:" + hh.hexdigest()[:16]


def regen_patches():
    for ppem, glyphs in PATCH_GLYPHS.items():
        patch_dir = f"{STRIKES}/wght400/ppem{ppem}"
        os.makedirs(patch_dir, exist_ok=True)
        for glyph in glyphs:
            src = f"{STAGE2}/ppem{ppem}/{glyph}.png"
            if not os.path.exists(src):
                print(f"  MISSING stage2: {src}")
                continue
            img = Image.open(src)
            w, h = img.size
            baseline = _hash_raster(src)
            # bbox: xMin=0 yMin=0 xMax=w yMax=h (pixel coords)
            patch_path = f"{patch_dir}/{glyph}.patch"
            with open(patch_path, "w") as f:
                f.write(f"format 1\n")
                f.write(f"family      sabas-ui\n")
                f.write(f"glyph       {glyph}\n")
                f.write(f"ppem        {ppem}\n")
                f.write(f"weight      400\n")
                f.write(f"baseline    {baseline}\n")
                f.write(f"raster-env  {RASTER_ENV}\n")
                f.write(f"bbox        0 0 {w} {h}\n")
                f.write(f"advance     {w}\n")
                f.write(f"\n")
                f.write(f"# x  y   from ->  to      8-bit coverage\n")
            print(f"  patch: {patch_path}")


def regen_golden():
    stage4 = "/tmp/sabas-strikes/stage4"
    for ppem, glyphs in GOLDEN_GLYPHS.items():
        gdir = f"{GOLDEN}/ppem{ppem:02d}"
        os.makedirs(gdir, exist_ok=True)
        for glyph in glyphs:
            # prefer stage4 (post-patch), fall back to stage1
            src = f"{stage4}/ppem{ppem:02d}/{glyph}.png"
            if not os.path.exists(src):
                src = f"{STAGE1}/ppem{ppem}/{glyph}.png"
            dst = f"{gdir}/{glyph}.png"
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f"  golden: {dst}")
            else:
                print(f"  MISSING: {src}")


if __name__ == "__main__":
    print("=== Regenerating patches ===")
    regen_patches()
    print("=== Regenerating golden PNGs ===")
    regen_golden()
    print("Done.")
