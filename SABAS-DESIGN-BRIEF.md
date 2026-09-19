# Sabas — System Typeface Specification

**For:** Sabas OS · **Status:** Draft 0.4 · **Date:** 2026-09-17
**Rendering stack:** FreeType + HarfBuzz · **Density targets:** 1× (96 dpi) and HiDPI (≥2×)
**License:** SIL Open Font License 1.1, **no Reserved Font Name**

**Confirmed constraints:** Sabas OS ships a 1× target at launch, and the compositor
already blends in linear light. Consequences: the §3.1 rendering contract is satisfiable
as written with no compositor work, and bitmap strike production (§6.5) is on the
critical path from M1 — it is the largest single line item in the plan.

---

## 1. Role and roster

Sabas is the system typeface of Sabas OS. It has to be correct at 11 px on a cheap 1×
panel and beautiful at 96 px on a 3× panel, in every language the OS claims to support.
Those are different problems and this spec solves them with different mechanisms.

### 1.1 Drawn in-house

| Family | Job | Sizes | Bitmap strikes |
|---|---|---|---|
| **Sabas UI** | Interface chrome: labels, menus, buttons, tables, notifications | 11–20 px | **yes** |
| **Sabas Text** | Long-form reading: documents, help, articles | 14–24 px | no |
| **Sabas Display** | Headings, settings panels, onboarding, lock screen | 28–120 px | no |
| **Sabas Mono** | Terminal, editor, logs, diffs | 11–18 px | **yes** |
| **Sabas Icons** | Inline shell icons, COLRv1 variable colour | 16/24 px grids | no — grid-exact (§9.4) |
| **Sabas Console** | Framebuffer console, TTY, early boot, panic screen | 8×16, 10×20, 12×24 | bitmap-only |

### 1.2 Adopted and harmonised

Full Unicode coverage is achieved by *adoption*, not by pretending to draw Han. All
sources below are OFL without Reserved Font Name, so rebuilding them with Sabas vertical
metrics and redistributing under a `Sabas` name is permitted — provided the OFL text and
original authorship are carried through (§14).

| Derived family | Upstream | Scripts |
|---|---|---|
| **Sabas Han** | Noto Sans CJK / Source Han Sans | Han, Hiragana, Katakana, Hangul, Bopomofo |
| **Sabas Arabic** | Noto Sans Arabic | Arabic, Persian, Urdu |
| **Sabas Indic** | Noto Sans {Devanagari, Bengali, Tamil, Telugu, …} | Indic scripts |
| **Sabas Hebrew / Thai / Ethiopic / …** | corresponding Noto Sans | per script |
| **Sabas Emoji** | Noto Emoji (COLRv1 build) | Emoji, with monochrome cut for Console |
| **Sabas Symbols** | Noto Sans Symbols 1 & 2 | symbol blocks not in core |

Harmonisation is a real engineering task, not a rename — see §7.

### 1.3 Non-goals

Drawing Han, Arabic, or Indic from scratch. Decorative and script faces. Any icon
artwork inside the text families.

---

## 2. Design principles

**Neo-grotesque skeleton, humanist apertures.** Vertical stress, counters closed but not
sealed, apertures on `a c e s g` opened deliberately — the neo-grotesque instinct to
close them is exactly what makes Helvetica fail at 11 px and on dark backgrounds.

**Optical, not geometric, correction.** Horizontal stems at 84–88 % of verticals.
Overshoot on rounds 1.2 % of UPM at text sizes, tapering to zero as `opsz` rises. Joins
thinned where strokes meet (`n m u b d p q a`) rather than left at full stem weight.

**Designed for the pixel grid, not merely hinted onto it.** Key horizontals — baseline,
x-height, cap height, figure height — are chosen for how they land at the target ppem, not
as round numbers. No single value lands cleanly at every UI size (§6.3 shows why that is
arithmetically impossible below ~37 ppem), so the goal is to land cleanly at the sizes the
OS actually ships and to fail *predictably* elsewhere. This is upstream of hinting, and it
is what makes hinting cheap where it works and makes the failures enumerable where it
doesn't.

**Disambiguation as a hard requirement**, weighted per family:

| Pair | UI | Text / Display | Mono | Console |
|---|---|---|---|---|
| `0` / `O` | narrow zero | narrow zero | **dotted zero** (`cv01`, default on) | slashed |
| `1` / `l` / `I` | `1` flag, no foot serif; tailed `l` | as UI | `1` flag + foot serif; tailed `l`; serifed `I` | all three distinct |
| `rn` / `m` | wide `r` arm gap | wide `r` arm gap | grid separates | 1 px gap enforced |
| `5` / `S` | flat-top `5` | flat-top `5` | flat-top `5` | flat-top `5` |
| `:` / `;` | — | — | enlarged dots | 2 px dots |
| `''` / `"` | — | — | distinct widths | distinct |
| `8` / `B` | — | — | open-counter `8` | open-counter `8` |

**Diacritics are drawn per script**, with small-size variants driven by `opsz`, attached
by real `mark`/`mkmk` anchors. Never precomposed-only. Vietnamese stacking (`Ẩ Ồ ự`) is a
release gate, not a nice-to-have.

---

## 3. The rendering contract

Pixel accuracy is a property of the font *and* the rasteriser together. Because you own
both, they get co-designed, and the client-side settings below are part of this spec —
the font is only guaranteed correct when rendered this way.

### 3.1 Required FreeType configuration

| Setting | Value | Why |
|---|---|---|
| FreeType | ≥ 2.13.2 | `avar2`, COLRv1, and current autohinter |
| `truetype:interpreter-version` | **40** | Subpixel-hinting mode: y-only grid fitting, ignores horizontal instructions |
| Load target | **`FT_LOAD_TARGET_LIGHT`** | Autohinter, vertical snapping only, horizontal metrics untouched |
| `FT_LOAD_NO_BITMAP` | **unset** | Embedded strikes must be reachable (§6) |
| `autofitter:no-stem-darkening` | **false** (darkening ON) | Compensates AA thinning — valid *only* with linear blending below |
| LCD filter | `FT_LCD_FILTER_DEFAULT` (FIR5) | Subpixel colour fringing control on 1× RGB panels |
| Subpixel positioning | **on**, ≥ 1/4 px | Preserves spacing rhythm; light hinting is designed for it |
| Blending | **linear light** (sRGB decode → blend → encode) | Non-linear blending is the actual cause of "light-on-dark looks too thin" |

The compositor already blends in linear light, so stem darkening can be enabled safely —
the two are a package. Enabling darkening on top of sRGB-space blending double-counts and
produces text that is genuinely too heavy, so if the blending path is ever changed, this
row changes with it. CI asserts the pairing by rendering a known light-on-dark string and
comparing measured coverage against the dark-on-light equivalent.

**Light hinting, not full hinting, and not manual VTT.** With interpreter v40 FreeType
discards horizontal instructions anyway, so hand-authored horizontal hints are dead
code. Light hinting snaps the horizontals — the axis where 1× rendering actually breaks —
and leaves widths alone so subpixel positioning keeps the spacing. It also works on
variable instances, which manual hinting does not.

### 3.2 Compositor and toolkit obligations

- Glyph cache keyed on `(glyph, ppem, subpixel-phase, variation-coords, GRAD)`.
- Never scale a rasterised bitmap. Re-render at the target ppem.
- Never synthesise bold or oblique. Use `wght` and `slnt`; synthesis is why fake bold
  looks like a smear.
