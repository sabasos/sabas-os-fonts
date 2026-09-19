"""
Run every Sabas font QA gate and fail if any is red.

  tools/run_qa.py           the full shipped set (every static and both variable fonts)
  tools/run_qa.py --quick   Regular and the variable font of each family

Runs, in order: master compatibility, shaping goldens (UI and Mono), the Mono grid
invariants, the variable-font invariants, the kerning collision scan, then fontbakery's
universal profile on every font. fontbakery checks listed in docs/waivers.md are
excluded, and an expired waiver is itself a failure.
"""
import datetime
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
UI = ["Thin", "Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold", "Black", "Ultra"]
MONO = ["Light", "Regular", "Medium", "SemiBold", "Bold", "ExtraBold"]


# Checks that ask a third-party website. They error when the service changes and say nothing
# about the font, so a gate that must give the same answer offline leaves them out.
NETWORK_CHECKS = ["fontdata_namecheck"]


def waivers():
    """(excluded check ids, expired waiver ids) from docs/waivers.md."""
    ids, expired = [], []
    today = datetime.date.today()
    for line in (ROOT / "docs" / "waivers.md").read_text().split("## Resolved")[0].splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and re.match(r"W-\d+", cells[0]):
            ids += re.findall(r"`([^`]+)`", cells[1])
            if datetime.date.fromisoformat(cells[3]) < today:
                expired.append(cells[0])
    return ids, expired


def step(label, cmd, must_contain=None):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = r.stdout + r.stderr
    ok = r.returncode == 0 and (must_contain is None or must_contain in out)
    print(("ok   " if ok else "FAIL ") + label)
    if not ok:
        print("     " + "\n     ".join(out.strip().splitlines()[-8:]))
    return ok


def fontbakery(path, excluded):
    cmd = [PY, "-m", "fontbakery", "check-universal", "-l", "WARN", "--no-progress"]
    for c in excluded:
        cmd += ["-x", c]
    r = subprocess.run(cmd + [str(path)], cwd=ROOT, capture_output=True, text=True)
    out = r.stdout + r.stderr
    counts = {k: int(v) for k, v in re.findall(r"^\s+(ERROR|FATAL|FAIL):\s+(\d+)", out, re.M)}
    bad = sum(counts.get(k, 0) for k in ("ERROR", "FATAL", "FAIL"))
    failing = re.findall(r"^ >> (\S+)\n(?:.*\n)*?\s+Result: (?:FAIL|ERROR|FATAL)", out, re.M)
    print(("ok   " if not bad else "FAIL ") + f"fontbakery {path.name}" + (f"  {failing}" if bad else ""))
    return not bad


def main():
    quick = "--quick" in sys.argv
    ui = ["Regular"] if quick else UI
    mono = ["Regular"] if quick else MONO
    excluded, expired = waivers()
    excluded = excluded + NETWORK_CHECKS
    results = []
    if expired:
        print(f"FAIL expired waivers: {', '.join(expired)} (renew or resolve in docs/waivers.md)")
        results.append(False)
    results += [
        step("UI masters compatible", [PY, "tools/check_masters.py"], "compatible"),
        step("Mono masters compatible", [PY, "tools/check_masters.py", "sources/sabas-mono/SabasM-*.ufo"], "compatible"),
        step("UI shaping goldens (Regular)", [PY, "tools/test_features.py", "fonts/SabasUI-Regular.ttf"], "all feature cases pass"),
        step("UI shaping goldens (VF)", [PY, "tools/test_features.py", "fonts/SabasUI-VF.ttf"], "all feature cases pass"),
        step("Mono shaping goldens", [PY, "tools/test_mono_features.py"], "all mono feature cases pass"),
        step("Mono grid invariants", [PY, "tools/check_mono.py"], "all mono checks pass"),
        step("Variable-font invariants", [PY, "tools/check_vf.py"], "all variable-font checks pass"),
        step("Kerning collisions", [PY, "tools/check_kerning.py", "fonts/SabasUI-Regular.ttf", "16"], "0 closer"),
    ]
    for w in ui:
        results.append(fontbakery(ROOT / "fonts" / f"SabasUI-{w}.ttf", excluded))
    results.append(fontbakery(ROOT / "fonts" / "SabasUI-VF.ttf", excluded))
    for w in mono:
        results.append(fontbakery(ROOT / "fonts" / f"SabasM-{w}.ttf", excluded))
    results.append(fontbakery(ROOT / "fonts" / "SabasM-VF.ttf", excluded))
    print("\nQA PASSED" if all(results) else f"\nQA FAILED ({results.count(False)} red)")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
