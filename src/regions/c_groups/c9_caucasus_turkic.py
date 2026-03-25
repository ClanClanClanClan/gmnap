"""
C9 - Caucasus-Turkic region implementation.

Covers: Azerbaijan, North Caucasus Turkic communities, Caucasus diaspora
Features: Latin/Cyrillic dual script support, -ov/-ova/-zade patronymic
          patterns, Azerbaijani naming conventions, oglu/qizi patronymics.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class C9CaucasusTurkic(RegionSpec):
    """
    Caucasus-Turkic region (C9).

    Handles Azerbaijani and Caucasian Turkic naming conventions:
    - Latin script (modern Azerbaijani, post-1991) and Cyrillic (Soviet-era)
    - Patronymic patterns: -ov/-ova (Russian-style), -zade (Persian-style),
      oglu/oghlu (son of), qizi/gizi (daughter of)
    - Turkic name particles and suffixes
    - Dual script normalisation (Cyrillic <-> Latin)
    """

    def __init__(self):
        super().__init__(
            code="C9",
            yaml_files=["c9_caucasus_turkic.yaml"],
            scripts=["Latin", "Cyrillic"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["Azerbaijani-Latin", "BGN/PCGN"],
        )

        # Cyrillic range
        self.cyrillic_range = (0x0400, 0x04FF)

        # Azerbaijani-specific Latin characters
        self.az_special_chars = {
            "\u0259": "e",  # schwa (Azerbaijani e)
            "\u018f": "E",  # capital schwa
            "\u011f": "g",  # g with breve
            "\u011e": "G",  # G with breve
            "\u0131": "i",  # dotless i
            "\u0130": "I",  # dotted I
            "\u00f6": "o",  # o with diaeresis
            "\u00d6": "O",  # O with diaeresis
            "\u00fc": "u",  # u with diaeresis
            "\u00dc": "U",  # U with diaeresis
            "\u015f": "sh",  # s with cedilla
            "\u015e": "Sh",  # S with cedilla
            "\u00e7": "ch",  # c with cedilla
            "\u00c7": "Ch",  # C with cedilla
        }

        # Patronymic patterns
        self.patronymic_particles = {
            "oglu": "son of",
            "oghlu": "son of",
            "o\u011flu": "son of",  # with breve-g
            "qizi": "daughter of",
            "g\u0131z\u0131": "daughter of",  # with dotless i
            "gizi": "daughter of",
        }

        # Surname suffix patterns
        self.surname_suffixes = {
            "ov": "patronymic (Russian-style, male)",
            "ova": "patronymic (Russian-style, female)",
            "yev": "patronymic (Russian-style, male)",
            "yeva": "patronymic (Russian-style, female)",
            "zade": "descendant of (Persian-style)",
            "zadeh": "descendant of (Persian-style)",
            "li": "from (place)",
            "lu": "possessing",
        }

        # Titles and honorifics to strip
        self.titles = {
            # Azerbaijani
            "c\u0259nab",
            "xan\u0131m",
            "b\u0259y",
            # Cyrillic forms
            "\u0433\u043e\u0441\u043f\u043e\u0434\u0438\u043d",  # Gospodin
            "\u0433\u043e\u0441\u043f\u043e\u0436\u0430",  # Gospozha
            # Latin
            "Dr",
            "Dr.",
            "Prof",
            "Prof.",
            "Professor",
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
        }

        # Cyrillic to Azerbaijani-Latin transliteration map
        self.cyrillic_to_latin = {
            "\u0410": "A",
            "\u0430": "a",
            "\u0411": "B",
            "\u0431": "b",
            "\u0412": "V",
            "\u0432": "v",
            "\u0413": "Q",
            "\u0433": "q",  # Azerbaijani: G -> Q
            "\u0414": "D",
            "\u0434": "d",
            "\u0415": "Ye",
            "\u0435": "ye",  # initial, otherwise e
            "\u0416": "J",
            "\u0436": "j",
            "\u0417": "Z",
            "\u0437": "z",
            "\u0418": "\u0130",
            "\u0438": "i",  # dotted I / i
            "\u0419": "Y",
            "\u0439": "y",
            "\u041a": "K",
            "\u043a": "k",
            "\u041b": "L",
            "\u043b": "l",
            "\u041c": "M",
            "\u043c": "m",
            "\u041d": "N",
            "\u043d": "n",
            "\u041e": "O",
            "\u043e": "o",
            "\u041f": "P",
            "\u043f": "p",
            "\u0420": "R",
            "\u0440": "r",
            "\u0421": "S",
            "\u0441": "s",
            "\u0422": "T",
            "\u0442": "t",
            "\u0423": "U",
            "\u0443": "u",
            "\u0424": "F",
            "\u0444": "f",
            "\u0425": "X",
            "\u0445": "x",
            "\u0426": "Ts",
            "\u0446": "ts",
            "\u0427": "\u00c7",
            "\u0447": "\u00e7",  # Ch
            "\u0428": "\u015e",
            "\u0448": "\u015f",  # Sh
            "\u042b": "I",
            "\u044b": "\u0131",  # dotless i
            "\u042d": "E",
            "\u044d": "e",
            "\u042e": "Yu",
            "\u044e": "yu",
            "\u042f": "Ya",
            "\u044f": "ya",
            # Azerbaijani-specific Cyrillic
            "\u0492": "\u011e",
            "\u0493": "\u011f",  # Ghe with stroke -> breve-g
            "\u04e8": "\u00d6",
            "\u04e9": "\u00f6",  # Barred O -> o-diaeresis
            "\u04ae": "\u00dc",
            "\u04af": "\u00fc",  # Straight U -> u-diaeresis
            "\u0498": "\u015e",
            "\u0499": "\u015f",  # Ze with cedilla -> Sh
            "\u04ba": "H",
            "\u04bb": "h",  # Shha
            "\u0258": "\u0259",  # schwa
            # Soft/hard signs (typically dropped)
            "\u042c": "",
            "\u044c": "",
            "\u042a": "",
            "\u044a": "",
        }

    # ------------------------------------------------------------------
    # clean
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C9 Caucasus-Turkic rules (in-place)."""
        for field in ("CanonicalLatin", "CanonicalNative"):
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])

        if "Variants" in entry:
            for variant in entry["Variants"].get("Observed", []):
                if "str" in variant and variant["str"]:
                    variant["str"] = self._clean_name(variant["str"])

    def _clean_name(self, name: str) -> str:
        if not name:
            return name

        # Apply Unicode fold exceptions (Rule 16)
        name = self.apply_unicode_fold_exceptions(name)

        # NFC normalisation
        name = unicodedata.normalize("NFC", name)

        # Remove titles
        name = self._remove_titles(name)

        # Normalise Azerbaijani-specific characters
        name = self._normalize_az_chars(name)

        # Collapse whitespace
        name = " ".join(name.split())

        # Normalise punctuation
        name = self._normalize_punctuation(name)

        return name

    def _remove_titles(self, text: str) -> str:
        if not text:
            return text
        words = text.split()
        cleaned = [w for w in words if w.rstrip(".,") not in self.titles]
        return " ".join(cleaned) if cleaned else text

    def _normalize_az_chars(self, name: str) -> str:
        """Ensure consistent encoding of Azerbaijani special characters."""
        # Normalise different representations of schwa
        name = name.replace("\u04d9", "\u0259")  # Cyrillic schwa -> Latin schwa
        name = name.replace("\u04d8", "\u018f")  # Capital Cyrillic schwa -> Capital Latin schwa
        return name

    def _normalize_punctuation(self, name: str) -> str:
        name = re.sub(r"\s+", " ", name)
        name = re.sub(r"[\u2014\u2013\u2012]", "-", name)
        name = re.sub(r"[,;:]$", "", name)
        return name.strip()

    def _is_cyrillic(self, text: str) -> bool:
        s, e = self.cyrillic_range
        for ch in text:
            if s <= ord(ch) <= e:
                return True
        return False

    def _is_latin(self, text: str) -> bool:
        for ch in text:
            if ch.isalpha() and ord(ch) < 0x0250:  # Basic Latin + Extensions
                return True
        return False

    # ------------------------------------------------------------------
    # augment
    # ------------------------------------------------------------------
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C9-specific regional data (in-place)."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        extras = entry["RegionalExtras"]

        extras["script"] = "Cyrillic" if self._is_cyrillic(canonical) else "Latin"

        # Extract name components
        components = self._extract_components(canonical)
        extras.update(components)

        # Detect patronymic type
        pat_info = self._detect_patronymic(canonical)
        if pat_info:
            extras["has_patronymic"] = True
            extras["patronymic_type"] = pat_info["type"]
            extras["patronymic_particle"] = pat_info["particle"]
        else:
            extras["has_patronymic"] = False

        # Detect -ov/-ova / -zade suffix
        family = components.get("family_name", "")
        suffix_info = self._detect_surname_suffix(family)
        if suffix_info:
            extras["surname_suffix"] = suffix_info["suffix"]
            extras["suffix_type"] = suffix_info["type"]

        # Infer gender from -ov/-ova pattern
        gender_hint = self._infer_gender_from_suffix(family, pat_info)
        if gender_hint:
            extras["gender_source"] = "turkic-patronymic"
            entry.setdefault("GenderProvided", False)
            if not entry.get("GenderProvided"):
                entry["Gender"] = gender_hint

        extras["likely_country"] = "AZ"

        # Ensure Variants structure
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        synthesised = entry["Variants"]["Synthesised"]

        # Transliterate Cyrillic to Latin
        if self._is_cyrillic(canonical):
            latin = self._transliterate_to_latin(canonical)
            if latin and latin != canonical:
                entry["CanonicalLatin"] = latin
                synthesised.append({"str": latin, "type": "transliteration"})

        # ASCII-safe variant (strip Azerbaijani special chars)
        latin = entry.get("CanonicalLatin", "")
        if latin:
            ascii_safe = self._to_ascii_safe(latin)
            if ascii_safe != latin:
                synthesised.append({"str": ascii_safe, "type": "ascii-safe"})

        # -ov/-ova gender toggle variant
        if suffix_info and suffix_info["suffix"] in ("ov", "ova", "yev", "yeva"):
            toggled = self._toggle_gender_suffix(family)
            if toggled and toggled != family:
                # Build full name variant with toggled family
                given = components.get("given_name", "")
                full_toggled = f"{given} {toggled}" if given else toggled
                synthesised.append({"str": full_toggled, "type": "gender-suffix-toggle"})

        # Variant without patronymic particle (oglu/qizi)
        if pat_info and pat_info.get("index") is not None:
            no_pat = self._strip_patronymic(canonical, pat_info)
            if no_pat and no_pat != canonical:
                synthesised.append({"str": no_pat, "type": "no-patronymic"})

    def _extract_components(self, name: str) -> Dict[str, Any]:
        components: Dict[str, Any] = {}
        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip()
            return components

        words = name.split()

        # Look for oglu/qizi patronymic particle
        pat_idx = self._find_patronymic_particle_index(words)
        if pat_idx is not None:
            # Pattern: Given Father-name oglu/qizi Family
            components["given_name"] = words[0] if pat_idx >= 1 else ""
            if pat_idx >= 2:
                components["father_name"] = " ".join(words[1:pat_idx])
            if pat_idx + 1 < len(words):
                components["family_name"] = " ".join(words[pat_idx + 1 :])
            else:
                components["family_name"] = ""
            return components

        # Default: last word is family name
        if len(words) >= 3:
            # Three-part: Given Patronymic Family (Soviet style)
            components["given_name"] = words[0]
            if self._is_soviet_patronymic(words[1]):
                components["patronymic_name"] = words[1]
                components["family_name"] = " ".join(words[2:])
            else:
                components["given_name"] = " ".join(words[:-1])
                components["family_name"] = words[-1]
        elif len(words) == 2:
            components["given_name"] = words[0]
            components["family_name"] = words[1]
        else:
            components["given_name"] = name
            components["family_name"] = ""
        return components

    def _find_patronymic_particle_index(self, words: List[str]) -> Optional[int]:
        for i, w in enumerate(words):
            wl = w.lower()
            if wl in self.patronymic_particles:
                return i
        return None

    def _detect_patronymic(self, name: str) -> Optional[Dict[str, Any]]:
        words = name.split()
        for i, w in enumerate(words):
            wl = w.lower()
            if wl in self.patronymic_particles:
                return {
                    "particle": wl,
                    "type": self.patronymic_particles[wl],
                    "index": i,
                }
        # Check for -ovich/-ovna Soviet patronymic
        for i, w in enumerate(words):
            if self._is_soviet_patronymic(w):
                return {
                    "particle": w,
                    "type": "soviet-patronymic",
                    "index": i,
                }
        return None

    def _is_soviet_patronymic(self, word: str) -> bool:
        lower = word.lower()
        return bool(re.search(r"(ovich|ovna|evich|evna|ogly|kyzy)$", lower))

    def _detect_surname_suffix(self, family: str) -> Optional[Dict[str, str]]:
        if not family:
            return None
        lower = family.lower()
        # Check longest suffixes first
        sorted_suffixes = sorted(self.surname_suffixes.items(), key=lambda x: -len(x[0]))
        for suffix, stype in sorted_suffixes:
            if lower.endswith(suffix):
                return {"suffix": suffix, "type": stype}
        return None

    def _infer_gender_from_suffix(
        self,
        family: str,
        pat_info: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Infer gender from Turkic patronymic patterns (Rule 26 compliant)."""
        lower = family.lower() if family else ""
        # -ova / -yeva -> female
        if lower.endswith("ova") or lower.endswith("yeva"):
            return "F"
        # -ov / -yev -> male
        if lower.endswith("ov") or lower.endswith("yev"):
            return "M"
        # qizi/gizi -> female
        if pat_info and pat_info.get("particle", "") in ("qizi", "gizi", "g\u0131z\u0131"):
            return "F"
        # oglu/oghlu -> male
        if pat_info and pat_info.get("particle", "") in ("oglu", "oghlu", "o\u011flu"):
            return "M"
        return None

    def _toggle_gender_suffix(self, family: str) -> Optional[str]:
        """Toggle between -ov/-ova or -yev/-yeva."""
        if family.endswith("ova"):
            return family[:-3] + "ov"
        if family.endswith("ov") and not family.endswith("ova"):
            return family + "a"
        if family.endswith("yeva"):
            return family[:-4] + "yev"
        if family.endswith("yev") and not family.endswith("yeva"):
            return family + "a"
        return None

    def _strip_patronymic(self, name: str, pat_info: Dict[str, Any]) -> Optional[str]:
        words = name.split()
        idx = pat_info["index"]
        # Remove the particle
        cleaned = words[:idx] + words[idx + 1 :]
        return " ".join(cleaned) if cleaned else None

    def _transliterate_to_latin(self, name: str) -> str:
        """Transliterate Cyrillic text to Azerbaijani Latin."""
        result = []
        for ch in name:
            if ch in self.cyrillic_to_latin:
                result.append(self.cyrillic_to_latin[ch])
            else:
                result.append(ch)
        transliterated = "".join(result)
        transliterated = " ".join(transliterated.split())
        return transliterated.title() if transliterated else transliterated

    def _to_ascii_safe(self, name: str) -> str:
        """Convert Azerbaijani special characters to ASCII approximation."""
        result = []
        for ch in name:
            if ch in self.az_special_chars:
                result.append(self.az_special_chars[ch])
            else:
                result.append(ch)
        return "".join(result)

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry against C9 Caucasus-Turkic rules. Raises RegionRuleError."""
        cn = entry.get("CanonicalNative", "")
        cl = entry.get("CanonicalLatin", "")

        if not cn and not cl:
            raise RegionRuleError("C9: Missing both CanonicalNative and CanonicalLatin")

        # For C9, both Latin and Cyrillic are acceptable for CanonicalNative
        # (dual-script region)

        # CanonicalLatin should not be Cyrillic
        if cl and self._is_cyrillic(cl) and not self._is_latin(cl):
            raise RegionRuleError(f"C9: CanonicalLatin should be Latin script: {cl}")

        # Minimum length
        effective = cl or cn
        if effective and len(effective.replace(" ", "")) < 2:
            raise RegionRuleError(f"C9: Name too short: {effective}")

        # Character validity for Latin form
        if cl and not self._valid_chars(cl):
            raise RegionRuleError(f"C9: Invalid characters in CanonicalLatin: {cl}")

    def _valid_chars(self, name: str) -> bool:
        s, e = self.cyrillic_range
        for ch in name:
            if ch.isalpha() or ch in " -'.,\u0259\u018f":
                continue
            cp = ord(ch)
            if s <= cp <= e:
                continue
            # Allow Azerbaijani special chars
            if ch in self.az_special_chars:
                continue
            return False
        return True

    # ------------------------------------------------------------------
    # order_key
    # ------------------------------------------------------------------
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for C9 names."""
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if self._is_cyrillic(canonical):
            canonical = self._transliterate_to_latin(canonical)

        # Normalise Azerbaijani chars to ASCII for sort
        sort_family = self._to_ascii_safe(family).upper() if family else ""
        sort_given = self._to_ascii_safe(given).upper() if given else ""

        # Remove punctuation
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        key = f"{sort_family} {sort_given}".strip()
        return " ".join(key.split())