- Pass fractional pen positions to FreeType, not rounded ones.
- Apply `font-optical-sizing: auto` semantics natively: `opsz` tracks rendered px size.

### 3.3 HarfBuzz

Shaping via HarfBuzz ≥ 8.0 with `hb-ft`, sharing one `FT_Face` and identical variation
coordinates with the rasteriser. A mismatch between shaping coords and raster coords is
the single most common source of "text is subtly wrong and nobody knows why."

---

## 4. Metrics

### 4.1 Units per em

**1000 UPM**, cubic sources, quadratic `glyf` output.

The traditional argument for 2048 is TrueType hinting on a power-of-two grid. Interpreter
v40 plus light hinting makes that moot, and 1000 keeps the parametric arithmetic in §5.2
and the pixel-grid table in §6.3 legible to humans.

### 4.2 Vertical metrics — identical across every family, in-house and adopted

| Field | Value | Note |
|---|---|---|
| `unitsPerEm` | 1000 | |
| `sTypoAscender` | 800 | |
| `sTypoDescender` | −200 | |
| `sTypoLineGap` | 200 | ⇒ default line height 1.20 em |
| `hhea.ascender` / `.descender` / `.lineGap` | 800 / −200 / 200 | mirror typo exactly |
| `usWinAscent` | 1010 | real ink max: stacked Vietnamese |
| `usWinDescent` | 300 | real ink min: `Ģ ç ŋ Ų` |
| `fsSelection` bit 7 | **set** | `USE_TYPO_METRICS` — non-negotiable |

This is the highest-leverage constraint in the document. Because **Sabas Han**, **Sabas
Arabic**, **Sabas Emoji** and every other adopted family are rebuilt to these same
numbers, a Japanese string, an Arabic string, an emoji and a Latin string in one line box
share a baseline and do not change the line height. Every OS that skipped this has
paragraphs that visibly jump when the script changes.

### 4.3 Horizontal proportions (`wght` 400, `wdth` 100, default `opsz`)

| Metric | UI | Text | Display | Mono |
|---|---|---|---|---|
| Cap height | 720 | 700 | 700 | 700 |
| x-height | 540 | 495 | 470 | 525 |
| x/cap | 0.750 | 0.707 | 0.671 | 0.750 |
| Ascender (`b d k l`) | 750 | 760 | 770 | 750 |
| Descender (`p q y`) | −205 | −215 | −220 | −205 |
| Vertical stem | 88 | 84 | 78 | 84 |
| Horizontal stem | 76 | 71 | 62 | 72 |
| Contrast | 1 : 1.16 | 1 : 1.18 | 1 : 1.26 | 1 : 1.17 |
| Advance `n` | 570 | 545 | 530 | **600 fixed** |

Mono advance is **0.600 em**, matching SF Mono and JetBrains Mono, so existing terminal
and editor configs port without column re-tuning.

---

## 5. Design space

### 5.1 Registered axes

| Family | `wght` | `wdth` | `opsz` | `GRAD` | Slant / Italic |
|---|---|---|---|---|---|
| **UI** | 100–1000 / 400 | 75–125 / 100 | 10–32 / 16 | −200…150 / 0 | `slnt` 0…−10 |
| **Text** | 200–900 / 400 | 87.5–112.5 / 100 | 8–36 / 16 | −150…100 / 0 | **`ital` 0/1**, true italic, discrete |
| **Display** | 200–900 / 400 | 75–125 / 100 | 28–144 / 48 | −100…100 / 0 | `ital` 0/1 |
| **Mono** | 200–800 / 400 | — *(fixed grid)* | 9–24 / 13 | −200…150 / 0 | `slnt` 0…−9 |
| **Icons** | 100–1000 / 400 | — | 16–48 / 20 | −200…150 / 0 | — |

**`GRAD` earns its place in an OS more than anywhere else.** It changes apparent weight
at *zero* advance change: compensate the apparent-weight gain of light-on-dark text,
thicken terminal glyphs for a low-contrast theme, add a hair of weight for an
accessibility setting — none of it reflows a single line or invalidates a layout. Paired
with the linear blending in §3.1 it is how dark mode stops looking anaemic.

**`opsz` is a real optical size.** As it falls: x-height rises, counters open, spacing
loosens, hairlines thicken, overshoot reduces. It is doing continuously and by design
what hinting attempts discretely and by force.

`Sabas Icons` shares `wght` and `GRAD` ranges with `Sabas UI` so a 400-weight icon sits
beside a 400-weight label without one looking pasted in.

### 5.2 Parametric axes (hidden, `avar2` inputs)

Masters are built on parametric extremes; registered axes are mapped onto them by
`avar2` (Amstelvar / Roboto Flex model). Hidden axes carry the `STAT` hidden flag.

| Tag | Meaning |
|---|---|
| `XOPQ` | vertical stem thickness |
| `YOPQ` | horizontal stem thickness |
| `XTRA` | counter / internal width |
| `YTLC` `YTUC` `YTAS` `YTDE` `YTFI` | x, cap, ascender, descender, figure heights |

Mappings, via designspace 5.1 `<axes><mappings>`:

- `wght` → `XOPQ`, with `YOPQ` at ≈0.86 and `XTRA` *negative*, so heavy weights don't balloon.
- `opsz` → inverse `YTLC`, `XTRA`, `YOPQ`, and spacing.
- `GRAD` → `XOPQ` + `YOPQ` with compensating `XTRA` holding the advance constant.
- `wdth` → `XTRA` with a small negative `XOPQ` correction so narrow cuts don't clog.

**`avar2` support:** solid in FreeType ≥ 2.13 and HarfBuzz ≥ 7, which is your entire
stack — so unlike a font shipping to the open web, Sabas can rely on it. Static
instances still bake the mapping resolved, and CI asserts static ≡ variable at every
named instance.

### 5.3 Italics

- **Text and Display** get a drawn italic: single-storey `a`, cursive `e f g k v w y`,
  real entry/exit strokes, 9.5° slope. Separate UFOs joined by a **discrete** `ital` axis.
- **UI and Mono** get a corrected oblique on `slnt` — mechanical shear plus per-glyph
  repair (rounds redrawn, `f` and `l` retuned, diagonals rebalanced). An interface or a
  terminal rarely wants a cursive voice, and `slnt` keeps the metric compatibility that
  syntax highlighting and column alignment depend on.

---

## 6. Pixel accuracy

### 6.1 Definition — measurable, not aspirational

"Pixel perfect" means, at every ppem in §6.2 on a 1× display:

1. Every vertical stem covers a whole number of pixels at full coverage — no 1.5-px stems.
2. Baseline, x-height, cap height and figure height land on integer pixel boundaries.
3. Stems intended to match visually (e.g. both stems of `n`) rasterise identically.
4. No counter closes: `e a s g 8 6 9` retain ≥ 1 px of open counter at 11 px.
5. Rendering is byte-identical across every FreeType version in the support matrix.
6. Raster diff against the committed golden PNG is **zero** differing pixels.

Item 6 is the enforcement mechanism. Without golden-raster tests in CI, pixel accuracy
decays on the first unrelated commit.

### 6.2 Three-tier strategy

