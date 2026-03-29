from __future__ import annotations
import json, sys, pathlib, hashlib
from typing import List, Dict, Any, Tuple
from src.core.stage9_write_diff.write_and_diff import write_yaml_sorted


def canonical_bytes(obj):
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class IdempotencyGate:
    """Idempotency gate for Stage 11 - ensures 0-byte difference requirement."""

    def verify_idempotency(self, entries: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Verify entries produce identical output when written twice."""
        # Write entries twice to temp files
        out1 = pathlib.Path("temp_idempotency_1.json")
        out2 = pathlib.Path("temp_idempotency_2.json")

        write_yaml_sorted(entries, str(out1))
        write_yaml_sorted(entries, str(out2))

        b1 = out1.read_bytes()
        b2 = out2.read_bytes()

        # Clean up temp files
        out1.unlink(missing_ok=True)
        out2.unlink(missing_ok=True)

        if b1 != b2:
            return False, f"Idempotency violation: {sha256_hex(b1)} != {sha256_hex(b2)}"

        if sha256_hex(b1) != sha256_hex(canonical_bytes(entries)):
            return False, "Non-canonical output format"

        return True, "Idempotency verified"

    async def compute_file_hash(self, file_path: pathlib.Path) -> str:
        """Compute SHA256 hash of a file."""
        if isinstance(file_path, str):
            file_path = pathlib.Path(file_path)

        if not file_path.exists():
            return ""

        content = file_path.read_bytes()
        return sha256_hex(content)

    def check_zero_byte_diff(
        self, old_entries: List[Dict[str, Any]], new_entries: List[Dict[str, Any]]
    ) -> bool:
        """Check if two entry sets produce identical canonical output."""
        old_bytes = canonical_bytes(old_entries)
        new_bytes = canonical_bytes(new_entries)
        return old_bytes == new_bytes


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
        print("Non-canonical Stage9 writer")
        sys.exit(2)
    print("Stage 11 gate passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
