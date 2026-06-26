#!/usr/bin/env python3
# Quick wrapper to print the test diagnostic summary only.
import json
import pathlib
import sys

from test_repair_tool import diagnose

root = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("tests")
rep = diagnose(root)
print(json.dumps(rep["summary"], indent=2))
