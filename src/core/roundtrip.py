from __future__ import annotations
import unicodedata
from typing import Dict

try:
    import icu  # PyICU
except Exception:  # pragma: no cover
    icu = None


def _norm(s: str) -> str:
    return unicodedata.normalize("NFC", s).casefold()


def _dice(a: str, b: str) -> float:
    # 2|X∩Y|/(|X|+|Y|) over bigrams
    def bigrams(x: str):
        return {x[i : i + 2] for i in range(len(x) - 1)} if len(x) >= 2 else {x}

    A, B = bigrams(a), bigrams(b)
    denom = (len(A) + len(B)) or 1
    return (2 * len(A & B)) / denom


def cjk_roundtrip_ok(entry: Dict) -> bool:
    """
    Minimal structural check – full language‑specific logic should live in
    region hooks. Here we perform a conservative transliteration and compare
    CanonicalLatin to a romanised CanonicalNative if present.
    """
    if icu is None:
        return True  # caller must enforce stronger gate when ICU available
    native = entry.get("CanonicalNative", "")
    latin = entry.get("CanonicalLatin", "")
    if not native or not latin:
        return True
    tr = icu.Transliterator.createInstance("Any-Latin; Latin-ASCII")
    lat2 = tr.transliterate(native)
    return _dice(_norm(latin), _norm(lat2)) >= 0.97
