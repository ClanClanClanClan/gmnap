#!/usr/bin/env python3
import os, sys, json

gate = int(os.getenv("GMNAP_IDEMPOTENT_DIFF_BYTES_MAX", "0") or "0")
report = os.path.join(
    sys.argv[1] if len(sys.argv) > 1 else "snapshots/latest", "IDEMPOTENCY_REPORT.txt"
)
try:
    txt = open(report, "r", encoding="utf-8").read()
    for line in txt.splitlines():
        if line.startswith("diff_bytes:"):
            diff = int(line.split(":", 1)[1].strip())
            if diff > gate:
                print(f"::error ::Idempotency gate failed: diff_bytes={diff} > {gate}")
                sys.exit(1)
            else:
                print(f"Idempotency gate OK: diff_bytes={diff} <= {gate}")
                sys.exit(0)
except FileNotFoundError:
    print("::warning ::No idempotency report found; skipping gate")
    sys.exit(0)
