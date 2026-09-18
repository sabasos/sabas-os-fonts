#!/usr/bin/env bash
# build.sh — compile Sabas UI designspace → TTF statics + VF, then embed strikes.
# §4.1: statics must be quadratic TTF (glyf table), not CFF.
# §6.2: strikes must be embedded in the shipped static instances.
# §12.1: fontc is the shipped artefact; fontmake is the referee only.
# Run from sabas-fonts/ with the venv active.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/../venv"
source "$VENV/bin/activate"

# ── §12.1: fontc required ────────────────────────────────────────────────────
if ! command -v fontc &>/dev/null; then
  echo "ERROR: fontc not installed. §12.1 requires fontc as the shipped compiler."
  echo "Install: cargo install fontc  (or add to PATH)"
  exit 1
fi

echo "=== Compiling VF with fontc (§12.1 shipped artefact) ==="
fontc sources/sabas-ui/SabasUI.designspace -o fonts/SabasUI-VF.ttf

echo ""
echo "=== Generating TTF statics from VF (quadratic glyf, §4.1) ==="
# fontmake used here only as referee to instantiate named instances from the VF
fontmake -m sources/sabas-ui/SabasUI.designspace \
         -o ttf \
         --output-dir fonts/ \
         --verbose

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
    --golden  "tests/raster/sabas-ui/wght${WGHT}" \
    --out     "$TTF"   # overwrite in-place: strikes live in the shipped file
done

echo ""
echo "=== Post-build fixup: hhea / gasp / STAT AxisValues ==="
python tools/post_build_fixup.py

echo ""
echo "Done. Shipped artefacts: fonts/SabasUI-{Regular,Medium,SemiBold,Bold}.ttf + SabasUI-VF.ttf"
