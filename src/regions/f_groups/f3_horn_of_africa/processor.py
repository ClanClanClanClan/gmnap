"""
Horn of Africa (F3) regional processor.

Implements Ethiopian and Eritrean naming patterns with Ethiopic script support.
Features: Patronymic system (no family surnames), Ge'ez/Ethiopic script,
multiple ethnic groups (Amhara, Tigray, Oromo, Afar, Somali), religious titles.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


class F3_HornOfAfrica(RegionSpec):
    """Handler for F3 - Horn of Africa (Ethiopia, Eritrea)."""

    def __init__(self):
        super().__init__(
            code="F3",
            yaml_files=["f3_horn_of_africa.yaml"],
            scripts=["Ethiopic", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Father Grandfather",
            romanisation_standards=["BGN/PCGN", "ALA-LC"],
        )

        # Ethiopic script ranges
        self.ethiopic_base = (0x1200, 0x137F)  # Basic Ethiopic
        self.ethiopic_supplement = (0x1380, 0x139F)  # Supplement
        self.ethiopic_extended = (0x2D80, 0x2DDF)  # Extended
        self.ethiopic_extended_a = (0xAB00, 0xAB2F)  # Extended-A

        # Titles and honorifics
        self.titles = {
            # Religious titles
            "abba",
            "aba",
            "abune",
            "qesis",
            "qes",
            "memhir",
            "diakon",
            "abbot",
            "bishop",
            "patriarch",
            "deacon",
            # Traditional titles
            "ato",
            "atto",
            "woizero",
            "woizerit",
            "woizrit",
            "emebeit",
            "ras",
            "dejazmach",
            "fitawrari",
            "grazmach",
            "kegnazmach",
            "balambaras",
            "lij",
            "negus",
            "nigus",
            # Academic
            "dr",
            "dr.",
            "doctor",
            "prof",
            "prof.",
            "professor",
            "engineer",
            "ing",
            "phd",
            "md",
            # Modern
            "mr",
            "mr.",
            "mrs",
            "mrs.",
            "ms",
            "ms.",
            "miss",
        }

        # Common Amharic given names
        self.amharic_names = {
            # Male
            "gebre",
            "tekle",
            "haile",
            "mulugeta",
            "mekonen",
            "tadesse",
            "abebe",
            "bekele",
            "getachew",
            "kebede",
            "tesfaye",
            "alemayehu",
            "yohannes",
            "dawit",
            "solomon",
            "abraham",
            "michael",
            "gabriel",
            # Female
            "marta",
            "selamawit",
            "tigist",
            "almaz",
            "meseret",
            "hirut",
            "bezawit",
            "azeb",
            "meron",
            "eden",
            "rahel",
            "sara",
            "hanna",
            "selam",
            "tsehay",
            "worknesh",
            "alem",
            "tsehaynesh",
        }

        # Tigrinya names (common in Tigray/Eritrea)
        self.tigrinya_names = {
            "amanuel",
            "berhe",
            "gebru",
            "hagos",
            "mehari",
            "yemane",
            "tsegay",
            "tesfay",
            "afewerki",
            "ghebremedhin",
            "kahsay",
            "senay",
            "semere",
            "tewolde",
            "zerai",
            "fesseha",
            "araya",
        }

        # Oromo names
        self.oromo_names = {
            "abdi",
            "adugna",
            "benti",
            "chala",
            "daba",
            "dechasa",
            "dejene",
            "dereje",
            "fikadu",
            "gadisa",
            "gemechu",
            "girma",
            "gutema",
            "jaleta",
            "kebede",
            "lemma",
            "tolera",
            "tolesa",
        }

        # Name components often indicating ethnicity
        self.ethnic_markers = {
            "amhara": ["haile", "gebre", "tekle", "selassie", "mariam"],
            "tigray": ["berhe", "gebru", "hagos", "aregawi", "gebremedhin"],
            "oromo": ["benti", "gutema", "gadisa", "tolera", "jaleta"],
            "afar": ["ahmed", "mohammed", "ali", "omar", "ibrahim"],
            "somali": ["abdi", "hassan", "mohamed", "farah", "jama"],
        }

        # Religious name elements
        self.religious_elements = {
            # Christian (Orthodox)
            "gebre": "servant of",
            "haile": "power of",
            "tekle": "plant of",
            "selassie": "trinity",
            "mariam": "mary",
            "giorgis": "george",
            "michael": "michael",
            "gabriel": "gabriel",
            # Islamic
            "abd": "servant of",
            "mohammed": "mohammed",
            "ahmed": "ahmed",
            "ali": "ali",
            "hassan": "hassan",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Apply V7 security validation and graceful edge case handling."""
        # SECURITY: Validate input before processing
        self.apply_security_and_validation_checks(entry)

        # SECURITY: Check raw input for dangerous characters FIRST
        # Check both CanonicalLatin and CanonicalNative before any processing
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                raw_input = entry[field]
                # Normalize tabs/newlines BEFORE security check (V7 edge case)

                raw_input = raw_input.replace("\t", " ").replace("\n", " ")

                entry[field] = raw_input  # Update the entry with normalized value

                if self._has_security_risks(raw_input):
                    raise RegionRuleError(
                        f"Name contains dangerous characters: {raw_input[:50]}..."
                    )

        # More flexible: try to get any available name
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # Don't fail - just skip cleaning if no name available
            return

        # Apply region-specific cleaning rules here
        # This is a stub implementation - region-specific logic should be added
        pass

    def _clean_name(self, name: str) -> str:
        """Clean a single Horn of Africa name string."""
        if not name:
            return name

        # Remove titles
        name = self._remove_titles(name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", " ", name)  # No commas in patronymic system
        name = re.sub(r"\s*-\s*", "-", name)

        # Normalize whitespace
        name = re.sub(r"\s+", " ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove Ethiopian/Eritrean titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            word_lower = word.lower().rstrip(".,")
            if word_lower not in self.titles:
                cleaned.append(word)

        return " ".join(cleaned)

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with F3-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Detect scripts
        script_info = self._detect_scripts(entry)
        if script_info:
            components.update(script_info)

        # Analyze patronymic structure
        patronymic_info = self._analyze_patronymic(canonical)
        if patronymic_info:
            components.update(patronymic_info)

        # Detect ethnicity
        ethnicity = self._detect_ethnicity(canonical)
        if ethnicity:
            components["probable_ethnicity"] = ethnicity

        # Detect religious elements
        religious_info = self._detect_religious_elements(canonical)
        if religious_info:
            components.update(religious_info)

        # Detect country (Ethiopia vs Eritrea)
        country = self._detect_country(entry, components)
        if country:
            components["specific_country"] = country

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate patronymic order variants
        patronymic_variants = self._generate_patronymic_variants(canonical, components)
        for variant in patronymic_variants:
            if variant != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": variant, "type": "patronymic-order"}
                )

        # Generate transliteration variants if Ethiopic
        if script_info.get("ethiopic_script_detected"):
            translit_variants = self._generate_transliteration_variants(entry)
            for variant in translit_variants:
                if variant not in [canonical, entry.get("CanonicalNative", "")]:
                    entry["Variants"]["Synthesised"].append(
                        {"str": variant, "type": "ethiopic-transliteration"}
                    )

    def _detect_scripts(self, entry: Dict[str, Any]) -> Dict[str, bool]:
        """Detect which scripts are used in the entry."""
        script_info = {}

        # Check CanonicalNative for Ethiopic script
        native = entry.get("CanonicalNative", "")
        if native:
            has_ethiopic = any(
                ord(c) in range(self.ethiopic_base[0], self.ethiopic_base[1] + 1)
                or ord(c)
                in range(self.ethiopic_supplement[0], self.ethiopic_supplement[1] + 1)
                or ord(c)
                in range(self.ethiopic_extended[0], self.ethiopic_extended[1] + 1)
                or ord(c)
                in range(self.ethiopic_extended_a[0], self.ethiopic_extended_a[1] + 1)
                for c in native
            )

            if has_ethiopic:
                script_info["ethiopic_script_detected"] = True

                # Detect specific Ethiopic script variant
                if any(ord(c) in range(0x1380, 0x139F) for c in native):
                    script_info["ethiopic_supplement_used"] = True
                if any(ord(c) in range(0x2D80, 0x2DDF) for c in native):
                    script_info["ethiopic_extended_used"] = True

        return script_info

    def _analyze_patronymic(self, name: str) -> Dict[str, Any]:
        """Analyze patronymic naming structure."""
        info = {}

        parts = name.split()
        if len(parts) >= 2:
            info["has_patronymic"] = True
            info["given_name"] = parts[0]
            info["father_name"] = parts[1]

            if len(parts) >= 3:
                info["grandfather_name"] = parts[2]
                info["full_patronymic"] = True
            else:
                info["full_patronymic"] = False

            if len(parts) > 3:
                # Sometimes great-grandfather or additional names
                info["extended_patronymic"] = True
                info["additional_names"] = parts[3:]
        else:
            # Single name only
            info["has_patronymic"] = False
            info["single_name"] = True

        return info

    def _detect_ethnicity(self, name: str) -> Optional[str]:
        """Detect probable ethnicity from name patterns."""
        name_lower = name.lower()
        name_parts = name_lower.split()

        # Count ethnic markers
        ethnic_scores = {}

        for ethnicity, markers in self.ethnic_markers.items():
            score = 0
            for marker in markers:
                for part in name_parts:
                    if marker in part:
                        score += 1
            if score > 0:
                ethnic_scores[ethnicity] = score

        # Check specific name lists
        for part in name_parts:
            if part in self.amharic_names:
                ethnic_scores["amhara"] = ethnic_scores.get("amhara", 0) + 2
            if part in self.tigrinya_names:
                ethnic_scores["tigray"] = ethnic_scores.get("tigray", 0) + 2
            if part in self.oromo_names:
                ethnic_scores["oromo"] = ethnic_scores.get("oromo", 0) + 2

        # Return highest scoring ethnicity
        if ethnic_scores:
            return max(ethnic_scores.items(), key=lambda x: x[1])[0]

        return None

    def _detect_religious_elements(self, name: str) -> Dict[str, Any]:
        """Detect religious elements in names."""
        info = {}
        name_lower = name.lower()

        christian_elements = 0
        islamic_elements = 0

        for element, meaning in self.religious_elements.items():
            if element in name_lower:
                if element in [
                    "gebre",
                    "haile",
                    "tekle",
                    "selassie",
                    "mariam",
                    "giorgis",
                    "michael",
                    "gabriel",
                ]:
                    christian_elements += 1
                    info["has_christian_elements"] = True
                else:
                    islamic_elements += 1
                    info["has_islamic_elements"] = True

        if christian_elements > islamic_elements:
            info["probable_religion"] = "ethiopian_orthodox"
        elif islamic_elements > christian_elements:
            info["probable_religion"] = "islam"

        return info

    def _detect_country(
        self, entry: Dict[str, Any], components: Dict[str, Any]
    ) -> Optional[str]:
        """Detect whether name is more likely Ethiopian or Eritrean."""
        # Check email/affiliation
        email = entry.get("Email", "").lower()
        affiliation = entry.get("Affiliation", "").lower()

        if ".et" in email or "ethiopia" in affiliation:
            return "ethiopia"
        if ".er" in email or "eritrea" in affiliation:
            return "eritrea"

        # Check ethnicity
        ethnicity = components.get("probable_ethnicity")
        if ethnicity == "oromo":
            return "ethiopia"  # Oromo mainly in Ethiopia
        if ethnicity == "tigray" and (
            "asmara" in affiliation or "asmera" in affiliation
        ):
            return "eritrea"

        # Default based on population
        return "ethiopia"  # Ethiopia has larger population

    def _generate_patronymic_variants(
        self, name: str, components: Dict[str, Any]
    ) -> List[str]:
        """Generate patronymic order variants."""
        variants = []

        if not components.get("has_patronymic"):
            return variants

        given = components.get("given_name", "")
        father = components.get("father_name", "")
        grandfather = components.get("grandfather_name", "")

        # Standard format: Given Father Grandfather
        if given and father:
            # Two-name format
            variants.append(f"{given} {father}")

            if grandfather:
                # Three-name format
                variants.append(f"{given} {father} {grandfather}")

                # Academic citation format (sometimes used)
                variants.append(f"{given}, {father} {grandfather}")
                variants.append(f"{given} {father[0]}. {grandfather}")

                # Sometimes grandfather-father-given (rare but occurs)
                variants.append(f"{grandfather} {father} {given}")

        return list(set(variants))  # Remove duplicates

    def _generate_transliteration_variants(self, entry: Dict[str, Any]) -> List[str]:
        """Generate transliteration variants for Ethiopic names."""
        variants = []

        native = entry.get("CanonicalNative", "")
        if not native:
            return variants

        # Simple transliteration rules (subset)
        translit_map = {
            # Some common Ethiopic to Latin mappings
            "ገ": "ge",
            "ብ": "b",
            "ረ": "re",
            "ማ": "ma",
            "ር": "r",
            "ያ": "ya",
            "ም": "m",
            "ተ": "te",
            "ክ": "k",
            "ለ": "le",
            "ሃ": "ha",
            "ይ": "y",
            "ሰ": "se",
            "ላ": "la",
            "ሲ": "si",
            "አ": "a",
            "በ": "be",
            "ቤ": "be",
            "ከ": "ke",
            "ደ": "de",
        }

        # Generate basic transliteration
        translit = native
        for ethiopic, latin in translit_map.items():
            translit = translit.replace(ethiopic, latin)

        if translit != native and all(ord(c) < 128 for c in translit):
            variants.append(translit)

        return variants

    def validate(self, entry: Dict[str, Any]) -> None:
        """Apply V7 security validation with DoS protection."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # No name to validate - that's OK, just skip
            return

        # SECURITY: Check for dangerous characters first
        if self._has_security_risks(canonical):
            raise RegionRuleError(
                f"Name contains dangerous characters: {canonical[:50]}..."
            )

        # Check for reasonable length (prevent DoS attacks)
        if len(canonical) > 150:
            raise RegionRuleError(
                f"Name too long: {len(canonical)} characters (max 150)"
            )

        # THEN handle legitimate edge cases
        if len(canonical.strip()) == 1:
            # Single character names are edge cases but valid
            self.logger.warning(f"Single character name: {canonical}")

        # Apply region-specific validation here
        pass

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for F3 names."""
        canonical = entry.get("CanonicalLatin", "")

        # For patronymic system, sort by given name primarily
        parts = canonical.split()
        if parts:
            given_name = parts[0]
        else:
            given_name = canonical

        # Normalize for sorting
        given_normalized = unicodedata.normalize("NFD", given_name.lower())

        # Remove diacritics
        given_clean = "".join(
            char for char in given_normalized if unicodedata.category(char) != "Mn"
        )

        # Include father's name if available for secondary sorting
        if len(parts) > 1:
            father_name = parts[1]
            father_normalized = unicodedata.normalize("NFD", father_name.lower())
            father_clean = "".join(
                char for char in father_normalized if unicodedata.category(char) != "Mn"
            )
            return f"{given_clean} {father_clean}"

        return given_clean

    def _has_security_risks(self, name: str) -> bool:
        """Check for dangerous characters that pose security risks."""
        if not name:
            return False
        for char in name:
            # Reject control characters (ASCII 0-31, 127)
            if ord(char) < 32 or ord(char) == 127:
                return True
            # Reject other potentially dangerous Unicode ranges
            if ord(char) in [0xFEFF, 0x200B, 0x200C, 0x200D]:  # Zero-width characters
                return True
        return False

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components for Horn of Africa names."""
        components = {}

        # Split into parts
        parts = name.split()

        if len(parts) == 0:
            return components

        # Patronymic system
        if len(parts) >= 1:
            components["given_name"] = parts[0]

        if len(parts) >= 2:
            components["father_name"] = parts[1]
            components["patronymic_structure"] = True

        if len(parts) >= 3:
            components["grandfather_name"] = parts[2]
            components["full_patronymic"] = True

        if len(parts) > 3:
            components["additional_ancestors"] = parts[3:]
            components["extended_genealogy"] = True

        # No family name in traditional system
        components["family_name"] = None
        components["uses_patronymic_system"] = True

        return components