| Tier | Condition | Mechanism |
|---|---|---|
| **1** | 1×, at a shipping UI size | **Embedded bitmap strike** — hand-corrected, exact |
| **2** | 1×, any other size | Outline + FreeType light hinting + stem darkening |
| **3** | HiDPI (≥2×) | Outline, unhinted, `opsz`-driven, subpixel positioned |

Strike sizes: **UI** 11, 12, 13, 14, 16, 18, 20 px · **Mono** 12, 13, 14, 16, 18 px.
Weights Regular / Medium / SemiBold / Bold, upright only. **Icons carry no strikes** — they
are grid-exact by construction, see §9.4.

**Strikes ship in the static instances, not the variable font.** `EBDT`/`EBLC` strikes
are per-font, with no mechanism to vary across a design space — a strike for `wght` 400
is simply wrong at `wght` 700. So: the OS loads *static* UI/Mono/Icons instances for
chrome at 1×, and the variable fonts for content, animation and HiDPI. This constraint is
easy to miss and expensive to discover late.

Strike depth: 8-bit grayscale (`bitDepth 8`) as primary, 1-bit for Console and for the
panic-screen path where no AA compositor exists yet.

Strike scope: T1 Core charset only (~230 glyphs). Beyond that, tier 2 applies. Roughly
230 × 5 sizes × 4 weights ≈ 4,600 bitmaps per family — generated, then hand-corrected.

### 6.3 Pixel-grid alignment

At 1000 UPM and *P* ppem, 1 px = 1000/*P* units, so a height of *H* units renders at
*H·P*/1000 px. Define the **residual gap** *g* = |*H·P*/1000 − round(*H·P*/1000)|, in
pixels: how far light hinting has to move that height to reach the grid. Maximum possible
gap is 0.5 px.

Sabas UI, x-height 540 and cap height 720:

| ppem | 1 px = | x-height px | *g* | class | Cap px | *g* | class |
|---|---|---|---|---|---|---|---|
| 11 | 90.9 u | 5.94 → 6 | 0.06 | **A** | 7.92 → 8 | 0.08 | **A** |
| 12 | 83.3 u | 6.48 → 6 | 0.48 | **C** | 8.64 → 9 | 0.36 | **C** |
| 13 | 76.9 u | 7.02 → 7 | 0.02 | **A** | 9.36 → 9 | 0.36 | **C** |
| 14 | 71.4 u | 7.56 → 8 | 0.44 | **C** | 10.08 → 10 | 0.08 | **A** |
| 16 | 62.5 u | 8.64 → 9 | 0.36 | **C** | 11.52 → 12 | 0.48 | **C** |
| 18 | 55.6 u | 9.72 → 10 | 0.28 | **C** | 12.96 → 13 | 0.04 | **A** |
| 20 | 50.0 u | 10.80 → 11 | 0.20 | **B** | 14.40 → 14 | 0.40 | **C** |

#### What `opsz` can actually close

`opsz` carries a per-size `YTLC`/`YTUC` adjustment, but its budget is bounded: beyond
about **±2.5 %** the family stops reading as one size series across the range, and the
parametric system starts distorting counters and sidebearings. In pixels that budget is

> *b*<sub>px</sub> = 0.025 · *H* · *P* / 1000

— which at *H* = 540 gives 0.162 px at 12 ppem and 0.216 px at 16 ppem. **Class B** is
`g ≤ b`<sub>px</sub>; **Class C** is `g > b`<sub>px</sub>; Class A is `g ≤ 0.10` px, where
nothing needs doing.

So the 12 px x-height gap of 0.48 px is three times its 0.162 px budget, and the 16 px cap
gap of 0.48 px is more than twice its 0.216 px. Neither is closable. That is not a tuning
failure, it is arithmetic:

An integer pixel height exists inside the reachable window only if the window is at least
1 px wide. Window width = 2·*b*·*H*·*P*/1000, so at ±2.5 % it reaches 1 px only at
*P* ≥ 37 ppem. **Below ~37 ppem, `opsz` grid-snapping is opportunistic and never
guaranteed** — at 16 ppem the window is 0.43 px, so it lands on-grid less than half the
time. Guaranteeing it would need *b* ≥ 500/(*H·P*): 5.8 % at 16 ppem, 8.4 % at 11 ppem.

#### The constraint that settles it

Chasing the grid at every ppem requires *non-monotonic* x-height across the size series —
11 px wants `YTLC` pushed up, 12 px wants it pushed down. The result is a type scale where
12 px lowercase can render *shorter* than 11 px. That is a worse defect than an off-grid
height, and it is user-visible in any settings panel that shows two sizes together.

**Monotonicity wins.** `YTLC(P)` is constrained to be non-decreasing in *P*, and grid
snapping happens only within whatever freedom is left. Class C gaps are therefore expected
and permanent, and §6.4 says what to do about them.

Implementation lever: the autohinter snaps to the UFO's `postscriptBlueValues`, so
rounding direction is controlled by blue zone placement, width, `blueFuzz` and `blueScale`
per `opsz` master — not left to the rasteriser's discretion.

### 6.4 Rounding policy and strike authority

#### Per-class action

| Class | Condition | Action |
|---|---|---|
| **A** | `g ≤ 0.10 px` | None. Light hinting rounds cleanly. Strike optional, auto-generated only. |
| **B** | `0.10 < g ≤ b`<sub>px</sub> | Close it with the `opsz` `YTLC`/`YTUC` adjustment, subject to monotonicity. Strike generated; hand-correction low priority. |
| **C** | `g > b`<sub>px</sub> | **Strike is mandatory and authoritative.** Hand-correction is required, not frequency-queued (§6.5 stage 3). |

#### Does the strike unconditionally override? Mechanically yes — and that is the hazard

With `FT_LOAD_NO_BITMAP` unset, FreeType uses a strike whenever one exists at that ppem.
There is no threshold and no negotiation: **presence is the decision.**

The hazard is that strike coverage is *partial* — T1 Core only, 4 weights, upright only.
So at 12 px a single string can draw `Name` from the strike and `Ná​mě` partly from
outlines, and if the strike chose a 6 px x-height while light hinting rounded the outline
glyph to 7, the two render at visibly different sizes inside one word. Partial coverage
plus an authoritative strike is exactly how you get mixed x-heights in one label.

So the policy is the *inverse* of "override":

> **The strike's chosen integer height is normative for that ppem, and the outline path
> must be tuned to agree with it.** Blue zones and `YTLC(P)` at each strike ppem are set so
> tier-2 rasterisation lands on the same integers the strike uses.

CI enforces it: render every **non**-strike glyph at every strike ppem and assert its
x-height, cap height and baseline match the strike's integers exactly. A mismatch is a
build failure. This test is cheap and it catches the entire class of bug.

This is also what makes the strike worth its cost. A bitmap is not obliged to be a
faithful rasterisation of the outline — only to be *right*. At 12 px the strike can render
a 6.48 px x-height as 6 px and compensate with a lifted crossbar, a redistributed stem, a
1 px counter held open. The outline cannot do that. The freedom to diverge from the outline
is the whole point.

#### Fallback when no strike exists

Class C also occurs where no strike is available: a non-strike ppem, a non-T1 glyph, or an
italic/oblique or weight outside the strike matrix. There is no mechanism left, so the
policy is a constraint on the *product* rather than the font:

