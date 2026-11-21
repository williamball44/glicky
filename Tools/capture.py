"""Decode an MCP CaptureViewport JSON result file to a PNG.
Usage: python Tools/capture.py <tool-result.txt> <out.png>"""
import base64, json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
r = d.get("returnValue", d)
open(sys.argv[2], "wb").write(base64.b64decode(r["image"]["data"]))
print(sys.argv[2])
