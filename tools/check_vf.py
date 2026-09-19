"""
Instantiate SabasUI-VF.ttf across its axes and assert the invariants the design
space is built to keep:

  wght  x-height and cap height stay put; advances grow with weight
  wdth  advances grow with width; cap height stays put
  opsz  lowercase x-height follows the size (580 at 10, 540 at 16, 460 at 32);
        cap height stays put
  GRAD  advances do not change at all
  slnt  cap height stays put; the ink leans right
"""
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

DEFAULT = dict(wght=400, wdth=100, opsz=16, GRAD=0, slnt=0)
TOL = 2


def measure(vf_path, **coords):
    loc = dict(DEFAULT, **coords)
    f = instantiateVariableFont(TTFont(vf_path), loc, inplace=False)
    gs = f.getGlyphSet()

    def bounds(name):
        p = BoundsPen(gs)
        gs[name].draw(p)
        return p.bounds

    return {
        "x_top": bounds("x")[3],
        "H_top": bounds("H")[3],
        "p_bottom": bounds("p")[1],
        "n_adv": f["hmtx"]["n"][0],
        "H_xmax": bounds("H")[2],
    }


def main(vf_path="fonts/SabasUI-VF.ttf"):
    failures = []

    def check(ok, what):
        print(("ok   " if ok else "FAIL ") + what)
        if not ok:
            failures.append(what)

    weights = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    rows = {w: measure(vf_path, wght=w) for w in weights}
    check(all(abs(r["x_top"] - 540) <= TOL for r in rows.values()), "wght: x-height 540 at every weight")
    check(all(abs(r["H_top"] - 720) <= TOL for r in rows.values()), "wght: cap height 720 at every weight")
    check(all(abs(r["p_bottom"] + 205) <= 12 for r in rows.values()), "wght: descender within 12 of -205")
    adv = [rows[w]["n_adv"] for w in weights]
    check(all(b > a for a, b in zip(adv, adv[1:])), f"wght: n advance strictly increasing {adv}")

    wd = {w: measure(vf_path, wdth=w) for w in (75, 100, 125)}
    check(wd[75]["n_adv"] < wd[100]["n_adv"] < wd[125]["n_adv"], f"wdth: n advance {[wd[w]['n_adv'] for w in wd]}")
    check(all(abs(r["H_top"] - 720) <= TOL for r in wd.values()), "wdth: cap height 720")

    op = {s: measure(vf_path, opsz=s) for s in (10, 16, 32)}
    check([op[s]["x_top"] for s in (10, 16, 32)] == [580, 540, 460], f"opsz: x-heights {[op[s]['x_top'] for s in (10, 16, 32)]}")
    check(all(abs(r["H_top"] - 720) <= TOL for r in op.values()), "opsz: cap height 720")
    check(op[10]["n_adv"] > op[16]["n_adv"] > op[32]["n_adv"], f"opsz: tracking loosens as size falls {[op[s]['n_adv'] for s in (10, 16, 32)]}")

    gr = {g: measure(vf_path, GRAD=g) for g in (-200, 0, 150)}
    check(len({r["n_adv"] for r in gr.values()}) == 1, f"GRAD: advance-neutral {[gr[g]['n_adv'] for g in gr]}")

    sl = measure(vf_path, slnt=-10)
    check(abs(sl["H_top"] - 720) <= TOL and sl["H_xmax"] > rows[400]["H_xmax"] + 100, "slnt: leans right, cap height unchanged")

    corner = measure(vf_path, wght=1000, wdth=125, opsz=10, GRAD=150, slnt=-10)
    check(abs(corner["H_top"] - 720) <= 6 and corner["n_adv"] > 0, f"corner (Ultra, Extended, Caption, GradMax, Oblique) sane: {corner}")

    print("all variable-font checks pass" if not failures else f"{len(failures)} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
