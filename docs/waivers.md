# Sabas Font — Waiver Register

Waivers document known deviations from a QA check that are intentional. Each entry
names the check, the reason and an expiry no more than 90 days out. `tools/run_qa.py`
reads this table: a waived check is excluded from the fontbakery run, and the run
fails once a waiver has expired, so an exception cannot quietly become permanent.

## Active Waivers

| ID | Check | Reason | Expires |
|----|-------|--------|---------|
| W-002 | `linegaps` | Brief §4.2 sets hhea lineGap to 200 (a 1.20 em line box) in every family so mixed-script lines do not change height. | 2026-12-18 |
| W-003 | `typoascender_exceeds_Agrave` | Brief §4.2 fixes sTypoAscender at 800. usWinAscent (1010) covers the tallest stacked accent, so nothing clips. | 2026-12-18 |
| W-004 | `contour_count` | Counts are inferred from other families' drawings. Sabas builds letters from strokes and composites, so its counts differ without being wrong. | 2026-12-18 |
| W-005 | `alt_caron` | After overlap removal the static instances fold tcaron into a single outline, so the check cannot inspect it. The source glyph is base plus the `caronalt` tick and has been checked by eye. | 2026-12-18 |
| W-006 | `mandatory_avar_table` | Axis progress is set by the masters, which sit at the named weights and widths, not remapped by an avar table. | 2026-12-18 |
| W-007 | `opentype/monospace` | Only the hhea.numberOfHMetrics recommendation remains; the PANOSE, fixed-pitch and advance checks pass. | 2026-12-18 |
| W-008 | `overlapping_path_segments`, `unreachable_glyphs`, `opentype/points_out_of_bounds` | A few duplicate segments left where overlap removal merges strokes, `caronalt` (only reachable as a component) in statics, and scaled figure components whose points are not extremes. None affect rendering. | 2026-12-18 |
| W-009 | `gpos_kerning_info` | Sabas Mono has no kern feature by design (brief §8): a fixed grid has nothing to kern. | 2026-12-18 |

## Resolved Waivers

| ID | Check | Resolution |
|----|-------|------------|
| W-001 | `name/no_copyright_at_first` | Copyright now reads the first line of `OFL.txt`, so the OFL header and the name table agree. |

## Adding a Waiver

1. Add a row to the Active Waivers table with an expiry no more than 90 days out.
2. Use the check's fontbakery ID (the last path segment is enough) in the Check column.
3. Renew or resolve it before it expires; `tools/run_qa.py` fails on an expired waiver.
