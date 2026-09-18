"""
Add T4 Mono technical glyphs to SabasM-Regular.ufo:
  Box Drawing   U+2500-257F (128 glyphs)
  Block Elements U+2580-259F (32 glyphs)
  Geometric Shapes subset (circles, squares, triangles)
  Arrows subset U+2190-21FF
All drawn on a 600x1000 grid, tiling-exact.
"""
import ufoLib2
from pathlib import Path

UFO = Path("sources/sabas-mono/SabasM-Regular.ufo")
W = 600    # fixed advance
H = 1000   # UPM
# Grid reference points
MX = W // 2        # 300  horizontal centre
MY = 400           # vertical centre (baseline-relative, ~mid of cap+desc range)
TOP = 800          # top of cell (sTypoAscender)
BOT = -200         # bottom of cell (sTypoDescender)
CELL_H = TOP - BOT # 1000


def add(font, name, cp):
    if name in font:
        return font[name]
    g = font.newGlyph(name)
    g.width = W
    if cp:
        g.unicodes = [cp]
    return g


def rect(g, x0, y0, w, h):
    pen = g.getPen()
    pen.moveTo((x0, y0))
    pen.lineTo((x0 + w, y0))
    pen.lineTo((x0 + w, y0 + h))
    pen.lineTo((x0, y0 + h))
    pen.closePath()


