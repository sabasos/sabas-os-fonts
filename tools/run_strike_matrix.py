"""
Run the full M2 strike matrix: 4 weights × 7 ppem sizes.
Spec §6.2: UI sizes 11,12,13,14,16,18,20 × Regular/Medium/SemiBold/Bold.
Strikes are embedded into the shipped static TTF in-place (§6.2: no separate -strikes file).
"""
import subprocess, sys
from pathlib import Path

# §6.2: 4 weights required — Regular, Medium, SemiBold, Bold
STRIKE_WEIGHTS = [
    ("Regular",  400, "fonts/SabasUI-Regular.ttf"),
    ("Medium",   500, "fonts/SabasUI-Medium.ttf"),
    ("SemiBold", 600, "fonts/SabasUI-SemiBold.ttf"),
    ("Bold",     700, "fonts/SabasUI-Bold.ttf"),
]

PPEM_SIZES = [11, 12, 13, 14, 16, 18, 20]

PIPELINE = "tools/strike/pipeline.py"
GOLDEN   = "tests/raster/sabas-ui"
STRIKES  = "sources/strikes"


def run_weight(stylename, wght, font_file):
    golden = f"{GOLDEN}/wght{wght}"
    Path(golden).mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, PIPELINE,
        "--font",         font_file,
        "--family",       "sabas-ui",
        "--weight",       str(wght),
        "--ppem",         *[str(p) for p in PPEM_SIZES],
        "--work-dir",     f"/tmp/sabas-strikes-{wght}",
        "--strikes-root", STRIKES,
        "--golden",       golden,
        "--out",          font_file,   # §6.2: overwrite in-place, no separate file
    ]
    print(f"\n{'='*60}")
    print(f"  {stylename} (wght={wght})  →  {font_file} (in-place)")
    print(f"{'='*60}")
    r = subprocess.run(cmd, capture_output=False)
    return r.returncode


def main():
    failures = []
    for stylename, wght, font_file in STRIKE_WEIGHTS:
        if not Path(font_file).exists():
            print(f"FAIL {font_file} — not found (build statics first)")
            failures.append(stylename)
            continue
        rc = run_weight(stylename, wght, font_file)
        if rc != 0:
            failures.append(stylename)

    print("\n" + "="*60)
    if failures:
        print(f"FAILED: {failures}")
        sys.exit(1)
    else:
        print("All 4 strike weights completed (§6.2).")


if __name__ == "__main__":
    main()
