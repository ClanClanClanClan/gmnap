from __future__ import annotations
import unicodedata, re
from difflib import SequenceMatcher
from typing import Optional, Tuple, Dict, Any, List


def normalize_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s)
    return s.strip().lower()


def fuzzy_ratio(a: str, b: str) -> float:
    a_n = normalize_name(a)
    b_n = normalize_name(b)
    if not a_n or not b_n:
        return 0.0
    return SequenceMatcher(None, a_n, b_n).ratio()


def map_wikidata_to_global_id(
    wd_name: str,
    birth_year: Optional[int],
    entries: List[Dict[str, Any]],
    min_ratio: float = 0.85,
) -> Tuple[Optional[str], float]:
    # Exact pass
    for e in entries:
        if e.get("CanonicalLatin", "").lower() == wd_name.lower():
            if (birth_year is None) or (e.get("BirthYear") == birth_year):
                return e["GlobalID"], 1.0

    # Fuzzy pass
    best = (None, 0.0)
    for e in entries:
        score = fuzzy_ratio(e.get("CanonicalLatin", ""), wd_name)
        if birth_year and e.get("BirthYear"):
            diff = abs(int(e["BirthYear"]) - int(birth_year))
            score *= 1.0 if diff == 0 else 0.9 if diff <= 2 else 0.6
        if score > best[1]:
            best = (e["GlobalID"], score)

    return best if best[1] >= min_ratio else (None, 0.0)
