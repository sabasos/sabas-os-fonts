"""
CI runner — executes all gates in sequence.
Exit 0 = all gates passed. Exit 1 = one or more failed.

Gates:
  Strike matrix        §6.2: 4 weights × 7 ppem, strikes in shipped TTFs
  Static ≡ Variable    §5.2: cmap/glyph-count match + parametric gvar delta check
  fontc divergence     §12.1: fontc required (hard fail if absent)
"""
import subprocess, sys
from pathlib import Path

GATES = [
    # (label, script, extra_args)
    ("Strike matrix",          "tools/run_strike_matrix.py",      []),
    ("Strike conformance §6.4",  "tools/ci_strike_conformance.py",  []),
    ("Patch format",            "tools/ci_patch_format.py",        []),
    ("Static ≡ Variable",       "tools/ci_static_vs_variable.py",  []),
    ("fontc divergence",        "tools/ci_fontc_divergence.py",    []),
]


def run_gate(label, script, extra_args):
    print(f"\n{'─'*60}")
    print(f"  {label}")
    print(f"{'─'*60}")
    r = subprocess.run([sys.executable, script] + extra_args)
    return r.returncode == 0


def main():
    results = []
    for label, script, extra in GATES:
        if not Path(script).exists():
            print(f"SKIP {label}: {script} not found")
            continue
        ok = run_gate(label, script, extra)
        results.append((label, ok))

    print(f"\n{'='*60}")
    print("  CI SUMMARY")
    print(f"{'='*60}")
    all_ok = True
    for label, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}  {label}")
        if not ok:
            all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
