"""
CI gate: fontc/fontmake divergence tolerance.
Spec §9: "CI fails on an expired tolerance" — tolerance expires after 90 days
or the next fontc minor version, whichever comes first.

Checks:
1. fontc is available and its version is recorded
2. Both fontc and fontmake can compile the designspace
3. Cmap and glyph count match between outputs
4. Advance widths agree within TOLERANCE_ADVANCE units
5. Tolerance record is not expired (>90 days old)
"""
import sys, subprocess, json, datetime
from pathlib import Path
from fontTools.ttLib import TTFont

DS_PATH      = Path("sources/sabas-ui/SabasUI.designspace")
RECORD_PATH  = Path("tools/ci_fontc_tolerance.json")
TOLERANCE_ADVANCE = 4
TOLERANCE_DAYS    = 90


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def get_fontc_version():
    try:
        rc, out = run(["fontc", "--version"])
    except FileNotFoundError:
        return None
    if rc != 0:
        return None
    return out.strip().split()[-1]


def compile_fontmake(out_path):
    rc, out = run([
        "fontmake", "-m", str(DS_PATH), "-o", "variable",
        "--output-path", str(out_path),
    ])
    return rc == 0, out


def compile_fontc(out_path):
    rc, out = run([
        "fontc", str(DS_PATH), "-o", str(out_path),
    ])
    return rc == 0, out


def compare_fonts(path_a, path_b, label_a, label_b):
    failures = []
    try:
        fa = TTFont(path_a)
        fb = TTFont(path_b)
    except Exception as e:
        return [f"Could not load fonts: {e}"]

    cmap_a = fa.getBestCmap() or {}
    cmap_b = fb.getBestCmap() or {}
    missing = set(cmap_a) - set(cmap_b)
    extra   = set(cmap_b) - set(cmap_a)
    if missing:
        failures.append(f"cmap in {label_a} not in {label_b}: {sorted(hex(u) for u in list(missing)[:5])}")
    if extra:
        failures.append(f"cmap in {label_b} not in {label_a}: {sorted(hex(u) for u in list(extra)[:5])}")

    ga, gb = len(fa.getGlyphOrder()), len(fb.getGlyphOrder())
    if ga != gb:
        failures.append(f"glyph count {label_a}={ga} {label_b}={gb}")

    hmtx_a = fa["hmtx"].metrics
    hmtx_b = fb["hmtx"].metrics
    mismatches = []
    for gname in list(cmap_a.values())[:100]:
        if gname not in hmtx_a or gname not in hmtx_b:
            continue
        wa, wb = hmtx_a[gname][0], hmtx_b[gname][0]
        if abs(wa - wb) > TOLERANCE_ADVANCE:
            mismatches.append(f"{gname}: {label_a}={wa} {label_b}={wb}")
    if mismatches:
        failures.append(f"advance mismatch ({len(mismatches)}): {mismatches[:3]}")

    return failures


def check_expiry(fontc_version):
    if not RECORD_PATH.exists():
        return False, "No tolerance record found — run with --update to create one"
    record = json.loads(RECORD_PATH.read_text())
    recorded_date = datetime.date.fromisoformat(record["date"])
    recorded_ver  = record["fontc_version"]
    age = (datetime.date.today() - recorded_date).days
    if age > TOLERANCE_DAYS:
        return False, f"Tolerance record expired: {age} days old (limit {TOLERANCE_DAYS})"
    if recorded_ver != fontc_version:
        return False, f"fontc version changed: recorded={recorded_ver} current={fontc_version}"
    return True, f"Tolerance record valid: {age} days old, fontc={fontc_version}"


def update_record(fontc_version):
    RECORD_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "date": datetime.date.today().isoformat(),
        "fontc_version": fontc_version,
        "updated_by": "ci_fontc_divergence.py --update",
    }
    RECORD_PATH.write_text(json.dumps(record, indent=2))
    print(f"Updated tolerance record: {RECORD_PATH}")


def main():
    update_mode = "--update" in sys.argv

    fontc_version = get_fontc_version()
    if fontc_version is None:
        print("FONTC GATE: FAILED — fontc not installed")
        print("  §12.1 requires fontc as the shipped compiler.")
        print("  Install: cargo install fontc  (or add to PATH)")
        sys.exit(1)

    print(f"fontc version: {fontc_version}")

    if update_mode:
        update_record(fontc_version)

    # Check expiry
    valid, msg = check_expiry(fontc_version)
    print(f"Expiry check: {msg}")
    if not valid and not update_mode:
        print("FONTC GATE: FAILED — tolerance expired, run with --update")
        sys.exit(1)

    # Compile with both tools
    fm_out = Path("/tmp/sabas-fontmake-ci.ttf")
    fc_out = Path("/tmp/sabas-fontc-ci.ttf")

    ok_fm, _ = compile_fontmake(fm_out)
    if not ok_fm:
        print("FONTC GATE: FAILED — fontmake compilation failed")
        sys.exit(1)

    ok_fc, fc_log = compile_fontc(fc_out)
    if not ok_fc:
        print(f"FONTC GATE: FAILED — fontc compilation failed:\n{fc_log[:500]}")
        sys.exit(1)

    failures = compare_fonts(fm_out, fc_out, "fontmake", "fontc")
    if failures:
        print("FONTC GATE: FAILED")
        for f in failures:
            print(f"  {f}")
        sys.exit(1)

    print("FONTC GATE: PASSED")


if __name__ == "__main__":
    main()
