"""
D5 - Sinhala region implementation.

Covers: Sri Lanka (Sinhalese community)
Features: Sinhala script (U+0D80 - U+0DFF), long multi-part names
          (Jayawardena, Wickramasinghe), colonial-era anglicised surnames,
          Ge names (clan/caste-based hereditary titles).

Script range:
  Sinhala  U+0D80 - U+0DFF
"""

import re
import unicodedata
from typing import Any, Dict, List, Tuple

from ..base import RegionRuleError, RegionSpec


# ---------------------------------------------------------------------------
# Script helpers
# ---------------------------------------------------------------------------
_SINHALA_RANGE: Tuple[int, int] = (0x0D80, 0x0DFF)


def _in_sinhala(char: str) -> bool:
    cp = ord(char)
    return _SINHALA_RANGE[0] <= cp <= _SINHALA_RANGE[1]


def _has_sinhala(text: str) -> bool:
    return any(_in_sinhala(c) for c in text)


# ---------------------------------------------------------------------------
# Titles and honorifics
# ---------------------------------------------------------------------------
_TITLES = {
    # Sinhala Latin-transliterated titles
    "Mr",
    "Mr.",
    "Mrs",
    "Mrs.",
    "Miss",
    "Ms",
    "Ms.",
    "Dr",
    "Dr.",
    "Prof",
    "Prof.",
    "Rev",
    "Rev.",
    "Sir",
    "Lady",
    "Ven",
    "Ven.",  # Venerable (monks)
    "Vidyajothi",
    "Deshamanya",
    "Deshabandu",  # National honours
    "Mahanayaka",  # Senior Buddhist monk
    # Sinhala script titles (common)
    "\u0db8\u0dc4\u0dad\u0dcf",  # Mahatha (Mr)
    "\u0db8\u0dc4\u0dad\u0dca\u0db8\u0dd2\u0dba",  # Mahathmiya
}

# ---------------------------------------------------------------------------
# Ge names (clan / caste hereditary titles)
# ---------------------------------------------------------------------------
_GE_NAMES = {
    # High-caste Ge names (Govigama and related)
    "mudiyanselage",
    "mudiyanse",
    "herath",
    "herat",
    "dissanayake",
    "dissanayaka",
    "bandaranayake",
    "bandaranaike",
    "jayawardena",
    "jayawardene",
    "jayewardene",
    "wickramasinghe",
    "wickremasinghe",
    "ratnayake",
    "rathnayake",
    "kumarasinghe",
    "kumarasingha",
    "samarasinghe",
    "samarasingha",
    "senanayake",
    "senanayaka",
    "ekanayake",
    "ekanayaka",
    "karunaratne",
    "karunarathne",
    "gunawardena",
    "gunawardene",
    "weerasinghe",
    "weerasingha",
    "pathirana",
    "pathiraja",
    "liyanage",
    "liyanaarachchi",
    "amarasinghe",
    "amarasingha",
    "hewage",
    "gamage",
    "arachchige",
    "vithanage",
    "hettiarachchi",
    # Ge prefixes (appear before personal name)
    "don",
    "dona",
    "de",
}

# Ge suffixes that indicate the name is a Ge element
_GE_SUFFIXES = {"ge", "lage", "arachchi", "achchi"}

# ---------------------------------------------------------------------------
# Colonial anglicised surnames
# ---------------------------------------------------------------------------
_COLONIAL_SURNAMES = {
    "de silva",
    "de mel",
    "de soysa",
    "de alwis",
    "de zoysa",
    "fernando",
    "perera",
    "pereira",
    "de saram",
    "fonseka",
    "fonseca",
    "peiris",
    "pieris",
    "dias",
    "jayasuriya",
    "mendis",
    "rodrigo",
    "gomes",
    "corea",
    "ondaatje",
}

# Common long Sinhalese surnames (for validation heuristic)
_COMMON_SURNAMES_LOWER = {
    "jayawardena",
    "wickramasinghe",
    "bandara",
    "dissanayake",
    "senanayake",
    "ratnayake",
    "gunawardena",
    "karunaratne",
    "samarasinghe",
    "ekanayake",
    "kumarasinghe",
    "weerasinghe",
    "pathirana",
    "liyanage",
    "amarasinghe",
    "vithanage",
    "fernando",
    "perera",
    "de silva",
    "silva",
    "fonseka",
    "peiris",
    "mendis",
    "dias",
    "bandara",
    "herath",
    "kumara",
    "lakmal",
    "gamage",
    "rathnayake",
}


