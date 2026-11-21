"""Bakes the Terra grass mask (run with normal Python, not inside Unreal):
  python Tools/bake_grass_mask.py
Writes Tools/out/T_TerraGrassMask.png: 2048x2048 RGB covering 2048 x 2048 m centred on the origin (1 m texels).
  R = grass density (0..1)   G = tall-grass patches (0 short .. 1 tall)   B = bare dirt (0..1)
The ground material reads B for bare patches; PCG reads R for density and G to pick tall or short clumps,
so the ground and the grass always agree (the Unity grass mask's role).
Column = world X (north), row = world Y (east), row 0 at the top: u = (X + 1024 m) / 2048 m, v = (Y + 1024 m) / 2048 m.
That is PCG's texture-data convention (local X -> U, local Y -> V), so PCG uses an unrotated transform.
"""
import math
import os
import struct
import zlib

SIZE = 2048
EXTENT_M = 2048.0
OUT = os.path.join(os.path.dirname(__file__), "out", "T_TerraGrassMask.png")


def hash2(ix, iy, seed):
    h = (ix * 374761393 + iy * 668265263 + seed * 144665) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def noise(x, y, seed):
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = hash2(ix, iy, seed), hash2(ix + 1, iy, seed)
    c, d = hash2(ix, iy + 1, seed), hash2(ix + 1, iy + 1, seed)
    return (a + (b - a) * ux) + ((c + (d - c) * ux) - (a + (b - a) * ux)) * uy


def fbm(x, y, seed, octaves):
    s, amp, n = 0.0, 0.5, 0.0
    for k in range(octaves):
        s += amp * noise(x, y, seed + k * 31)
        n += amp
        amp *= 0.5
        x, y = x * 2.03 + 17.1, y * 2.03 + 17.1
    return s / n


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def river_y_m(x_m):
    # UVoyagerTerra::RiverXM (Unity z = world X north).
    return 110.0 + 55.0 * math.sin(x_m * 0.0045) + 18.0 * math.sin(x_m * 0.013 + 1.3)


HOUSE = (25.0, -30.0)   # world (X north, Y east) in metres
SHIP = (-22.0, 32.0)

rows = []
for j in range(SIZE):
    y = -EXTENT_M / 2 + (j + 0.5) * EXTENT_M / SIZE          # image row = world Y (east), metres
    row = bytearray()
    for i in range(SIZE):
        x = -EXTENT_M / 2 + (i + 0.5) * EXTENT_M / SIZE      # image column = world X (north), metres
        ry = river_y_m(x)
        # Bare patches 2-5 m across with ragged edges (as Unity HomeSurface.BarePatch).
        bare = smooth(0.70, 0.78, noise(x * 0.22, y * 0.22, 11) * 0.8 + noise(x * 0.6, y * 0.6, 12) * 0.2)
        # Trampled ground around the house and the ship pad.
        dh = math.hypot(x - HOUSE[0], y - HOUSE[1])
        ds = math.hypot(x - SHIP[0], y - SHIP[1])
        bare = max(bare, 1.0 - smooth(6.0, 12.0, dh), 0.6 * (1.0 - smooth(5.0, 9.0, ds)))
        # Density: thins on the river banks (the channel itself has no turf) and in broad sparse swathes.
        dr = abs(y - ry)
        density = smooth(24.0, 34.0, dr) * (0.55 + 0.45 * smooth(0.3, 0.55, fbm(x * 0.01, y * 0.01, 21, 3)))
        density *= 1.0 - 0.85 * bare
        # Tall-grass patches: a few broad tall swathes, mostly short meadow (Unity: most clumps short).
        tall = smooth(0.48, 0.68, fbm(x * 0.02, y * 0.02, 31, 3))
        row += bytes((int(density * 255), int(tall * 255), int(bare * 255)))
    rows.append(bytes(row))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
raw = b"".join(b"\x00" + r for r in rows)
def chunk(t, d):
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0)) + \
      chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")
open(OUT, "wb").write(png)
print("wrote", OUT)
