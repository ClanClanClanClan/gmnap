"""
C7 - Armenian region implementation.

Covers: Armenia, Armenian diaspora
Features: Armenian script U+0530-U+058F, -yan/-ian surname suffixes,
          Hubschmann-Meillet transliteration, patronymic conventions.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class C7Armenian(RegionSpec):
    """
    Armenian region (C7).

    Handles Armenian naming conventions:
    - Armenian script (Aybuben) U+0530-U+058F
    - Surname suffixes: -yan / -ian (Eastern / Western Armenian)
    - Hubschmann-Meillet transliteration standard
    - Soviet-era patronymic conventions (-ovich/-ovna for Russian context)
    - Given name in Armenian; family name with -yan/-ian suffix
    """

    def __init__(self):
        super().__init__(
            code="C7",
            yaml_files=["c7_armenian.yaml"],
            scripts=["Armenian", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["Hubschmann-Meillet", "BGN/PCGN", "ISO-9985"],
        )

        # Armenian script range
        self.armenian_range = (0x0530, 0x058F)
        # Armenian ligatures
        self.armenian_ligature_range = (0xFB13, 0xFB17)

        # Titles and honorifics to strip
        self.titles = {
            # Armenian titles
            "\u054a\u0580\u0578\u0586.",     # Prof. (Armenian)
            "\u0534-\u0580",                  # Dr (Armenian)
            "\u054a\u0561\u0580\u0578\u0576", # Baron (Mr)
            "\u054f\u056b\u056f\u056b\u0576", # Tikin (Mrs)
            # Latin equivalents
            "Dr", "Dr.", "Prof", "Prof.", "Professor",
            "Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms.",
        }

        # Armenian surname suffixes (patronymic-derived)
        self.surname_suffixes = {
            # Eastern Armenian (Republic of Armenia)
            "\u0575\u0561\u0576": "yan",     # -yan
            "\u0565\u0561\u0576": "ean",     # -ean
            "\u0578\u0582\u0576\u056b": "uni", # -uni
            "\u0561\u0576": "an",             # -an
            # Western Armenian (diaspora)
            # -ian is the Western transliteration of -yan
        }

        self.latin_surname_suffixes = [
            "yan", "ian", "ean", "uni", "ants", "yants", "iants",
            "djian", "jian", "chian", "tzian", "gian",
        ]

        # Hubschmann-Meillet romanization map (Armenian -> Latin)
        self.romanization_map = {
            "\u0531": "A",   "\u0561": "a",   # Ayb
            "\u0532": "B",   "\u0562": "b",   # Ben
            "\u0533": "G",   "\u0563": "g",   # Gim
            "\u0534": "D",   "\u0564": "d",   # Da
            "\u0535": "E",   "\u0565": "e",   # Ech
            "\u0536": "Z",   "\u0566": "z",   # Za
            "\u0537": "E",   "\u0567": "e",   # Eh (E with diacritic in HM)
            "\u0538": "E'",  "\u0568": "e'",  # Et
            "\u0539": "T'",  "\u0569": "t'",  # To
            "\u053a": "Zh",  "\u056a": "zh",  # Zhe
            "\u053b": "I",   "\u056b": "i",   # Ini
            "\u053c": "L",   "\u056c": "l",   # Liwn
            "\u053d": "X",   "\u056d": "x",   # Xeh
            "\u053e": "C'",  "\u056e": "c'",  # Ca
            "\u053f": "K",   "\u056f": "k",   # Ken
            "\u0540": "H",   "\u0570": "h",   # Ho
            "\u0541": "Dz",  "\u0571": "dz",  # Ja
            "\u0542": "Gh",  "\u0572": "gh",  # Ghad
            "\u0543": "Ch",  "\u0573": "ch",  # Cheh
            "\u0544": "M",   "\u0574": "m",   # Men
            "\u0545": "Y",   "\u0575": "y",   # Yi
            "\u0546": "N",   "\u0576": "n",   # Now
            "\u0547": "Sh",  "\u0577": "sh",  # Sha
            "\u0548": "O",   "\u0578": "o",   # Vo (initial = vo)
            "\u0549": "Ch'", "\u0579": "ch'", # Cha
            "\u054a": "P",   "\u057a": "p",   # Peh
            "\u054b": "J",   "\u057b": "j",   # Jheh
            "\u054c": "R'",  "\u057c": "r'",  # Ra
            "\u054d": "S",   "\u057d": "s",   # Seh
            "\u054e": "V",   "\u057e": "v",   # Vew
            "\u054f": "T",   "\u057f": "t",   # Tiwn
            "\u0550": "R",   "\u0580": "r",   # Reh
            "\u0551": "C",   "\u0581": "c",   # Co
            "\u0552": "W",   "\u0582": "w",   # Yiwn (u/w)
            "\u0553": "P'",  "\u0583": "p'",  # Piwr
            "\u0554": "K'",  "\u0584": "k'",  # Keh
            "\u0555": "O'",  "\u0585": "o'",  # Oh
            "\u0556": "F",   "\u0586": "f",   # Feh
            # Special characters
            "\u0587": "ev",  # Ligature ew
            "\u0589": ".",   # Armenian full stop
            "\u058a": "-",   # Armenian hyphen
        }

        # Common Armenian given name gender markers (not definitive)
        self.female_suffixes_arm = [
            "\u0578\u0582\u0570\u056b",  # -uhi
            "\u056b\u0576\u0565",         # -ine
            "\u0561\u0576\u0578\u0582\u0577", # -anush
        ]

    # ------------------------------------------------------------------
    # clean
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C7 Armenian rules (in-place)."""
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

        # Normalise Armenian ligatures to decomposed form
        name = self._decompose_armenian_ligatures(name)

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

    def _decompose_armenian_ligatures(self, text: str) -> str:
        """Decompose Armenian ligatures to their component letters."""
        ligature_map = {
            "\ufb13": "\u0574\u0576",  # men now
            "\ufb14": "\u0574\u0565",  # men ech
            "\ufb15": "\u0574\u056b",  # men ini
            "\ufb16": "\u057e\u0576",  # vew now
            "\ufb17": "\u0574\u056d",  # men xeh
        }
        for lig, decomp in ligature_map.items():
            text = text.replace(lig, decomp)
        return text

    def _normalize_punctuation(self, name: str) -> str:
        name = re.sub(r"\s+", " ", name)
        # Armenian full stop -> period
        name = name.replace("\u0589", ".")
        # Armenian hyphen -> ASCII hyphen
        name = name.replace("\u058a", "-")
        # Normalise dashes
        name = re.sub(r"[\u2014\u2013\u2012]", "-", name)
        name = re.sub(r"[,;:]$", "", name)
        return name.strip()

    def _is_armenian(self, text: str) -> bool:
        s, e = self.armenian_range
        ls, le = self.armenian_ligature_range
        for ch in text:
            cp = ord(ch)
            if (s <= cp <= e) or (ls <= cp <= le):
                return True
        return False

    # ------------------------------------------------------------------
    # augment
    # ------------------------------------------------------------------
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C7-specific regional data (in-place)."""
        canonical = (
            entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        )
        if not canonical:
            return

        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}
        extras = entry["RegionalExtras"]

        extras["script"] = "Armenian" if self._is_armenian(canonical) else "Latin"

        # Extract name components
        components = self._extract_components(canonical)
        extras.update(components)

        # Detect -yan/-ian suffix
        family = components.get("family_name", "")
        suffix_info = self._detect_surname_suffix(family)
        if suffix_info:
            extras["surname_suffix"] = suffix_info["suffix"]
            extras["armenian_tradition"] = suffix_info["tradition"]

        # Detect Soviet-era patronymic
        patronymic = self._detect_soviet_patronymic(canonical)
        if patronymic:
            extras["has_patronymic"] = True
            extras["patronymic_type"] = "soviet-style"
            extras["patronymic"] = patronymic
        else:
            extras["has_patronymic"] = False

        extras["likely_country"] = "AM"

        # Ensure Variants structure
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        synthesised = entry["Variants"]["Synthesised"]

        # Romanise Armenian script
        if self._is_armenian(canonical):
            romanised = self._romanize_name(canonical)
            if romanised and romanised != canonical:
                entry["CanonicalLatin"] = romanised
                synthesised.append({"str": romanised, "type": "romanization"})

        # -yan / -ian cross-variant
        latin_name = entry.get("CanonicalLatin", "")
        if latin_name:
            alt = self._yan_ian_variant(latin_name)
            if alt and alt != latin_name:
                synthesised.append({"str": alt, "type": "yan-ian-variant"})

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
            # Check if middle word is a Soviet-style patronymic
            mid = words[1] if len(words) == 3 else None
            if mid and self._is_soviet_patronymic(mid):
                components["given_name"] = words[0]
                components["patronymic_name"] = mid
                components["family_name"] = " ".join(words[2:])
                return components

        # Default: last word is family name (likely ends in -yan/-ian)
        if len(words) >= 2:
            # Find the family name: look for -yan/-ian suffix from the end
            for i in range(len(words) - 1, 0, -1):
                if self._has_armenian_suffix(words[i]):
                    components["given_name"] = " ".join(words[:i])
                    components["family_name"] = " ".join(words[i:])
                    return components
            components["given_name"] = " ".join(words[:-1])
            components["family_name"] = words[-1]
        else:
            components["given_name"] = name
            components["family_name"] = ""
        return components

    def _has_armenian_suffix(self, word: str) -> bool:
        lower = word.lower()
        return any(lower.endswith(s) for s in self.latin_surname_suffixes)

    def _detect_surname_suffix(self, family: str) -> Optional[Dict[str, str]]:
        lower = family.lower() if family else ""
        # Eastern Armenian: -yan, -ean, -uni, -yants, -iants
        eastern = ["yan", "ean", "uni", "yants", "iants"]
        for s in eastern:
            if lower.endswith(s):
                return {"suffix": s, "tradition": "eastern"}
        # Western Armenian: -ian, -djian, -jian, -chian, -tzian
        western = ["ian", "djian", "jian", "chian", "tzian", "gian"]
        for s in western:
            if lower.endswith(s):
                return {"suffix": s, "tradition": "western"}
        return None

    def _detect_soviet_patronymic(self, name: str) -> Optional[str]:
        """Detect Russian-style patronymic (e.g., Ivanovich, Petrovna)."""
        words = name.split()
        for w in words:
            if self._is_soviet_patronymic(w):
                return w
        return None

    def _is_soviet_patronymic(self, word: str) -> bool:
        lower = word.lower()
        return bool(
            re.search(r"(ovich|ovna|evich|evna|ich)$", lower)
        )

    def _strip_soviet_patronymic(self, name: str, patronymic: str) -> Optional[str]:
        words = name.split()
        cleaned = [w for w in words if w != patronymic]
        return " ".join(cleaned) if cleaned else None

    def _yan_ian_variant(self, name: str) -> Optional[str]:
        """Toggle between -yan and -ian suffix."""
        if name.endswith("yan"):
            return name[:-3] + "ian"
        if name.endswith("ian"):
            return name[:-3] + "yan"
        if name.endswith("YAN"):
            return name[:-3] + "IAN"
        if name.endswith("IAN"):
            return name[:-3] + "YAN"
        return None

    def _romanize_name(self, name: str) -> str:
        """Romanise Armenian script using Hubschmann-Meillet convention."""
        result = []
        for ch in name:
            if ch in self.romanization_map:
                result.append(self.romanization_map[ch])
            else:
                result.append(ch)
        romanised = "".join(result)
        romanised = " ".join(romanised.split())
        # Remove aspiration marks for clean display
        romanised = romanised.replace("'", "")
        return romanised.title() if romanised else romanised

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry against C7 Armenian rules. Raises RegionRuleError."""
        cn = entry.get("CanonicalNative", "")
        cl = entry.get("CanonicalLatin", "")

        if not cn and not cl:
            raise RegionRuleError(
                "C7: Missing both CanonicalNative and CanonicalLatin"
            )

        # Script consistency
        if cn and self._is_armenian(cn):
            pass  # expected
        elif cn and not cn.isascii():
            # Non-ASCII, non-Armenian in native field is unusual
            self.logger.warning(f"C7: CanonicalNative contains non-Armenian script: {cn}")

        if cl and self._is_armenian(cl):
            raise RegionRuleError(
                f"C7: CanonicalLatin must not contain Armenian script: {cl}"
            )

        # Minimum length
        effective = cl or cn
        if effective and len(effective.replace(" ", "")) < 2:
            raise RegionRuleError(f"C7: Name too short: {effective}")

        # Validate character set for Latin form
        if cl and not self._valid_latin_chars(cl):
            raise RegionRuleError(
                f"C7: Invalid characters in CanonicalLatin: {cl}"
            )

    def _valid_latin_chars(self, name: str) -> bool:
        s, e = self.armenian_range
        for ch in name:
            if ch.isalpha() or ch in " -'.,":
                continue
            cp = ord(ch)
            if s <= cp <= e:
                continue
            return False
        return True

    # ------------------------------------------------------------------
    # order_key
    # ------------------------------------------------------------------
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for C7 names."""
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if self._is_armenian(canonical):
            canonical = self._romanize_name(canonical)

        sort_family = family.upper() if family else ""
        sort_given = given.upper() if given else ""

        # Remove punctuation for sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        key = f"{sort_family} {sort_given}".strip()
        return " ".join(key.split())
