"""
CI gate: patch format validator.

Checks every .patch file in sources/strikes/:
  - Required header fields present (format, family, glyph, ppem, weight,
    baseline, raster-env, bbox, advance)
  - baseline uses full 64-char sha256 hex (not truncated 16-char)
  - raster-env contains compiler= field
  - Zero-edit patches are rejected (they should not be committed)
  - preview block present when edits exist
"""
import sys, re
from pathlib import Path

STRIKES_ROOT = Path("sources/strikes")
REQUIRED_FIELDS = {"format", "family", "glyph", "ppem", "weight",
                   "baseline", "raster-env", "bbox", "advance"}
BASELINE_RE = re.compile(r"^(sha256|blake3):[0-9a-f]{64}$")
EDIT_RE     = re.compile(r"^\s*\d+\s+\d+\s+\d+\s*->\s*\d+")


def validate_patch(path: Path) -> list[str]:
    failures = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    meta: dict[str, str] = {}
    edits = []
    has_preview = False

    for line in lines:
        if line.startswith("# --- preview"):
            has_preview = True
        if line.startswith("#") or not line.strip():
            continue
        if EDIT_RE.match(line):
            edits.append(line)
            continue
        if "  " in line or "\t" in line:
            key, _, val = line.partition("  ")
            meta[key.strip()] = val.strip()

    missing = REQUIRED_FIELDS - set(meta)
    if missing:
        failures.append(f"missing fields: {sorted(missing)}")

    baseline = meta.get("baseline", "")
    if not BASELINE_RE.match(baseline):
        failures.append(f"baseline must be sha256:<64hex> or blake3:<64hex>, got: {repr(baseline)}")

    raster_env = meta.get("raster-env", "")
    if "compiler=" not in raster_env:
        failures.append(f"raster-env missing compiler= field: {repr(raster_env)}")

    if not edits:
        failures.append("zero-edit patch must not be committed (delete or add real edits)")

    if edits and not has_preview:
        failures.append("patch has edits but no '# --- preview ---' block")

    return failures


def main() -> None:
    patches = sorted(STRIKES_ROOT.rglob("*.patch"))
    if not patches:
        print("PATCH FORMAT GATE: no patches found — nothing to validate")
        sys.exit(0)

    all_failures: list[tuple[Path, list[str]]] = []
    for p in patches:
        errs = validate_patch(p)
        if errs:
            all_failures.append((p, errs))

    if all_failures:
        print("PATCH FORMAT GATE: FAILED")
        for p, errs in all_failures:
            print(f"  {p}")
            for e in errs:
                print(f"    {e}")
        sys.exit(1)

    print(f"PATCH FORMAT GATE: PASSED ({len(patches)} patches)")


if __name__ == "__main__":
    main()
