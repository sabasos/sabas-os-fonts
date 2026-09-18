"""
CI gate: hb-shape golden regression.

Runs hb-shape on a set of test strings and compares output against
committed golden files in tests/shaping/. Fails if any output differs.

To update goldens: python tools/ci_hbshape_goldens.py --update
"""
import sys, subprocess, json
from pathlib import Path

FONT      = Path("fonts/SabasUI-Regular.ttf")
GOLDEN_DIR = Path("tests/shaping")

# (test_id, text, features, script, language)
TEST_CASES = [
    ("latin_basic",    "Hello World",  "",          "latn", "ENG"),
    ("kern_AV",        "AV VA",        "",          "latn", "ENG"),
    ("vietnamese",     "Tiếng Việt",   "",          "latn", "VIE"),
    ("romanian_locl",  "șțȘȚ",         "locl",      "latn", "ROM"),
    ("ligatures_ss01", "->  =>  !=",   "ss01",      "latn", "ENG"),
    ("marks_stack",    "ẫẵ",           "",          "latn", "VIE"),
]


def run_hbshape(text: str, features: str, script: str, language: str) -> str:
    cmd = [
        "hb-shape", str(FONT),
        "--text", text,
        "--script", script,
        "--language", language,
        "--output-format", "json",
    ]
    if features:
        cmd += ["--features", features]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"hb-shape failed: {r.stderr[:200]}")
    return r.stdout.strip()


def main() -> None:
    update = "--update" in sys.argv
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

    if not FONT.exists():
        print(f"HBSHAPE GATE: FAILED — {FONT} not found")
        sys.exit(1)

    failures = []
    for test_id, text, features, script, language in TEST_CASES:
        golden_path = GOLDEN_DIR / f"{test_id}.json"
        try:
            actual = run_hbshape(text, features, script, language)
        except RuntimeError as e:
            failures.append(f"{test_id}: {e}")
            continue

        if update:
            golden_path.write_text(actual + "\n", encoding="utf-8")
            print(f"  Updated: {golden_path}")
            continue

        if not golden_path.exists():
            failures.append(f"{test_id}: golden missing — run with --update to create")
            continue

        expected = golden_path.read_text(encoding="utf-8").strip()
        if actual != expected:
            failures.append(f"{test_id}: output differs from golden {golden_path}")

    if update:
        print(f"HBSHAPE GATE: goldens updated ({len(TEST_CASES)} cases)")
        return

    if failures:
        print("HBSHAPE GATE: FAILED")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)

    print(f"HBSHAPE GATE: PASSED ({len(TEST_CASES)} cases)")


if __name__ == "__main__":
    main()