class D5Sinhala(RegionSpec):
    """
    Sinhala (D5) region processor.

    Key linguistic features handled:
    * Sinhala script (U+0D80 - U+0DFF) and Latin transliteration.
    * Very long multi-part names common in Sinhalese tradition
      (e.g. Herath Mudiyanselage Don Karunasena Jayawardena).
    * Ge names -- clan/hereditary titles that precede the personal name
      (e.g. Mudiyanselage, Arachchige, Gamage, Hewage).
    * Colonial-era anglicised (Portuguese / Dutch / English) surnames
      (de Silva, Fernando, Perera, Peiris).
    * Sri Lankan national honour prefixes stripped as titles.
    """

    def __init__(self):
        super().__init__(
            code="D5",
            yaml_files=["d5_sinhala.yaml"],
            scripts=["Sinhala"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["UN 2003"],
        )

    # ------------------------------------------------------------------
    # clean  (in-place)
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry data according to D5 Sinhala rules (in-place)."""
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

        # Remove titles / honorifics
        name = self._strip_titles(name)

        # Normalise whitespace
        name = re.sub(r"\s+", " ", name)

        # Normalise hyphens
        name = re.sub(r"[\u2013\u2014\u2212]", "-", name)

        # Remove trailing punctuation
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
        """Augment entry with D5-specific data (in-place)."""
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not canonical:
            return

        entry["RegionCode"] = self.code

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        extras = entry["RegionalExtras"]

        # Script detection
        native = entry.get("CanonicalNative", "")
        extras["script"] = "Sinhala" if _has_sinhala(native) else "Latin"
        extras["likely_country"] = "LK"

        # Extract components
        comps = self._extract_components(canonical)
        extras.update(comps)

        # Flag Ge name
        extras["has_ge_name"] = bool(comps.get("ge_name"))

        # Flag colonial surname
        family = comps.get("family_name", "").lower()
        family_two = " ".join([comps.get("surname_particle", ""), family]).strip().lower()
        extras["has_colonial_surname"] = (
            family_two in _COLONIAL_SURNAMES or family in _COLONIAL_SURNAMES
        )

        # Build synthesised variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []
        synth = entry["Variants"]["Synthesised"]

        given = comps.get("given_name", "")
        family_raw = comps.get("family_name", "")
        particle = comps.get("surname_particle", "")

        full_family = f"{particle} {family_raw}".strip() if particle else family_raw

        # Variant: "Family, Given"
        if given and full_family:
            synth.append({"str": f"{full_family}, {given}", "type": "family-comma-given"})

        # Variant: initials
        if given and full_family:
            synth.append({"str": f"{given[0]}. {full_family}", "type": "initials"})

        # Variant: without Ge name (short form)
        ge = comps.get("ge_name", "")
        if ge and given and full_family:
            synth.append({"str": f"{given} {full_family}", "type": "short-form"})

        # Variant: with Ge name fully expanded
        if ge and given and full_family:
            synth.append(
                {
                    "str": f"{ge} {given} {full_family}",
                    "type": "ge-expanded",
                }
            )

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

        # Identify Ge name elements at the front
        ge_parts: List[str] = []
        remaining: List[str] = list(words)
        while remaining:
            w_lower = remaining[0].lower()
            # Check if it is a known Ge name or ends with a Ge suffix
            is_ge = w_lower in _GE_NAMES
            if not is_ge:
                is_ge = any(w_lower.endswith(suf) for suf in _GE_SUFFIXES)
            if is_ge:
                ge_parts.append(remaining.pop(0))
            else:
                break

        if ge_parts:
            comps["ge_name"] = " ".join(ge_parts)

        # Detect colonial "de" particle before surname
        # Pattern: ... de Silva, ... de Mel
        particle = ""
        if len(remaining) >= 2 and remaining[-2].lower() == "de":
            particle = remaining[-2]
            comps["surname_particle"] = particle
            comps["family_name"] = remaining[-1]
            personal = remaining[:-2]
        elif len(remaining) >= 1:
            comps["family_name"] = remaining[-1]
            personal = remaining[:-1]
        else:
            personal = []

        if len(personal) == 0:
            # Only one word left -- treat as given name
            if "family_name" in comps and not ge_parts:
                comps["given_name"] = comps.pop("family_name")
            elif "family_name" in comps:
                comps["given_name"] = comps["family_name"]
                comps["family_name"] = ""
        elif len(personal) == 1:
            comps["given_name"] = personal[0]
        else:
            comps["given_name"] = personal[0]
            comps["middle_name"] = " ".join(personal[1:])

        return comps

    # ------------------------------------------------------------------
    # validate  (raises RegionRuleError)
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to D5 Sinhala rules."""
        canon_latin = entry.get("CanonicalLatin", "")
        canon_native = entry.get("CanonicalNative", "")

        if not canon_latin and not canon_native:
            raise RegionRuleError("D5: missing both CanonicalLatin and CanonicalNative")

        # Native text should be Sinhala script or Latin transliteration
        if canon_native:
            has_sinh = _has_sinhala(canon_native)
            is_latin = all(c.isascii() or c in " -'.," for c in canon_native if not c.isspace())
            if not has_sinh and not is_latin:
                raise RegionRuleError(
                    f"D5: CanonicalNative contains unexpected script: {canon_native!r}"
                )

        # Latin canonical must not contain Sinhala code-points
        if canon_latin and _has_sinhala(canon_latin):
            raise RegionRuleError("D5: CanonicalLatin must not contain Sinhala script characters")

        # Minimum length
        effective = canon_latin or canon_native
        if effective and len(effective.replace(" ", "").replace(".", "")) < 2:
            raise RegionRuleError(f"D5: name too short: {effective!r}")

        # Character validation on Latin form
        if canon_latin and not self._valid_latin_chars(canon_latin):
            raise RegionRuleError(f"D5: invalid characters in CanonicalLatin: {canon_latin!r}")

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
        """Generate deterministic sort key for D5 Sinhala names.

        Primary sort by family name (including colonial particle),
        secondary by given name.  Ge name is excluded from the sort key
        to keep ordering consistent regardless of Ge expansion.
        """
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")
        middle = extras.get("middle_name", "")
        particle = extras.get("surname_particle", "")

        if not family and not given:
            canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
            return re.sub(r"[^\w\s]", "", canonical).upper().strip()

        parts = []
        # Include particle for correct alphabetical placement
        # "de Silva" sorts under D
        if particle:
            parts.append(f"{particle} {family}".upper())
        elif family:
            parts.append(family.upper())
        if given:
            parts.append(given.upper())
        if middle:
            parts.append(middle.upper())

        key = " ".join(parts)
        key = re.sub(r"[^\w\s]", "", key)
        return " ".join(key.split())
