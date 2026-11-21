"""Bakes a tileable gust noise texture (run with normal Python): python Tools/bake_gust_noise.py
Writes Tools/out/T_GustNoise.png, 256x256 greyscale, periodic fbm (3 octaves). The grass material scrolls it along
the wind (MPC GustScale / GustScroll) to sweep waves across the meadow."""
import math
import os
import struct
import zlib

SIZE = 256
OUT = os.path.join(os.path.dirname(__file__), "out", "T_GustNoise.png")


def h(ix, iy, period, seed):
    ix %= period
    iy %= period
    v = (ix * 374761393 + iy * 668265263 + seed * 144665) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def noise(x, y, period, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = h(ix, iy, period, seed), h(ix + 1, iy, period, seed)
    c, d = h(ix, iy + 1, period, seed), h(ix + 1, iy + 1, period, seed)
    top = a + (b - a) * ux
    return top + ((c + (d - c) * ux) - top) * uy


rows = []
for j in range(SIZE):
    row = bytearray()
    for i in range(SIZE):
        s, amp, n = 0.0, 0.5, 0.0
        for o in range(3):
            period = 4 << o                      # 4, 8, 16 cells across: tiles seamlessly
            s += amp * noise(i / SIZE * period, j / SIZE * period, period, 7 + o)
            n += amp
            amp *= 0.5
        row.append(int(min(max(s / n, 0.0), 1.0) * 255))
    rows.append(bytes(row))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
raw = b"".join(b"\x00" + r for r in rows)
def chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
open(OUT, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 0, 0, 0, 0)) +
                      chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
print("wrote", OUT)
