#!/usr/bin/env python3
import re, sys, pathlib, json

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("tests")
h = []
for p in root.rglob("test_*.py"):
    s = p.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"\binput\(", s):
        h.append(str(p))
print(json.dumps({"input_calls": h}, indent=2))
