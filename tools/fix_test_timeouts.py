#!/usr/bin/env python3
import os, re, sys, pathlib

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("tests")
for p in root.rglob("test_*.py"):
    t = p.read_text(encoding="utf-8", errors="ignore")
    n = t
    if "import pytest" not in n:
        n = "import pytest\n" + n
    n = re.sub(
        r"(\n\s*def\s+test_[A-Za-z0-9_]+\s*\()", "\n@pytest.mark.timeout(15)\n\\1", n
    )
    if n != t:
        p.write_text(n, encoding="utf-8")
        print("patched", p)
