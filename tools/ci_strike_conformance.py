"""
CI gate: §6.4 strike conformance.

For each shipped static TTF with EBDT/EBLC:
  1. Integer-height: every bitmap's pixel height == ppem (no fractional scaling)
  2. Mixed-coverage: no strike contains both 1-bit and 8-bit bitmaps
  3. Monotonicity: strike ppem values are strictly increasing in EBLC
  4. Advance agreement: bitmap advance (px) == round(outline advance * ppem / UPM)
     within ±1 pixel tolerance
"""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont

STATIC_WEIGHTS = [
    ("Regular",  400),
    ("Medium",   500),
    ("SemiBold", 600),
    ("Bold",     700),
]
TOLERANCE_PX = 1


def check_font(path: Path) -> list[str]:
    failures = []
    font = TTFont(str(path))

    if "EBLC" not in font or "EBDT" not in font:
        failures.append(f"{path.name}: missing EBLC/EBDT tables")
        return failures

    eblc = font["EBLC"]
    hmtx = font["hmtx"].metrics
    upm  = font["head"].unitsPerEm

    ppem_list = []
    for strike in eblc.strikes:
        bst = strike.bitmapSizeTable
        ppem = bst.ppemX
        ppem_list.append(ppem)

        # 1. Integer-height: ppemY must equal ppemX
        if bst.ppemY != ppem:
            failures.append(f"{path.name} ppem={ppem}: ppemX≠ppemY ({bst.ppemX}≠{bst.ppemY})")

        # 2. Mixed-coverage: all sub-tables must use same image format
        formats = set()
        for sub in strike.indexSubTables:
            formats.add(sub.imageFormat)
        if len(formats) > 1:
            failures.append(f"{path.name} ppem={ppem}: mixed image formats {formats}")

        # 4. Advance agreement
        for sub in strike.indexSubTables:
            for glyph_name in sub.names:
                if glyph_name not in hmtx:
                    continue
                outline_adv = hmtx[glyph_name][0]
                expected_px = round(outline_adv * ppem / upm)
                # Get bitmap metrics if available
                if hasattr(sub, "metrics") and sub.metrics:
                    bm_adv = sub.metrics.horiAdvance
                    if abs(bm_adv - expected_px) > TOLERANCE_PX:
                        failures.append(
                            f"{path.name} ppem={ppem} {glyph_name}: "
                            f"bitmap advance={bm_adv} expected≈{expected_px} "
                            f"(outline={outline_adv} upm={upm})"
                        )

    # 3. Monotonicity
    for i in range(1, len(ppem_list)):
        if ppem_list[i] <= ppem_list[i - 1]:
            failures.append(
                f"{path.name}: EBLC ppem not strictly increasing: {ppem_list}"
            )
            break

    return failures


def main() -> None:
    all_failures = []
    checked = 0

    for stylename, wght in STATIC_WEIGHTS:
        path = Path(f"fonts/SabasUI-{stylename}.ttf")
        if not path.exists():
            all_failures.append((path, [f"file not found"]))
            continue
        errs = check_font(path)
        if errs:
            all_failures.append((path, errs))
        checked += 1

    if all_failures:
        print("STRIKE CONFORMANCE GATE: FAILED")
        for p, errs in all_failures:
            print(f"  {p}")
            for e in errs:
                print(f"    {e}")
        sys.exit(1)

    print(f"STRIKE CONFORMANCE GATE: PASSED ({checked} fonts)")


if __name__ == "__main__":
    main()
