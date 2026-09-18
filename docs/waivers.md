# Sabas Font — Waiver Register

Waivers document known deviations from the spec that are intentional or
pending resolution. Each entry must include: check ID, reason, expiry.

## Active Waivers

| ID | Check | Reason | Expires |
|----|-------|--------|---------|
| W-001 | `com.google.fonts/check/name/no_copyright_at_first` | Copyright line format differs from Google Fonts convention; OFL header is correct | 2025-06-01 |

## Resolved Waivers

_(none)_

## Adding a Waiver

1. Add a row to the Active Waivers table above.
2. Add a corresponding `WARN` override in `config/fontspector.toml`.
3. Open a tracking issue referencing the waiver ID.
4. Set an expiry date no more than 90 days out.
