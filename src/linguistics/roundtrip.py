from __future__ import annotations


def dice(a: str, b: str) -> float:
    def bigrams(s: str):
        s = s.lower()
        return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}

    A = bigrams(a)
    B = bigrams(b)
    if not A and not B:
        return 1.0
    return 2 * len(A & B) / max(1, (len(A) + len(B)))


_CJK_LAT = {"张伟": "Zhang Wei", "김민준": "Kim Min-jun", "佐藤": "Satō"}
_LAT_CJK = {v: k for k, v in _CJK_LAT.items()}
_SEA_LAT = {"ไทย": "Thai", "ភាសាខ្មែរ": "Khmer", "ລາວ": "Lao"}
_LAT_SEA = {v: k for k, v in _SEA_LAT.items()}


def romanise(native: str) -> str:
    return _CJK_LAT.get(native) or _SEA_LAT.get(native) or native


def back_convert(latin: str) -> str:
    return _LAT_CJK.get(latin) or _LAT_SEA.get(latin) or latin


def roundtrip_score(native: str) -> float:
    lat = romanise(native)
    back = back_convert(lat)
    return dice(native, back)
