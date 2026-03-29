"""
Maritime SEA (E7) regional processor.

Implements Malay bin/binti (Rule 28), Indonesian mononyms (Rule 14), 
Filipino maternal middle names (Rule 30).
Features: Patronymic handling, mononym detection, diverse naming patterns.
"""

import re
from typing import Any, Dict, Optional
from ..base import RegionSpec, RegionRuleError


class E7MaritimeSEA(RegionSpec):
    """Handler for E7 - Maritime SEA."""

    def __init__(self):
        super().__init__(
            code="E7",
            yaml_files=["e7_maritime_sea.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Given Family",  # Most common in region
            romanisation_standards=[],
        )

        # Rule 28: Malay bin/binti patronymic indicators
        self.malay_patronymics = {
            "bin": "son of",
            "binti": "daughter of",
            "bt": "daughter of",  # Abbreviated form
            "b.": "son of",  # Abbreviated form (ambiguous)
        }

        # Common Indonesian mononyms (Rule 14)
        # These are single names without family names
        self.indonesian_mononym_indicators = {
            # Common single names
            "Suharto",
            "Sukarno",
            "Megawati",
            "Jokowi",
            "Prabowo",
            "Wiranto",
            "Habibie",
            "Wahid",
            "Susilo",
            "Bambang",
            # Javanese single names
            "Soekarno",
            "Soeharto",
            "Abdurrahman",
            "Kalla",
            # Patterns that suggest mononyms
            "Harto",
            "Karno",
            "Wati",
            "Joko",
        }

        # Filipino naming patterns (Rule 30)
        # Common Filipino surnames and maternal indicators
        self.filipino_surnames = {
            "Santos",
            "Cruz",
            "Reyes",
            "Ramos",
            "Mendoza",
            "Garcia",
            "Rodriguez",
            "Fernandez",
            "Lopez",
            "Gonzales",
            "Hernandez",
            "Perez",
            "Sanchez",
            "Ramirez",
            "Torres",
            "Flores",
            "Rivera",
            "Gomez",
            "Diaz",
            "Morales",
        }

        # Common Maritime SEA countries for pattern detection
        self.country_patterns = {
            "MY": {"patronymics": ["bin", "binti"], "surnames": ["Ahmad", "Hassan", "Rahman"]},
            "SG": {"mixed": True},  # Mixed patterns
            "ID": {"mononyms": True, "surnames": ["Sari", "Indra", "Putra", "Dewi"]},
            "BN": {"patronymics": ["bin", "binti"]},
            "PH": {"maternal_middle": True, "surnames": self.filipino_surnames},
            "TL": {"portuguese_influence": True},
        }

        # Common titles to remove
        self.titles = {
            # Malay/Indonesian
            "Dato",
            "Datuk",
            "Tan Sri",
            "Tun",
            "Haji",
            "Hajjah",
            "Encik",
            "Puan",
            "Cik",
            "Tuan",
            "Dr",
            "Prof",
            # Filipino
            "Don",
            "Doña",
            "Ginoo",
            "Ginang",
            "Bb.",
            "G.",
            # English (common in region)
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Dr.",
            "Prof.",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to E7 rules."""
        # Clean canonical forms
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                entry[field] = self._clean_name(entry[field])

        # Clean variants
        if "Variants" in entry:
            if "Observed" in entry["Variants"]:
                for variant in entry["Variants"]["Observed"]:
                    if "str" in variant:
                        variant["str"] = self._clean_name(variant["str"])

    def _clean_name(self, name: str) -> str:
        """Clean a single Maritime SEA name string."""
        if not name:
            return name

        # Remove titles
        name = self._remove_titles(name)

        # Normalize whitespace
        name = re.sub(r"\s+", " ", name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove Maritime SEA titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            # Remove periods and check against titles
            clean_word = word.rstrip(".,")
            if clean_word not in self.titles:
                cleaned.append(word)

        return " ".join(cleaned)

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with E7-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Rule 14: Indonesian Mononyms – FamilyNameType=mononym; initials clustering skipped
        # Rule 29: Indonesian Mononyms (one-token canonical) – ensure single-token form
        if self._is_mononym(canonical):
            entry["FamilyNameType"] = "mononym"
            components["is_mononym"] = True
            components["initials_clustering_skipped"] = True

            # Rule 29: Ensure canonical form is exactly one token
            canonical_normalized = self._normalize_mononym_canonical(canonical)
            if canonical_normalized != canonical:
                entry["CanonicalLatin"] = canonical_normalized
                # Add original as variant if it was multi-token
                if " " in canonical:
                    entry["Variants"]["Synthesised"].append(
                        {"str": canonical, "type": "multi-token-original"}
                    )

        # Rule 28: Malay bin/binti – patronymic stripped; stored in extras
        malay_patronymic = self._find_malay_patronymic(canonical)
        if malay_patronymic:
            components["malay_patronymic"] = malay_patronymic["patronymic"]
            components["patronymic_meaning"] = malay_patronymic["meaning"]

        # Rule 30: Filipino Maternal Middle Name – stored as secondary_surname
        filipino_maternal = self._extract_filipino_maternal_name(canonical)
        if filipino_maternal:
            components["secondary_surname"] = filipino_maternal
            components["has_maternal_middle"] = True

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate variant without patronymic (Rule 28)
        if malay_patronymic:
            without_patronymic = self._generate_no_patronymic_variant(canonical, malay_patronymic)
            if without_patronymic and without_patronymic != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": without_patronymic, "type": "no-patronymic"}
                )

        # Generate order swap variant (if not mononym)
        if (
            not components.get("is_mononym")
            and components.get("family_name")
            and components.get("given_name")
        ):
            family_given = f"{components['family_name']}, {components['given_name']}"
            if family_given != canonical:
                entry["Variants"]["Synthesised"].append({"str": family_given, "type": "order-swap"})

    def _is_mononym(self, name: str) -> bool:
        """
        Rule 14: Detect Indonesian mononyms (single names).

        Indonesian culture commonly uses single names without family names.
        These should be marked as mononyms and excluded from initials clustering.
        """
        # Remove comma format for analysis
        name_clean = name.replace(", ", " ").strip()
        words = name_clean.split()

        # Single word is potential mononym
        if len(words) == 1:
            # Check against known Indonesian mononyms
            if words[0] in self.indonesian_mononym_indicators:
                return True

            # Check for Indonesian name patterns
            name_lower = words[0].lower()

            # Common Indonesian mononym patterns
            if (
                name_lower.endswith(("harto", "karno", "wati", "joko"))
                or name_lower.startswith(("su", "mega", "pra", "bam"))
                or len(words[0]) > 6
            ):  # Long single names often mononyms
                return True

        return False

    def _normalize_mononym_canonical(self, name: str) -> str:
        """
        Rule 29: Indonesian Mononyms (one-token canonical) – normalize to single token.

        Indonesian mononyms should be represented as single tokens in canonical form.
        This rule handles cases where mononyms might be split across multiple tokens:

        - "Soekarno Jr" → "Soekarno" (remove generational suffixes)
        - "Mega Wati" → "Megawati" (compound mononym)
        - "Joko Wi" → "Jokowi" (common abbreviation pattern)
        - "Pra Bowo" → "Prabowo" (restore original single form)

        The goal is to ensure the canonical form matches how the person is actually known.
        """
        if not name or len(name.split()) == 1:
            return name

        words = name.split()

        # Remove common suffixes that don't belong in mononym canonical
        suffixes_to_remove = {
            "jr",
            "jr.",
            "senior",
            "senior.",
            "ii",
            "iii",
            "iv",
            "muda",
            "tua",
            "besar",
            "kecil",  # Indonesian generational markers
        }

        # Filter out suffix words
        filtered_words = []
        for word in words:
            if word.lower() not in suffixes_to_remove:
                filtered_words.append(word)

        # If we removed suffixes and now have one word, return it
        if len(filtered_words) == 1:
            return filtered_words[0]

        # Handle common Indonesian compound mononym patterns
        if len(filtered_words) == 2:
            first, second = filtered_words
            combined = first + second

            # Check if the combined form is a known mononym
            known_compound_mononyms = {
                "megawati": "Megawati",
                "jokowi": "Jokowi",
                "prabowo": "Prabowo",
                "wiranto": "Wiranto",
                "bambangdh": "Bambang",  # Handle "Bambang DH" style names
                "susilo": "Susilo",
                "abdurrahman": "Abdurrahman",
            }

            combined_lower = combined.lower()
            if combined_lower in known_compound_mononyms:
                return known_compound_mononyms[combined_lower]

            # Handle common abbreviation patterns
            # "Joko Wi" → "Jokowi"
            if len(second) <= 2 and not second.endswith("."):
                potential_abbrev = first + second.lower()
                if potential_abbrev.lower() in known_compound_mononyms:
                    return known_compound_mononyms[potential_abbrev.lower()]

            # Check if it's likely a split compound name (both parts short)
            if len(first) <= 4 and len(second) <= 4:
                return combined.capitalize()

        # If we have multiple words and can't determine a single form,
        # take the first word (most significant part of the name)
        if filtered_words:
            return filtered_words[0]

        # Fallback: return original if no processing was possible
        return name

    def _find_malay_patronymic(self, name: str) -> Optional[Dict[str, str]]:
        """
        Rule 28: Find Malay bin/binti patronymic indicators.

        These indicate father's name and should be stripped for sorting
        but stored in RegionalExtras for cultural context.
        """
        words = name.split()

        for i, word in enumerate(words):
            word_clean = word.lower().rstrip(",.")
            if word_clean in self.malay_patronymics:
                return {
                    "patronymic": word,
                    "meaning": self.malay_patronymics[word_clean],
                    "index": i,
                }

        return None

    def _extract_filipino_maternal_name(self, name: str) -> Optional[str]:
        """
        Rule 30: Extract Filipino maternal middle name.

        Filipino naming convention often includes maternal surname as middle name:
        Given [Maternal] Paternal → Maternal becomes secondary_surname
        """
        # Look for three-part names that might be Filipino
        words = name.replace(", ", " ").split()

        if len(words) == 3:
            given, middle, last = words

            # Check if last name is common Filipino surname
            if last in self.filipino_surnames:
                # Middle name is likely maternal surname
                return middle

            # Check if middle name looks like Filipino surname
            if middle in self.filipino_surnames:
                return middle

        return None

    def _generate_no_patronymic_variant(
        self, name: str, patronymic_info: Dict[str, str]
    ) -> Optional[str]:
        """Generate variant without Malay patronymic."""
        words = name.split()
        patronymic_index = patronymic_info["index"]

        # Remove patronymic and following name (father's name)
        filtered_words = []
        i = 0
        while i < len(words):
            if i == patronymic_index:
                # Skip patronymic and next word (father's name)
                i += 2 if i + 1 < len(words) else 1
            else:
                filtered_words.append(words[i])
                i += 1

        if filtered_words:
            return " ".join(filtered_words)

        return None

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate E7 name requirements."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        # Basic validation - to be enhanced
        if len(canonical) < 3:
            raise RegionRuleError("Name too short")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for E7 names."""
        canonical = entry.get("CanonicalLatin", "")

        # Simple sort by family name
        if ", " in canonical:
            family = canonical.split(", ")[0]
            return family.lower()

        return canonical.lower()

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        if ", " in name:
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated
            parts = name.split(None, 1)
            if len(parts) >= 2:
                components["given_name"] = parts[0].strip()
                components["family_name"] = parts[1].strip()
            else:
                components["family_name"] = name.strip()
                components["given_name"] = ""

        return components