1. Accept the rounding, and
2. assert the **monotonicity invariant** — across the OS design system's approved size
   list, rendered x-height and cap height in whole pixels must be non-decreasing, and must
   strictly increase at least every second step.
3. If a ppem violates that invariant and cannot be strike-backed for the glyph coverage
   that size actually needs, **that ppem is removed from the approved size list.**

Point 3 is the real answer, and it reframes open question §16.2: **the size list is an
output of this table, not an input to it.** A scale of 11 / 13 / 16 / 20 is *better* than
11 / 12 / 13 / 14 / 16 / 18 / 20 — every step is a distinguishable step at 1×, and it cuts
strike volume by 40 %. Sizes 12 and 14 are the weakest members of that list on this
analysis; 13 and 18 are the strongest.

The invariant is a generated report, published with each build, so the design system owns
its size list against real rendering data rather than round numbers.

### 6.5 Strike production pipeline

Since 1× ships at launch, this is critical path. Roughly 230 glyphs × 5 sizes × 4 weights
≈ 4,600 bitmaps per family, across UI, Mono and Icons. Done naively by hand that is a
year of work and it rots the first time an outline moves. The pipeline below makes it
tractable and, more importantly, makes it *repeatable*.

**Stage 1 — Generate.** Rasterise the light-hinted outline at each target ppem through
the §3.1 FreeType configuration, 8-bit grayscale. This baseline is already close, because
the design put its key heights near the pixel grid where it could (§6.3). At Class C sizes
the baseline is *not* close, and those are the strikes that need the most hand work.

**Stage 2 — Auto-correct.** A deterministic pass that: snaps stems to whole pixels at
full coverage; enforces symmetry between stems meant to match (`n`, `H`, `o`); guarantees
≥ 1 px of open counter in `e a s g 8 6 9`; equalises the two dots of `:` and the sidebearings
of symmetric glyphs. Every rule is testable, and the pass reports which glyphs it changed
by more than a threshold — that report *is* the hand-correction work queue.

**Stage 3 — Hand-correct, in frequency order.** Not all 230 glyphs deserve equal
attention. Prioritise by frequency measured over a real corpus of OS UI strings and
source code, not by alphabet order. In practice ~40 glyphs carry most of the perceived
quality: lowercase `a e i o n s r t l h u c d m`, digits, `. , : ; - / ( )`, and the
capitals that actually start UI labels.

**Stage 4 — Store corrections as an overlay, never as flat bitmaps.** This is the
decision that determines whether the strikes survive the project. Hand edits are
committed as a *patch layer* keyed on `(glyph, ppem, weight)` — a sparse per-pixel delta
against the Stage 2 output — not as finished images. When an outline changes, Stages 1–2
re-run and the overlay re-applies.

Flat-bitmap storage is the standard way this goes wrong: the strikes become
un-regenerable, the outlines and the bitmaps drift apart, and eventually nobody dares
touch either.

#### Patch format — frozen at v1, decided before M1

**One file per `(glyph, ppem, weight)`**, laid out as
`sources/strikes/<family>/wght<NNN>/ppem<NN>/<glyphname>.patch`. Not one file per size
holding every glyph: per-glyph files mean a one-pixel fix is a one-file, one-line diff, two
designers editing different glyphs at the same size never conflict, and a reviewer reading
"4 files changed" knows immediately that four glyphs changed.

**Line-oriented plain text**, not JSON, TOML or PNG. JSON arrays diff badly, PNG is opaque
to review, and the payload is naturally one record per line — which makes `git diff` show
exactly which pixels a designer touched.

```
format 1
family      sabas-ui
glyph       a
ppem        12
weight      400
baseline    blake3:9f2a41c7…       # fingerprint of the Stage-2 raster
raster-env  freetype-2.13.3 target=light interp=40 darken=on compiler=fontc-1.4.2
bbox        0 -1 7 7               # xMin yMin xMax yMax, px, baseline-relative, y-up
advance     7                      # px; must equal round(outline advance)

# x  y   from ->  to      8-bit coverage
  2  3    128 -> 255
  2  4    128 -> 255
  5  3    200 ->  64
  5  4      0 -> 176

# --- preview (tool-generated, do not hand-edit) ---
# ..####..
# .#....#.
# .#....#.
# ..#####.
# .#....#.
# .#....#.
# ..####.#
```

Five decisions inside that, in order of how much they matter:

1. **Every edit records `from -> to`, not just `to`.** This moves conflict detection from
   per-glyph to **per-pixel**. On regeneration, if the new Stage-2 raster still has 128 at
   (2,3) that line reapplies silently; if it now has 96, *that one line* conflicts while the
   other nineteen edits still apply. A whole-glyph hash alone would throw away a day's work
   over a single changed pixel.
2. **`baseline` is a fast path, not the mechanism.** Hash matches → apply everything
   unchecked. Hash differs → fall through to per-pixel `from` verification.
3. **`raster-env` is part of the fingerprint input**, including the compiler identity. A
   FreeType upgrade — or a `fontc` upgrade — legitimately changes rasterisation, so it
   *should* invalidate baselines. Because of decision 1 the common outcome is that all 4,600
   patches reapply cleanly as "verified reapply" rather than 4,600 conflicts. This is the case
   that would otherwise stall an upgrade indefinitely. It is also why §12.1 pins the shipped
   artefact to one compiler: switching would invalidate every patch at once.
4. **Coordinates are baseline-relative, y-up, matching the UFO convention** — stated
   explicitly because getting it wrong flips glyphs vertically and the bug looks like a
   design error rather than a units error.
5. **The ASCII preview is generated, never authoritative.** It exists so a reviewer sees
   the actual glyph in the diff instead of a list of coverage integers. The tool rewrites it
   on every apply; a hand-edited preview that disagrees with the payload is a lint error.

**Conflict policy**

| Situation | Outcome |
|---|---|
| `baseline` matches | Apply all. Silent. |
| `baseline` differs, all `from` match | Apply all, mark *verified reapply*, rewrite `baseline`. No review. |
| Some `from` differ | Apply the rest, flag those pixels, glyph enters the review queue. **Build fails.** |
| `bbox` or `advance` changed | Whole glyph conflicts, full re-review. |

`--accept-drift` overrides for a designer's local loop; it is rejected in CI.

At 1-bit depth (Console, panic path) coverage values are constrained to 0 and 255 and the
tool rejects anything else, so the same format serves both paths.

**Stage 5 — Merge and validate.** Strikes are written into the static instances as
`EBDT`/`EBLC` (8-bit grayscale primary, 1-bit for the no-AA paths) by a fontTools-based
tool, post-compile. Validation: zero-pixel golden diff, stem-width histogram per ppem,
counter-openness check, and a rendered specimen sheet per size for human sign-off.

**Icons are outside this pipeline.** Per §9.4 they are drawn grid-exact per size and need
no strikes, so `Sabas Icons` ships as a single variable COLRv1 font. This is also the
convenient outcome, because COLRv1 and `CBDT`/`CBLC` cannot coexist usefully in one font —
FreeType prefers the bitmap and the colour layers become unreachable. Had icons needed
strikes, they would have required two separate artefacts. If individual un-griddable icons
later need strikes, they go in a small companion monochrome static, not in the colour font.

### 6.6 Sabas Console

Not an outline font. PSF2 bitmaps at **8×16**, **10×20**, **12×24**, hand-pixeled from
the Mono skeletons.

