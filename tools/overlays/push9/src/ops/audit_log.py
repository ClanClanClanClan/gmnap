from __future__ import annotations
import json, time, hmac, hashlib, os, io
from typing import Optional, Dict, Any


class AuditLogger:
    """
    Append-only audit trail with hash chaining and optional HMAC key for tamper-evidence.
    Each entry: {"ts": "...", "actor": "...", "action": "...", "details": {...}, "prev_hash": "...", "hash": "..."}
    """

    def __init__(self, path: str, key: Optional[bytes] = None):
        self.path = path
        self.key = key or (os.getenv("AUDIT_HMAC_KEY") or "").encode("utf-8") or None
        self._prev_hash = None
        # Load last hash if file exists
        try:
            with open(self.path, "rb") as f:
                last = None
                for line in f:
                    last = line
                if last:
                    obj = json.loads(last.decode("utf-8"))
                    self._prev_hash = obj.get("hash")
        except Exception:
            self._prev_hash = None

    def _digest(self, payload: bytes) -> str:
        if self.key:
            return hmac.new(self.key, payload, hashlib.sha256).hexdigest()
        return hashlib.sha256(payload).hexdigest()

    def log(self, actor: str, action: str, details: Dict[str, Any] | None = None) -> str:
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "actor": actor,
            "action": action,
            "details": details or {},
            "prev_hash": self._prev_hash,
        }
        payload = json.dumps(rec, sort_keys=True, separators=(",", ":")).encode("utf-8")
        rec["hash"] = self._digest(payload)
        with open(self.path, "ab") as f:
            f.write(json.dumps(rec, ensure_ascii=False).encode("utf-8") + b"\n")
        self._prev_hash = rec["hash"]
        return rec["hash"]

    def verify_chain(self) -> bool:
        prev = None
        try:
            with open(self.path, "rb") as f:
                for line in f:
                    obj = json.loads(line.decode("utf-8"))
                    # verify prev
                    if obj.get("prev_hash") != prev:
                        return False
                    tmp = obj.copy()
                    h = tmp.pop("hash", None)
                    payload = json.dumps(tmp, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    dig = self._digest(payload)
                    if h != dig:
                        return False
                    prev = dig
            return True
        except Exception:
            return False
