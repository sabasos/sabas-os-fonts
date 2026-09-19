# Sabas UI Regular — handover

**Date:** 18 September 2026
**Scope:** the T1 (core Latin) glyph set of Sabas UI Regular, milestone M2.
**Design brief:** `SABAS-DESIGN-BRIEF.md` in this directory. This document does not
replace it — the brief is the spec, this is the state of the work against it.

---

## 1. Where things stand

`sources/sabas-ui/SabasUI-Regular.ufo` holds **369 glyphs and 19 kern pairs** and
compiles cleanly with no warnings to `fonts/SabasUI-Regular.otf`.

Everything is generated procedurally. **Do not edit `.glif` files** — they are
output, and the next generator run overwrites them. All glyph changes go in:

```
tools/strike/build_t1_glyphs.py
```

One command regenerates the UFO and compiles it:

```sh
cd sabas-os-fonts
.venv/bin/python tools/strike/build_t1_glyphs.py
# → Saved 369 glyphs to sources/sabas-ui/SabasUI-Regular.ufo
# → Compiled OK → fonts/SabasUI-Regular.otf
```

### Backups

| What | Where |
|---|---|
| `sources/` before any of this work | `sources.bak.20260917-220215/` (also at `/home/bs/Downloads/sabas-sources-backup-20260917/sources.bak.20260917-220215/`) |
| The UFO immediately before the first real generator run | `/tmp/SabasUI-Regular.ufo.before-run` (ephemeral — copy it somewhere durable if you want to keep it) |

---

## 2. What was fixed

### Letters and digits