Coverage per size: ASCII, Latin-1, Latin Extended-A subset, Cyrillic basic, Greek basic,
Box Drawing `U+2500–257F`, Block Elements `U+2580–259F`, arrows subset — with a Unicode
mapping table, so PSF's 512-glyph ceiling is respected by shipping per-locale variants
rather than one overloaded file.

Requirements: legible with no antialiasing, no subpixel rendering, no GPU, at a
framebuffer's native resolution, on a possibly miscalibrated display, while reporting a
kernel panic. This is the least glamorous family and the one users see at the worst
possible moment.

---

## 7. Language coverage and the fallback chain

### 7.1 In-house charset tiers

| Tier | Content | Families |
|---|---|---|
| **T1 Core** | ASCII, GF Latin Core (~230), core punctuation, `€ £ ¥ ¢ ₹`, arithmetic | all |
| **T2 Latin Plus** | Latin Ext-A, full European, **Vietnamese** with full tone/vowel stacking | all |
| **T3 Cyrillic + Greek** | GF Cyrillic Core & Plus, monotonic Greek | all |
| **T4 Mono technical** | Box Drawing, Block Elements, Geometric Shapes subset, arrows | Mono, Console |
| **T5 Typographic** | Small caps, oldstyle figures, `f`-ligatures, fractions, superior/inferior | Text, Display |
| **T6 Extras** | IPA, Latin Ext-B remainder, extended math operators | all, post-1.0 |

### 7.2 Harmonising adopted families

A rename is not harmonisation. Each adopted font is rebuilt:

1. **Scale to 1000 UPM** and apply the §4.2 vertical metrics verbatim.
2. **Match apparent weight** — Noto's Regular is not Sabas's Regular at the same nominal
   value. Calibrate by measured stem darkness at 16 px, not by name, and record the
   mapping so `wght` 500 means one thing system-wide.
3. **Match x-height ratios** where the script has one, so Latin and Greek at 14 px look
   like the same size — which is what users mean by "the font."
4. **Han-specific:** ideographs are full-width by construction; verify the em-square
   alignment survives the UPM change, and keep the `vert`/`vrt2` tables intact for
   vertical Japanese.
5. **Strip and rebuild** `name`, `STAT`, `OS/2` for the Sabas namespace; preserve
   `AUTHORS`, licence, and original designer credit.
6. Re-run the §12 QA gates. An adopted font that fails them does not ship.

### 7.3 Fallback architecture

- **Coverage manifest** — a generated, committed map of codepoint → owning family. The
  single source of truth for both fontconfig and the toolkit.
- **fontconfig** — `system-ui` → Sabas UI, `sans-serif` → Sabas Text, `monospace` →
  Sabas Mono, with per-script `<match>` rules driving the chain, plus explicit
  `<binding>` so user config can override but defaults are deterministic.
- **Per-script order**, not per-font order. Falling back by font list produces the
  classic bug where a Cyrillic glyph is served by the Han font because it happened to be
  earlier and happened to have one.
- **Emoji before symbols.** `U+2764` and friends exist in both; the OS must decide
  presentation deliberately, honouring `VS15`/`VS16`.
- **`.notdef` policy** — a real drawn `.notdef` (hollow box with the hex codepoint at
  larger sizes), never a blank. Silent missing glyphs are unreportable bugs.
- **Tofu telemetry hook** — count fallback misses so gaps are discovered from usage
  rather than from a bug report.

Coverage claims are proven by `shaperglot` per language, not asserted from a codepoint
count. Target: Unicode 17.0.

---

## 8. OpenType features

**All in-house families:** `ccmp`, `locl`, `mark`, `mkmk`, `case`, `frac`, `numr`,
`dnom`, `sups`, `subs`, `ordn`, `aalt`, `calt`, plus `kern` (all but Mono).

`locl` must cover at minimum: Romanian/Moldovan `Ș Ț` comma-below, Dutch `IJ`, Catalan
`ŀ`, Turkish/Azeri dotless `ı`, Serbian & Macedonian Cyrillic italic `б г д п т`, Polish
kreska angle, Greek `tonos`.

**Figures**

| Family | Default | Available |
|---|---|---|
| UI | proportional lining | `tnum`, `onum` |
| Text / Display | proportional lining | `tnum`, `onum`, `pnum`, `lnum` |
| Mono | tabular by construction | `zero` |

**Stylistic sets**

| Tag | UI | Text / Display | Mono |
|---|---|---|---|
| `ss01` | single-storey `a` | single-storey `a` | **programming ligatures** (opt-in) |
| `ss02` | straight-tail `l` | — | straight-tail `l` |
| `ss03` | flat-top `3` | flat-top `3` | flat-top `3` |
| `cv01` | slashed zero | slashed zero | **dotted zero, default on** |
| `cv02` | open `4` | open `4` | open `4` |
| `cv03` | serifed `I` | serifed `I` | serifed `I`, default on |

**Mono `calt` — texture healing.** On a fixed grid `mill` leaves a hole and `WWW` clogs.
`calt` substitutes wider variants of narrow glyphs when neighbours are narrow, and
narrower variants of wide glyphs when neighbours are wide, redistributing space *inside*
the fixed advance so the grid never breaks.

Width classes, defined on **base glyphs only**:

- **NARROW** — `i j l t f r I 1 . , ; : ' " ` ! | ( ) [ ] { } / \`
- **WIDE** — `m w M W @ % &`
- **NEUTRAL** — everything else, including space

Decision rule, evaluated per glyph on its immediate left and right neighbours:

| Glyph class | Narrow neighbours | Result |
|---|---|---|
| NARROW | 2 | widest variant (`.wide2`) |
| NARROW | 1 | intermediate variant (`.wide1`) |
| WIDE | — (2 wide neighbours) | narrowest variant (`.narrow1`) |
| otherwise | — | base form |

≈24 base glyphs × 2 variants, plus 7 × 1. The rule keys on *neighbour count*, not on which
side — so `il` and `li` treat the `i` identically and there is no left/right asymmetry to
debug.

#### Window composition

This is the part that is easy to get wrong, and `ifill`, `llll`, `MWMW` are exactly the
cases that expose it. Four properties are required, and they follow from one architectural
choice:

> **Every healing rule has a single-glyph input sequence with backtrack and lookahead
> context.** Never a multi-glyph input run.

In FEA terms `sub @NARROW i' @NARROW by i.wide2`, where the outer classes are *context* and
only `i` is consumed.

1. **No window consumption.** HarfBuzz resumes scanning after the matched *input*
   sequence, not after the context. With single-glyph input it advances one glyph at a time,
   so every position in `llll` is evaluated — whereas a three-glyph input rule would consume
   positions 0–2 and skip evaluating position 1 entirely. This alone is why the multi-glyph
   formulation quietly fails on runs of four or more.

2. **No substitution cascade.** Scanning left-to-right mutates the buffer, so when position
   *n* is evaluated its left neighbour may already have been substituted. The fix is that
   **every variant belongs to the same width class as its base** — `i.wide2 ∈ NARROW` — so
   context matching is invariant under prior substitution and decisions are effectively made
   on the original classes. Omit this and `llll` resolves differently from `llll ` depending
   on what preceded it.

3. **Idempotence.** Variants appear in context coverage but never in *input* coverage, so
   re-shaping already-shaped text is a no-op. Terminals re-shape cached runs constantly; a
   non-idempotent `calt` produces glyphs that creep wider on every repaint.

