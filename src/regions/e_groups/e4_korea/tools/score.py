#!/usr/bin/env python
"""
score.py  – run both test suites, print   math  diverse   to stdout
Returns 0 on success, 2 if either test fails to import.
"""

import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def run_math():
    res = subprocess.run(
        [sys.executable, "scripts/validate.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode:
        print(res.stderr.strip(), file=sys.stderr)
        sys.exit(2)
    # Parse "619/733 = 84.45% round‑trip"
    m = re.search(r"(\d+)/(\d+)\s*=", res.stdout)
    if not m:
        print(f"Could not parse math output: {res.stdout[:100]}", file=sys.stderr)
        sys.exit(2)
    return int(m.group(1)), int(m.group(2))


def run_diverse():
    res = subprocess.run(
        [sys.executable, "scripts/test_diverse_dataset.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode:
        print(res.stderr.strip(), file=sys.stderr)
        sys.exit(2)

    # Parse "Diverse Dataset: 86.50% accuracy" - calculate from percentage
    pct_match = re.search(r"Diverse Dataset:\s*([\d.]+)%", res.stdout)
    if pct_match:
        pct = float(pct_match.group(1))
        correct = int(round(200 * pct / 100))
        return correct, 200

    print(f"Could not parse diverse output: {res.stdout[:200]}", file=sys.stderr)
    sys.exit(2)


math_ok, math_total = run_math()
div_ok, div_total = run_diverse()
print(json.dumps({"math": [math_ok, math_total], "diverse": [div_ok, div_total]}))
