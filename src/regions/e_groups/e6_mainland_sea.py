"""
E6 - Mainland SEA regional processor.

Covers: Thailand (TH), Cambodia (KH), Laos (LA)
Features: Thai RTGS romanisation, Khmer UNGEGN, Lao MOICT,
          Thai no-space word boundaries, Khmer no-family-name tradition,
          Thai surname law (since 1913).

Script ranges:
  Thai   U+0E00-U+0E7F
  Khmer  U+1780-U+17FF
  Lao    U+0E80-U+0EFF
"""

import re
import unicodedata
from typing import Any, Dict, Optional

from ..base import RegionSpec, RegionRuleError


class E6MainlandSEA(RegionSpec):
    """
    Mainland SEA region (E6).

    Handles Thai, Khmer and Lao naming conventions:
    - Thai: family name law since 1913, given-name-first order,
      no spaces between words in native script, RTGS romanisation.
    - Khmer: traditionally no family names, given-name-first order,
      UNGEGN romanisation.
    - Lao: similar to Thai structure, MOICT romanisation.
    """

    def __init__(self):
        super().__init__(
            code="E6",
            yaml_files=["e6_mainland_sea.yaml"],
            scripts=["Thai", "Khmer", "Lao", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["RTGS", "UNGEGN", "MOICT"],
        )

        # Thai script range U+0E00-U+0E7F
        self.thai_range = (0x0E00, 0x0E7F)
        # Khmer script range U+1780-U+17FF
        self.khmer_range = (0x1780, 0x17FF)
        # Lao script range U+0E80-U+0EFF
        self.lao_range = (0x0E80, 0x0EFF)

        # Common titles to strip
        self.titles = {
            # Thai
            "นาย",
            "นาง",
            "นางสาว",
            "ดร.",
            "ดร",
            "ศ.",
            "ศ.ดร.",
            "รศ.",
            "รศ.ดร.",
            "ผศ.",
            "ผศ.ดร.",
            "คุณ",
            "พ.ต.อ.",
            "พล.อ.",
            "พล.ต.",
            # Khmer
            "លោក",
            "អ្នកស្រី",
            "ឯកឧត្តម",
            # Lao
            "ທ່ານ",
            "ນາງ",
            # Latin equivalents common in academic contexts
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Khun",
            "Nai",
            "Nang",
        }

        # Thai honorific particles (often follow given name)
        self.thai_particles = {"ณ", "ณ ", "บ", "ป"}

        # Common Thai compound surname prefixes
        self.thai_surname_prefixes = {
            "วง",
            "ศรี",
            "สุ",
            "ชัย",
            "พร",
            "ทอง",
            "สิริ",
            "วัฒน",
        }

    # ------------------------------------------------------------------
    # clean
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to E6 rules (modifies in-place)."""
        for field in ("CanonicalLatin", "CanonicalNative"):
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])

        # Clean observed variants
        if "Variants" in entry:
            if "Observed" in entry["Variants"]:
                for variant in entry["Variants"]["Observed"]:
                    if "str" in variant:
                        variant["str"] = self._clean_name(variant["str"])

    def _clean_name(self, name: str) -> str:
        """Clean a single Mainland SEA name string."""
        if not isinstance(name, str):
            raise RegionRuleError(f"Name must be string, not {type(name).__name__}")
        if not name:
            return name

        # Security: reject dangerous control characters
        if any(ord(c) < 32 and c not in "\t\n\r " for c in name):
            raise RegionRuleError("Name contains dangerous control characters")

        # Remove titles
        name = self._remove_titles(name)

        # Normalise Unicode (NFC for Thai/Khmer/Lao combining marks)
        name = unicodedata.normalize("NFC", name)

        # Normalise whitespace (but preserve lack of spaces in Thai script)
        name = re.sub(r"[ \t]+", " ", name)

        # Normalise punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Strip titles from beginning of name."""
        if not text:
            return text

        changed = True
        while changed:
            changed = False
            stripped = text.lstrip()
            for title in sorted(self.titles, key=len, reverse=True):
                if stripped.startswith(title):
                    stripped = stripped[len(title) :].lstrip(" .")
                    text = stripped
                    changed = True
                    break
        return text

    # ------------------------------------------------------------------
    # augment
    # ------------------------------------------------------------------
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with E6-specific data (modifies in-place)."""
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")
        name_to_analyze = native if native else canonical
        if not name_to_analyze:
            return

        components = self._extract_components(name_to_analyze)

        # Detect script
        script = self._detect_script(name_to_analyze)
        components["script"] = script

        # Detect likely country from script
        likely_country = self._detect_country(name_to_analyze, script)
        if likely_country:
            components["likely_country"] = likely_country

        # Khmer: traditionally no family name
        if likely_country == "KH" and not components.get("family_name"):
            components["is_mononym"] = True
            entry["FamilyNameType"] = "mononym"

        # Ensure RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        entry["RegionalExtras"].update(components)

        # Ensure Variants structure
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate order-swap variant for non-mononyms
        family = components.get("family_name", "")
        given = components.get("given_name", "")
        if family and given:
            swapped = f"{family}, {given}"
            if swapped != canonical:
                entry["Variants"]["Synthesised"].append({"str": swapped, "type": "order-swap"})

        # Rule 27: Generate romanisation variant for native-script names
        if native and script in ("Thai", "Khmer", "Lao"):
            romanised = self.romanise_native(native)
            if romanised and romanised != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": romanised, "type": "romanisation-alt"}
                )

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract given / family components from name string."""
        components: Dict[str, Any] = {}

        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            parts = name.split(None, 1)
            if len(parts) >= 2:
                # Given Family order (default for E6)
                components["given_name"] = parts[0].strip()
                components["family_name"] = parts[1].strip()
            else:
                # Single token -- could be mononym (especially Khmer)
                components["given_name"] = name.strip()
                components["family_name"] = ""

        return components

    def _detect_script(self, name: str) -> str:
        """Detect primary script in name."""
        thai_count = sum(1 for c in name if self.thai_range[0] <= ord(c) <= self.thai_range[1])
        khmer_count = sum(1 for c in name if self.khmer_range[0] <= ord(c) <= self.khmer_range[1])
        lao_count = sum(1 for c in name if self.lao_range[0] <= ord(c) <= self.lao_range[1])
        latin_count = sum(1 for c in name if c.isascii() and c.isalpha())

        counts = {
            "Thai": thai_count,
            "Khmer": khmer_count,
            "Lao": lao_count,
            "Latin": latin_count,
        }
        best = max(counts, key=counts.get)  # type: ignore[arg-type]
        return best if counts[best] > 0 else "Unknown"

    def _detect_country(self, name: str, script: str) -> Optional[str]:
        """Heuristic country detection from script."""
        mapping = {"Thai": "TH", "Khmer": "KH", "Lao": "LA"}
        return mapping.get(script)

    # ------------------------------------------------------------------
    # Rule 27: Romanisation (RTGS / UNGEGN / MOICT)
    # ------------------------------------------------------------------
    # Simplified consonant onset mappings from official standards.
    # Full tables require ~120 combination rules for Thai alone; these
    # cover the initial consonant onsets used in proper names.

    _THAI_RTGS_ONSETS: Dict[str, str] = {
        "\u0e01": "k",
        "\u0e02": "kh",
        "\u0e03": "kh",
        "\u0e04": "kh",
        "\u0e06": "kh",
        "\u0e07": "ng",
        "\u0e08": "ch",
        "\u0e09": "ch",
        "\u0e0a": "ch",
        "\u0e0b": "s",
        "\u0e0c": "ch",
        "\u0e0d": "y",
        "\u0e0e": "d",
        "\u0e0f": "t",
        "\u0e10": "th",
        "\u0e11": "th",
        "\u0e12": "th",
        "\u0e13": "n",
        "\u0e14": "d",
        "\u0e15": "t",
        "\u0e16": "th",
        "\u0e17": "th",
        "\u0e18": "th",
        "\u0e19": "n",
        "\u0e1a": "b",
        "\u0e1b": "p",
        "\u0e1c": "ph",
        "\u0e1d": "f",
        "\u0e1e": "ph",
        "\u0e1f": "f",
        "\u0e20": "ph",
        "\u0e21": "m",
        "\u0e22": "y",
        "\u0e23": "r",
        "\u0e25": "l",
        "\u0e27": "w",
        "\u0e28": "s",
        "\u0e29": "s",
        "\u0e2a": "s",
        "\u0e2b": "h",
        "\u0e2c": "l",
        "\u0e2d": "o",
        "\u0e2e": "h",
    }

    _KHMER_UNGEGN_ONSETS: Dict[str, str] = {
        "\u1780": "ka",
        "\u1781": "kha",
        "\u1782": "ko",
        "\u1783": "kho",
        "\u1784": "ngo",
        "\u1785": "cha",
        "\u1786": "chha",
        "\u1787": "cho",
        "\u1788": "chho",
        "\u1789": "nho",
        "\u178a": "da",
        "\u178b": "ttha",
        "\u178c": "do",
        "\u178d": "ttho",
        "\u178e": "nno",
        "\u178f": "ta",
        "\u1790": "tha",
        "\u1791": "to",
        "\u1792": "tho",
        "\u1793": "no",
        "\u1794": "ba",
        "\u1795": "pha",
        "\u1796": "po",
        "\u1797": "pho",
        "\u1798": "mo",
        "\u1799": "yo",
        "\u179a": "ro",
        "\u179b": "lo",
        "\u179c": "vo",
        "\u179f": "sa",
        "\u17a0": "ha",
        "\u17a1": "la",
        "\u17a2": "qa",
    }

    _LAO_MOICT_ONSETS: Dict[str, str] = {
        "\u0e81": "k",
        "\u0e82": "kh",
        "\u0e84": "kh",
        "\u0e87": "ng",
        "\u0e88": "ch",
        "\u0e8a": "s",
        "\u0e8d": "ny",
        "\u0e94": "d",
        "\u0e95": "t",
        "\u0e96": "th",
        "\u0e97": "th",
        "\u0e99": "n",
        "\u0e9a": "b",
        "\u0e9b": "p",
        "\u0e9c": "ph",
        "\u0e9d": "f",
        "\u0e9e": "ph",
        "\u0e9f": "f",
        "\u0ea1": "m",
        "\u0ea2": "y",
        "\u0ea3": "r",
        "\u0ea5": "l",
        "\u0ea7": "v",
        "\u0eab": "h",
        "\u0ead": "o",
    }

    def romanise_native(self, native: str, standard: str = "auto") -> str:
        """Rule 27: Romanise a native-script name using the appropriate
        standard (RTGS for Thai, UNGEGN for Khmer, MOICT for Lao).

        Returns a Latin-script approximation.  The mapping covers initial
        consonant onsets; vowels and tone marks are simplified to ASCII.
        """
        if not native:
            return ""
        if standard == "auto":
            script = self._detect_script(native)
            standard = {"Thai": "RTGS", "Khmer": "UNGEGN", "Lao": "MOICT"}.get(script, "RTGS")

        table = {
            "RTGS": self._THAI_RTGS_ONSETS,
            "UNGEGN": self._KHMER_UNGEGN_ONSETS,
            "MOICT": self._LAO_MOICT_ONSETS,
        }.get(standard, self._THAI_RTGS_ONSETS)

        result = []
        for ch in native:
            if ch in table:
                result.append(table[ch])
            elif ch.isascii():
                result.append(ch)
            # Skip vowel/tone marks for simplified romanisation
        return "".join(result)

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to E6 rules (raises RegionRuleError)."""
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")

        if not canonical and not native:
            raise RegionRuleError("Missing both CanonicalLatin and CanonicalNative")

        name = native if native else canonical

        # Length guard
        if len(name.strip()) < 2:
            raise RegionRuleError("Name too short for E6 region")

        # Script consistency: if native is present, must contain
        # at least one Thai, Khmer or Lao character
        if native:
            has_sea_script = any(
                self.thai_range[0] <= ord(c) <= self.thai_range[1]
                or self.khmer_range[0] <= ord(c) <= self.khmer_range[1]
                or self.lao_range[0] <= ord(c) <= self.lao_range[1]
                for c in native
            )
            if not has_sea_script and not any(c.isascii() and c.isalpha() for c in native):
                raise RegionRuleError("CanonicalNative contains no recognised E6 script characters")

    # ------------------------------------------------------------------
    # order_key
    # ------------------------------------------------------------------
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for E6 names."""
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        if family:
            sort_key = f"{family} {given}".strip()
        else:
            # Mononym or single-part name
            canonical = entry.get("CanonicalLatin", "")
            native = entry.get("CanonicalNative", "")
            sort_key = canonical if canonical else native

        # Normalise for deterministic comparison
        sort_key = unicodedata.normalize("NFC", sort_key)
        sort_key = " ".join(sort_key.split())
        return sort_key.upper()