4. **Cluster preservation — the decisive reason.** A single-glyph substitution keeps the
   HarfBuzz cluster mapping 1:1. Multi-glyph input merges clusters, and in a terminal or
   editor that breaks caret placement, selection extents and hit-testing: the cursor can no
   longer land between the two `l`s of `ll`. Composition correctness is the visible argument
   for single-glyph rules; cluster integrity is the one that makes it non-negotiable.

**Lookup ordering.** HarfBuzz applies lookups in GSUB index order, not feature-tag order,
so healing lookups must carry **higher indices than the `ss01` ligature lookups**.
Ligation changes glyph count and therefore changes every window; healing must see the
post-ligature run. Same reasoning applies to `ccmp`, which must precede both.

**Advance is never modified**, by any healing rule. That is what lets a terminal shape
per-run, per-cell, or not at all: if a terminal shapes each cell in isolation the context
is absent, no rule fires, and healing degrades to the base forms with the grid intact.
Graceful degradation, not breakage.

**Required golden-file cases** (§12 `hb-shape` suite): `ifill`, `llll`, `lllll`, `MWMW`,
`ilil`, `mil`, `lim`, `i.l`, `1ll1`, `WWiWW`, `....`, `::::`, `-->`, `--->`, plus every
boundary condition — run start and end, adjacent to space, adjacent to a combining mark,
and adjacent to a glyph served by a *different* font from the fallback chain, where the
context genuinely does not exist. The run-boundary and font-boundary cases are the ones
hand-reasoning gets wrong.

**Mono ligatures are `ss01`, never `liga`.** `-> => != === <= >= :: |> // /* **` ligate
only on request. Defaulting them on silently changes what a programmer believes is on
screen and breaks diff alignment. `calt` must additionally *break* ligation across token
boundaries: `--->` must not render as `--` + `->`.

**No `kern` table in Mono or Console at all** — absent, not zeroed, so no shaper can
reintroduce it.

**Sabas Icons** uses COLRv1 with variable colour, plus a `CPAL`-driven palette so the OS
theme recolours icons without reissuing the font. Icons are drawn on strict 16/20/24
grids with 2 px keylines at 1× so they snap.

---

## 9. Sabas Icons — inventory, grid and cost

No icons exist yet, so this section specifies the set rather than inheriting one.

### 9.1 There is an existing list, and it is not optional

The **freedesktop.org Icon Naming Specification** defines ~300 standard icon names across
eleven contexts. Any third-party GTK or Qt application on Sabas OS will look up its icons
by those names — `document-save`, `edit-undo`, `network-wireless-signal-good`. Miss them and
those apps render blank buttons through no fault of their own.

So the inventory is not a blank page: **T1 is the freedesktop spec**, verified against its
current revision rather than from memory.

| fdo context | ≈ names | fdo context | ≈ names |
|---|---|---|---|
| Actions | 120 | Emotes | 15 |
| Status | 45 | Categories | 20 |
| Applications | 35 | Places | 12 |
| Devices | 30 | Emblems | 12 |
| MimeTypes | 30 | Animations | 1 |

### 9.2 Inventory tiers

| Tier | Content | Count |
|---|---|---|
| **T1** | freedesktop Icon Naming Spec — third-party app compatibility | ~300 |
| **T2** | Modern shell: Wi-Fi/cellular signal levels, Bluetooth states, VPN, hotspot, airplane & DND modes, biometrics, screenshot/recording, night light, power profiles, workspaces, tiling layouts, cast, PiP, in-use camera/mic/location indicators | ~180 |
| **T3** | Settings and first-party apps: accounts, updates, sandbox permissions, firewall, containers, package manager, git states, terminal, editor | ~200 |
| **T4** | File-type icons beyond fdo MimeTypes | ~120 |
| **T5** | Extended and long-tail | ~240 |

**1.0 target: T1 + T2 ≈ 480.** T3–T5 post-1.0. For calibration: Material Symbols is ~3,700
and SF Symbols ~6,900 — both representing many years of a dedicated team. 480 is the
smallest number that makes an OS not feel unfinished.

### 9.3 Two delivery channels, one source

- **SVG icon theme** — the full set, laid out per the fdo Icon Theme Specification with
  per-size directories. This is the primary, app-facing asset; third-party toolkits expect
  it and cannot consume a font.
- **`Sabas Icons` COLRv1 font** — only the subset that renders *inline with text* in shell
  chrome: roughly **120 icons**. Menu items, buttons, status bars, breadcrumbs.

Splitting these is a large scope reduction and it is also simply correct. A font is the
right delivery for glyphs that sit in a text run and must share its baseline, weight and
colour; it is the wrong delivery for a 48 px application icon in a launcher.

### 9.4 Icons need no bitmap strikes — the grid does it for free

This is the finding that changes §6.2, so it is worth showing.

Icons are drawn **per target size**, each on its own integer pixel grid, with the em box
equal to the design box: a 16 px icon fills 1000 units and renders at 16 ppem.

| Design size | 1 px = | 1 unit = | keyline rounding error |
|---|---|---|---|
| 16 px | 62.5 u | 0.016 px | ≤ 0.008 px |
| 20 px | 50.0 u | 0.020 px | ≤ 0.010 px |
| 24 px | 41.67 u | 0.024 px | ≤ 0.012 px |

Rounding a keyline to integer units costs at most 0.012 px. **Grid exactness is free.**

Text cannot do this because one x-height must serve every size, and §6.3 showed that is
arithmetically impossible below ~37 ppem. Icons have no such constraint: **each size is an
independent drawing with no cross-size continuity requirement.** That structural difference
is why icons escape the strike problem entirely.

Consequence: the 7,200 icon strike bitmaps implied by the earlier "3 sizes × 4 weights"
assumption **are not needed**. Strikes remain available as a fallback for individual icons
that genuinely cannot be gridded — heavy 45°-off diagonals, small circular arcs — expected
to be a few dozen, not thousands.

### 9.5 The weight ceiling at small sizes

At 1× only integer stroke widths are crisp, which caps how many icon weights can exist:

| Design size | Crisp stroke widths | Usable weights |
|---|---|---|
| 16 px | 1, 2 px | **2** — Regular 1 px, Bold 2 px |
| 20 px | 1, 2, 3 px | 3 |
| 24 px | 1, 2, 3 px | 3 |

**At 16 px you cannot have four distinguishable icon weights.** A 1.5 px stroke is not
crisp at 1×; it resolves as two half-covered pixels and reads as blur, not as an
intermediate weight. Regular and Bold are the guaranteed pair at every size; Light and
SemiBold exist only at 20 and 24.

This also means stroke weight cannot stay a constant fraction of size: Regular is 6.25 % of
the box at 16 px and 8.3 % at 24 px. Do not fix that by going lighter — **fix it with
detail reduction.** A 16 px icon has room for about three distinct strokes, a 24 px icon
about six. The small size is not a scaled-down large one; it is a simpler drawing. This is
what makes per-size work genuinely necessary rather than merely careful.

### 9.6 Cost model and the recommended M6 cut

| Scope | Sizes | Weight masters | Drawings |
|---|---|---|---|
| Naive: 480 icons, 3 sizes, 4 weights | 3 | 4 | 5,760 |
| **Recommended M6: 120 inline icons** | 16, 24 | Regular, Bold | **480** |
| Full SVG theme, T1+T2 = 480 icons | 16, 24 | Regular, Bold | 1,920 |

