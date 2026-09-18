"""
Snapshot golden PNGs and generate identity patches for all strike weights
from their stage4 pipeline output.
"""
import os, hashlib, shutil, sys
from pathlib import Path
import png as _png

sys.path.insert(0, str(Path(__file__).parent / "strike"))
from stage4_patch import PatchFile, write_patch, _hash_raster as _hash_rows

GOLDEN_ROOT  = Path("tests/raster/sabas-ui")
STRIKES_ROOT = Path("sources/strikes/sabas-ui")
PPEM_SIZES   = [11, 12, 13, 14, 16, 18, 20]
GOLDEN_GLYPHS = ["H", "a", "n", "o"]
RASTER_ENV   = "freetype-2.13.3 target=light interp=40 darken=on compiler=fontc"

# Glyphs that get patches (hand-correction candidates from stage2 work queue)
PATCH_GLYPHS = ["H", "a", "n"]

WEIGHTS = [
    (400, "/tmp/sabas-strikes-400"),
    (600, "/tmp/sabas-strikes-600"),
    (700, "/tmp/sabas-strikes-700"),
]


def _load_rows(path: Path) -> tuple[int, int, list[list[int]]]:
    reader = _png.Reader(filename=str(path))
    w, h, rows_iter, _ = reader.read()
    return w, h, [list(r) for r in rows_iter]


def snapshot_goldens(wght, work_dir):
    stage4 = Path(work_dir) / "stage4"
    for ppem in PPEM_SIZES:
        gdir = GOLDEN_ROOT / f"wght{wght}" / f"ppem{ppem:02d}"
        gdir.mkdir(parents=True, exist_ok=True)
        for glyph in GOLDEN_GLYPHS:
            src = stage4 / f"ppem{ppem:02d}" / f"{glyph}.png"
            if not src.exists():
                src = stage4 / f"ppem{ppem}" / f"{glyph}.png"
            dst = gdir / f"{glyph}.png"
            if src.exists():
                shutil.copy2(src, dst)


def write_patches(wght, work_dir):
    """Write patches using canonical write_patch; skip glyphs with zero edits."""
    stage2 = Path(work_dir) / "stage2"
    for ppem in PPEM_SIZES:
        patch_dir = STRIKES_ROOT / f"wght{wght}" / f"ppem{ppem:02d}"
        for glyph in PATCH_GLYPHS:
            src = stage2 / f"ppem{ppem:02d}" / f"{glyph}.png"
            if not src.exists():
                src = stage2 / f"ppem{ppem}" / f"{glyph}.png"
            if not src.exists():
                continue
            w, h, rows = _load_rows(src)
            baseline = _hash_rows(rows)
            pf = PatchFile(
                format=1,
                family="sabas-ui",
                glyph=glyph,
                ppem=ppem,
                weight=wght,
                baseline=baseline,
                raster_env=RASTER_ENV,
                bbox=(0, 0, w, h),
                advance=w,
                edits=[],
            )
            # §patch-format: suppress zero-edit patches — no hand correction needed
            if not pf.edits:
                continue
            patch_dir.mkdir(parents=True, exist_ok=True)
            write_patch(pf, rows, patch_dir / f"{glyph}.patch")


def main():
    for wght, work_dir in WEIGHTS:
        print(f"wght={wght}...")
        snapshot_goldens(wght, work_dir)
        write_patches(wght, work_dir)

    # Count results
    goldens = list(GOLDEN_ROOT.rglob("*.png"))
    patches = list(STRIKES_ROOT.rglob("*.patch"))
    print(f"Golden PNGs: {len(goldens)}")
    print(f"Patches:     {len(patches)}")
    print("Done.")


if __name__ == "__main__":
    main()
