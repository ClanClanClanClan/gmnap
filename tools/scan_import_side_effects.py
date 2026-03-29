#!/usr/bin/env python3
import re, sys, pathlib, json

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("tests")
o = []
for p in root.rglob("test_*.py"):
    s = p.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"^\s*pipeline\s*=\s*Pipeline\(", s, flags=re.M):
        o.append(str(p))
    if re.search(r"^\s*result\s*=\s*.*process\(", s, flags=re.M):
        o.append(str(p))
    if re.search(r"^\s*asyncio\.run\(", s, flags=re.M):
        o.append(str(p))
print(json.dumps({"offenders": sorted(set(o))}, indent=2))
