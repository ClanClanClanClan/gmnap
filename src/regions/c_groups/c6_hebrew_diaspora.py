"""
C6 - Hebrew & Diaspora region implementation.

Covers: Israel, Jewish diaspora communities worldwide
Features: Hebrew script (RTL), niqqud (vowel mark) stripping,
          ben/bat patronymics, multiple transliteration standards.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class C6HebrewDiaspora(RegionSpec):
    """
    Hebrew & Diaspora region (C6).

    Handles Hebrew and Israeli diaspora naming conventions:
    - Hebrew script U+0590-U+05FF (right-to-left)
    - Niqqud (vowel points) stripping for canonical form
    - ben/bat patronymics (son of / daughter of)
    - Multiple romanisation systems (Academy, BGN/PCGN, ISO 259)
    - Diaspora surname conventions (Ashkenazi -sky/-stein, Sephardic)
    """

    def __init__(self):
        super().__init__(
            code="C6",
            yaml_files=["c6_hebrew_diaspora.yaml"],
            scripts=["Hebrew", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["Academy", "BGN/PCGN", "ISO-259"],
        )

        # Hebrew script range
        self.hebrew_range = (0x0590, 0x05FF)

        # Niqqud (vowel point) range - to be stripped for canonical form
        # U+0591-U+05BD: cantillation marks + niqqud
        # U+05BF: rafe
        # U+05C1-U+05C2: sin/shin dots
        # U+05C4-U+05C5: puncta
        # U+05C7: qamats qatan
        self.niqqud_range = set(range(0x0591, 0x05C8))

        # Patronymic particles
        self.patronymic_particles = {
            "ben": "son of",
            "\u05d1\u05df": "son of",       # Hebrew: ben
            "bat": "daughter of",
            "\u05d1\u05ea": "daughter of",   # Hebrew: bat
            "bar": "son of (Aramaic)",
        }

        # Titles and honorifics to strip
        self.titles = {
            # Hebrew titles
            "\u05e4\u05e8\u05d5\u05e4\u05f3",    # Prof'
            "\u05d3\u05f4\u05e8",                  # Dr
            "\u05de\u05e8",                         # Mr
            "\u05d2\u05d1\u05e8\u05ea",            # Mrs
            "\u05e8\u05d1",                         # Rav (Rabbi)
            "\u05d4\u05e8\u05d1",                  # HaRav
            # Latin titles
            "Dr", "Dr.", "Prof", "Prof.", "Professor",
            "Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms.",
            "Rabbi", "Rav",
        }

        # Common Hebrew-to-Latin romanization (Academy of the Hebrew Language)
        self.romanization_map = {
            "\u05d0": "",   # Alef (silent)
            "\u05d1": "v",  # Vet (default; Bet with dagesh = b)
            "\u05d2": "g",  # Gimel
            "\u05d3": "d",  # Dalet
            "\u05d4": "h",  # He
            "\u05d5": "v",  # Vav (consonantal)
            "\u05d6": "z",  # Zayin
            "\u05d7": "ch", # Chet
            "\u05d8": "t",  # Tet
            "\u05d9": "y",  # Yod
            "\u05da": "kh", # Final Kaf
            "\u05db": "kh", # Kaf (without dagesh)
            "\u05dc": "l",  # Lamed
            "\u05dd": "m",  # Final Mem
            "\u05de": "m",  # Mem
            "\u05df": "n",  # Final Nun
            "\u05e0": "n",  # Nun
            "\u05e1": "s",  # Samekh
            "\u05e2": "",   # Ayin (silent in many dialects)
            "\u05e3": "f",  # Final Pe
            "\u05e4": "f",  # Pe (without dagesh)
            "\u05e5": "ts", # Final Tsadi
            "\u05e6": "ts", # Tsadi
            "\u05e7": "k",  # Qof
            "\u05e8": "r",  # Resh
            "\u05e9": "sh", # Shin (default; Sin = s)
            "\u05ea": "t",  # Tav
        }

        # Diaspora surname suffixes (for pattern detection)
        self.ashkenazi_suffixes = [
            "stein", "berg", "man", "mann", "ski", "sky", "witz",
            "vitz", "ovich", "ovitch", "baum", "feld", "haus",
            "blatt", "gold", "silver", "rosen", "green", "klein",
        ]

        self.sephardic_patterns = [
            "ben-", "bar-", "ibn-",
            "cohen", "levi", "levy",
            "mizrahi", "azoulay", "abecassis", "benveniste",
        ]

    # ------------------------------------------------------------------
    # clean
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C6 Hebrew rules (in-place)."""
        for field in ("CanonicalLatin", "CanonicalNative"):
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field], field)

        # Clean observed variants
        if "Variants" in entry:
            for variant in entry["Variants"].get("Observed", []):
                if "str" in variant and variant["str"]:
                    variant["str"] = self._clean_name(variant["str"], "variant")

    def _clean_name(self, name: str, field_hint: str = "") -> str:
        if not name:
            return name

        # Apply Unicode fold exceptions (Rule 16)
        name = self.apply_unicode_fold_exceptions(name)

        # NFC normalisation
        name = unicodedata.normalize("NFC", name)

        # Strip niqqud (vowel points) from Hebrew text
        if self._is_hebrew(name):
            name = self._strip_niqqud(name)

        # Remove titles / honorifics
        name = self._remove_titles(name)

        # Collapse whitespace
        name = " ".join(name.split())

        # Normalise punctuation
        name = self._normalize_punctuation(name)

        return name

    def _strip_niqqud(self, text: str) -> str:
        """Remove Hebrew niqqud (vowel points) and cantillation marks."""
        return "".join(
            ch for ch in text if ord(ch) not in self.niqqud_range
        )

    def _remove_titles(self, text: str) -> str:
        if not text:
            return text
        words = text.split()
        cleaned = [w for w in words if w.rstrip(".,'\u05f3\u05f4") not in self.titles]
        return " ".join(cleaned) if cleaned else text

    def _normalize_punctuation(self, name: str) -> str:
        name = re.sub(r"\s+", " ", name)
        # Hebrew geresh/gershayim are meaningful - keep them
        # Normalise dashes
        name = re.sub(r"[\u2014\u2013\u2012]", "-", name)
        name = re.sub(r"[,;:]$", "", name)
        return name.strip()

    def _is_hebrew(self, text: str) -> bool:
        s, e = self.hebrew_range
        for ch in text:
            if s <= ord(ch) <= e:
                return True
        return False

    # ------------------------------------------------------------------
    # augment
    # ------------------------------------------------------------------
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C6-specific regional data (in-place)."""
        canonical = (
            entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        )
        if not canonical:
            return

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        extras = entry["RegionalExtras"]

        extras["script"] = "Hebrew" if self._is_hebrew(canonical) else "Latin"

        # Extract name components
        components = self._extract_components(canonical)
        extras.update(components)

        # Detect patronymic
        pat = self._detect_patronymic(canonical)
        if pat:
            extras["has_patronymic"] = True
            extras["patronymic_type"] = pat["type"]
            extras["patronymic_particle"] = pat["particle"]
        else:
            extras["has_patronymic"] = False

        # Detect diaspora tradition
        extras["diaspora_tradition"] = self._detect_tradition(
            entry.get("CanonicalLatin", "") or canonical
        )

        extras["likely_country"] = "IL"

        # Ensure Variants structure
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        synthesised = entry["Variants"]["Synthesised"]

        # Romanise Hebrew script
        if self._is_hebrew(canonical):
            romanised = self._romanize_name(canonical)
            if romanised and romanised != canonical:
                entry["CanonicalLatin"] = romanised
                synthesised.append({"str": romanised, "type": "romanization"})

        # Variant without patronymic particle
        if pat and pat.get("index") is not None:
            no_pat = self._variant_without_patronymic(canonical, pat)
            if no_pat and no_pat != canonical:
                synthesised.append({"str": no_pat, "type": "no-patronymic"})

        # Hyphenated vs spaced ben/bat variant
        latin = entry.get("CanonicalLatin", "")
        if latin:
            hyph = self._toggle_ben_hyphen(latin)
            if hyph and hyph != latin:
                synthesised.append({"str": hyph, "type": "ben-hyphen-toggle"})

    def _extract_components(self, name: str) -> Dict[str, Any]:
        components: Dict[str, Any] = {}
        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip()
            return components

        words = name.split()
        # Look for ben/bat to split around patronymic
        pat_idx = self._find_patronymic_index(words)
        if pat_idx is not None and pat_idx > 0:
            components["given_name"] = " ".join(words[:pat_idx])
            # Everything from patronymic onward is patronymic + family
            if pat_idx + 2 <= len(words):
                components["family_name"] = " ".join(words[pat_idx + 2:])
                components["parent_name"] = words[pat_idx + 1] if pat_idx + 1 < len(words) else ""
            else:
                components["family_name"] = " ".join(words[pat_idx + 1:])
        elif len(words) >= 2:
            components["given_name"] = " ".join(words[:-1])
            components["family_name"] = words[-1]
        else:
            components["given_name"] = name
            components["family_name"] = ""
        return components

    def _find_patronymic_index(self, words: List[str]) -> Optional[int]:
        for i, w in enumerate(words):
            if w.lower().rstrip("-") in self.patronymic_particles or w in self.patronymic_particles:
                return i
        return None

    def _detect_patronymic(self, name: str) -> Optional[Dict[str, Any]]:
        words = name.split()
        for i, w in enumerate(words):
            wl = w.lower().rstrip("-")
            if wl in self.patronymic_particles:
                return {
                    "particle": wl,
                    "type": self.patronymic_particles[wl],
                    "index": i,
                }
            # Check Hebrew script particles
            if w in self.patronymic_particles:
                return {
                    "particle": w,
                    "type": self.patronymic_particles[w],
                    "index": i,
                }
        return None

    def _detect_tradition(self, latin_name: str) -> str:
        """Detect Ashkenazi vs Sephardic vs general Israeli tradition."""
        lower = latin_name.lower()
        for suffix in self.ashkenazi_suffixes:
            if lower.endswith(suffix):
                return "ashkenazi"
        for pattern in self.sephardic_patterns:
            if pattern in lower:
                return "sephardic"
        return "israeli"

    def _variant_without_patronymic(
        self, name: str, pat: Dict[str, Any]
    ) -> Optional[str]:
        words = name.split()
        idx = pat["index"]
        # Remove the particle and the parent name after it
        before = words[:idx]
        after = words[idx + 2:] if idx + 2 <= len(words) else words[idx + 1:]
        combined = before + after
        return " ".join(combined) if combined else None

    def _toggle_ben_hyphen(self, name: str) -> Optional[str]:
        """Toggle between 'Ben David' and 'Ben-David'."""
        # Hyphenated -> spaced
        m = re.search(r"\b(Ben|Bat|Bar)-(\w)", name)
        if m:
            return name.replace(f"{m.group(1)}-", f"{m.group(1)} ", 1)
        # Spaced -> hyphenated
        m = re.search(r"\b(Ben|Bat|Bar)\s+(\w)", name)
        if m:
            return re.sub(
                r"\b(Ben|Bat|Bar)\s+", r"\1-", name, count=1
            )
        return None

    def _romanize_name(self, name: str) -> str:
        """Romanise Hebrew script using Academy transliteration."""
        result = []
        for ch in name:
            if ch in self.romanization_map:
                result.append(self.romanization_map[ch])
            elif ord(ch) in self.niqqud_range:
                continue  # skip niqqud
            else:
                result.append(ch)
        romanised = "".join(result)
        romanised = " ".join(romanised.split())
        return romanised.title() if romanised else romanised

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry against C6 Hebrew rules. Raises RegionRuleError."""
        cn = entry.get("CanonicalNative", "")
        cl = entry.get("CanonicalLatin", "")

        if not cn and not cl:
            raise RegionRuleError(
                "C6: Missing both CanonicalNative and CanonicalLatin"
            )

        # Script consistency
        if cn and not self._is_hebrew(cn) and not cn.isascii():
            # Allow pure Latin in CanonicalNative for diaspora entries
            pass

        if cl and self._is_hebrew(cl):
            raise RegionRuleError(
                f"C6: CanonicalLatin must not contain Hebrew script: {cl}"
            )

        # Minimum length
        effective = cl or cn
        if effective and len(effective.replace(" ", "")) < 2:
            raise RegionRuleError(f"C6: Name too short: {effective}")

        # Character validity for Latin form
        if cl and not self._valid_latin_chars(cl):
            raise RegionRuleError(
                f"C6: Invalid characters in CanonicalLatin: {cl}"
            )

    def _valid_latin_chars(self, name: str) -> bool:
        s, e = self.hebrew_range
        for ch in name:
            if ch.isalpha() or ch in " -'.,":
                continue
            if s <= ord(ch) <= e:
                continue
            return False
        return True

    # ------------------------------------------------------------------
    # order_key
    # ------------------------------------------------------------------
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for C6 names."""
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        # Prefer Latin form for sorting
        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if self._is_hebrew(canonical):
            canonical = self._romanize_name(canonical)

        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""

        # Strip patronymic particles from sort key
        for particle in ("BEN ", "BAT ", "BAR ", "BEN-", "BAT-", "BAR-"):
            sort_family = sort_family.replace(particle, "")

        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        key = f"{sort_family} {sort_given}".strip()
        return " ".join(key.split())
