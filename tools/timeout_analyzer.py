#!/usr/bin/env python3
# Lists tests without timeout decorators and those that call input()
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("tests")
out = {"missing_timeout": [], "input_calls": []}
for p in root.rglob("test_*.py"):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    if "@pytest.mark.timeout" not in txt:
        out["missing_timeout"].append(str(p))
    if re.search(r"\binput\(", txt):
        out["input_calls"].append(str(p))
print(json.dumps(out, indent=2))
