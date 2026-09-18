#!/usr/bin/env bash
# build.sh — compile Sabas UI designspace → TTF statics + VF, then embed strikes.
# §4.1: statics must be quadratic TTF (glyf table), not CFF.
# §6.2: strikes must be embedded in the shipped static instances.
# §12.1: fontc is the shipped artefact; fontmake is the referee only.
# Run from sabas-fonts/ with the venv active.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
VENV="$SCRIPT_DIR/.venv"
# shellcheck source=/dev/null
source "$VENV/bin/activate"

mkdir -p fonts

# ── §12.1: fontc is the shipped artefact; fontmake is the fallback referee ───
if command -v fontc &>/dev/null; then
  echo "=== Compiling VF with fontc (§12.1 shipped artefact) ==="
  fontc sources/sabas-ui/SabasUI.designspace -o fonts/

  echo ""
  echo "=== Generating TTF statics from VF (quadratic glyf, §4.1) ==="
  fontmake -i \
           --ttf-curves \
           -m fonts/SabasUI-VF.ttf \
           --output-dir fonts/ \
           --verbose
else
  echo "WARNING: fontc not found — falling back to fontmake only (§12.1 not satisfied)."
  echo "Install fontc: cargo install fontc"
  echo ""
  echo "=== Compiling VF + statics with fontmake (fallback) ==="
  fontmake -m sources/sabas-ui/SabasUI.designspace \
           -o variable \
           --output-path fonts/SabasUI-VF.ttf \
           --verbose
  fontmake -i \
           --ttf-curves \
           -m fonts/SabasUI-VF.ttf \
           --output-dir fonts/ \
           --verbose
fi

echo ""
echo "=== Embedding strikes into shipped statics (§6.2) ==="
for WEIGHT in Regular Medium SemiBold Bold; do
  TTF="fonts/SabasUI-${WEIGHT}.ttf"
  if [[ ! -f "$TTF" ]]; then
    echo "  SKIP $TTF — not found"
    continue
  fi
  WGHT=400
  case "$WEIGHT" in
    Medium)   WGHT=500 ;;
    SemiBold) WGHT=600 ;;
    Bold)     WGHT=700 ;;
  esac
  echo "  Embedding strikes → $TTF (wght=$WGHT)"
  python tools/strike/pipeline.py \
    --font    "$TTF" \
    --family  sabas-ui \
    --weight  "$WGHT" \
    --ppem    11 12 13 14 16 18 20 \
    --glyphs  space H a n o \
    --work-dir "/tmp/sabas-strikes-${WGHT}" \
    --strikes-root sources/strikes \
    --golden  "tests/raster/sabas-ui" \
    --out     "$TTF"   # overwrite in-place: strikes live in the shipped file
done

echo ""
echo "=== Post-build fixup: hhea / gasp / STAT AxisValues ==="
python tools/post_build_fixup.py

echo ""
echo "Done. Shipped artefacts: fonts/SabasUI-{Regular,Medium,SemiBold,Bold}.ttf + SabasUI-VF.ttf"