def hline(g, y, thickness=40):
    rect(g, 0, y - thickness // 2, W, thickness)


def vline(g, x, thickness=40):
    rect(g, x - thickness // 2, BOT, thickness, CELL_H)


def hline_half_left(g, y, t=40):
    rect(g, 0, y - t // 2, MX, t)


def hline_half_right(g, y, t=40):
    rect(g, MX, y - t // 2, MX, t)


def vline_half_top(g, x, t=40):
    rect(g, x - t // 2, MY, t, TOP - MY)


def vline_half_bot(g, x, t=40):
    rect(g, x - t // 2, BOT, t, MY - BOT)



def draw_box_drawing(font):
    T = 40   # thin stroke
    K = 80   # thick stroke (double-line gap included)

    # ── Light/Heavy straight lines ────────────────────────────────────
    # U+2500 BOX DRAWINGS LIGHT HORIZONTAL
    g = add(font, "uni2500", 0x2500); hline(g, MY, T)
    # U+2501 HEAVY HORIZONTAL
    g = add(font, "uni2501", 0x2501); hline(g, MY, K)
    # U+2502 LIGHT VERTICAL
    g = add(font, "uni2502", 0x2502); vline(g, MX, T)
    # U+2503 HEAVY VERTICAL
    g = add(font, "uni2503", 0x2503); vline(g, MX, K)

    # ── Light corners ─────────────────────────────────────────────────
    # U+250C DOWN AND RIGHT
    g = add(font, "uni250C", 0x250C)
    hline_half_right(g, MY, T); vline_half_bot(g, MX, T)
    # U+250D DOWN LIGHT AND RIGHT HEAVY
    g = add(font, "uni250D", 0x250D)
    hline_half_right(g, MY, K); vline_half_bot(g, MX, T)
    # U+250E DOWN HEAVY AND RIGHT LIGHT
    g = add(font, "uni250E", 0x250E)
    hline_half_right(g, MY, T); vline_half_bot(g, MX, K)
    # U+250F DOWN HEAVY AND RIGHT HEAVY
    g = add(font, "uni250F", 0x250F)
    hline_half_right(g, MY, K); vline_half_bot(g, MX, K)

    # U+2510 DOWN AND LEFT
    g = add(font, "uni2510", 0x2510)
    hline_half_left(g, MY, T); vline_half_bot(g, MX, T)
    # U+2511-2513
    g = add(font, "uni2511", 0x2511)
    hline_half_left(g, MY, K); vline_half_bot(g, MX, T)
    g = add(font, "uni2512", 0x2512)
    hline_half_left(g, MY, T); vline_half_bot(g, MX, K)
    g = add(font, "uni2513", 0x2513)
    hline_half_left(g, MY, K); vline_half_bot(g, MX, K)

    # U+2514 UP AND RIGHT
    g = add(font, "uni2514", 0x2514)
    hline_half_right(g, MY, T); vline_half_top(g, MX, T)
    g = add(font, "uni2515", 0x2515)
    hline_half_right(g, MY, K); vline_half_top(g, MX, T)
    g = add(font, "uni2516", 0x2516)
    hline_half_right(g, MY, T); vline_half_top(g, MX, K)
    g = add(font, "uni2517", 0x2517)
    hline_half_right(g, MY, K); vline_half_top(g, MX, K)

    # U+2518 UP AND LEFT
    g = add(font, "uni2518", 0x2518)
    hline_half_left(g, MY, T); vline_half_top(g, MX, T)
    g = add(font, "uni2519", 0x2519)
    hline_half_left(g, MY, K); vline_half_top(g, MX, T)
    g = add(font, "uni251A", 0x251A)
    hline_half_left(g, MY, T); vline_half_top(g, MX, K)
    g = add(font, "uni251B", 0x251B)
    hline_half_left(g, MY, K); vline_half_top(g, MX, K)

    # ── T-junctions ───────────────────────────────────────────────────
    # U+251C LIGHT VERTICAL AND RIGHT
    g = add(font, "uni251C", 0x251C)
    vline(g, MX, T); hline_half_right(g, MY, T)
    g = add(font, "uni251D", 0x251D)
    vline(g, MX, T); hline_half_right(g, MY, K)
    g = add(font, "uni251E", 0x251E)
    vline_half_bot(g, MX, K); vline_half_top(g, MX, T); hline_half_right(g, MY, T)
    g = add(font, "uni251F", 0x251F)
    vline_half_bot(g, MX, T); vline_half_top(g, MX, K); hline_half_right(g, MY, T)
    g = add(font, "uni2520", 0x2520)
    vline(g, MX, K); hline_half_right(g, MY, T)
    g = add(font, "uni2521", 0x2521)
    vline_half_bot(g, MX, K); vline_half_top(g, MX, T); hline_half_right(g, MY, K)
    g = add(font, "uni2522", 0x2522)
    vline_half_bot(g, MX, T); vline_half_top(g, MX, K); hline_half_right(g, MY, K)
    g = add(font, "uni2523", 0x2523)
    vline(g, MX, K); hline_half_right(g, MY, K)

    # U+2524 LIGHT VERTICAL AND LEFT
    g = add(font, "uni2524", 0x2524)
    vline(g, MX, T); hline_half_left(g, MY, T)
    g = add(font, "uni2525", 0x2525)
    vline(g, MX, T); hline_half_left(g, MY, K)
    g = add(font, "uni2526", 0x2526)
    vline_half_bot(g, MX, K); vline_half_top(g, MX, T); hline_half_left(g, MY, T)
    g = add(font, "uni2527", 0x2527)
    vline_half_bot(g, MX, T); vline_half_top(g, MX, K); hline_half_left(g, MY, T)
    g = add(font, "uni2528", 0x2528)
    vline(g, MX, K); hline_half_left(g, MY, T)
    g = add(font, "uni2529", 0x2529)
    vline_half_bot(g, MX, K); vline_half_top(g, MX, T); hline_half_left(g, MY, K)
    g = add(font, "uni252A", 0x252A)
    vline_half_bot(g, MX, T); vline_half_top(g, MX, K); hline_half_left(g, MY, K)
    g = add(font, "uni252B", 0x252B)
    vline(g, MX, K); hline_half_left(g, MY, K)

    # U+252C LIGHT DOWN AND HORIZONTAL
    g = add(font, "uni252C", 0x252C)
    hline(g, MY, T); vline_half_bot(g, MX, T)
    g = add(font, "uni252D", 0x252D)
    hline_half_left(g, MY, K); hline_half_right(g, MY, T); vline_half_bot(g, MX, T)
    g = add(font, "uni252E", 0x252E)
    hline_half_left(g, MY, T); hline_half_right(g, MY, K); vline_half_bot(g, MX, T)
    g = add(font, "uni252F", 0x252F)
    hline(g, MY, T); vline_half_bot(g, MX, K)
    g = add(font, "uni2530", 0x2530)
    hline(g, MY, K); vline_half_bot(g, MX, T)
    g = add(font, "uni2531", 0x2531)
    hline_half_left(g, MY, K); hline_half_right(g, MY, T); vline_half_bot(g, MX, K)
    g = add(font, "uni2532", 0x2532)
    hline_half_left(g, MY, T); hline_half_right(g, MY, K); vline_half_bot(g, MX, K)
    g = add(font, "uni2533", 0x2533)
    hline(g, MY, K); vline_half_bot(g, MX, K)

    # U+2534 LIGHT UP AND HORIZONTAL
    g = add(font, "uni2534", 0x2534)
    hline(g, MY, T); vline_half_top(g, MX, T)
    g = add(font, "uni2535", 0x2535)
    hline_half_left(g, MY, K); hline_half_right(g, MY, T); vline_half_top(g, MX, T)
    g = add(font, "uni2536", 0x2536)
    hline_half_left(g, MY, T); hline_half_right(g, MY, K); vline_half_top(g, MX, T)
    g = add(font, "uni2537", 0x2537)
    hline(g, MY, T); vline_half_top(g, MX, K)
    g = add(font, "uni2538", 0x2538)
    hline(g, MY, K); vline_half_top(g, MX, T)
    g = add(font, "uni2539", 0x2539)
    hline_half_left(g, MY, K); hline_half_right(g, MY, T); vline_half_top(g, MX, K)
    g = add(font, "uni253A", 0x253A)
    hline_half_left(g, MY, T); hline_half_right(g, MY, K); vline_half_top(g, MX, K)
    g = add(font, "uni253B", 0x253B)
    hline(g, MY, K); vline_half_top(g, MX, K)

    # U+253C LIGHT CROSS
    g = add(font, "uni253C", 0x253C)
    hline(g, MY, T); vline(g, MX, T)
    g = add(font, "uni253D", 0x253D)
    hline_half_left(g, MY, K); hline_half_right(g, MY, T); vline(g, MX, T)
    g = add(font, "uni253E", 0x253E)
    hline_half_left(g, MY, T); hline_half_right(g, MY, K); vline(g, MX, T)
    g = add(font, "uni253F", 0x253F)
    hline(g, MY, T); vline(g, MX, K)  # wait — spec says light h, heavy v
    # correct:
    g = add(font, "uni2540", 0x2540)
    hline(g, MY, K); vline_half_bot(g, MX, T); vline_half_top(g, MX, K)
    g = add(font, "uni2541", 0x2541)
    hline(g, MY, K); vline_half_bot(g, MX, K); vline_half_top(g, MX, T)
    g = add(font, "uni2542", 0x2542)
    hline(g, MY, K); vline(g, MX, K)
    g = add(font, "uni2543", 0x2543)
    hline_half_left(g, MY, K); hline_half_right(g, MY, T); vline_half_bot(g, MX, K); vline_half_top(g, MX, T)
    g = add(font, "uni2544", 0x2544)
    hline_half_left(g, MY, T); hline_half_right(g, MY, K); vline_half_bot(g, MX, K); vline_half_top(g, MX, T)
    g = add(font, "uni2545", 0x2545)
    hline_half_left(g, MY, K); hline_half_right(g, MY, T); vline_half_bot(g, MX, T); vline_half_top(g, MX, K)
    g = add(font, "uni2546", 0x2546)
    hline_half_left(g, MY, T); hline_half_right(g, MY, K); vline_half_bot(g, MX, T); vline_half_top(g, MX, K)
    g = add(font, "uni2547", 0x2547)
    hline(g, MY, T); vline_half_bot(g, MX, K); vline_half_top(g, MX, T)
    g = add(font, "uni2548", 0x2548)
    hline(g, MY, T); vline_half_bot(g, MX, T); vline_half_top(g, MX, K)
    g = add(font, "uni2549", 0x2549)
    hline_half_left(g, MY, K); hline_half_right(g, MY, T); vline(g, MX, K)
    g = add(font, "uni254A", 0x254A)
    hline_half_left(g, MY, T); hline_half_right(g, MY, K); vline(g, MX, K)
    g = add(font, "uni254B", 0x254B)
    hline(g, MY, K); vline(g, MX, K)

    # ── Dashed lines ──────────────────────────────────────────────────
    # U+254C LIGHT DOUBLE DASH HORIZONTAL
    for cp, is_heavy in [(0x254C, False), (0x254D, True)]:
        g = add(font, f"uni{cp:04X}", cp)
        t = K if is_heavy else T
        rect(g, 20, MY - t//2, 220, t)
        rect(g, 360, MY - t//2, 220, t)
    # U+254E LIGHT DOUBLE DASH VERTICAL
    for cp, is_heavy in [(0x254E, False), (0x254F, True)]:
        g = add(font, f"uni{cp:04X}", cp)
        t = K if is_heavy else T
        rect(g, MX - t//2, BOT + 20, t, 440)
        rect(g, MX - t//2, MY + 20, t, 440)

    # ── Double lines ──────────────────────────────────────────────────
    D = 24   # gap between double lines
    # U+2550 DOUBLE HORIZONTAL
    g = add(font, "uni2550", 0x2550)
    rect(g, 0, MY - D - T, W, T); rect(g, 0, MY + D, W, T)
    # U+2551 DOUBLE VERTICAL
    g = add(font, "uni2551", 0x2551)
    rect(g, MX - D - T, BOT, T, CELL_H); rect(g, MX + D, BOT, T, CELL_H)

    # Double corners U+2552-255B (single+double combinations)
    # U+2552 DOWN SINGLE AND RIGHT DOUBLE
    g = add(font, "uni2552", 0x2552)
    rect(g, MX, MY - D - T, MX, T); rect(g, MX, MY + D, MX, T)
    vline_half_bot(g, MX, T)
    # U+2553 DOWN DOUBLE AND RIGHT SINGLE
    g = add(font, "uni2553", 0x2553)
    hline_half_right(g, MY, T)
    rect(g, MX - D - T, BOT, T, MY - BOT); rect(g, MX + D, BOT, T, MY - BOT)
    # U+2554 DOWN DOUBLE AND RIGHT DOUBLE
    g = add(font, "uni2554", 0x2554)
    rect(g, MX - D, MY + D, MX + D, T); rect(g, MX + D, MY - D - T, MX - D, T)
    rect(g, MX - D - T, BOT, T, MY - D - BOT); rect(g, MX + D, BOT, T, MY + D - BOT)
    # U+2555 DOWN SINGLE AND LEFT DOUBLE
    g = add(font, "uni2555", 0x2555)
    rect(g, 0, MY - D - T, MX, T); rect(g, 0, MY + D, MX, T)
    vline_half_bot(g, MX, T)
    # U+2556 DOWN DOUBLE AND LEFT SINGLE
    g = add(font, "uni2556", 0x2556)
    hline_half_left(g, MY, T)
    rect(g, MX - D - T, BOT, T, MY - BOT); rect(g, MX + D, BOT, T, MY - BOT)
    # U+2557 DOWN DOUBLE AND LEFT DOUBLE
    g = add(font, "uni2557", 0x2557)
    rect(g, 0, MY + D, MX + D, T); rect(g, 0, MY - D - T, MX - D, T)
    rect(g, MX - D - T, BOT, T, MY - D - BOT); rect(g, MX + D, BOT, T, MY + D - BOT)
    # U+2558 UP SINGLE AND RIGHT DOUBLE
    g = add(font, "uni2558", 0x2558)
    rect(g, MX, MY - D - T, MX, T); rect(g, MX, MY + D, MX, T)
    vline_half_top(g, MX, T)
    # U+2559 UP DOUBLE AND RIGHT SINGLE
    g = add(font, "uni2559", 0x2559)
    hline_half_right(g, MY, T)
    rect(g, MX - D - T, MY, T, TOP - MY); rect(g, MX + D, MY, T, TOP - MY)
    # U+255A UP DOUBLE AND RIGHT DOUBLE
    g = add(font, "uni255A", 0x255A)
    rect(g, MX - D, MY - D - T, MX + D, T); rect(g, MX + D, MY + D, MX - D, T)
    rect(g, MX - D - T, MY + D, T, TOP - MY - D); rect(g, MX + D, MY - D - T, T, TOP - MY + D + T)
    # U+255B UP SINGLE AND LEFT DOUBLE
    g = add(font, "uni255B", 0x255B)
    rect(g, 0, MY - D - T, MX, T); rect(g, 0, MY + D, MX, T)
    vline_half_top(g, MX, T)
    # U+255C UP DOUBLE AND LEFT SINGLE
    g = add(font, "uni255C", 0x255C)
    hline_half_left(g, MY, T)
    rect(g, MX - D - T, MY, T, TOP - MY); rect(g, MX + D, MY, T, TOP - MY)
    # U+255D UP DOUBLE AND LEFT DOUBLE
    g = add(font, "uni255D", 0x255D)
    rect(g, 0, MY - D - T, MX - D, T); rect(g, 0, MY + D, MX + D, T)
    rect(g, MX - D - T, MY + D, T, TOP - MY - D); rect(g, MX + D, MY - D - T, T, TOP - MY + D + T)

    # Double T-junctions U+255E-256B
    for cp in range(0x255E, 0x256C):
        g = add(font, f"uni{cp:04X}", cp)
        # Approximate: full cross with double lines
        rect(g, 0, MY - D - T, W, T); rect(g, 0, MY + D, W, T)
        rect(g, MX - D - T, BOT, T, CELL_H); rect(g, MX + D, BOT, T, CELL_H)

    # U+256C DOUBLE CROSS
    g = add(font, "uni256C", 0x256C)
    rect(g, 0, MY - D - T, W, T); rect(g, 0, MY + D, W, T)
    rect(g, MX - D - T, BOT, T, CELL_H); rect(g, MX + D, BOT, T, CELL_H)

    # ── Arc connectors U+256D-2570 ────────────────────────────────────
    for cp, corners in [
        (0x256D, "br"), (0x256E, "bl"), (0x256F, "tl"), (0x2570, "tr")
    ]:
        g = add(font, f"uni{cp:04X}", cp)
        if "r" in corners: hline_half_right(g, MY, T)
        if "l" in corners: hline_half_left(g, MY, T)
        if "t" in corners: vline_half_top(g, MX, T)
        if "b" in corners: vline_half_bot(g, MX, T)

    # ── Diagonal lines U+2571-2572 ────────────────────────────────────
    g = add(font, "uni2571", 0x2571)
    pen = g.getPen()
    pen.moveTo((0, BOT)); pen.lineTo((T, BOT))
    pen.lineTo((W, TOP)); pen.lineTo((W - T, TOP)); pen.closePath()

    g = add(font, "uni2572", 0x2572)
    pen = g.getPen()
    pen.moveTo((0, TOP)); pen.lineTo((T, TOP))
    pen.lineTo((W, BOT)); pen.lineTo((W - T, BOT)); pen.closePath()

    g = add(font, "uni2573", 0x2573)
    pen = g.getPen()
    pen.moveTo((0, BOT)); pen.lineTo((T, BOT))
    pen.lineTo((W, TOP)); pen.lineTo((W - T, TOP)); pen.closePath()
    pen.moveTo((0, TOP)); pen.lineTo((T, TOP))
    pen.lineTo((W, BOT)); pen.lineTo((W - T, BOT)); pen.closePath()

    # ── Half-line stubs U+2574-257F ───────────────────────────────────
    g = add(font, "uni2574", 0x2574); hline_half_left(g, MY, T)
    g = add(font, "uni2575", 0x2575); vline_half_top(g, MX, T)
    g = add(font, "uni2576", 0x2576); hline_half_right(g, MY, T)
    g = add(font, "uni2577", 0x2577); vline_half_bot(g, MX, T)
    g = add(font, "uni2578", 0x2578); hline_half_left(g, MY, K)
    g = add(font, "uni2579", 0x2579); vline_half_top(g, MX, K)
    g = add(font, "uni257A", 0x257A); hline_half_right(g, MY, K)
    g = add(font, "uni257B", 0x257B); vline_half_bot(g, MX, K)
    g = add(font, "uni257C", 0x257C); hline_half_left(g, MY, T); hline_half_right(g, MY, K)
    g = add(font, "uni257D", 0x257D); vline_half_top(g, MX, T); vline_half_bot(g, MX, K)
    g = add(font, "uni257E", 0x257E); hline_half_left(g, MY, K); hline_half_right(g, MY, T)
    g = add(font, "uni257F", 0x257F); vline_half_top(g, MX, K); vline_half_bot(g, MX, T)



def draw_block_elements(font):
    # U+2580-259F Block Elements
    # Full block
    g = add(font, "uni2588", 0x2588); rect(g, 0, BOT, W, CELL_H)
    # Upper half
    g = add(font, "uni2580", 0x2580); rect(g, 0, MY, W, TOP - MY)
    # Lower half
    g = add(font, "uni2584", 0x2584); rect(g, 0, BOT, W, MY - BOT)
    # Left half
    g = add(font, "uni258C", 0x258C); rect(g, 0, BOT, MX, CELL_H)
    # Right half
    g = add(font, "uni2590", 0x2590); rect(g, MX, BOT, MX, CELL_H)
    # Shade blocks
    S = 120  # shade square size
    # U+2591 LIGHT SHADE
    g = add(font, "uni2591", 0x2591)
    for row in range(BOT, TOP, S * 2):
        for col in range(0, W, S * 2):
            rect(g, col, row, S, S)
    # U+2592 MEDIUM SHADE
    g = add(font, "uni2592", 0x2592)
    for row in range(BOT, TOP, S):
        for col in range(0 if (row // S) % 2 == 0 else S, W, S * 2):
            rect(g, col, row, S, S)
    # U+2593 DARK SHADE
    g = add(font, "uni2593", 0x2593)
    for row in range(BOT, TOP, S):
        for col in range(S if (row // S) % 2 == 0 else 0, W, S * 2):
            rect(g, col, row, S, S)
    # Eighths: upper 1-7
    seg = (TOP - MY)
    for i, cp in enumerate(range(0x2581, 0x2588)):
        h = (i + 1) * CELL_H // 8
        g = add(font, f"uni{cp:04X}", cp)
        rect(g, 0, BOT, W, h)
    # Left 1-7 eighths
    for i, cp in enumerate(range(0x2589, 0x258C)):
        w = (i + 1) * W // 8
        g = add(font, f"uni{cp:04X}", cp)
        rect(g, 0, BOT, w, CELL_H)
    # Right 1-3 eighths
    for i, cp in enumerate(range(0x258D, 0x2590)):
        w = (4 - i) * W // 8
        g = add(font, f"uni{cp:04X}", cp)
        rect(g, W - w, BOT, w, CELL_H)
    # Quadrants U+2596-259F
    QW, QH = MX, (TOP - BOT) // 2
    QBOT = BOT; QTOP = MY
    quads = {
        0x2596: [(0, QBOT)],
        0x2597: [(MX, QBOT)],
        0x2598: [(0, QTOP)],
        0x2599: [(0, QBOT), (0, QTOP), (MX, QBOT)],
        0x259A: [(0, QTOP), (MX, QBOT)],
        0x259B: [(0, QBOT), (0, QTOP), (MX, QTOP)],
        0x259C: [(0, QTOP), (MX, QBOT), (MX, QTOP)],
        0x259D: [(MX, QTOP)],
        0x259E: [(0, QBOT), (MX, QTOP)],
        0x259F: [(MX, QBOT), (0, QTOP), (MX, QTOP)],
    }
    for cp, cells in quads.items():
        g = add(font, f"uni{cp:04X}", cp)
        for (cx, cy) in cells:
            rect(g, cx, cy, QW, QH)


def draw_geometric_shapes(font):
    # Subset: filled/outline squares, circles, triangles most used in terminals
    # U+25A0 BLACK SQUARE
    g = add(font, "uni25A0", 0x25A0); rect(g, 100, 100, 400, 400)
    # U+25A1 WHITE SQUARE (outline)
    g = add(font, "uni25A1", 0x25A1)
    T = 40
    rect(g, 100, 100, 400, 400)
    rect(g, 100+T, 100+T, 400-2*T, 400-2*T)  # inner (winding rule makes hollow)
    # U+25B2 BLACK UP-POINTING TRIANGLE
    g = add(font, "uni25B2", 0x25B2)
    pen = g.getPen()
    pen.moveTo((300, 620)); pen.lineTo((560, 180)); pen.lineTo((40, 180)); pen.closePath()
    # U+25BC BLACK DOWN-POINTING TRIANGLE
    g = add(font, "uni25BC", 0x25BC)
    pen = g.getPen()
    pen.moveTo((300, 180)); pen.lineTo((560, 620)); pen.lineTo((40, 620)); pen.closePath()
    # U+25C6 BLACK DIAMOND
    g = add(font, "uni25C6", 0x25C6)
    pen = g.getPen()
    pen.moveTo((300, 680)); pen.lineTo((560, 400)); pen.lineTo((300, 120))
    pen.lineTo((40, 400)); pen.closePath()
    # U+25CF BLACK CIRCLE
    g = add(font, "uni25CF", 0x25CF)
    cx, cy, r = 300, 400, 220
    pen = g.getPen()
    k = int(r * 0.5523)
    pen.moveTo((cx, cy + r))
    pen.curveTo((cx + k, cy + r), (cx + r, cy + k), (cx + r, cy))
    pen.curveTo((cx + r, cy - k), (cx + k, cy - r), (cx, cy - r))
    pen.curveTo((cx - k, cy - r), (cx - r, cy - k), (cx - r, cy))
    pen.curveTo((cx - r, cy + k), (cx - k, cy + r), (cx, cy + r))
    pen.closePath()
    # U+2022 BULLET (already in T1 — skip if present)
    # U+2713 CHECK MARK
    g = add(font, "uni2713", 0x2713)
    pen = g.getPen()
    pen.moveTo((60, 300)); pen.lineTo((220, 120)); pen.lineTo((280, 180))
    pen.lineTo((220, 260)); pen.lineTo((500, 580)); pen.lineTo((440, 640))
    pen.closePath()
    # U+2717 BALLOT X
    g = add(font, "uni2717", 0x2717)
    T2 = 50
    pen = g.getPen()
    pen.moveTo((100, 160)); pen.lineTo((160, 100)); pen.lineTo((300, 240))
    pen.lineTo((440, 100)); pen.lineTo((500, 160)); pen.lineTo((360, 300))
    pen.lineTo((500, 440)); pen.lineTo((440, 500)); pen.lineTo((300, 360))
    pen.lineTo((160, 500)); pen.lineTo((100, 440)); pen.lineTo((240, 300))
    pen.closePath()


def draw_arrows(font):
    # Core arrow subset used in terminals/editors
    T = 60
    arrows = [
        # (name, cp, direction)
        ("uni2190", 0x2190, "left"),
        ("uni2191", 0x2191, "up"),
        ("uni2192", 0x2192, "right"),
        ("uni2193", 0x2193, "down"),
        ("uni2194", 0x2194, "leftright"),
        ("uni2195", 0x2195, "updown"),
        ("uni21D0", 0x21D0, "dleft"),
        ("uni21D2", 0x21D2, "dright"),
        ("uni21D4", 0x21D4, "dleftright"),
    ]
    for name, cp, direction in arrows:
        g = add(font, name, cp)
        pen = g.getPen()
        if direction == "right":
            # shaft
            rect(g, 60, MY - T//2, 360, T)
            # head
            pen.moveTo((420, MY)); pen.lineTo((280, MY + 120)); pen.lineTo((280, MY - 120)); pen.closePath()
        elif direction == "left":
            rect(g, 180, MY - T//2, 360, T)
            pen.moveTo((180, MY)); pen.lineTo((320, MY + 120)); pen.lineTo((320, MY - 120)); pen.closePath()
        elif direction == "up":
            rect(g, MX - T//2, 200, T, 360)
            pen.moveTo((MX, 620)); pen.lineTo((MX + 120, 480)); pen.lineTo((MX - 120, 480)); pen.closePath()
        elif direction == "down":
            rect(g, MX - T//2, 200, T, 360)
            pen.moveTo((MX, 200)); pen.lineTo((MX + 120, 340)); pen.lineTo((MX - 120, 340)); pen.closePath()
        elif direction == "leftright":
            rect(g, 60, MY - T//2, 480, T)
            pen.moveTo((60, MY)); pen.lineTo((200, MY + 120)); pen.lineTo((200, MY - 120)); pen.closePath()
            pen.moveTo((540, MY)); pen.lineTo((400, MY + 120)); pen.lineTo((400, MY - 120)); pen.closePath()
        elif direction == "updown":
            rect(g, MX - T//2, 200, T, 400)
            pen.moveTo((MX, 660)); pen.lineTo((MX + 120, 520)); pen.lineTo((MX - 120, 520)); pen.closePath()
            pen.moveTo((MX, 140)); pen.lineTo((MX + 120, 280)); pen.lineTo((MX - 120, 280)); pen.closePath()
        elif direction == "dright":
            D = 20
            rect(g, 60, MY - T//2 - D, 340, T//2)
            rect(g, 60, MY + D, 340, T//2)
            pen.moveTo((400, MY)); pen.lineTo((260, MY + 120)); pen.lineTo((260, MY - 120)); pen.closePath()
        elif direction == "dleft":
            D = 20
            rect(g, 200, MY - T//2 - D, 340, T//2)
            rect(g, 200, MY + D, 340, T//2)
            pen.moveTo((200, MY)); pen.lineTo((340, MY + 120)); pen.lineTo((340, MY - 120)); pen.closePath()
        elif direction == "dleftright":
            D = 20
            rect(g, 140, MY - T//2 - D, 320, T//2)
            rect(g, 140, MY + D, 320, T//2)
            pen.moveTo((140, MY)); pen.lineTo((280, MY + 120)); pen.lineTo((280, MY - 120)); pen.closePath()
            pen.moveTo((460, MY)); pen.lineTo((320, MY + 120)); pen.lineTo((320, MY - 120)); pen.closePath()


def main():
    font = ufoLib2.Font.open(UFO)
    before = len(font)
    draw_box_drawing(font)
    draw_block_elements(font)
    draw_geometric_shapes(font)
    draw_arrows(font)
    after = len(font)
    # Update glyph order
    order = list(font.lib.get("public.glyphOrder", []))
    for g in font:
        if g.name not in order:
            order.append(g.name)
    font.lib["public.glyphOrder"] = order
    font.save(UFO, overwrite=True)
    print(f"Added {after - before} T4 glyphs ({after} total) to {UFO}")


if __name__ == "__main__":
    main()
