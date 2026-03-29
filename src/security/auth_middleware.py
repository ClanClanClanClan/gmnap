from __future__ import annotations
import os
from typing import Dict, Tuple
from ..ops.metrics import AUTH_FAILS, AUTH_OK


class AuthError(Exception):
    pass


def _load_allowed_keys() -> set[str]:
    raw = os.getenv("GMNAP_API_KEYS", "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    return set(keys)


def check_auth(headers: Dict[str, str]) -> Tuple[bool, str]:
    """
    Validate request authorization.
    - Accepts "Authorization: Bearer <token>" where token ∈ GMNAP_API_KEYS (comma-separated).
    - If GMNAP_MTLS_REQUIRED=1, also requires X-Client-Cert header presence (reverse proxy should set this).
    """
    required_mtls = os.getenv("GMNAP_MTLS_REQUIRED", "0") == "1"
    allowed = _load_allowed_keys()
    auth = headers.get("Authorization", "")
    token = ""
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1].strip()
    if token and token in allowed:
        if required_mtls and not headers.get("X-Client-Cert"):
            AUTH_FAILS.inc()
            return False, "mTLS required but certificate header missing"
        AUTH_OK.inc()
        return True, "ok"
    AUTH_FAILS.inc()
    return False, "invalid token"


__all__ = ["AuthError", "check_auth"]
