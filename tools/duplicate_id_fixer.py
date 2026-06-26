#!/usr/bin/env python3
"""
Duplicate GlobalID Analyzer/Fixer
- Analyzes Stage 9 JSON/YAML entries for duplicates
- Policies:
  * Extreme: duplicates are fatal (report & exit non-zero)
  * Quick/Full: can suffix (--1,--2,...) deterministically unless --no-suffix
Usage:
  python tools/duplicate_id_fixer.py --in stage9.json --policy extreme
  python tools/duplicate_id_fixer.py --in stage9.json --policy full --write fixed.json
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


def load_entries(path: str):
    txt = open(path, encoding="utf-8").read()
    try:
        return json.loads(txt)
    except Exception:
        if yaml is None:
            raise
        return yaml.safe_load(txt)


def suggest_suffixes(entries):
    by_gid = collections.defaultdict(list)
    for e in entries:
        gid = e.get("GlobalID")
        if gid:
            by_gid[gid].append(e)
    renames = {}
    for gid, group in by_gid.items():
        if len(group) <= 1:
            continue
        for i, e in enumerate(group, start=1):
            if i == 1:
                continue
            renames[id(e)] = f"{gid}--{i-1}"
    return renames


def fix(entries, renames):
    out = []
    for e in entries:
        e2 = dict(e)
        if id(e) in renames:
            e2["GlobalID"] = renames[id(e)]
        out.append(e2)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--policy", choices=["extreme", "full", "quick"], default="extreme")
    ap.add_argument("--no-suffix", action="store_true")
    ap.add_argument("--write", dest="write")
    a = ap.parse_args()
    entries = load_entries(a.inp)
    counts = collections.Counter(
        [e.get("GlobalID") for e in entries if e.get("GlobalID")]
    )
    dups = {k: v for k, v in counts.items() if v > 1}
    if not dups:
        print("No duplicates found.")
        sys.exit(0)
    print(f"Duplicates: {dups}")
    if a.policy == "extreme" or a.no_suffix:
        sys.exit("Extreme policy: duplicates are fatal")
    ren = suggest_suffixes(entries)
    fixed = fix(entries, ren)
    if a.write:
        open(a.write, "w", encoding="utf-8").write(
            json.dumps(fixed, ensure_ascii=True, separators=(",", ":"))
        )
        print(f"Wrote fixed entries to {a.write}")
    else:
        print("Fix preview (first 3 renames):", list(ren.values())[:3])
