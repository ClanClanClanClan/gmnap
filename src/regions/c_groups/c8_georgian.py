"""
C8 - Georgian region implementation.

Covers: Georgia
Features: Georgian script U+10A0-U+10FF (Mkhedruli), -shvili/-dze/-adze/-eli
          surname suffixes, ISO 9984 transliteration standard.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class C8Georgian(RegionSpec):
    """
    Georgian region (C8).

    Handles Georgian naming conventions:
    - Georgian Mkhedruli script U+10D0-U+10FF
    - Georgian Asomtavruli (uppercase) U+10A0-U+10CF
    - Surname suffixes indicating lineage: -shvili (child of), -dze (son of),
      -adze (variant), -eli (from place), -iani (belonging to), -uri/-uli
    - ISO 9984 transliteration standard
    - Soviet-era patronymic conventions
    """

    def __init__(self):
        super().__init__(
            code="C8",
            yaml_files=["c8_georgian.yaml"],
            scripts=["Georgian", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ISO-9984", "BGN/PCGN", "National"],
        )

        # Georgian script ranges
        self.mkhedruli_range = (0x10D0, 0x10FF)  # Modern lowercase
        self.asomtavruli_range = (0x10A0, 0x10CF)  # Capital letters
        self.mtavruli_range = (0x1C90, 0x1CBF)  # Mtavruli (new uppercase, Unicode 11)

        # Titles and honorifics to strip
        self.titles = {
            # Georgian titles
            "\u10d1\u10d0\u10e2\u10dd\u10dc\u10dd",  # Batono (Sir)
            "\u10e5\u10d0\u10da\u10d1\u10d0\u10e2\u10dd\u10dc\u10dd",  # Kalbatono (Madam)
            "\u10de\u10e0\u10dd\u10e4.",  # Prof. (Georgian)
            "\u10d3-\u10e0",  # Dr (Georgian)
            # Latin equivalents
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
            "Batoni",
            "Kalbatoni",
        }

        # Georgian surname suffixes with meaning
        self.surname_suffixes = {
            "shvili": "child of",  # Mkhedruli: -შვილი
            "dze": "son of",  # Mkhedruli: -ძე
            "adze": "son of (variant)",  # Mkhedruli: -აძე
            "eli": "from (place)",  # Mkhedruli: -ელი
            "iani": "belonging to",  # Mkhedruli: -იანი
            "ani": "of (place/clan)",  # Mkhedruli: -ანი
            "uri": "of / related to",  # Mkhedruli: -ური
            "uli": "of / related to",  # Mkhedruli: -ული
            "ava": "of (Mingrelian)",  # Mkhedruli: -ავა
            "ia": "of (Mingrelian)",  # Mkhedruli: -ია
            "ua": "of (Svan)",  # Mkhedruli: -უა
        }

        # Georgian script suffix forms (Mkhedruli)
        self.georgian_suffixes = {
            "\u10e8\u10d5\u10d8\u10da\u10d8": "shvili",
            "\u10eb\u10d4": "dze",
            "\u10d0\u10eb\u10d4": "adze",
            "\u10d4\u10da\u10d8": "eli",
            "\u10d8\u10d0\u10dc\u10d8": "iani",
            "\u10d0\u10dc\u10d8": "ani",
            "\u10e3\u10e0\u10d8": "uri",
            "\u10e3\u10da\u10d8": "uli",
            "\u10d0\u10d5\u10d0": "ava",
            "\u10d8\u10d0": "ia",
            "\u10e3\u10d0": "ua",
        }

        # ISO 9984 romanisation map (Mkhedruli -> Latin)
        self.romanization_map = {
            "\u10d0": "a",  # Ani
            "\u10d1": "b",  # Bani
            "\u10d2": "g",  # Gani
            "\u10d3": "d",  # Doni
            "\u10d4": "e",  # Eni
            "\u10d5": "v",  # Vini
            "\u10d6": "z",  # Zeni
            "\u10d7": "t'",  # T'ani (ejective)
            "\u10d8": "i",  # Ini
            "\u10d9": "k'",  # K'ani (ejective)
            "\u10da": "l",  # Lasi
            "\u10db": "m",  # Mani
            "\u10dc": "n",  # Nari
            "\u10dd": "o",  # Oni
            "\u10de": "p'",  # P'ari (ejective)
            "\u10df": "zh",  # Zhani
            "\u10e0": "r",  # Rae
            "\u10e1": "s",  # Sani
            "\u10e2": "t",  # T'ari
            "\u10e3": "u",  # Uni
            "\u10e4": "p",  # Pari
            "\u10e5": "k",  # Kani
            "\u10e6": "gh",  # Ghani
            "\u10e7": "q'",  # Q'ari (ejective)
            "\u10e8": "sh",  # Shini
            "\u10e9": "ch",  # Chini
            "\u10ea": "ts",  # Tsani
            "\u10eb": "dz",  # Dzili
            "\u10ec": "ts'",  # Ts'ili (ejective)
            "\u10ed": "ch'",  # Ch'ari (ejective)
            "\u10ee": "kh",  # Khani
            "\u10ef": "j",  # Jani
            "\u10f0": "h",  # Hae
            # Archaic letters (rarely used in names)
            "\u10f1": "e",  # He
            "\u10f2": "hi",  # Hie
            "\u10f3": "we",  # We
            "\u10f4": "har",  # Har
            "\u10f5": "hoe",  # Hoe
        }

        # Asomtavruli (uppercase) map - same sounds, different codepoints
        self.asomtavruli_map = {
            chr(cp): self.romanization_map.get(chr(cp + 0x30), "")
            for cp in range(0x10A0, 0x10CF + 1)
            if chr(cp + 0x30) in self.romanization_map
        }

    # ------------------------------------------------------------------
    # clean
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C8 Georgian rules (in-place)."""
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

    def _normalize_punctuation(self, name: str) -> str:
        name = re.sub(r"\s+", " ", name)
        # Normalise dashes
        name = re.sub(r"[\u2014\u2013\u2012]", "-", name)
        name = re.sub(r"[,;:]$", "", name)
        return name.strip()

    def _is_georgian(self, text: str) -> bool:
        ms, me = self.mkhedruli_range
        as_, ae = self.asomtavruli_range
        mts, mte = self.mtavruli_range
        for ch in text:
            cp = ord(ch)
            if (ms <= cp <= me) or (as_ <= cp <= ae) or (mts <= cp <= mte):
                return True
        return False

    # ------------------------------------------------------------------
    # augment
    # ------------------------------------------------------------------
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C8-specific regional data (in-place)."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        extras = entry["RegionalExtras"]

        extras["script"] = "Georgian" if self._is_georgian(canonical) else "Latin"

        # Extract name components
        components = self._extract_components(canonical)
        extras.update(components)

        # Detect surname suffix type
        family = components.get("family_name", "")
        suffix_info = self._detect_surname_suffix(family)
        if suffix_info:
            extras["surname_suffix"] = suffix_info["suffix"]
            extras["suffix_meaning"] = suffix_info["meaning"]

        # Detect Soviet-era patronymic
        patronymic = self._detect_soviet_patronymic(canonical)
        if patronymic:
            extras["has_patronymic"] = True
            extras["patronymic_type"] = "soviet-style"
            extras["patronymic"] = patronymic
        else:
            extras["has_patronymic"] = False

        # Detect sub-ethnic group from suffix
        extras["ethnic_group"] = self._detect_ethnic_group(suffix_info)

        extras["likely_country"] = "GE"

        # Ensure Variants structure
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        synthesised = entry["Variants"]["Synthesised"]

        # Romanise Georgian script
        if self._is_georgian(canonical):
            romanised = self._romanize_name(canonical)
            if romanised and romanised != canonical:
                entry["CanonicalLatin"] = romanised
                synthesised.append({"str": romanised, "type": "romanization"})

        # Simplified romanisation variant (without ejective marks)
        latin = entry.get("CanonicalLatin", "")
        if latin:
            simple = self._simplified_romanisation(latin)
            if simple != latin:
                synthesised.append({"str": simple, "type": "simplified-romanization"})

        # Variant without Soviet patronymic if present
        if patronymic:
            no_pat = self._strip_soviet_patronymic(canonical, patronymic)
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
        if len(words) >= 3:
            # Check for Soviet-style patronymic in middle position
            mid = words[1]
            if self._is_soviet_patronymic(mid):
                components["given_name"] = words[0]
                components["patronymic_name"] = mid
                components["family_name"] = " ".join(words[2:])
                return components

        # Default: look for Georgian family suffix from the end
        if len(words) >= 2:
            for i in range(len(words) - 1, 0, -1):
                if self._has_georgian_family_suffix(words[i]):
                    components["given_name"] = " ".join(words[:i])
                    components["family_name"] = " ".join(words[i:])
                    return components
            components["given_name"] = " ".join(words[:-1])
            components["family_name"] = words[-1]
        else:
            components["given_name"] = name
            components["family_name"] = ""
        return components

    def _has_georgian_family_suffix(self, word: str) -> bool:
        lower = word.lower()
        # Check Latin suffixes
        for suffix in self.surname_suffixes:
            if lower.endswith(suffix):
                return True
        # Check Georgian script suffixes
        for geo_suffix in self.georgian_suffixes:
            if word.endswith(geo_suffix):
                return True
        return False

    def _detect_surname_suffix(self, family: str) -> Optional[Dict[str, str]]:
        if not family:
            return None
        lower = family.lower()
        # Check Latin suffixes (longest first to avoid partial matches)
        sorted_suffixes = sorted(self.surname_suffixes.items(), key=lambda x: -len(x[0]))
        for suffix, meaning in sorted_suffixes:
            if lower.endswith(suffix):
                return {"suffix": suffix, "meaning": meaning}
        # Check Georgian script suffixes
        for geo_suffix, latin_suffix in self.georgian_suffixes.items():
            if family.endswith(geo_suffix):
                return {
                    "suffix": latin_suffix,
                    "meaning": self.surname_suffixes.get(latin_suffix, "unknown"),
                }
        return None

    def _detect_ethnic_group(self, suffix_info: Optional[Dict[str, str]]) -> str:
        """Infer sub-ethnic group from surname suffix."""
        if not suffix_info:
            return "kartvelian"
        suffix = suffix_info["suffix"]
        if suffix in ("ava", "ia"):
            return "mingrelian"
        if suffix == "ua":
            return "svan"
        return "kartvelian"

    def _detect_soviet_patronymic(self, name: str) -> Optional[str]:
        words = name.split()
        for w in words:
            if self._is_soviet_patronymic(w):
                return w
        return None

    def _is_soviet_patronymic(self, word: str) -> bool:
        lower = word.lower()
        return bool(re.search(r"(ovich|ovna|evich|evna)$", lower))

    def _strip_soviet_patronymic(self, name: str, patronymic: str) -> Optional[str]:
        words = name.split()
        cleaned = [w for w in words if w != patronymic]
        return " ".join(cleaned) if cleaned else None

    def _romanize_name(self, name: str) -> str:
        """Romanise Georgian script using ISO 9984 convention."""
        result = []
        for ch in name:
            if ch in self.romanization_map:
                result.append(self.romanization_map[ch])
            elif ch in self.asomtavruli_map:
                result.append(self.asomtavruli_map[ch])
            else:
                result.append(ch)
        romanised = "".join(result)
        romanised = " ".join(romanised.split())
        return romanised.title() if romanised else romanised

    def _simplified_romanisation(self, latin: str) -> str:
        """Remove ejective marks (') from ISO 9984 romanisation."""
        return latin.replace("'", "").replace("\u2018", "").replace("\u2019", "")

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry against C8 Georgian rules. Raises RegionRuleError."""
        cn = entry.get("CanonicalNative", "")
        cl = entry.get("CanonicalLatin", "")

        if not cn and not cl:
            raise RegionRuleError("C8: Missing both CanonicalNative and CanonicalLatin")

        # Script consistency
        if cn and not self._is_georgian(cn) and not cn.isascii():
            self.logger.warning(f"C8: CanonicalNative contains non-Georgian script: {cn}")

        if cl and self._is_georgian(cl):
            raise RegionRuleError(f"C8: CanonicalLatin must not contain Georgian script: {cl}")

        # Minimum length
        effective = cl or cn
        if effective and len(effective.replace(" ", "")) < 2:
            raise RegionRuleError(f"C8: Name too short: {effective}")

        # Character validity for Latin form
        if cl and not self._valid_latin_chars(cl):
            raise RegionRuleError(f"C8: Invalid characters in CanonicalLatin: {cl}")

    def _valid_latin_chars(self, name: str) -> bool:
        ms, me = self.mkhedruli_range
        as_, ae = self.asomtavruli_range
        for ch in name:
            if ch.isalpha() or ch in " -'.,":
                continue
            cp = ord(ch)
            if (ms <= cp <= me) or (as_ <= cp <= ae):
                continue
            return False
        return True

    # ------------------------------------------------------------------
    # order_key
    # ------------------------------------------------------------------
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for C8 names."""
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if self._is_georgian(canonical):
            canonical = self._romanize_name(canonical)

        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""

        # Remove ejective marks and punctuation for sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        key = f"{sort_family} {sort_given}".strip()
        return " ".join(key.split())
