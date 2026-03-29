#!/usr/bin/env python3
# Greps tests for third-party imports and emits a suggested requirements.tests.txt
import sys, pathlib, re

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("tests")
third = set()
for p in root.rglob("test_*.py"):
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = re.match(r"\s*import\s+([\w\.]+)", line) or re.match(
            r"\s*from\s+([\w\.]+)\s+import\s+", line
        )
        if not m:
            continue
        mod = m.group(1).split(".")[0]
        if mod not in {"src", "tests", "pytest"} and not mod.startswith("_"):
            third.add(mod)
with open("requirements.tests.txt", "w", encoding="utf-8") as fh:
    for m in sorted(third):
        fh.write(m + "\n")
print("Wrote requirements.tests.txt")
