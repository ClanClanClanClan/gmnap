from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
import hashlib, time


@dataclass
class HashcashStamp:
    version: str
    bits: int
    date: str
    resource: str
    ext: str
    rand: str
    counter: str

    def to_stamp(self) -> str:
        # Classic stamp: ver:bits:date:resource:ext:rand:counter
        return f"{self.version}:{self.bits}:{self.date}:{self.resource}:{self.ext}:{self.rand}:{self.counter}"


def _leading_zero_bits(h: bytes) -> int:
    n = 0
    for b in h:
        if b == 0:
            n += 8
            continue
        # count leading zeros in this byte
        for i in range(7, -1, -1):
            if (b >> i) & 1 == 0:
                n += 1
            else:
                return n
        return n
    return n


def parse_stamp(s: str) -> Optional[HashcashStamp]:
    parts = s.strip().split(":")
    if len(parts) != 7:
        return None
    ver, bits, date, resource, ext, rand, counter = parts
    try:
        bits_i = int(bits)
    except Exception:
        return None
    return HashcashStamp(
        version=ver, bits=bits_i, date=date, resource=resource, ext=ext, rand=rand, counter=counter
    )


def verify_hashcash(
    stamp_str: str, min_bits: int, resource: Optional[str] = None, max_age_seconds: int = 3600
) -> Tuple[bool, str]:
    """
    Verify a classic Hashcash v1 stamp. Returns (ok, reason).
    - min_bits: required difficulty (e.g., 18)
    - resource: if provided, must match stamp resource
    - max_age_seconds: stamp date freshness (approx, accepts UTC YYYYMMDDHHMMSS or shorter YYYYMMDD)
    """
    st = parse_stamp(stamp_str)
    if st is None:
        return False, "malformed"
    if st.version not in ("1", "1.0"):
        return False, "unsupported_version"
    if st.bits < min_bits:
        return False, "insufficient_bits"
    if resource and st.resource != resource:
        return False, "resource_mismatch"

    # Verify SHA-1 leading zeros (classic Hashcash uses SHA-1 on whole stamp)
    digest = hashlib.sha1(st.to_stamp().encode("utf-8")).digest()
    lzb = _leading_zero_bits(digest)
    if lzb < st.bits:
        return False, "invalid_proof"

    # Date freshness check (tolerate formats YYYYMMDD or YYYYMMDDhhmmss)
    try:
        now = time.time()
        # Accept either 8 or 14 digits
        if len(st.date) == 14:
            tm = time.strptime(st.date, "%Y%m%d%H%M%S")
        elif len(st.date) == 8:
            tm = time.strptime(st.date, "%Y%m%d")
        else:
            return False, "bad_date"
        stamp_ts = time.mktime(tm)
        if abs(now - stamp_ts) > max_age_seconds:
            return False, "expired"
    except Exception:
        return False, "bad_date"
    return True, "ok"
