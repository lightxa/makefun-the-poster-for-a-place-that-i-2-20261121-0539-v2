#!/usr/bin/env python3
"""LUMARIS — The Poster for a Place That Isn't There (variant 2).

A travel poster for LUMARIS, a floating archipelago of gardens above a
sea of clouds at dawn. One landmark: the great garden island of Lumaris
itself, its waterfall pouring off the edge into the clouds below, joined
by a rope bridge to its sister isle while a small balloon drifts past
the rising sun.

Drawn entirely procedurally with the Python standard library only.
Writes /output/entry.png (1024x1024, deterministic, no network).
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- canvas

buf = bytearray(W * H * 3)


def px(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r
        buf[i + 1] = g
        buf[i + 2] = b


def blend(x, y, r, g, b, a):
    """Alpha-blend a colour over the pixel at (x, y); a in 0..1."""
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        i = (y * W + x) * 3
        buf[i] = int(buf[i] * (1.0 - a) + r * a)
        buf[i + 1] = int(buf[i + 1] * (1.0 - a) + g * a)
        buf[i + 2] = int(buf[i + 2] * (1.0 - a) + b * a)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_col(c1, c2, t):
    return (int(lerp(c1[0], c2[0], t)),
            int(lerp(c1[1], c2[1], t)),
            int(lerp(c1[2], c2[2], t)))


def fill_rect(x0, y0, x1, y1, col, alpha=1.0):
    x0 = max(0, int(x0))
    y0 = max(0, int(y0))
    x1 = min(W, int(x1))
    y1 = min(H, int(y1))
    for y in range(y0, y1):
        for x in range(x0, x1):
            if alpha >= 1.0:
                px(x, y, *col)
            else:
                blend(x, y, *col, alpha)


def disc(cx, cy, rad, col, alpha=1.0, soft=0):
    """Filled disc; soft>0 feather the rim over that many pixels."""
    r0 = int(max(0, cx - rad - soft))
    r1 = int(min(W - 1, cx + rad + soft))
    y0 = int(max(0, cy - rad - soft))
    y1 = int(min(H - 1, cy + rad + soft))
    for y in range(y0, y1 + 1):
        for x in range(r0, r1 + 1):
            d = math.hypot(x - cx, y - cy)
            if d <= rad:
                a = alpha
            elif soft and d <= rad + soft:
                a = alpha * (1.0 - (d - rad) / soft)
            else:
                continue
            if a >= 1.0:
                px(x, y, *col)
            else:
                blend(x, y, *col, a)


def ellipse(cx, cy, rx, ry, col, alpha=1.0):
    x0 = int(max(0, cx - rx))
    x1 = int(min(W - 1, cx + rx))
    y0 = int(max(0, cy - ry))
    y1 = int(min(H - 1, cy + ry))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                if alpha >= 1.0:
                    px(x, y, *col)
                else:
                    blend(x, y, *col, alpha)


def poly(points, col, alpha=1.0):
    """Scanline fill of a simple polygon."""
    ys = [p[1] for p in points]
    y0 = max(0, int(min(ys)))
    y1 = min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, y1p = points[i]
            x2, y2p = points[(i + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                t = (y - y1p) / (y2p - y1p)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = max(0, int(math.ceil(xs[k])))
            xb = min(W - 1, int(math.floor(xs[k + 1])))
            for x in range(xa, xb + 1):
                if alpha >= 1.0:
                    px(x, y, *col)
                else:
                    blend(x, y, *col, alpha)


def line(x0, y0, x1, y1, col, width=1, alpha=1.0):
    steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for s in range(steps + 1):
        t = s / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        for dy in range(-width // 2, width // 2 + 1):
            for dx in range(-width // 2, width // 2 + 1):
                if alpha >= 1.0:
                    px(int(x) + dx, int(y) + dy, *col)
                else:
                    blend(int(x) + dx, int(y) + dy, *col, alpha)


# ---------------------------------------------------------------- font
# Bold 5x7 bitmap capitals, drawn by our own code (no font files).

FONT = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["01110", "00100", "00100", "00100", "00100", "00100", "01110"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}


def text_width(s, cell, gap):
    return len(s) * cell * 5 + (len(s) - 1) * gap


def draw_text(s, x, y, cell, gap, col, shadow=None, shadow_off=(7, 8)):
    """Draw s with the top-left corner at (x, y); cell is px per bitmap cell."""
    if shadow is not None:
        draw_text(s, x + shadow_off[0], y + shadow_off[1], cell, gap, shadow)
    cx = x
    for ch in s:
        glyph = FONT.get(ch)
        if glyph:
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == "1":
                        fill_rect(cx + c * cell, y + r * cell,
                                  cx + (c + 1) * cell, y + (r + 1) * cell, col)
        cx += 5 * cell + gap


# ---------------------------------------------------------------- scene

def sky():
    """Dawn gradient: deep violet at the top, rose, coral, gold at the horizon."""
    stops = [
        (0.00, (38, 34, 84)),
        (0.30, (94, 62, 122)),
        (0.52, (198, 96, 110)),
        (0.68, (240, 138, 92)),
        (0.82, (250, 186, 110)),
        (1.00, (252, 214, 140)),
    ]
    for y in range(H):
        t = y / (H - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
                col = lerp_col(c0, c1, f)
                break
        else:
            col = stops[-1][1]
        fill_rect(0, y, W, y + 1, col)


def sun():
    """Low rising sun with a warm halo, upper right of centre."""
    cx, cy = 700, 430
    for r, a in ((210, 0.10), (160, 0.14), (120, 0.20)):
        disc(cx, cy, r, (255, 196, 110), alpha=a, soft=30)
    disc(cx, cy, 78, (255, 226, 150), soft=6)
    disc(cx, cy, 62, (255, 240, 196), soft=4)


def cloud_puff(cx, cy, s, col, alpha=0.9):
    """One billowing cloud made of overlapping soft discs."""
    for dx, dy, r in ((-1.6, 0.25, 0.85), (-0.8, -0.15, 1.0), (0.0, 0.0, 1.15),
                     (0.9, -0.1, 0.95), (1.7, 0.3, 0.8), (-0.2, 0.35, 0.9)):
        disc(cx + dx * s, cy + dy * s, r * s, col, alpha=alpha, soft=int(s * 0.35))


def cloud_sea():
    """The sea of clouds the islands float above, filling the lower third."""
    base_y = 700
    # Deep lavender under-layer.
    for y in range(base_y, H):
        t = (y - base_y) / (H - base_y)
        col = lerp_col((226, 178, 196), (250, 224, 196), t)
        fill_rect(0, y, W, y + 1, col)
    puffs = [
        (90, 760, 95, (250, 214, 190)), (300, 730, 120, (255, 226, 200)),
        (540, 770, 110, (252, 210, 184)), (790, 740, 125, (255, 228, 202)),
        (950, 780, 100, (250, 212, 188)), (180, 880, 130, (244, 196, 200)),
        (470, 900, 140, (252, 220, 200)), (760, 890, 135, (248, 205, 196)),
        (960, 920, 120, (252, 218, 198)), (40, 960, 120, (240, 190, 198)),
        (330, 980, 130, (250, 214, 196)), (660, 985, 125, (246, 202, 196)),
        (900, 990, 110, (252, 216, 198)),
    ]
    for cx, cy, s, col in puffs:
        cloud_puff(cx, cy, s, col, alpha=0.95)
    # Soft shadowed gaps between puffs, low in the frame.
    for cx, cy, s in ((210, 830, 70), (620, 850, 80), (880, 860, 65)):
        disc(cx, cy, s, (214, 158, 178), alpha=0.25, soft=40)


def island(cx, top_y, w, h, rock_top, rock_bot, grass, grass_light):
    """A floating island: tapered rock body, grassy cap, pointed keel."""
    pts = [
        (cx - w / 2, top_y + 18),
        (cx - w / 2 + 14, top_y + h * 0.45),
        (cx - w * 0.22, top_y + h * 0.78),
        (cx, top_y + h),
        (cx + w * 0.22, top_y + h * 0.78),
        (cx + w / 2 - 14, top_y + h * 0.45),
        (cx + w / 2, top_y + 18),
    ]
    # Vertical rock gradient, drawn band by band over the polygon's rows.
    ys = [p[1] for p in pts]
    y0, y1 = int(min(ys)), int(max(ys))
    for y in range(y0, y1 + 1):
        t = (y - y0) / max(1, y1 - y0)
        col = lerp_col(rock_top, rock_bot, t)
        xs = []
        n = len(pts)
        for i in range(n):
            x1, ya = pts[i]
            x2, yb = pts[(i + 1) % n]
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(x1 + (y - ya) / (yb - ya) * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            for x in range(max(0, int(xs[k])), min(W - 1, int(xs[k + 1])) + 1):
                px(x, y, *col)
    # Grassy cap: a shallow dome on the island's top.
    ellipse(cx, top_y + 6, w / 2 + 6, 34, grass)
    ellipse(cx, top_y + 2, w / 2 - 14, 26, grass_light)
    # A few rock ledges for depth.
    line(cx - w * 0.30, top_y + h * 0.42, cx + w * 0.18, top_y + h * 0.42,
         (60, 44, 66), width=3, alpha=0.5)
    line(cx - w * 0.16, top_y + h * 0.62, cx + w * 0.26, top_y + h * 0.62,
         (60, 44, 66), width=3, alpha=0.45)


def trees(cx, top_y, w, n, seed):
    """Round-canopy garden trees dotted along an island's cap."""
    import random
    rnd = random.Random(seed)
    for _ in range(n):
        tx = cx - w / 2 + 30 + rnd.random() * (w - 60)
        ty = top_y - 6 - rnd.random() * 14
        r = 16 + rnd.random() * 14
        trunk = (96, 66, 52)
        line(tx, ty + 4, tx, ty + 22, trunk, width=4)
        greens = [(46, 122, 74), (62, 148, 88), (34, 102, 62)]
        disc(tx, ty, r, greens[rnd.randrange(3)])
        disc(tx - r * 0.45, ty + r * 0.3, r * 0.6, greens[rnd.randrange(3)])
        disc(tx + r * 0.45, ty + r * 0.35, r * 0.55, greens[rnd.randrange(3)])
        disc(tx, ty - r * 0.3, r * 0.45, (120, 190, 120), alpha=0.8)