M6 ships the **font** — 480 drawings, tractable for one designer. The full SVG theme runs
as its own track on the same sources, not gated on M6. 20 px is interpolated from the
16/24 masters, with a strike fallback for any icon that lands visibly off-grid there.

### 9.7 Encoding and the manifest

Icons occupy a Private Use Area range, with `liga`-based name access as a convenience
(typing `document-save` renders the glyph). Neither is the contract.

**The contract is a generated manifest** mapping fdo name → codepoint → glyph name → SVG
theme path, emitted as both JSON and a toolkit header. The OS never hard-codes a PUA
codepoint; it resolves through the manifest, so the range can be renumbered without
breaking callers. Hard-coded PUA values are how icon fonts become impossible to reorganise.

COLRv1 layers use a `CPAL` palette so the OS theme recolours icons without reissuing the
font — including a monochrome palette entry that must remain legible on its own.

### 9.8 Alignment with text

An icon beside a label must look centred on the *lowercase*, not on the baseline. Icon
vertical centre therefore sits at **x-height/2 of Sabas UI at the matching `opsz`** — 270
units at UI x-height 540 — not at 0.5 em. Advance equals the design box with no side
bearings; inline spacing is the caller's padding, not the font's, so a toolkit can set it
per context.

`Sabas Icons` shares `wght` and `GRAD` ranges with `Sabas UI` (§5.1) so a 400-weight icon
sits beside a 400-weight label without looking pasted in.

---

## 10. Spacing and kerning

1. **Spacing derives from parameters** — sidebearings computed from `XTRA` and `XOPQ` via
   HT-Letterspacer-style rules, per family, so spacing tracks weight and optical size
   automatically instead of being re-tuned by hand per master.
2. **Class-based kerning only.** Flat pair kerning is banned from sources: it does not
   survive interpolation review and it rots.
3. Kerning is authored in the **parametric extremes** and interpolated by `varLib` into
   `GPOS` variations — never per named instance.
4. Kern proofs generated across `{Light, Regular, Black} × {Narrow, Normal, Wide} ×
   {opsz min, default, max}`; human review at release only.

---

## 11. Source layout

```
sabas-fonts/
├── sources/
│   ├── sabas-ui/        SabasUI.designspace + parametric UFOs
│   ├── sabas-text/      + discrete `ital` axis, italic UFOs
│   ├── sabas-display/
│   ├── sabas-mono/
│   ├── sabas-icons/     COLRv1 sources, picosvg-normalised SVGs
│   ├── sabas-console/   PSF2 pixel sources + Unicode map tables
│   ├── strikes/         per family/size/weight bitmap sources
│   └── features/
│       ├── _shared/     locl, mark, case, figures, frac
│       └── ui/ text/ display/ mono/
├── adopted/             harmonisation recipes for Noto/Source Han (no vendored binaries)
├── config/              gftools builder yaml, fontconfig templates
├── docs/                this spec, decision log, specimens, per-platform notes
├── tests/
│   ├── shaping/         hb-shape golden files
│   ├── raster/          golden PNGs per family × ppem × mode
│   └── coverage/        shaperglot manifests
├── tools/               strike generator, harmoniser, spacing, proofing
├── fonts/               build output (gitignored)
└── OFL.txt  OFL-FAQ.txt  AUTHORS.txt  CONTRIBUTORS.txt  TRADEMARKS.md
```

Masters are **sparse**: a glyph that doesn't change on an axis is not duplicated into
that axis's master.

---

## 12. Build and QA

**Compile:** `fontc` (Rust) primary via `gftools builder`; `fontmake` runs as a
differential cross-check per §12.1. Strikes are produced and merged post-compile per §6.5,
including the overlay re-application and conflict report — a strike conflict blocks the
build.

### 12.1 Compiler divergence policy

**`fontc` output is always the shipped artefact. `fontmake` is a referee, never a
candidate.** Even where `fontmake` is demonstrably more correct, its output is not
substituted — because the strike patch baselines in §6.5 are fingerprinted against the
rasterisation of a specific binary, so switching artefact source mid-project invalidates
every patch in the repository. A `fontmake`-only correctness win is a bug filed against
`fontc`, not a change of shipping pipeline.

**Prerequisite:** the `cu2qu` conversion error is pinned to one value in the `gftools`
config and passed identically to both compilers. Without that, divergence is guaranteed
and the entire comparison is noise.

**Comparison is on evaluated behaviour, not bytes.** Both compilers legitimately differ in
subtable packing, `gvar` IUP choices, table order and padding while producing identical
text. Sample set: every named instance, every axis min/max corner, plus 16 interior
coordinates from a fixed seed for reproducibility.

#### Tier 0 — hard failure, zero tolerance, no waiver

Semantic identity. Any difference here is a real bug in one compiler.

| Compared | Tolerance |
|---|---|
| Glyph order, glyph names, `cmap` coverage and mappings | exact |
| `hmtx` advance widths, at every sampled coordinate | **0 units** |
| Vertical metrics, `OS/2`, `head`, `post` | exact |
| Axis definitions, ranges, defaults, `STAT`, named instance coordinates | exact |
| `avar` / `avar2` **evaluated** mapping over a sampled input grid | 0 units |
| `hb-shape` output over the golden corpus — glyph IDs, clusters, positions | exact |
| Kerning as **evaluated** by `hb-shape` | 0 units |

The shaping row also covers lookup ordering, so the §8 `calt`-after-`ss01` requirement is
guarded here rather than by comparing lookup indices — which are Tier 2 and allowed to
differ.

#### Tier 1 — tolerance-bounded, waiver possible

Outline geometry, where `cu2qu` may legitimately emit a different number of quadratic
segments. **Point-by-point comparison is invalid** because point counts differ; compare
count-invariant properties instead:

| Metric | Threshold |
|---|---|
| Bounding box per glyph | ≤ 1 unit on each edge |
| Enclosed area per glyph | ≤ 0.05 % relative |
| Centroid per glyph | ≤ 0.5 units in x and y |
| Rasterised coverage at each strike ppem, 1× | max per-pixel Δ ≤ 5/255, mean ≤ 0.5/255 |

The coverage threshold is derived, not chosen: a 1-unit outline shift at 16 ppem is 0.016 px,
which moves an edge pixel's coverage by about 4/255. A divergence that stays under these
bounds cannot change what a user sees at any shipping size.

#### Tier 2 — advisory, never fails the build

Table order and padding, checksums, `head.created`, `gvar`/`HVAR` byte encoding and IUP
choices, `GPOS`/`GSUB` subtable packing, lookup index numbering, file size. Logged in the
build report for debugging; no gate.

#### Escalation

1. **Tier 0 divergence** → hard failure. No override exists. File upstream against the
   diverging compiler; blocks release.
2. **Tier 1 within threshold** → pass, logged.
3. **Tier 1 over threshold** → build fails and emits a `diffenator3` report for the affected
   glyphs. A named reviewer may sign off, which records a **waiver**.
4. **Tier 2** → report only.

**Waivers expire.** Each entry in `config/compiler-divergence-waivers.toml` carries glyph,
tier, measured delta, both compiler versions, reviewer, date, rationale, and an expiry —
whichever comes first of 90 days or the next `fontc` minor version. CI fails on an expired
or unattributed waiver. Expiry is the whole point: an exception that cannot expire is
indistinguishable from having no gate, which is how a tolerance policy quietly becomes a
rubber stamp.

