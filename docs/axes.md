# Sabas UI — Axis Architecture (§5.2)

## Registered Axes

| Tag  | Name         | Min  | Default | Max  | Notes |
|------|--------------|------|---------|------|-------|
| wght | Weight       | 100  | 400     | 1000 | |
| wdth | Width        | 75   | 100     | 125  | |
| opsz | Optical Size | 10   | 16      | 32   | |
| GRAD | Grade        | −200 | 0       | 150  | Advance-neutral |
| slnt | Slant        | −10  | 0       | 0    | |

## Parametric Axes (hidden, avar2 inputs)

| Tag  | Name             | Min  | Default | Max  | Controls |
|------|------------------|------|---------|------|----------|
| XOPQ | X Opaque         | 20   | 88      | 200  | Stem width (x) |
| YOPQ | Y Opaque         | 17   | 76      | 172  | Stem width (y) |
| XTRA | X Transparent    | −100 | 0       | 100  | Counter/advance width |
| YTLC | Y Transparent LC | 460  | 540     | 580  | x-height |
| YTUC | Y Transparent UC | 640  | 720     | 760  | cap-height |

## avar2 Mappings

avar2 maps registered axis positions to parametric axis positions.
The parametric masters sit at their parametric coordinates so gvar
accumulates real deltas — driving YTLC actually changes x-height.

| Registered input | Parametric outputs |
|------------------|--------------------|
| wght=100         | XOPQ=20, YOPQ=17, XTRA=+30 |
| wght=400         | XOPQ=88, YOPQ=76, XTRA=0 (default) |
| wght=1000        | XOPQ=200, YOPQ=172, XTRA=−60 |
| GRAD=−200        | XOPQ=−30Δ, YOPQ=−26Δ, XTRA=+30Δ |
| GRAD=+150        | XOPQ=+22Δ, YOPQ=+19Δ, XTRA=−22Δ |
| opsz=10          | YTLC=570, XTRA=+20, YOPQ=−8Δ |
| opsz=32          | YTLC=510, XTRA=−10, YOPQ=+6Δ |
| wdth=75          | XTRA=−80, XOPQ=−8Δ |
| wdth=125         | XTRA=+80, XOPQ=+4Δ |

## §6.3 YTLC and Pixel Grid

The per-size YTLC nudge via opsz→YTLC closes pixel-grid gaps at small ppem.
At ppem=11, YTLC=570 raises the x-height by ~5.6% so the crossbar of 'e'
lands on a full pixel row rather than straddling two rows.