def waterfall(x, y0, y1):
    """Bright water pouring off the main island's edge into the clouds."""
    for xoff in range(-24, 25, 3):
        xx = x + xoff
        for y in range(y0, y1):
            t = (y - y0) / max(1, y1 - y0)
            wob = int(6 * math.sin((y - y0) / 26.0 + xoff))
            col = lerp_col((140, 200, 228), (252, 246, 232), t)
            a = 0.95 - 0.3 * abs(xoff) / 24.0
            blend(xx + wob, y, *col, a)
    # White highlight streaks down the middle of the fall.
    for xoff in (-6, 0, 6):
        for y in range(y0, y1):
            blend(x + xoff, y, 255, 255, 255, 0.55)


def bridge(x0, y0, x1, y1):
    """A rope bridge sagging between the two main islands."""
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + 42
    # Ropes.
    for off in (-8, 8):
        steps = 40
        for s in range(steps + 1):
            t = s / steps
            x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1
            y = (1 - t) ** 2 * (y0 + off) + 2 * (1 - t) * t * (my + off) + t * t * (y1 + off)
            px(int(x), int(y), 122, 88, 60)
    # Planks.
    steps = 26
    for s in range(steps + 1):
        t = s / steps
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1
        fill_rect(x - 7, y - 3, x + 7, y + 3, (146, 104, 66))


