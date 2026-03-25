"""
D3 - South Asia Bengali region implementation.

Covers: Bangladesh, West Bengal (India), Tripura, Assam Bengali speakers
Features: Bengali/Bangla script (U+0980 - U+09FF), common surname suffixes
          (-das, -dutta, -gupta, -roy, -sen, -bose, -ghosh), honorific
          titles (Shri, Srimati, Babu), Bangladesh vs West Bengal naming
          differences, frequent script-switching between Bengali and Latin.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from ..base import RegionRuleError, RegionSpec


# ---------------------------------------------------------------------------
# Script helpers
# ---------------------------------------------------------------------------
_BENGALI_RANGE: List[Tuple[int, int]] = [(0x0980, 0x09FF)]


def _in_bengali(char: str) -> bool:
    cp = ord(char)
    return 0x0980 <= cp <= 0x09FF


def _has_bengali(text: str) -> bool:
    return any(_in_bengali(c) for c in text)


# ---------------------------------------------------------------------------
# Shared data
# ---------------------------------------------------------------------------
_TITLES = {
    # Bengali / Indian titles (Latin)
    "Shri",
    "Sri",
    "Sree",
    "Srimati",
    "Smt",
    "Smt.",
    "Babu",
    "Begum",
    "Bibi",
    "Dr",
    "Dr.",
    "Prof",
    "Prof.",
    "Er",
    "Er.",
    "Maulvi",
    "Maulana",
    "Haji",
    "Joy",
    "Bangla",
    # Bengali script titles
    "\u09b6\u09cd\u09b0\u09c0",  # Shri
    "\u09b6\u09cd\u09b0\u09c0\u09ae\u09a4\u09bf",  # Srimati
    "\u09ac\u09be\u09ac\u09c1",  # Babu
}

# Common Bengali surname suffixes (lowercase for matching)
_SURNAME_SUFFIXES = {
    "das",
    "dutta",
    "datta",
    "gupta",
    "roy",
    "ray",
    "sen",
    "bose",
    "basu",
    "ghosh",
    "gosh",
    "banerjee",
    "bandyopadhyay",
    "bandopadhyay",
    "chatterjee",
    "chattopadhyay",
    "mukherjee",
    "mukhopadhyay",
    "bhattacharya",
    "bhattacharyya",
    "bhattacharjee",
    "ganguly",
    "gangopadhyay",
    "sarkar",
    "sarker",
    "mitra",
    "mitter",
    "chakraborty",
    "chakrabarti",
    "chakravarty",
    "majumdar",
    "mazumdar",
    "kundu",
    "mondal",
    "mandal",
    "paul",
    "pal",
    "saha",
    "biswas",
    "chowdhury",
    "choudhury",
    "barman",
    "nath",
    "kar",
    "dey",
    "islam",
    "ahmed",
    "hossain",
    "hasan",
    "rahman",
    "alam",
    "uddin",
    "khan",
    "begum",
    "khatun",
}

# Bangladesh-specific patronymic connectors
_BD_PATRONYMIC_CONNECTORS = {"bin", "binte", "ibn"}

# West Bengal -padhyay / -jee style double surnames (original + anglicised)
_WB_DOUBLE_SURNAMES = {
    "bandyopadhyay": "banerjee",
    "chattopadhyay": "chatterjee",
    "mukhopadhyay": "mukherjee",
    "gangopadhyay": "ganguly",
}


class D3SouthAsiaBengali(RegionSpec):
    """
    South Asia - Bengali (D3) region processor.

    Key linguistic features handled:
    * Bengali/Bangla script (U+0980 - U+09FF) with frequent Latin switching.
    * Honoric titles: Shri, Srimati, Babu stripped during clean.
    * Surname suffixes: -das, -dutta, -gupta, -roy, -sen, -bose, -ghosh.
    * Bangladesh vs West Bengal differences:
        - BD names may include patronymic connectors (bin/binte).
        - WB names often use anglicised -jee/-ji suffixes.
    * Double-barrelled original+anglicised surname variants
      (Bandyopadhyay / Banerjee, Chattopadhyay / Chatterjee, etc.).
    """

    def __init__(self):
        super().__init__(
            code="D3",
            yaml_files=["d3_south_asia_bengali.yaml"],
            scripts=["Bengali"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ISO 15919"],
        )

    # ------------------------------------------------------------------
    # clean  (in-place)
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry data according to D3 Bengali rules (in-place)."""
        for field in ("CanonicalLatin", "CanonicalNative"):
            val = entry.get(field)
            if val:
                entry[field] = self._clean_name(val)

        variants = entry.get("Variants", {})
        for obs in variants.get("Observed", []):
            if "str" in obs and obs["str"]:
                obs["str"] = self._clean_name(obs["str"])

    def _clean_name(self, name: str) -> str:
        if not name:
            return name

        name = self.apply_unicode_fold_exceptions(name)
        name = name.strip()
        name = self._strip_titles(name)
        name = re.sub(r"\s+", " ", name)
        # Normalise hyphens and dashes
        name = re.sub(r"[\u2013\u2014\u2212]", "-", name)
        name = re.sub(r"[,;:]+$", "", name)
        return name.strip()

    def _strip_titles(self, text: str) -> str:
        words = text.split()
        cleaned: List[str] = []
        for w in words:
            bare = w.rstrip(".,")
            if bare in _TITLES:
                continue
            cleaned.append(w)
        return " ".join(cleaned)

    # ------------------------------------------------------------------
    # augment  (in-place)
    # ------------------------------------------------------------------
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with D3-specific data (in-place)."""
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not canonical:
            return

        entry["RegionCode"] = self.code

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        extras = entry["RegionalExtras"]

        # Script detection
        native = entry.get("CanonicalNative", "")
        extras["script"] = "Bengali" if _has_bengali(native) else "Latin"

        # Extract components
        comps = self._extract_components(canonical)
        extras.update(comps)

        # Determine likely country heuristic
        extras["likely_country"] = self._guess_country(comps)

        # Surname suffix flag
        family = comps.get("family_name", "").lower()
        extras["has_surname_suffix"] = family in _SURNAME_SUFFIXES

        # Patronymic connector (Bangladesh)
        extras["has_patronymic"] = comps.get("patronymic_connector") is not None

        # Build synthesised variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []
        synth = entry["Variants"]["Synthesised"]

        given = comps.get("given_name", "")
        family_raw = comps.get("family_name", "")

        # Variant: "Family, Given"
        if given and family_raw:
            synth.append({"str": f"{family_raw}, {given}", "type": "family-comma-given"})

        # Variant: initials
        if given and family_raw:
            synth.append({"str": f"{given[0]}. {family_raw}", "type": "initials"})

        # Variant: anglicised <-> original surname
        family_lower = family_raw.lower()
        alt = _WB_DOUBLE_SURNAMES.get(family_lower)
        if alt is None:
            # Try reverse lookup
            for orig, ang in _WB_DOUBLE_SURNAMES.items():
                if ang == family_lower:
                    alt = orig
                    break
        if alt and given:
            synth.append({"str": f"{given} {alt.title()}", "type": "surname-variant"})

    def _extract_components(self, name: str) -> Dict[str, Any]:
        comps: Dict[str, Any] = {}

        # "Family, Given" format
        if ", " in name:
            parts = name.split(", ", 1)
            comps["family_name"] = parts[0].strip()
            comps["given_name"] = parts[1].strip()
            return comps

        words = name.split()
        if not words:
            return comps

        # Check for patronymic connector (bin / binte)
        connector_idx = None
        for i, w in enumerate(words):
            if w.lower() in _BD_PATRONYMIC_CONNECTORS and 0 < i < len(words) - 1:
                connector_idx = i
                break

        if connector_idx is not None:
            comps["given_name"] = " ".join(words[:connector_idx])
            comps["patronymic_connector"] = words[connector_idx]
            comps["family_name"] = " ".join(words[connector_idx + 1 :])
            return comps

        if len(words) == 1:
            comps["given_name"] = words[0]
        elif len(words) == 2:
            comps["given_name"] = words[0]
            comps["family_name"] = words[1]
        else:
            comps["given_name"] = words[0]
            comps["family_name"] = words[-1]
            comps["middle_name"] = " ".join(words[1:-1])

        return comps

    @staticmethod
    def _guess_country(comps: Dict[str, Any]) -> str:
        """Heuristic: if patronymic connector present -> BD, else IN."""
        if comps.get("patronymic_connector"):
            return "BD"
        family = comps.get("family_name", "").lower()
        bd_surnames = {
            "islam",
            "ahmed",
            "hossain",
            "hasan",
            "rahman",
            "alam",
            "uddin",
            "khan",
            "begum",
            "khatun",
        }
        if family in bd_surnames:
            return "BD"
        return "IN"

    # ------------------------------------------------------------------
    # validate  (raises RegionRuleError)
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to D3 Bengali rules."""
        canon_latin = entry.get("CanonicalLatin", "")
        canon_native = entry.get("CanonicalNative", "")

        if not canon_latin and not canon_native:
            raise RegionRuleError("D3: missing both CanonicalLatin and CanonicalNative")

        # Native text should be Bengali script (or Latin transliteration)
        if canon_native:
            has_bn = _has_bengali(canon_native)
            is_pure_latin = all(
                c.isascii() or c in " -'.," for c in canon_native if not c.isspace()
            )
            if not has_bn and not is_pure_latin:
                raise RegionRuleError(
                    f"D3: CanonicalNative contains unexpected script: {canon_native!r}"
                )

        # Latin canonical must not contain Bengali code-points
        if canon_latin and _has_bengali(canon_latin):
            raise RegionRuleError("D3: CanonicalLatin must not contain Bengali script characters")

        # Minimum length
        effective = canon_latin or canon_native
        if effective and len(effective.replace(" ", "").replace(".", "")) < 2:
            raise RegionRuleError(f"D3: name too short: {effective!r}")

        # Character validation on Latin form
        if canon_latin and not self._valid_latin_chars(canon_latin):
            raise RegionRuleError(f"D3: invalid characters in CanonicalLatin: {canon_latin!r}")

    @staticmethod
    def _valid_latin_chars(text: str) -> bool:
        for ch in text:
            if ch.isalpha() and ord(ch) < 0x0300:
                continue
            if ch in " -'.,":
                continue
            if unicodedata.category(ch).startswith("M"):
                continue
            return False
        return True

    # ------------------------------------------------------------------
    # order_key  (pure function -> str)
    # ------------------------------------------------------------------
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for D3 Bengali names.

        Primary sort by family name (surname), secondary by given name.
        """
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")
        middle = extras.get("middle_name", "")

        if not family and not given:
            canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
            return re.sub(r"[^\w\s]", "", canonical).upper().strip()

        parts = []
        if family:
            parts.append(family.upper())
        if given:
            parts.append(given.upper())
        if middle:
            parts.append(middle.upper())

        key = " ".join(parts)
        key = re.sub(r"[^\w\s]", "", key)
        return " ".join(key.split())
