"""Summarise an Unreal CSV profiler capture.
Usage: python Tools/csv_summary.py <Profile.csv> [skip_frames]"""
import csv
import statistics
import sys

csv.field_size_limit(1 << 30)

path = sys.argv[1]
skip = int(sys.argv[2]) if len(sys.argv) > 2 else 300
with open(path, newline="", encoding="utf-8", errors="ignore") as f:
    rows = list(csv.reader(f))
# Unreal rewrites the full header at the end of the file when stats appear mid-capture; use the last one.
header = [r for r in rows if r and r[0] == "EVENTS"][-1]
data = []
ft_i = header.index("FrameTime")
for r in rows[1:]:
    if len(r) <= ft_i or r[0] == "EVENTS":
        continue
    try:
        float(r[ft_i])
    except ValueError:
        continue  # metadata / footer rows
    data.append(r)
data = data[skip:]
cols = {h: i for i, h in enumerate(header)}


def col(name):
    i = cols[name]
    out = []
    for r in data:
        if i < len(r) and r[i] not in ("", None):
            try:
                out.append(float(r[i]))
            except ValueError:
                pass
    return out


print(f"frames analysed: {len(data)} (skipped first {skip})")
for name in ["FrameTime", "GameThreadTime", "RenderThreadTime", "RHIThreadTime", "GPUTime"]:
    if name in cols:
        v = sorted(col(name))
        print(f"{name:18s} avg {statistics.mean(v):6.2f}  p50 {v[len(v)//2]:6.2f}  p95 {v[int(len(v)*0.95)]:6.2f} ms")
ft = col("FrameTime")
print(f"avg fps {1000.0 / statistics.mean(ft):.1f}   1% low fps {1000.0 / sorted(ft)[int(len(ft) * 0.99)]:.1f}")
gpu = [(statistics.mean(col(h)), h) for h in header if h.startswith("GPU/") and col(h)]
for t, h in sorted(gpu, reverse=True)[:15]:
    if t >= 0.05:
        print(f"  {t:6.2f} ms  {h}")
for key in ("systemresolution.resx", "systemresolution.resy"):
    for r in rows[-3:]:
        if key in r:
            print(key, r[r.index(key) + 1])
