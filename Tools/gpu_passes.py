"""Print the GPU passes from the last ProfileGPU dump in Saved/Logs/glick.log.
Usage: python Tools/gpu_passes.py [min_ms] [filter]"""
import re
import sys

min_ms = float(sys.argv[1]) if len(sys.argv) > 1 else 0.2
flt = sys.argv[2].lower() if len(sys.argv) > 2 else ""
lines = open("Saved/Logs/glick.log", encoding="utf-8", errors="ignore").read().splitlines()
start = max(i for i, l in enumerate(lines) if "GPU Profile for Frame" in l)
frame = re.search(r"Frame Time\s*:\s*([\d.]+)ms", "\n".join(lines[start:start + 6]))
print("frame", frame.group(1) if frame else "?", "ms")
for l in lines[start:start + 1500]:
    parts = l.split("┃")
    if len(parts) < 5:
        continue
    incl = re.findall(r"([\d.]+) ms", parts[2])
    name = parts[3].rstrip()
    if not incl or float(incl[0]) < min_ms:
        continue
    if flt and flt not in name.lower():
        continue
    print(f"{float(incl[0]):7.3f} ms {name[:110]}")
