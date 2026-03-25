"""
D4 - Pakistan & Urdu region implementation.

Covers: Pakistan, Urdu-speaking diaspora
Features: Urdu / Arabic script (Nastaliq style), right-to-left text,
          Khan/Chaudhry/Malik honorific-title patterns, bin/bint
          patronymics, tribal and caste identifiers.

Script ranges:
  Arabic core    U+0600 - U+06FF
  Arabic Supp.   U+0750 - U+077F  (includes Urdu-specific characters)
  Arabic Ext-A   U+08A0 - U+08FF  (additional Urdu forms)
"""

import re
import unicodedata
from typing import Any, Dict, List, Tuple

from ..base import RegionRuleError, RegionSpec


# ---------------------------------------------------------------------------
# Script helpers
# ---------------------------------------------------------------------------
_ARABIC_URDU_RANGES: List[Tuple[int, int]] = [
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement (Urdu-specific letters)
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
]


def _in_arabic_urdu(char: str) -> bool:
    cp = ord(char)
    return any(lo <= cp <= hi for lo, hi in _ARABIC_URDU_RANGES)


def _has_arabic_urdu(text: str) -> bool:
    return any(_in_arabic_urdu(c) for c in text)


# ---------------------------------------------------------------------------
# RTL handling helpers
# ---------------------------------------------------------------------------
_RTL_MARKS = {"\u200f", "\u200e", "\u061c", "\u202b", "\u202c", "\u202a"}


def _strip_bidi(text: str) -> str:
    """Remove Unicode bidi control characters."""
    return "".join(c for c in text if c not in _RTL_MARKS)


# ---------------------------------------------------------------------------
# Titles and honorifics
# ---------------------------------------------------------------------------
_TITLES = {
    # Urdu / Pakistani titles (Latin transliterations)
    "Khan",
    "Chaudhry",
    "Chaudhary",
    "Choudhry",
    "Choudhary",
    "Malik",
    "Mian",
    "Mir",
    "Syed",
    "Sayyid",
    "Sayyed",
    "Sheikh",
    "Shaikh",
    "Pir",
    "Sardar",
    "Nawab",
    "Begum",
    "Bibi",
    "Rani",
    "Raja",
    # Professional / religious
    "Dr",
    "Dr.",
    "Prof",
    "Prof.",
    "Engr",
    "Engr.",
    "Maulvi",
    "Maulana",
    "Mufti",
    "Qari",
    "Hafiz",
    "Hafiza",
    "Haji",
    "Hajia",
    "Allama",
    "Justice",
    # Urdu script titles
    "\u062e\u0627\u0646",  # Khan
    "\u0686\u0648\u062f\u0631\u06cc",  # Chaudhry
    "\u0645\u0644\u06a9",  # Malik
    "\u0645\u06cc\u0627\u0646",  # Mian
    "\u0633\u06cc\u062f",  # Syed
    "\u0628\u06cc\u06af\u0645",  # Begum
}

# Titles that may ALSO be surnames -- we only strip them from the leading
# position when they appear before a longer name.
_TITLE_ALSO_SURNAME = {
    "Khan",
    "Malik",
    "Chaudhry",
    "Chaudhary",
    "Choudhry",
    "Sheikh",
    "Shaikh",
    "Syed",
    "Sayyid",
    "Mir",
}

# Patronymic connectors
_PATRONYMIC_CONNECTORS = {"bin", "ibn", "bint", "binte"}

# Common Pakistani tribal / caste identifiers that appear as final element
_TRIBAL_IDENTIFIERS = {
    "khan",
    "malik",
    "butt",
    "bhatti",
    "rajput",
    "jatt",
    "jutt",
    "awan",
    "qureshi",
    "siddiqui",
    "abbasi",
    "shah",
    "mirza",
    "mughal",
    "moghul",
    "hashmi",
    "zaidi",
    "naqvi",
    "rizvi",
    "gilani",
    "bukhari",
    "chaudhry",
    "choudhry",
    "sheikh",
    "shaikh",
    "paracha",
    "marwat",
    "khattak",
    "afridi",
    "yousafzai",
    "wazir",
    "mehsud",
    "baloch",
    "baluch",
    "durrani",
    "lodhi",
    "gujjar",
    "arain",
    "niazi",
}


