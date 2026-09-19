#!/usr/bin/env bash
# build-mono.sh - compile Sabas Mono: designspace -> variable font, then static instances.
# Run after tools/build_mono_ufo.py and tools/build_mono_masters.py.
set -euo pipefail
cd "$(cd "$(dirname "$0")" && pwd)"
source .venv/bin/activate
mkdir -p fonts

if command -v fontc &>/dev/null; then
  fontc sources/sabas-mono/SabasM.designspace -o fonts/SabasM-VF.ttf
else
  fontmake -m sources/sabas-mono/SabasM.designspace -o variable --output-path fonts/SabasM-VF.ttf
fi

python - <<'PYEOF'
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont, OverlapMode
vf = fonts_path = 'fonts/SabasM-VF.ttf'
axes = {a.axisTag: a for a in TTFont(vf)['fvar'].axes}
for inst in TTFont(vf)['fvar'].instances:
    font = TTFont(vf)
    name = font['name'].getDebugName(inst.subfamilyNameID)
    loc = dict(inst.coordinates)
    if any(abs(loc[t] - axes[t].defaultValue) > 1e-6 for t in loc if t != 'wght'):
        continue   # statics are the upright weights; slant and grade live in the VF
    out = instantiateVariableFont(font, loc, inplace=True, overlap=OverlapMode.REMOVE)
    path = f"fonts/SabasM-{name.replace(' ', '')}.ttf"
    out.save(path)
    print(f'  {name} -> {path}')
PYEOF

python tools/post_build_mono.py
