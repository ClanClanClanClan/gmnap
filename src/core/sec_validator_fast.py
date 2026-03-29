from __future__ import annotations

import re
from functools import lru_cache

# Precompile patterns once
_RE_ALLOWED_GID = re.compile(r"^[A-Za-z0-9_.:-]+$")
_RE_WS_MULTI = re.compile(r"\s+")


@lru_cache(maxsize=65536)
def gid_ok(gid: str) -> bool:
    return bool(_RE_ALLOWED_GID.match(gid or ""))


def normalise_ws(s: str) -> str:
    return _RE_WS_MULTI.sub(" ", (s or "").strip())


def validate_entry(entry: dict) -> bool:
    gid = entry.get("GlobalID") or entry.get("id")
    if gid and not gid_ok(gid):
        return False
    # Add other hot-path checks here (CJK ranges, max length, etc.)
    return True