A waiver is scoped to `(glyph, tier, compiler version pair)`. It does not generalise to
other glyphs and does not survive a compiler upgrade.

**Gates — all blocking unless noted:**

| Check | Tool |
|---|---|
| Spec conformance, metrics, naming, `STAT` | `fontspector` |
| Visual regression vs. last tag | `diffenator3` |
| **Golden-raster diff, 1× at every strike ppem** | custom, FreeType harness |
| **Outline path agrees with strike integers** (§6.4) | custom — non-strike glyphs at strike ppem |
| **Monotonicity invariant across approved size list** (§6.4) | custom, published report |
| FreeType version matrix reproducibility | custom, 2.13 → current |
| Language coverage claims | `shaperglot` |
| Shaping stability: features, `calt`, marks, `locl` | `hb-shape` golden files |
| Interpolation compatibility across masters | `fontc` + outline-compat check |
| **Compiler divergence Tier 0** — semantic identity (§12.1) | custom, `fontc` vs `fontmake`, no waiver |
| **Compiler divergence Tier 1** — outline geometry within threshold (§12.1) | custom + `diffenator3`, waiver on sign-off |
| Compiler divergence Tier 2 — encoding and packing | report only, **not blocking** |
| Waiver register: no expired or unattributed entries | custom |
| Static ≡ variable at every named instance | custom |
| Adopted-family harmonisation: metrics, weight calibration | custom |
| Fallback chain resolves every Unicode 17 codepoint | coverage manifest test |

The golden-raster and `hb-shape` suites are the two that matter most. The first is the
only thing that makes "pixel perfect" survive contact with a refactor; the second is the
only thing that stops a `calt` edit from silently breaking Vietnamese mark stacking.

---

## 13. Naming and instances

Families: `Sabas UI`, `Sabas Text`, `Sabas Display`, `Sabas Mono`, `Sabas Icons`,
`Sabas Console`, plus the adopted `Sabas Han` / `Arabic` / `Indic` / `Emoji` / `Symbols`.

Named instances: Thin 100 → Black 900 (UI adds Ultra 1000), × upright/italic, × width
where the family has a `wdth` axis (Condensed / SemiCondensed / Normal / Expanded).

`name` table: typographic family in ID 16, typographic subfamily in ID 17, RIBBI-split
into IDs 1/2 for legacy consumers. `STAT` carries every axis, format 2 ranges for weight,
format 3 linked values for regular↔bold and upright↔italic. `fsType` = 0.

---

## 14. Licensing

OFL 1.1, **no Reserved Font Name** — deliberate, so downstream distributions and the
Nerd Fonts project can patch `Sabas Mono` without a rename fight.

For every adopted family: carry the upstream OFL text, list original designers in
`AUTHORS.txt`, and record the exact upstream commit in the harmonisation recipe.
Redistribution under a `Sabas` name is permitted precisely because those upstreams
have no RFN — verify this per font before adopting, since it is not universal.

`Sabas` as an OS and font name should get a trademark clearance check (note proximity to
`Saba` and to Sabon-adjacent names), and a 4-character `OS/2.achVendID` registered with
Microsoft.

---

## 15. Roadmap

| Milestone | Content |
|---|---|
| **M0** | Spec approved; axis ranges and parametric definitions frozen; name cleared |
| **M1** | Pipeline green: Sabas UI, T1, `wght` only. **Patch format v1 frozen (§6.5) before any strike is hand-corrected.** Strike toolchain (§6.5 stages 1–5) built and proven on UI Regular at 11/13/16 px, including a deliberate outline change to exercise the conflict path. Golden-raster and §6.4 conformance gates live. Approved size list ratified against the §6.3 class table. |
| **M2** | Sabas UI full design space + `avar2`, T2, **complete strike matrix** — 5 sizes × 4 weights |
| **M3** | Sabas Mono: texture healing, ligature set, T4, strikes; **Sabas Console** all three sizes |
| **M4** | Sabas Text + Display, drawn italics, T5 (no strikes — see §6.2 tier 3) |
| **M5** | T3 Cyrillic + Greek across all in-house families, incl. strike extension |
| **M6** | Sabas Icons: 120 inline icons × 16/24 px × Regular/Bold = 480 drawings (§9.6), COLRv1 + `CPAL`, manifest emitted. Harmonised adopted families, fallback chain. |
| **M6′** | *Parallel track, not gated on M6* — full SVG icon theme, T1 (fdo, ~300) then T2 (~180), same sources |
| **M7** | 1.0: specimens, per-platform rendering notes, OS integration docs |

**Two deliberate sequencing choices.** The strike *toolchain* is proven at M1 on three
sizes of one weight, before the design space opens up — building it at M2 alongside the
full matrix means discovering the overlay-conflict problem with 4,600 bitmaps already
hand-corrected. And Console lands at M3 because it is needed the first time the kernel
panics, which will be long before M6.

---

## 16. Open questions

**Resolved 2026-09-17:** 1× ships at launch (strikes are critical path, M1 onward) ·
compositor blends in linear light (§3.1 satisfiable as written; stem darkening on).

1. **Bootstrap the icon artwork, or draw all 480?** The only icon question left open, and
   it is a brand decision rather than a technical one. Lucide (ISC), Phosphor (MIT),
   Material Symbols (Apache-2.0) and Remix Icon (Apache-2.0) are all permissively licensed
   and legally adoptable. My recommendation: use one as a **coverage checklist only** and
   draw the ~120 inline font icons yourself, because shell icons are the most visible brand
   surface an OS has and an adopted set makes Sabas OS read as a Material theme. Bootstrapping
   is more defensible for the long tail — T4 file types and T5 — where recognisability
   matters more than originality.
2. **Which UI px sizes does the OS design system actually use?** §6.2 assumes 11, 12, 13,
   14, 16, 18, 20. Two reasons to trim: each size is ~920 hand-reviewable bitmaps per
   family, and per §6.3 sizes **12 and 14 are Class C on x-height while 12, 13, 16 and 20
   are Class C on cap height** — they cannot be brought on-grid by `opsz` at all. My
   recommendation is **11 / 13 / 16 / 20**, which drops the two weakest members, keeps
   every step visually distinguishable at 1×, and cuts strike volume ~40 %. Needs the
   design system's agreement before M1 closes.
3. **Vertical Japanese** — needed? If yes, `vert`/`vrt2` and vertical metrics for the
   adopted Han family become a real subsystem rather than a passthrough.
4. **Accessibility weight step.** A system "bolder text" setting maps naturally to `GRAD`
   or to `wght`; `GRAD` avoids reflow but is a smaller effect. Note it also multiplies
   strike count if the bolder setting must be pixel-perfect at 1× too.
5. **Text italic slope 9.5°** vs. UI `slnt` −10 — test that the two don't look
   accidentally different when mixed in one line.
6. **`opsz` default for Mono is 13** — assumes a typical editor default; measure against
   real configs before freezing.
7. **Subpixel (LCD) rendering on by default at 1×?** FIR5 filtering is specced, but it
   assumes RGB stripe geometry. If Sabas OS targets panels with other subpixel layouts,
   the OS needs per-display geometry detection or grayscale AA as the safe default.
