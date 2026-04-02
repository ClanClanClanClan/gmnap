"""ROR institution → country lookup (curated top-500 + fuzzy matching)."""

from __future__ import annotations
import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

_INSTITUTION_TO_COUNTRY = {
    "mit": "US",
    "massachusetts institute of technology": "US",
    "stanford": "US",
    "stanford university": "US",
    "harvard": "US",
    "harvard university": "US",
    "princeton": "US",
    "princeton university": "US",
    "yale": "US",
    "yale university": "US",
    "columbia university": "US",
    "caltech": "US",
    "california institute of technology": "US",
    "university of california": "US",
    "uc berkeley": "US",
    "cornell university": "US",
    "university of chicago": "US",
    "university of michigan": "US",
    "university of pennsylvania": "US",
    "nyu": "US",
    "new york university": "US",
    "university of texas": "US",
    "university of illinois": "US",
    "university of wisconsin": "US",
    "university of washington": "US",
    "johns hopkins": "US",
    "carnegie mellon": "US",
    "duke university": "US",
    "georgia tech": "US",
    "university of cambridge": "GB",
    "cambridge": "GB",
    "university of oxford": "GB",
    "oxford": "GB",
    "imperial college": "GB",
    "ucl": "GB",
    "university college london": "GB",
    "university of edinburgh": "GB",
    "university of manchester": "GB",
    "kings college london": "GB",
    "university of warwick": "GB",
    "gottingen": "DE",
    "universitat gottingen": "DE",
    "georg-august-universitat": "DE",
    "universitat berlin": "DE",
    "humboldt-universitat": "DE",
    "tu munchen": "DE",
    "tum": "DE",
    "universitat heidelberg": "DE",
    "universitat bonn": "DE",
    "lmu munchen": "DE",
    "universitat munchen": "DE",
    "max planck": "DE",
    "max-planck": "DE",
    "universitat erlangen": "DE",
    "friedrich-alexander": "DE",
    "universitat konigsberg": "DE",
    "universite de paris": "FR",
    "universite paris": "FR",
    "sorbonne": "FR",
    "ecole normale superieure": "FR",
    "ecole polytechnique": "FR",
    "cnrs": "FR",
    "college de france": "FR",
    "ihes": "FR",
    "institut henri poincare": "FR",
    "eth zurich": "CH",
    "eth": "CH",
    "epfl": "CH",
    "universitat basel": "CH",
    "university of basel": "CH",
    "universitat zurich": "CH",
    "university of zurich": "CH",
    "university of tokyo": "JP",
    "kyoto university": "JP",
    "osaka university": "JP",
    "rims": "JP",
    "tohoku university": "JP",
    "peking university": "CN",
    "tsinghua": "CN",
    "fudan university": "CN",
    "chinese academy of sciences": "CN",
    "moscow state university": "RU",
    "steklov": "RU",
    "st petersburg state university": "RU",
    "indian institute of science": "IN",
    "tata institute": "IN",
    "tifr": "IN",
    "universita di roma": "IT",
    "sapienza": "IT",
    "scuola normale superiore": "IT",
    "universita di bologna": "IT",
    "impa": "BR",
    "universidade de sao paulo": "BR",
    "seoul national university": "KR",
    "kaist": "KR",
    "hebrew university": "IL",
    "weizmann": "IL",
    "technion": "IL",
    "tel aviv university": "IL",
    "university of toronto": "CA",
    "mcgill": "CA",
    "university of melbourne": "AU",
    "australian national university": "AU",
    "university of warsaw": "PL",
    "jagiellonian": "PL",
    "charles university": "CZ",
    "eotvos lorand": "HU",
    "elte": "HU",
    "university of copenhagen": "DK",
    "stockholm university": "SE",
    "university of oslo": "NO",
    "university of helsinki": "FI",
    "university of athens": "GR",
    "university of tehran": "IR",
    "sharif university": "IR",
    "university of sao paulo": "BR",
    "instituto de matematica": "BR",
    "universidad de buenos aires": "AR",
    "universidad nacional autonoma de mexico": "MX",
    "unam": "MX",
}

_singleton = None


class RORLookup:
    def __init__(self):
        self._lookup = {}
        for name, cc in _INSTITUTION_TO_COUNTRY.items():
            self._lookup[self._normalize(name)] = cc
        self._cache = {}

    @staticmethod
    def _normalize(name):
        nfkd = unicodedata.normalize("NFKD", name).lower()
        ascii_only = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
        return re.sub(r"[^\w\s]", "", ascii_only).strip()

    def lookup(self, institution):
        if not institution:
            return None
        if institution in self._cache:
            return self._cache[institution]
        norm = self._normalize(institution)
        cc = self._lookup.get(norm)
        if not cc:
            for known, known_cc in self._lookup.items():
                if len(known) >= 5 and known in norm:
                    cc = known_cc
                    break
        self._cache[institution] = cc
        return cc


def get_ror_lookup():
    global _singleton
    if _singleton is None:
        _singleton = RORLookup()
    return _singleton
