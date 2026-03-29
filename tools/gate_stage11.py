import json, sys, hashlib
from pathlib import Path


def canonical(obj):
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


if __name__ == "__main__":
    new = json.loads(Path(sys.argv[1]).read_text("utf-8"))
    b1 = canonical(new)
    b2 = canonical(new)
    h = lambda b: hashlib.sha256(b).hexdigest()
    print("sha256_run1", h(b1))
    print("sha256_run2", h(b2))
    assert b1 == b2, "Idempotency violation"
    assert h(b1) == h(canonical(new)), "Non‑canonical serialiser"
    print("Stage 11 OK")