class D4PakistanUrdu(RegionSpec):
    """
    Pakistan & Urdu (D4) region processor.

    Key linguistic features handled:
    * Urdu script (Arabic + Urdu-specific characters) with RTL handling.
    * Khan/Chaudhry/Malik patterns -- these words function as both
      honorific titles *and* surnames depending on position.
    * bin/bint patronymic system inherited from Arabic tradition.
    * Tribal and caste identifiers as final name element.
    * Nastaliq calligraphic style requires careful bidi handling.
    """

    def __init__(self):
        super().__init__(
            code="D4",
            yaml_files=["d4_pakistan_urdu.yaml"],
            scripts=["Arabic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ALA-LC"],
        )

    # ------------------------------------------------------------------
    # clean  (in-place)
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry data according to D4 Pakistan/Urdu rules (in-place)."""
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
        name = _strip_bidi(name)
        name = name.strip()

        # Strip honorific titles (only from leading position when followed
        # by additional name parts)
        name = self._strip_leading_titles(name)

        # Normalise whitespace
        name = re.sub(r"\s+", " ", name)

        # Normalise hyphens / dashes
        name = re.sub(r"[\u2013\u2014\u2212]", "-", name)

        # Remove trailing punctuation
        name = re.sub(r"[,;:]+$", "", name)

        return name.strip()

    @staticmethod
    def _strip_leading_titles(text: str) -> str:
        """Remove leading titles, but only when the remaining name
        has at least two tokens (to avoid stripping 'Khan' when it
        is the entire surname)."""
        words = text.split()
        if len(words) <= 1:
            return text

        stripped: List[str] = []
        title_phase = True
        for i, w in enumerate(words):
            bare = w.rstrip(".,")
            remaining = len(words) - i - 1
            if title_phase and bare in _TITLES and remaining >= 1:
                # Only strip if there is still substance left
                continue
            else:
                title_phase = False
                stripped.append(w)

        return " ".join(stripped) if stripped else text

    # ------------------------------------------------------------------
    # augment  (in-place)
    # ------------------------------------------------------------------
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with D4-specific data (in-place)."""
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if not canonical:
            return

        entry["RegionCode"] = self.code

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        extras = entry["RegionalExtras"]

        # Script detection
        native = entry.get("CanonicalNative", "")
        extras["script"] = "Arabic" if _has_arabic_urdu(native) else "Latin"
        extras["likely_country"] = "PK"

        # Extract components
        comps = self._extract_components(canonical)
        extras.update(comps)

        # Patronymic flag
        extras["has_patronymic"] = comps.get("patronymic_connector") is not None
        if comps.get("patronymic_connector"):
            extras["patronymic_type"] = "bin-bint"

        # Tribal identifier flag
        family = comps.get("family_name", "").lower()
        extras["has_tribal_id"] = family in _TRIBAL_IDENTIFIERS

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
            initial = given.split()[0][0] if given else ""
            if initial:
                synth.append({"str": f"{initial}. {family_raw}", "type": "initials"})

        # Variant: with patronymic expanded
        connector = comps.get("patronymic_connector")
        father = comps.get("father_name", "")
        if connector and father and given:
            synth.append(
                {
                    "str": f"{given} {connector} {father}",
                    "type": "patronymic-expanded",
                }
            )

        # Variant: without patronymic (short form)
        if connector and given and family_raw:
            synth.append({"str": f"{given} {family_raw}", "type": "short-form"})

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

        # Detect patronymic connector (bin / bint)
        connector_idx = None
        for i, w in enumerate(words):
            if w.lower() in _PATRONYMIC_CONNECTORS and 0 < i < len(words) - 1:
                connector_idx = i
                break

        if connector_idx is not None:
            comps["given_name"] = " ".join(words[:connector_idx])
            comps["patronymic_connector"] = words[connector_idx]
            remaining = words[connector_idx + 1 :]
            if len(remaining) == 1:
                comps["father_name"] = remaining[0]
                comps["family_name"] = remaining[0]
            else:
                comps["father_name"] = remaining[0]
                comps["family_name"] = remaining[-1]
            return comps

        if len(words) == 1:
            comps["given_name"] = words[0]
        elif len(words) == 2:
            comps["given_name"] = words[0]
            comps["family_name"] = words[1]
        elif len(words) == 3:
            comps["given_name"] = words[0]
            comps["middle_name"] = words[1]
            comps["family_name"] = words[2]
        else:
            comps["given_name"] = words[0]
            comps["family_name"] = words[-1]
            comps["middle_name"] = " ".join(words[1:-1])

        return comps

    # ------------------------------------------------------------------
    # validate  (raises RegionRuleError)
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to D4 Pakistan/Urdu rules."""
        canon_latin = entry.get("CanonicalLatin", "")
        canon_native = entry.get("CanonicalNative", "")

        if not canon_latin and not canon_native:
            raise RegionRuleError("D4: missing both CanonicalLatin and CanonicalNative")

        # Native text should be Arabic/Urdu script or Latin transliteration
        if canon_native:
            has_au = _has_arabic_urdu(canon_native)
            is_latin = all(c.isascii() or c in " -'.," for c in canon_native if not c.isspace())
            if not has_au and not is_latin:
                raise RegionRuleError(
                    f"D4: CanonicalNative contains unexpected script: {canon_native!r}"
                )

        # Latin canonical must not contain Arabic/Urdu code-points
        if canon_latin and _has_arabic_urdu(canon_latin):
            raise RegionRuleError(
                "D4: CanonicalLatin must not contain Arabic/Urdu script characters"
            )

        # Minimum length
        effective = canon_latin or canon_native
        if effective and len(effective.replace(" ", "").replace(".", "")) < 2:
            raise RegionRuleError(f"D4: name too short: {effective!r}")

        # Character validation on Latin form
        if canon_latin and not self._valid_latin_chars(canon_latin):
            raise RegionRuleError(f"D4: invalid characters in CanonicalLatin: {canon_latin!r}")

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
        """Generate deterministic sort key for D4 Pakistani/Urdu names.

        Primary sort by family name / tribal identifier, secondary by
        given name.  Patronymic connectors are excluded from the key.
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