def balloon(cx, cy, s):
    """A small striped hot-air balloon drifting past the sun."""
    disc(cx, cy, int(34 * s), (232, 84, 96), soft=2)
    for dx, col in ((-18, (255, 214, 120)), (0, (232, 84, 96)), (18, (255, 214, 120))):
        ellipse(cx + dx * s, cy, int(11 * s), int(33 * s), col)
    poly([(cx - 12 * s, cy + 32 * s), (cx + 12 * s, cy + 32 * s),
          (cx + 8 * s, cy + 52 * s), (cx - 8 * s, cy + 52 * s)], (122, 88, 60))
    line(cx - 12 * s, cy + 30 * s, cx - 8 * s, cy + 52 * s, (96, 66, 52), width=2)
    line(cx + 12 * s, cy + 30 * s, cx + 8 * s, cy + 52 * s, (96, 66, 52), width=2)


def birds():
    """A few distant birds, simple two-stroke wings."""
    for cx, cy, s in ((240, 330, 14), (300, 300, 11), (880, 300, 12), (830, 350, 9)):
        line(cx - s, cy, cx, cy - s * 0.55, (58, 40, 70), width=3)
        line(cx, cy - s * 0.55, cx + s, cy, (58, 40, 70), width=3)


def title():
    """LUMARIS, large and legible, on a soft dusk band across the top."""
    name = "LUMARIS"
    cell, gap = 18, 26
    tw = text_width(name, cell, gap)
    th = 7 * cell
    x = (W - tw) // 2
    y = 88
    fill_rect(x - 46, y - 30, x + tw + 46, y + th + 34, (46, 34, 78), alpha=0.38)
    draw_text(name, x, y, cell, gap, (255, 243, 214),
              shadow=(58, 32, 66), shadow_off=(7, 8))


def build():
    sky()
    sun()
    birds()
    balloon(905, 330, 0.8)
    cloud_sea()
    # Far small isle, left, half-lost in morning light.
    island(150, 596, 190, 120, (128, 92, 110), (74, 52, 82),
           (84, 150, 96), (110, 176, 118))
    trees(150, 600, 190, 3, 7)
    # Sister isle, right.
    island(850, 560, 220, 150, (118, 84, 104), (66, 46, 76),
           (72, 140, 90), (98, 168, 110))
    trees(850, 564, 220, 4, 21)
    # Main island: the great garden of Lumaris, centre stage.
    island(430, 500, 480, 230, (112, 78, 98), (58, 40, 68),
           (64, 134, 84), (92, 164, 104))
    trees(430, 504, 480, 9, 42)
    # A white pavilion crowns the garden.
    poly([(400, 470), (460, 470), (452, 428), (408, 428)], (255, 246, 228))
    poly([(392, 432), (468, 432), (430, 398)], (214, 84, 96))
    disc(430, 396, 7, (255, 226, 150))
    fill_rect(424, 448, 436, 470, (58, 40, 68))
    # Rope bridge from the main isle to the sister isle.
    bridge(670, 552, 742, 566)
    # Waterfall off the main island's near edge, into the cloud sea.
    waterfall(380, 688, 832)
    # Mist where the fall meets the clouds, then the title last.
    disc(380, 826, 36, (255, 244, 230), alpha=0.45, soft=20)
    title()


# ---------------------------------------------------------------- PNG

def write_png(path):
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter: None
        start = y * W * 3
        raw.extend(buf[start:start + W * 3])
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        c = struct.pack(">I", len(data)) + typ + data
        return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    build()
    size = write_png(os.path.join(out_dir, "entry.png"))
    print(f"wrote {out_dir}/entry.png ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()
