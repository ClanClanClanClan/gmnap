#!/usr/bin/env python3
import json
import sys

from src.pipeline.stage1_ingest import ingest_and_normalise

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ingest_demo.py <input.(yaml|json)>")
        raise SystemExit(2)
    out = ingest_and_normalise(sys.argv[1])
    print(json.dumps(out, ensure_ascii=False, indent=2))
