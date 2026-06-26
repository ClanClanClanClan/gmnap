from __future__ import annotations

import hashlib
import json
import pathlib
import sys

from overlays.stage9_write_diff.src.diff.write_and_diff import write_yaml_sorted


def canonical_bytes(obj):
    return json.dumps(
        obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()


def sha256_hex(b: bytes) -> str:
    import hashlib

    return hashlib.sha256(b).hexdigest()


def main():
    import argparse

    ap = argparse.ArgumentParser(description="Stage 11 Idempotency Gate")
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    args = ap.parse_args()
    old = json.loads(pathlib.Path(args.old).read_text("utf-8"))
    new = json.loads(pathlib.Path(args.new).read_text("utf-8"))
    out1 = pathlib.Path("stage9_run1.yaml")
    out2 = pathlib.Path("stage9_run2.yaml")
    write_yaml_sorted(new, str(out1))
    write_yaml_sorted(new, str(out2))
    b1, b2 = out1.read_bytes(), out2.read_bytes()
    if b1 != b2:
        print("Idempotency violation", sha256_hex(b1), sha256_hex(b2))
        sys.exit(2)
    if sha256_hex(b1) != sha256_hex(canonical_bytes(new)):
        print("Non‑canonical Stage9 writer")
        sys.exit(2)
    print("Stage 11 gate passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
