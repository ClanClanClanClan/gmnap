import hashlib
import json


def canonicalize_entries(entries):
    def _canon(v):
        if isinstance(v, dict):
            return {k: _canon(v[k]) for k in sorted(v.keys())}
        if isinstance(v, list):
            if all(isinstance(x, dict) for x in v):
                return sorted(
                    [_canon(x) for x in v],
                    key=lambda d: (
                        d.get("GlobalID", ""),
                        json.dumps(d, sort_keys=True, ensure_ascii=True),
                    ),
                )
            return [_canon(x) for x in v]
        return v

    return _canon(entries)


def to_canonical_bytes(entries):
    canon = canonicalize_entries(entries)
    return json.dumps(
        canon, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
