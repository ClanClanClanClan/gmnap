#!/usr/bin/env python3
import sys

candidates = [
    "{base}/oai/request",
    "{base}/oai",
    "{base}/server/oai/request",
    "{base}/oai2d",
]
bases = sys.stdin.read().strip().splitlines()
for b in bases:
    for pat in candidates:
        print(pat.format(base=b.rstrip("/")))