| Glyph | Was | Now |
|---|---|---|
| `b d p q g` | bowls joined the stem with coincident edges, producing rasteriser seams | joins buried strictly inside the stem |
| `1` | the flag was a right triangle ending in a point, so it carried no weight at the tip and dropped out at text sizes | a blunt 70-unit wedge that ends *inside* the stem |
| `3` | the two bowls swept past each other and left a 7-unit spur at the waist | each bowl stops at its own extreme where its cut is vertical, and an explicit waist bar forms the blunt middle terminal |
| `5` | the bowl was only 5% wider than the top bar (Helvetica's is 33% wider), so the digit looked starved; a hairline crack at the stem junction | bowl enlarged to match `0`'s width; butt cap at the junction instead of an oblique cut |
| `k` | both arms started *inside* the stem 40 units apart, driving a white wedge into it with no junction mass | the leg springs off the arm at a vertex out at x=278; the junction covers 109 units of stem |
| `l` | the tail's inner edge ran back to the stem's *left* edge, eating the foot from below until the tail was a wisp | one centreline stroke: stem, a 110-unit turn, a level run to the tip |
| `t` | **no foot at all** — a bare cross, and `tt` read as a fence; crossbar straddled the x-height line | the stem turns right at y=110 and ends in a vertical cut; crossbar now hangs below x-height with its top *on* the line |
| `U` | **badly broken** — the bowl was a shallow 66-unit lens floating above the baseline with hairline cracks at both stems | one centreline from cap height, round the bottom and back up; exactly 88 units through both stems, no joins to crack |
| `J` | hand-traced hook that pinched to nothing where the inner edge came back | one centreline; even weight all the way round, with Helvetica's flat terminal at a third of the cap |

### Marks

| Glyph | Was | Now |
|---|---|---|
| `gravecomb` | **rose to the right — it was an acute.** `À` and `Á` were the same glyph | mirrored: high at the left, low at the right |
| `tildecomb` | **a single arch — it was a breve.** `Ã` and `Ă` were indistinguishable | a real wave, stroked so the crest and trough thin and the diagonal carries the weight |

### Symbols

| Glyph | Was | Now |
|---|---|---|
| `&` | an oval with two straight bars across it; read as a script `℘` | grotesque construction: closed loop, large bowl, thick diagonal, leg cut flat at both ends |
| `@` | the inner form was a dot — its counter was 120 units and closed up below 20 px | a legible `a`, counter 206 units, following Helvetica's 0.41-of-advance proportion |
| `%` | ring counters were 88 units across — a tenth of an em — so both rings filled in solid below 24 px and read as dots; the slash was a full stem thick | counters 144 units (Helvetica's 0.59 outer/inner ratio); slash cut to 0.59 of a stem |
| `*` | three identical rectangles plus three shapes whose corner arithmetic used `abs(int(sin))`, which is 0 or 1 — it drew a blob | a real five-pointed star, 145-unit arms, valley radius derived as `h / sin(36°)` |
| `<` `>` | arm ends were offset by `HSTEM` *horizontally* on a 34° arm, leaving only 42 units perpendicular — half a stem — so both were hairline and needle-pointed | even weight, blunt vertical cuts at both ends and the vertex |
| `(` `)` | terminals were 34 units against 88 at the middle, so both tapered to a hair | 62 at the tip, 88 at the middle (Helvetica's are 61 and 93) |
| `Tcedilla` `tcedilla` | **missing**, while their `S` partners were present | added |

### Build and feature-file bugs (none glyph-related; all would have blocked M3)

1. **`SabasUI-Regular.ufo/features.fea`** — the `include()` path had one `..` too
   many. ufo2ft hands feaLib a single include directory, the UFO's *parent*, and
   resolves every include against it — not against the file doing the including.
   The same correction was needed for the two `_shared` includes inside
   `sources/features/ui/features.fea`. **This UFO had never compiled.**
2. **Hand-written `mark`/`mkmk` blocks** in `features/ui/features.fea` declared
   `@MarkAbove` twice over the same glyphs — a hard "glyph already defined"
   error. Removed. ufo2ft writes both features itself from UFO anchors, and their
   placeholder `<anchor 0 0>` rules would have pinned every diacritic to the
   origin if they had compiled.
3. **`features/_shared/kern.fea` was silently discarding all your kerning.** It
   held 27 hand-written pairs and no `# Automatic Code` insertion marker, so
   ufo2ft decided the feature was hand-maintained and dropped `kerning.plist`
   wholesale in favour of that shorter list. The file is now the hook only. The
   two combinations the class table lacked — `L` before T/V/W/Y, and `f` before
   `i` — moved into `KERN_PAIRS` in the generator.
4. **`main()` called `fontmake` by bare name**, which is not on `PATH` — it lives
   in the venv. Now resolved from `sys.executable`'s directory.
5. **`_shared/mark_classes.fea`** listed nine combining marks (U+030D–U+0315)
   that T1 does not draw. A glyph class naming an absent glyph fails the whole
   compile, so they are commented out with a note to restore them as they are
   drawn.

---

## 3. What is pending

### Broken — will look wrong to a user

| Glyph | Problem |
|---|---|
| `ß` `germandbls` | wrong shape — reads as a `B` with a hooked top-left. Needs the eszett construction: straight left stem, curve right over the top, waist, lower bowl open at the bottom-left with a terminal pointing left. `uni1E9E` (capital ẞ) shares the code path. |
| `&` | reads correctly now, but **the leg joins awkwardly** — there is a notch at its top where it meets the diagonal, and the leg looks slightly detached. The bowl and diagonal both die inside the leg; the overlap needs widening or the leg's top cut lowering. |
| `ł` `lslash` | the bar sits wrong against the newly tailed `l`. The bar is positioned from `ink(font, "l")[0]`, and `l`'s ink bounds changed when the tail was added. |
| `{` `}` | too light. Lower priority than the parens were — they are legible, just thin. |
| `æ` | the join between `a` and `e` is not clean. |
| `ð` `eth` | low priority, but not right. |

### Polish — not broken, below the quality bar

- **`6` and `9`** are still hand-traced closed contours. Their weight wanders
  along the spine, and their terminals do not match the flat cut hanging at 0.74
  cap that the rest of the figures use. They should be rebuilt as centreline
  strokes, the same way `5` and `l` were.

### Brief-mandated items not yet done

- `hhea` ascender/descender/lineGap should be 800 / −200 / 200.
- `STAT` table `AxisValues` are not populated.
- The `fontc` cross-compiler gate does not hard-fail when the tool is absent, so
  it currently passes vacuously.
- Static instances compile to CFF; the brief calls for `glyf`/TTF.
- `ss01`/`ss02` are not wired, so `a.ss01` (and a future `l.ss02`) are
  unreachable.

### Downstream regeneration — **required before M3**

Only `SabasUI-Regular.ufo` has been regenerated. Everything derived from it is
now stale:

```
tools/strike/build_t2_glyphs.py
tools/strike/build_parametric_masters.py
tools/strike/build_weight_masters.py
tools/strike/build_medium_master.py
```

After those: rebuild the variable and static fonts, **re-snapshot the goldens**
(they will all differ — that is expected, not a regression), and regenerate the
strike patches.

---

## 4. How to look at what you changed

The inspection scripts are in `tools/strike/dev/`. Run all of them from
`sabas-fonts/` using the venv's Python.

```sh
# Fast preview: builds the font in memory to /tmp/spec.ttf without touching sources
.venv/bin/python tools/strike/dev/specimen.py

# Full specimen sheet, 96 px down to 12 px, from the compiled OTF
.venv/bin/python tools/strike/dev/render.py            # → /tmp/specimen.png
SABAS_FONT=/tmp/spec.ttf .venv/bin/python tools/strike/dev/render.py

# A few glyphs, large. Render at most 5-6 at a time (see the caveat below)
.venv/bin/python tools/strike/dev/big.py "Sabas &@%" 200 /tmp/out.png

# Pixel-level: crop and upscale with NEAREST so you see actual pixels
.venv/bin/python tools/strike/dev/crop.py /tmp/out.png /tmp/z.png X Y W H 3

# Measurement, not eyeballing: scanline ink runs every 20 units
.venv/bin/python tools/strike/dev/runs.py U J three

# Reference proportions from a real grotesque
.venv/bin/python tools/strike/dev/href.py ampersand germandbls six
```

`probe.py`, `scan.py` and `diag.py` are the older audit passes (winding, overlap,
oval consistency); they still run and are worth a sweep before a release.

> **Caveat that cost me real time:** a wide PNG gets downscaled when you view it,
> and the font then looks far lighter than it is. Judge weight from ≤6 glyphs per
> image, or from a NEAREST-upscaled crop. Never from the full specimen sheet.

---

## 5. Rules that govern this font's geometry

These are not style preferences. Each one is a failure that actually happened
here, and breaking them reintroduces it.

1. **Coincident edges are the enemy.** Two outlines sharing an edge exactly
   produce rasteriser seams, confuse the autohinter and break
   `booleanOperations`. Hence the deliberate small offsets (2, 4, 8 units) all
   over the generator, and cuts placed strictly *interior* to the shape that
   buries them.

2. **Tangency is nearly as bad as coincidence.** Curves that merely kiss give
   razor-thin regions and degenerate boolean input. Prefer a transversal
   crossing even at the cost of a 1–2 unit protrusion — 2 units is 0.048 px at
   24 px. (This is what forced `3`'s redesign: with the waist exactly one stroke
   thick, the upper bowl's counter edge and the lower bowl's outer edge are
   tangent and *never cross*, so no cut could ever be interior.)

3. **A stroke that changes direction cannot be hand-traced.** Traced by hand,
   the two edges drift apart and it swells, or they cross and the fill cancels
   to a hairline. Both happened, in `l`, `J`, `6` and `9`. Use the centreline
   stroker: `stroke(g, spline([...]), wx, wy)`.

4. **Cut geometry has a hard constraint.** A cut at angle θ to a stroke has
   length `thickness / sin θ`, and the stroker's `_slide` moves each corner along
   its own tangent by roughly `halfwidth / tan θ`. If that slide exceeds the
   distance the edge travels within the fitted stretch, the refitted edge
   **doubles back and opens a hairline crack** — that was `5`'s bug. A butt cap
   (`cap=None`, perpendicular) slides nothing and is always safe. Default to it.

5. **Junction topology must be derived from a reference, not assumed.** `k`,
   `3`, `1` and `5` were all wrong because I guessed how the strokes meet.
   Dumping the real proportions with `dev/href.py` was decisive every time.
   Use it for proportions and topology; draw the curves yourself.

6. **Measure, don't squint.** `dev/runs.py` found spurs, cracks and weight
   wander that were invisible at small sizes and ambiguous even at 300 px. A
   correct glyph shows one ink run per scanline where you expect one, and a
   stem's run width equals `VSTEM` exactly.

---

## 6. Setting up on another machine

The archive carries no virtual environment and no compiled fonts — `fonts/` is
build output and is recreated by the generator. From the extracted directory:

```sh
cd sabas-os-fonts
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Rebuild the source of truth and the font in one step
.venv/bin/python tools/strike/build_t1_glyphs.py
# → Saved 369 glyphs to sources/sabas-ui/SabasUI-Regular.ufo
# → Compiled OK → fonts/SabasUI-Regular.otf

# Then look at it
.venv/bin/python tools/strike/dev/render.py     # → /tmp/specimen.png
```

`fontc` is a Rust binary, not a pip package — `cargo install fontc` if you want
the cross-compiler divergence gate in §3 to do anything.

Two archives were produced. The slim one omits
`sources.bak.20260917-220215/`, which is a pre-edit copy of `sources/` kept as a
safety net; take the full one if you want that history on the new machine.

---

## 7. Suggested order of work

1. `ł`'s bar (one-line fix — `l`'s ink bounds moved).
2. `&`'s leg join (widen the overlap or lower the top cut).
3. `ß`, then `æ`, then `ð`.
4. Rebuild `6` and `9` as centreline strokes.
5. Braces.
6. The five brief-mandated table/format items in §3 — all cheap, all independent.
7. **Regenerate downstream and re-snapshot goldens.** Do not defer this; the
   longer the masters stay stale the harder the diff is to read.
