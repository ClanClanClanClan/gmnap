"""
C5 - Arabic Maghreb region implementation.

Covers: Morocco, Algeria, Tunisia, Libya, Western Sahara, Mauritania
Features: Arabic script with heavy French transliteration influence,
          Ben-prefix patronymics, el-/bou- particles, French spelling norms.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class C5ArabicMaghreb(RegionSpec):
    """
    Arabic Maghreb region (C5).

    Handles North African Arabic names with strong French colonial influence:
    - Arabic script support with French transliteration conventions
    - Ben-prefix patronymics (Benali, Bensaid, Ben Amor)
    - French-influenced spelling (Mohammed not Muhammad, Brahim not Ibrahim)
    - Particles: ben, bou, bel, el-, al-
    - Dual given-name order (French: Given Family; Arabic: flexible)
    """

    def __init__(self):
        super().__init__(
            code="C5",
            yaml_files=["c5_arabic_maghreb.yaml"],
            scripts=["Arabic", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["French-Maghreb", "ALA-LC", "BGN/PCGN"],
        )

        # Maghreb-specific patronymic particles (often fused or hyphenated)
        self.patronymic_particles = {
            "ben": "son of",
            "bel": "son of (dialectal)",
            "bou": "father of / possessor of",
            "ould": "son of (Mauritanian)",
            "mint": "daughter of (Mauritanian)",
            "ibn": "son of",
            "bin": "son of",
            "bint": "daughter of",
        }

        # Arabic particles that prefix family names
        self.name_particles = {"el", "al", "le", "la", "de", "d", "du"}

        # Titles and honorifics to strip
        self.titles = {
            # French-style titles common in Maghreb
            "Dr",
            "Dr.",
            "Pr",
            "Pr.",
            "Prof",
            "Prof.",
            "M.",
            "Mme",
            "Mlle",
            "Monsieur",
            "Madame",
            "Mademoiselle",
            "Maitre",
            "Me",
            # Arabic titles
            "Si",
            "Lalla",
            "Moulay",
            "Sidi",
            # Arabic script titles
            "\u062f\u0643\u062a\u0648\u0631",
            "\u0623\u0633\u062a\u0627\u0630",
            "\u0628\u0631\u0648\u0641\u064a\u0633\u0648\u0631",
            "\u0627\u0644\u0634\u064a\u062e",
            "\u0627\u0644\u0623\u0633\u062a\u0627\u0630",
            "\u0633\u064a\u062f",
            "\u0633\u064a\u062f\u0629",
            # English fallbacks
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Professor",
        }

        # French transliteration map (Maghreb convention overrides)
        # Maghreb French uses Mohammed (not Muhammad), Brahim (not Ibrahim), etc.
        self.french_transliteration_map = {
            "Muhammad": "Mohammed",
            "Ibrahim": "Brahim",
            "Ismail": "Isma\u00efl",
            "Yusuf": "Youssef",
            "Ahmad": "Ahmed",
            "Hussein": "Hocine",
            "Hassan": "Hassane",
            "Khalid": "Khaled",
            "Salih": "Salah",
            "Abd": "Abdel",
        }

        # Arabic character ranges
        self.arabic_ranges = [
            (0x0600, 0x06FF),
            (0x0750, 0x077F),
            (0x08A0, 0x08FF),
            (0xFB50, 0xFDFF),
            (0xFE70, 0xFEFF),
        ]

        # Romanisation map (Arabic to ALA-LC, with Maghreb adjustments)
        self.romanization_map = {
            "\u0627": "a",
            "\u0628": "b",
            "\u062a": "t",
            "\u062b": "th",
            "\u062c": "dj",
            "\u062d": "h",
            "\u062e": "kh",
            "\u062f": "d",
            "\u0630": "dh",
            "\u0631": "r",
            "\u0632": "z",
            "\u0633": "s",
            "\u0634": "ch",
            "\u0635": "s",
            "\u0636": "d",
            "\u0637": "t",
            "\u0638": "z",
            "\u0639": "",
            "\u063a": "gh",
            "\u0641": "f",
            "\u0642": "q",
            "\u0643": "k",
            "\u0644": "l",
            "\u0645": "m",
            "\u0646": "n",
            "\u0647": "h",
            "\u0648": "ou",
            "\u064a": "i",
            "\u0649": "a",
            "\u0629": "a",
            "\u0621": "",
            "\u0623": "a",
            "\u0625": "i",
            "\u0622": "a",
            "\u0624": "ou",
            "\u0626": "i",
            # Vowel marks
            "\u064e": "a",
            "\u064f": "ou",
            "\u0650": "i",
            "\u064b": "an",
            "\u064c": "oun",
            "\u064d": "in",
            "\u0652": "",
            "\u0651": "",
            "\u0670": "a",
        }

        # Common fused Ben-forms (written as one word)
        self._fused_ben_re = re.compile(
            r"^(Ben|BEN|ben)(ali|said|amor|youssef|ahmed|salah|omar|aissa|"
            r"bella|haj|hamouda|khaled|larbi|mansour|messaoud|moussa|"
            r"nasser|slimane|younes|ziane)$",
            re.IGNORECASE,
        )

    # ------------------------------------------------------------------
    # clean
    # ------------------------------------------------------------------
    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to C5 Maghreb rules (in-place)."""
        for field in ("CanonicalLatin", "CanonicalNative"):
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])

        # Clean observed variants
        if "Variants" in entry:
            for bucket in ("Observed",):
                for variant in entry["Variants"].get(bucket, []):
                    if "str" in variant and variant["str"]:
                        variant["str"] = self._clean_name(variant["str"])

    def _clean_name(self, name: str) -> str:
        """Clean a single name string."""
        if not name:
            return name

        # Apply Unicode fold exceptions (Rule 16)
        name = self.apply_unicode_fold_exceptions(name)

        # Strip diacritical marks on Latin text that are not meaningful
        # (keep them on Arabic script)
        if not self._is_arabic(name):
            name = self._normalize_french_diacritics(name)

        # Remove titles and honorifics
        name = self._remove_titles(name)

        # Normalise el-/al-/bel- particle casing and spacing
        name = self._normalize_particles(name)

        # Collapse whitespace
        name = " ".join(name.split())

        # Normalise punctuation (Arabic comma, dashes)
        name = self._normalize_punctuation(name)

        return name

    def _remove_titles(self, text: str) -> str:
        if not text:
            return text
        words = text.split()
        cleaned = []
        for word in words:
            bare = word.rstrip(".,")
            if bare not in self.titles:
                cleaned.append(word)
        return " ".join(cleaned) if cleaned else text

    def _normalize_french_diacritics(self, name: str) -> str:
        """Preserve meaningful French diacritics but normalise NFC."""
        return unicodedata.normalize("NFC", name)

    def _normalize_particles(self, name: str) -> str:
        """Standardise el-/al-/bel-/bou- to lower-case hyphenated form."""
        # el Mansouri -> el-Mansouri, El Mansouri -> El-Mansouri
        name = re.sub(r"\b([Ee]l|[Aa]l|[Bb]el|[Bb]ou)\s+", r"\1-", name)
        return name

    def _normalize_punctuation(self, name: str) -> str:
        name = re.sub(r"\s+", " ", name)
        name = name.replace("\u060c", ", ")
        name = name.replace("\u061b", "; ")
        name = re.sub(r"[-\u2014\u2013]", "-", name)
        name = re.sub(r"[,;:]$", "", name)
        return name.strip()

    # ------------------------------------------------------------------
    # augment
    # ------------------------------------------------------------------
    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with C5-specific regional data (in-place)."""
        canonical = entry.get("CanonicalNative", "") or entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Ensure RegionalExtras exists
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        extras = entry["RegionalExtras"]
        extras["script"] = "Arabic" if self._is_arabic(canonical) else "Latin"

        # Extract name components
        components = self._extract_components(canonical)
        extras.update(components)

        # Detect Ben-prefix patronymic
        ben_info = self._detect_ben_prefix(canonical)
        if ben_info:
            extras["has_patronymic"] = True
            extras["patronymic_type"] = ben_info["type"]
            extras["patronymic_particle"] = ben_info["particle"]
        else:
            extras["has_patronymic"] = False

        # Detect country hint from name features
        extras["likely_country"] = self._guess_country(canonical, extras)

        # Ensure Variants structure
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        synthesised = entry["Variants"]["Synthesised"]

        # If Arabic script, provide romanised Latin form
        if self._is_arabic(canonical):
            romanised = self._romanize_name(canonical)
            if romanised and romanised != canonical:
                entry["CanonicalLatin"] = romanised
                synthesised.append({"str": romanised, "type": "romanization"})

        # French transliteration variant
        latin = entry.get("CanonicalLatin", "")
        if latin and not self._is_arabic(latin):
            french = self._to_french_transliteration(latin)
            if french != latin:
                synthesised.append({"str": french, "type": "french-transliteration"})

        # Ben-prefix split/fused variants
        self._generate_ben_variants(canonical, synthesised)

        # Particle-stripped variant for matching
        stripped = self._strip_particles(entry.get("CanonicalLatin", "") or canonical)
        if stripped and stripped != canonical and stripped != entry.get("CanonicalLatin", ""):
            synthesised.append({"str": stripped, "type": "no-particle"})

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Split name into given / family, respecting particles."""
        components: Dict[str, Any] = {}
        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip()
            return components

        words = name.split()
        # Identify particle-prefixed family cluster at the end
        family_start = self._find_family_start(words)
        if family_start > 0:
            components["given_name"] = " ".join(words[:family_start])
            components["family_name"] = " ".join(words[family_start:])
        elif len(words) >= 2:
            components["given_name"] = " ".join(words[:-1])
            components["family_name"] = words[-1]
        else:
            components["given_name"] = name
            components["family_name"] = ""
        return components

    def _find_family_start(self, words: List[str]) -> int:
        """Locate where the family-name cluster begins (particle prefix)."""
        for i, w in enumerate(words):
            wl = w.rstrip("-").lower()
            if i > 0 and wl in self.name_particles:
                return i
        return -1

    def _detect_ben_prefix(self, name: str) -> Optional[Dict[str, str]]:
        """Detect Maghreb Ben/Bou/Bel patronymic prefix."""
        words = name.split()
        for i, w in enumerate(words):
            wl = w.rstrip("-").lower()
            if wl in self.patronymic_particles:
                return {
                    "particle": wl,
                    "type": self.patronymic_particles[wl],
                    "index": i,
                }
        # Check fused Ben-forms (Benali, Bensaid ...)
        for w in words:
            if self._fused_ben_re.match(w):
                return {
                    "particle": "ben",
                    "type": "son of (fused)",
                    "index": words.index(w),
                }
        return None

    def _guess_country(self, name: str, extras: Dict[str, Any]) -> str:
        """Heuristic country guess from naming features."""
        lower = name.lower()
        # Mauritanian patterns
        if any(p in lower for p in ("ould ", "mint ")):
            return "MR"
        # Bou- prefix more common in Algeria/Tunisia
        if "bou" in lower.split() or lower.startswith("bou"):
            return "DZ"
        # Default to Morocco as largest Maghreb mathematician population
        return "MA"

    def _to_french_transliteration(self, latin: str) -> str:
        """Convert standard romanisation to French-Maghreb spelling."""
        result = latin
        for standard, french in self.french_transliteration_map.items():
            result = re.sub(r"\b" + re.escape(standard) + r"\b", french, result)
        return result

    def _generate_ben_variants(self, name: str, synthesised: List[Dict[str, str]]) -> None:
        """Generate fused/split Ben-prefix variants."""
        words = name.split()
        for i, w in enumerate(words):
            wl = w.lower()
            # Split fused: Benali -> Ben Ali
            m = self._fused_ben_re.match(w)
            if m:
                split_form = f"{m.group(1)} {m.group(2).title()}"
                full = " ".join(words[:i] + [split_form] + words[i + 1 :])
                synthesised.append({"str": full, "type": "ben-split"})
                return
            # Fuse separated: Ben Ali -> Benali
            if wl == "ben" and i + 1 < len(words):
                fused = f"Ben{words[i + 1].lower()}"
                full = " ".join(words[:i] + [fused] + words[i + 2 :])
                synthesised.append({"str": full, "type": "ben-fused"})
                return

    def _strip_particles(self, name: str) -> str:
        """Remove el-/al-/bel-/bou- particles from name."""
        stripped = re.sub(r"\b(el|al|bel|bou)[- ]", "", name, flags=re.IGNORECASE)
        return " ".join(stripped.split())

    def _romanize_name(self, name: str) -> str:
        """Romanise Arabic script using Maghreb-French convention."""
        result = []
        for ch in name:
            if ch in self.romanization_map:
                result.append(self.romanization_map[ch])
            else:
                result.append(ch)
        romanised = "".join(result)
        romanised = " ".join(romanised.split())
        return romanised.title()

    def _is_arabic(self, text: str) -> bool:
        for ch in text:
            if any(s <= ord(ch) <= e for s, e in self.arabic_ranges):
                return True
        return False

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------
    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry against C5 Maghreb rules. Raises RegionRuleError."""
        cn = entry.get("CanonicalNative", "")
        cl = entry.get("CanonicalLatin", "")

        if not cn and not cl:
            raise RegionRuleError("C5: Missing both CanonicalNative and CanonicalLatin")

        # Script consistency checks
        if cn and not self._is_arabic(cn) and not cn.isascii():
            raise RegionRuleError(f"C5: CanonicalNative should be Arabic script: {cn}")
        if cl and self._is_arabic(cl):
            raise RegionRuleError(f"C5: CanonicalLatin must not be Arabic script: {cl}")

        # Minimum length
        effective = cl or cn
        if effective and len(effective.replace(" ", "")) < 2:
            raise RegionRuleError(f"C5: Name too short: {effective}")

        # Character validity
        if cl and not self._valid_latin_chars(cl):
            raise RegionRuleError(f"C5: Invalid characters in CanonicalLatin: {cl}")

    def _valid_latin_chars(self, name: str) -> bool:
        for ch in name:
            if ch.isalpha() or ch in " -'.,\u00e9\u00e8\u00ea\u00ef\u00ee\u00e7\u00f4":
                continue
            cp = ord(ch)
            if any(s <= cp <= e for s, e in self.arabic_ranges):
                continue
            return False
        return True

    # ------------------------------------------------------------------
    # order_key
    # ------------------------------------------------------------------
    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key for C5 names."""
        extras = entry.get("RegionalExtras", {})
        family = extras.get("family_name", "")
        given = extras.get("given_name", "")

        canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
        if self._is_arabic(canonical):
            canonical = self._romanize_name(canonical)

        # Strip particles from family for sort purposes
        sort_family = self._strip_particles(family).upper() if family else ""
        sort_given = given.upper() if given else ""

        # Remove non-alphanumeric
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        key = f"{sort_family} {sort_given}".strip()
        return " ".join(key.split())
