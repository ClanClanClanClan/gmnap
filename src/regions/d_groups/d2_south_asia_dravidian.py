"""
D2 - South Asia Dravidian region implementation.

Covers: Tamil Nadu, Andhra Pradesh/Telangana, Karnataka, Kerala (India)
Features: Tamil/Telugu/Kannada/Malayalam scripts, patronymic initial system,
          father's-name-as-initial convention, no traditional family names
          in Tamil, caste suffixes in Telugu/Kannada.

Script ranges:
  Tamil     U+0B80 - U+0BFF
  Telugu    U+0C00 - U+0C7F
  Kannada   U+0C80 - U+0CFF
  Malayalam U+0D00 - U+0D7F
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from ..base import RegionRuleError, RegionSpec


# ---------------------------------------------------------------------------
# Script-range helpers
# ---------------------------------------------------------------------------
_SCRIPT_RANGES: Dict[str, List[Tuple[int, int]]] = {
    "Tamil":     [(0x0B80, 0x0BFF)],
    "Telugu":    [(0x0C00, 0x0C7F)],
    "Kannada":   [(0x0C80, 0x0CFF)],
    "Malayalam": [(0x0D00, 0x0D7F)],
}

_ALL_DRAVIDIAN_RANGES: List[Tuple[int, int]] = [
    r for ranges in _SCRIPT_RANGES.values() for r in ranges
]


def _in_ranges(char: str, ranges: List[Tuple[int, int]]) -> bool:
    cp = ord(char)
    return any(lo <= cp <= hi for lo, hi in ranges)


def _has_script(text: str, script: str) -> bool:
    ranges = _SCRIPT_RANGES.get(script, [])
    return any(_in_ranges(c, ranges) for c in text)


def _has_any_dravidian(text: str) -> bool:
    return any(_in_ranges(c, _ALL_DRAVIDIAN_RANGES) for c in text)


def _detect_dravidian_script(text: str) -> Optional[str]:
    """Return the dominant Dravidian script name, or None."""
    for script, ranges in _SCRIPT_RANGES.items():
        if any(_in_ranges(c, ranges) for c in text):
            return script
    return None


# ---------------------------------------------------------------------------
# Shared data
# ---------------------------------------------------------------------------
_TITLES = {
    # Common honorifics (Latin transliterations)
    "Thiru", "Thirumathi", "Selvi", "Selvan",
    "Sri", "Shri", "Smt", "Smt.", "Kumari",
    "Dr", "Dr.", "Prof", "Prof.", "Er", "Er.",
    # Tamil script titles
    "\u0BA4\u0BBF\u0BB0\u0BC1",           # Thiru
    "\u0BA4\u0BBF\u0BB0\u0BC1\u0BAE\u0BA4\u0BBF",  # Thirumathi
}

# Patronymic initial pattern: single uppercase letter followed by a dot
_INITIAL_RE = re.compile(r"^([A-Z])\.\s*")

# Common Dravidian caste / community suffixes (Latin)
_CASTE_SUFFIXES = {
    # Tamil
    "Pillai", "Mudaliar", "Nadar", "Gounder", "Thevar", "Naicker",
    "Nair", "Naidu", "Chettiar", "Iyer", "Iyengar", "Mudali",
    # Telugu
    "Reddy", "Rao", "Naidu", "Raju", "Setty", "Chetty",
    # Kannada
    "Gowda", "Shetty", "Hegde", "Bhat", "Acharya",
    # Malayalam
    "Nair", "Menon", "Nambiar", "Kurup", "Pillai", "Warrier",
    "Namboothiri", "Nambudiri", "Panicker",
}

# Lowercase versions for matching
_CASTE_SUFFIXES_LOWER = {s.lower() for s in _CASTE_SUFFIXES}

# Common Dravidian given names for validation heuristic
_COMMON_GIVEN = {
    "Ramanujan", "Srinivasa", "Venkatesh", "Subramaniam",
    "Krishnamurthy", "Raghavan", "Lakshmi", "Meenakshi",
    "Anand", "Arun", "Balaji", "Ganesh", "Hari", "Karthik",
    "Mohan", "Nandini", "Priya", "Ravi", "Selvam", "Vimal",
}


class D2SouthAsiaDravidian(RegionSpec):
    """
    South Asia - Dravidian (D2) region processor.

    Key linguistic features handled:
    * Patronymic initial system -- e.g. "S. Ramanujan" where S stands
      for the father's given name Srinivasa.
    * Traditional Tamil names often lack a hereditary family name;
      the father's name serves as an initial.
    * Telugu/Kannada names may carry caste suffixes (Reddy, Gowda, etc.).
    * Four native scripts: Tamil, Telugu, Kannada, Malayalam.
    """

    def __init__(self):
        super().__init__(
            code="D2",
            yaml_files=["d2_south_asia_dravidian.yaml"],
            scripts=["Tamil", "Telugu", "Kannada", "Malayalam"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ISO 15919"],
        )

    # ------------------------------------------------------------------
    # clean  (in-place)
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry data according to D2 Dravidian rules (in-place)."""
        for field in ("CanonicalLatin", "CanonicalNative"):
            val = entry.get(field)
            if val:
                entry[field] = self._clean_name(val)

        # Clean observed variants
        variants = entry.get("Variants", {})
        for obs in variants.get("Observed", []):
            if "str" in obs and obs["str"]:
                obs["str"] = self._clean_name(obs["str"])

    def _clean_name(self, name: str) -> str:
        if not name:
            return name

        # Apply unicode fold exceptions from base class
        name = self.apply_unicode_fold_exceptions(name)

        # Strip leading/trailing whitespace
        name = name.strip()

        # Remove honorific titles
        name = self._strip_titles(name)

        # Normalise whitespace
        name = re.sub(r"\s+", " ", name)

        # Normalise punctuation around initials  (e.g. "S .R." -> "S. R.")
        name = re.sub(r"\s+\.", ".", name)

        # Remove trailing punctuation (commas, semicolons)
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
        """Augment entry with D2-specific data (in-place)."""
        canonical = (
            entry.get("CanonicalLatin", "")
            or entry.get("CanonicalNative", "")
        )
        if not canonical:
            return

        entry["RegionCode"] = self.code

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        extras = entry["RegionalExtras"]

        # Detect script
        native = entry.get("CanonicalNative", "")
        detected = _detect_dravidian_script(native) if native else None
        extras["script"] = detected or "Latin"
        extras["likely_country"] = "IN"

        # Extract components
        comps = self._extract_components(canonical)
        extras.update(comps)

        # Flag patronymic-initial usage
        extras["has_patronymic_initial"] = comps.get("patronymic_initial") is not None

        # Flag caste suffix
        family = comps.get("family_name", "")
        if family.lower() in _CASTE_SUFFIXES_LOWER:
            extras["has_caste_suffix"] = True
            extras["caste_suffix"] = family
        else:
            extras["has_caste_suffix"] = False

        # Flag mononym (traditional Tamil -- no family name)
        extras["is_mononym"] = (
            bool(comps.get("given_name")) and not comps.get("family_name")
        )

        # Build synthesised variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        synth = entry["Variants"]["Synthesised"]

        # Variant 1: expand patronymic initial if present
        initial = comps.get("patronymic_initial")
        given = comps.get("given_name", "")
        family = comps.get("family_name", "")
        if initial and given:
            # "S. Ramanujan" -> "Ramanujan, S."
            synth.append({"str": f"{given}, {initial}.", "type": "family-comma-given"})

        # Variant 2: initials form
        if given and family:
            synth.append({"str": f"{given[0]}. {family}", "type": "initials"})

        # Variant 3: reversed "Family, Given"
        if given and family:
            synth.append({"str": f"{family}, {given}", "type": "family-comma-given"})

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Parse a Dravidian name into components."""
        comps: Dict[str, Any] = {}

        # Check for leading patronymic initial  ("S. Ramanujan")
        m = _INITIAL_RE.match(name)
        if m:
            comps["patronymic_initial"] = m.group(1)
            rest = name[m.end():].strip()
        else:
            rest = name

        # Canonical-comma form: "Family, Given"
        if ", " in rest:
            parts = rest.split(", ", 1)
            comps["family_name"] = parts[0].strip()
            comps["given_name"] = parts[1].strip()
            return comps

        words = rest.split()
        if len(words) == 0:
            return comps
        elif len(words) == 1:
            # Mononym or single-part
            comps["given_name"] = words[0]
        elif len(words) == 2:
            comps["given_name"] = words[0]
            comps["family_name"] = words[1]
        else:
            # 3+ words: first is given, last is family, middle parts joined
            comps["given_name"] = words[0]
            comps["family_name"] = words[-1]
            comps["middle_name"] = " ".join(words[1:-1])

        return comps

    # ------------------------------------------------------------------
    # validate  (raises RegionRuleError)
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to D2 rules."""
        canon_latin = entry.get("CanonicalLatin", "")
        canon_native = entry.get("CanonicalNative", "")

        if not canon_latin and not canon_native:
            raise RegionRuleError("D2: missing both CanonicalLatin and CanonicalNative")

        # If native text is present it must belong to a Dravidian script (or Latin)
        if canon_native:
            is_dravidian = _has_any_dravidian(canon_native)
            is_latin = all(
                c.isascii() or c in " -'.,"
                for c in canon_native
                if not c.isspace()
            )
            if not is_dravidian and not is_latin:
                raise RegionRuleError(
                    f"D2: CanonicalNative contains non-Dravidian script: "
                    f"{canon_native!r}"
                )

        # Latin canonical should not contain Dravidian code-points
        if canon_latin and _has_any_dravidian(canon_latin):
            raise RegionRuleError(
                "D2: CanonicalLatin must not contain Dravidian script characters"
            )

        # Minimum length
        effective = canon_latin or canon_native
        if effective and len(effective.replace(" ", "").replace(".", "")) < 2:
            raise RegionRuleError(f"D2: name too short: {effective!r}")

        # Validate characters in Latin form
        if canon_latin and not self._valid_latin_chars(canon_latin):
            raise RegionRuleError(
                f"D2: invalid characters in CanonicalLatin: {canon_latin!r}"
            )

    @staticmethod
    def _valid_latin_chars(text: str) -> bool:
        for ch in text:
            if ch.isalpha() and ord(ch) < 0x0300:
                continue
            if ch in " -'.,":
                continue
            if unicodedata.category(ch).startswith("M"):
                # combining marks from transliteration
                continue
            return False
        return True

    # ------------------------------------------------------------------
    # order_key  (pure function -> str)
    # ------------------------------------------------------------------
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for D2 names.

        Dravidian convention: sort by family name (or caste suffix) first,
        then given name.  When the name is a mononym or uses only a
        patronymic initial, sort by the given name alone.
        """
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")
        middle = extras.get("middle_name", "")

        # Fallback to canonical text
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
