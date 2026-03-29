"""
G1 - Latin America & Iberian Caribbean region implementation.

Covers: Argentina, Bolivia, Brazil, Chile, Colombia, Costa Rica, Cuba, 
Dominican Republic, Ecuador, Guatemala, Guyana, Honduras, Haiti, Mexico, 
Nicaragua, Panama, Peru, Paraguay, El Salvador, Suriname, Uruguay, 
Venezuela, Puerto Rico.

Features: Latin script, dual surnames (paternal + maternal), 
Portuguese diacritics, Spanish naming conventions, Creole influences.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class G1_LatinAmerica(RegionSpec):
    """
    Latin America & Iberian Caribbean region (G1).

    Handles Latin American naming conventions including:
    - Spanish dual surnames (apellido paterno + apellido materno)
    - Portuguese/Brazilian naming patterns
    - Latin script with Spanish/Portuguese diacritics
    - Compound given names
    - Regional variations (Mexican, Brazilian, Argentinian, etc.)
    """

    def __init__(self):
        super().__init__(
            code="G1",
            yaml_files=["g1_latin_america.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["Spanish", "Portuguese", "Latin American"],
        )

        # Spanish/Portuguese particles (less common in Latin America)
        self.particles = {
            "de",
            "del",
            "de la",
            "de las",
            "de los",
            "da",
            "das",
            "do",
            "dos",
            "y",
            "e",
            "van",
            "von",  # Some European heritage
        }

        # Stop-words for Rule 1: Iberian Dual Surname Split
        # These are used to determine boundaries between primary and secondary surnames
        self.surname_stop_words = {
            # Spanish stop-words
            "de",
            "del",
            "de la",
            "de las",
            "de los",
            # Portuguese stop-words
            "da",
            "das",
            "do",
            "dos",
            "de",
            # Conjunctions that can separate surnames
            "y",
            "e",
        }

        # Spanish diacritics
        self.spanish_chars = set("áéíóúüñ¿¡ÁÉÍÓÚÜÑ")

        # Portuguese diacritics (more extensive)
        self.portuguese_chars = set("áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ")

        # Combined Latin American diacritics
        self.latin_american_chars = self.spanish_chars | self.portuguese_chars

        # Common compound name patterns
        self.compound_patterns = {
            "maria": re.compile(r"\bMar[íi]a\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+", re.IGNORECASE),
            "jose": re.compile(r"\bJos[eé]\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+", re.IGNORECASE),
            "juan": re.compile(r"\bJuan\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+", re.IGNORECASE),
            "ana": re.compile(r"\bAna\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+", re.IGNORECASE),
            "luis": re.compile(r"\bLuis\s+[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+", re.IGNORECASE),
        }

        # Country-specific patterns
        self.country_indicators = {
            "BR": {
                "chars": self.portuguese_chars,
                "patterns": [
                    "silva",
                    "santos",
                    "oliveira",
                    "souza",
                    "rodrigues",
                    "ferreira",
                    "alves",
                    "pereira",
                    "lima",
                    "gomes",
                ],
                "particles": {"da", "das", "do", "dos", "de"},
            },
            "MX": {
                "chars": self.spanish_chars,
                "patterns": [
                    "gonzález",
                    "rodríguez",
                    "garcía",
                    "hernández",
                    "lópez",
                    "martínez",
                    "sánchez",
                    "pérez",
                    "gómez",
                    "martín",
                ],
                "compounds": True,
            },
            "AR": {
                "chars": self.spanish_chars,
                "patterns": [
                    "fernández",
                    "gonzález",
                    "rodríguez",
                    "lópez",
                    "garcía",
                    "pérez",
                    "martínez",
                    "sánchez",
                    "romero",
                    "gómez",
                ],
                "italian_influence": True,  # Many Italian surnames
            },
            "ES_CARIBBEAN": {  # Cuba, DR, PR
                "chars": self.spanish_chars,
                "patterns": [
                    "garcía",
                    "rodríguez",
                    "pérez",
                    "gonzález",
                    "fernández",
                    "lópez",
                    "martínez",
                    "sánchez",
                    "hernández",
                    "díaz",
                ],
                "compounds": True,
            },
        }

        # Dual surname validation patterns
        self.dual_surname_pattern = re.compile(
            r"^([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]*)*)\s+([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)(?:\s+([A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+))?$"
        )

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean Latin American names according to regional conventions.

        - Remove titles and honorifics
        - Normalize Spanish/Portuguese diacritics
        - Handle compound names properly
        - Preserve dual surname structure
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin field")

        # Remove Spanish/Portuguese titles
        titles_pattern = re.compile(
            r"\b(Dr\.?|Dra\.?|Prof\.?|Profa\.?|Sr\.?|Sra\.?|Srta\.?|Don|Doña|Dom|Dona)\s+",
            re.IGNORECASE,
        )
        cleaned = titles_pattern.sub("", canonical)

        # Remove degrees and generation suffixes
        suffixes_pattern = re.compile(r"\s+\b(Jr\.?|Sr\.?|Filho|Neto|III?|IV|V)\b", re.IGNORECASE)
        cleaned = suffixes_pattern.sub("", cleaned)

        # Normalize Unicode for consistent diacritics
        cleaned = unicodedata.normalize("NFC", cleaned)

        # Fix common spacing issues around particles
        for particle in self.particles:
            pattern = re.compile(rf"\s+\b{re.escape(particle)}\s+", re.IGNORECASE)
            cleaned = pattern.sub(f" {particle} ", cleaned)

        # Clean up multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned.strip())

        # Handle compound names - ensure proper spacing
        for pattern_name, pattern in self.compound_patterns.items():
            if pattern.search(cleaned):
                # Ensure compound names are properly spaced
                cleaned = re.sub(r"\s+", " ", cleaned)

        entry["CanonicalLatin"] = cleaned

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment Latin American names with regional variants and metadata.

        - Generate ASCII variants
        - Handle dual surnames with variants
        - Extract compound names
        - Add country-specific metadata
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Initialize variants
        if "VariantsSynthesised" not in entry:
            entry["VariantsSynthesised"] = []

        variants = entry["VariantsSynthesised"]

        # Generate ASCII variant (remove diacritics)
        ascii_variant = self._remove_diacritics(canonical)
        if ascii_variant != canonical:
            variants.append({"str": ascii_variant, "type": "ascii-lossy"})

        # Rule 1: Iberian Dual Surname Split – stop-words yield primary and secondary surnames
        surname_components = self._split_iberian_surnames(canonical)
        if surname_components:
            # Store in RegionalExtras for V7 compliance
            if "RegionalExtras" not in entry:
                entry["RegionalExtras"] = {}

            entry["RegionalExtras"]["primary_surname"] = surname_components["primary"]
            entry["RegionalExtras"]["secondary_surname"] = surname_components.get("secondary", "")
            entry["RegionalExtras"]["given_names"] = surname_components.get("given", "")

            # Generate variants using primary surname only
            if surname_components.get("secondary"):
                primary_only = f"{surname_components['primary']}, {surname_components['given']}"
                variants.append({"str": primary_only, "type": "dual-surname-primary"})

                # Generate variant using secondary surname only
                secondary_only = f"{surname_components['secondary']}, {surname_components['given']}"
                variants.append({"str": secondary_only, "type": "dual-surname-secondary"})

        # Handle dual surnames
        if self._is_dual_surname(canonical):
            dual_variants = self._generate_dual_surname_variants(canonical)
            for variant in dual_variants:
                variants.append(variant)

        # Extract compound given names
        compound_names = self._extract_compound_names(canonical)
        if compound_names:
            entry["CompoundGivenNames"] = compound_names

            # Generate shortened variants
            for compound in compound_names:
                shortened = compound.split()[0]  # Take first part
                short_variant = canonical.replace(compound, shortened)
                if short_variant != canonical:
                    variants.append({"str": short_variant, "type": "initial-collapse"})

        # Generate order swap (Given Family)
        if ", " in canonical:
            family, given = canonical.split(", ", 1)
            swapped = f"{given} {family}"
            variants.append({"str": swapped, "type": "order-swap"})

        # Extract particles if present
        particles = self._extract_particles(canonical)
        if particles:
            entry["Particles"] = particles

            # Generate particle-drop variant
            no_particles = self._remove_particles(canonical)
            if no_particles != canonical:
                variants.append({"str": no_particles, "type": "particle-drop"})

        # Add regional metadata
        entry["RegionCode"] = "G1"
        entry["RegionFeatures"] = {
            "has_spanish_chars": self._has_spanish_chars(canonical),
            "has_portuguese_chars": self._has_portuguese_chars(canonical),
            "is_dual_surname": self._is_dual_surname(canonical),
            "has_compound_names": bool(compound_names),
            "estimated_country": self._estimate_country(canonical),
            "language_hint": self._estimate_language(canonical),
        }

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate Latin American names according to regional rules.

        - Check Latin script with appropriate diacritics
        - Validate dual surname structure
        - Ensure proper compound name formatting
        - Check regional consistency
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin field")

        # Check basic name structure
        if not (", " in canonical or " " in canonical):
            raise RegionRuleError("Invalid name format: must contain family and given names")

        # Validate character set
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
        valid_chars.update(self.latin_american_chars)
        valid_chars.update(" ,-'.")

        invalid_chars = set(canonical) - valid_chars
        if invalid_chars:
            raise RegionRuleError(
                f"Invalid characters for Latin America: {', '.join(invalid_chars)}"
            )

        # Check length
        if len(canonical) > 120:  # Latin American names can be quite long
            raise RegionRuleError("Name too long (>120 characters)")

        # Validate dual surname structure if present
        if self._is_dual_surname(canonical) and ", " in canonical:
            family, given = canonical.split(", ", 1)
            family_parts = family.split()
            if len(family_parts) < 2:
                self.logger.warning(f"Expected dual surname but found single: {canonical}")

        # Validate compound names don't have formatting issues
        compound_names = self._extract_compound_names(canonical)
        for compound in compound_names:
            if "  " in compound:  # Double spaces
                raise RegionRuleError(f"Malformed compound name spacing in: {compound}")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate sort key for Latin American names.

        - Sort by paternal surname (first surname)
        - Handle particles properly
        - Use ASCII for consistent sorting
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return ""

        # Extract family and given names
        if ", " in canonical:
            family, given = canonical.split(", ", 1)
        else:
            # Assume last parts are family names
            parts = canonical.split()
            if len(parts) >= 3:  # Likely dual surname
                family = " ".join(parts[-2:])
                given = " ".join(parts[:-2])
            elif len(parts) >= 2:
                family = parts[-1]
                given = " ".join(parts[:-1])
            else:
                family = canonical
                given = ""

        # For dual surnames, sort by first (paternal) surname
        family_parts = family.split()
        if len(family_parts) >= 2:
            primary_surname = family_parts[0]  # Paternal surname
        else:
            primary_surname = family

        # Remove particles and diacritics for sorting
        primary_surname = self._remove_particles(primary_surname)
        sort_family = self._remove_diacritics(primary_surname).upper()
        sort_given = self._remove_diacritics(given).upper()

        return f"{sort_family}, {sort_given}"

    def _remove_diacritics(self, text: str) -> str:
        """Remove diacritics, keeping base letters."""
        normalized = unicodedata.normalize("NFD", text)
        return "".join(c for c in normalized if unicodedata.category(c) != "Mn")

    def _has_spanish_chars(self, text: str) -> bool:
        """Check if text contains Spanish-specific characters."""
        return any(c in self.spanish_chars for c in text)

    def _has_portuguese_chars(self, text: str) -> bool:
        """Check if text contains Portuguese-specific characters."""
        return any(c in self.portuguese_chars for c in text)

    def _is_dual_surname(self, name: str) -> bool:
        """Check if name follows Latin American dual surname pattern."""
        if ", " in name:
            family, _ = name.split(", ", 1)
            # Check if family part has 2+ substantial words
            family_words = [
                w for w in family.split() if w.lower() not in self.particles and len(w) > 2
            ]
            return len(family_words) >= 2
        else:
            # For "Given Family" format, assume last 2 words are surnames if 3+ words total
            words = name.split()
            return len(words) >= 3

    def _generate_dual_surname_variants(self, name: str) -> List[Dict[str, str]]:
        """Generate variants for dual surnames."""
        variants = []

        if ", " in name:
            family, given = name.split(", ", 1)
            family_parts = family.split()

            if len(family_parts) >= 2:
                # Paternal surname only
                paternal = family_parts[0]
                variants.append({"str": f"{paternal}, {given}", "type": "order-swap"})

                # Maternal surname only (if exists)
                if len(family_parts) >= 2:
                    maternal = family_parts[-1]
                    variants.append({"str": f"{maternal}, {given}", "type": "order-swap"})

        return variants

    def _extract_compound_names(self, name: str) -> List[str]:
        """Extract compound given names."""
        compounds = []

        for pattern_name, pattern in self.compound_patterns.items():
            matches = pattern.findall(name)
            compounds.extend(matches)

        return compounds

    def _extract_particles(self, name: str) -> List[str]:
        """Extract particles from name."""
        words = name.split()
        particles_found = []

        for word in words:
            clean_word = word.lower().rstrip(",")
            if clean_word in self.particles:
                particles_found.append(word.rstrip(","))

        return particles_found

    def _remove_particles(self, name: str) -> str:
        """Remove particles from name."""
        words = name.split()
        filtered = []

        for word in words:
            if word.lower().rstrip(",") not in self.particles:
                filtered.append(word)

        return " ".join(filtered)

    def _estimate_country(self, name: str) -> Optional[str]:
        """Estimate likely country based on name characteristics."""
        name_lower = name.lower()

        # Brazilian indicators (Portuguese)
        if any(c in name_lower for c in "ãàâõ") or any(
            pattern in name_lower for pattern in self.country_indicators["BR"]["patterns"][:5]
        ):
            return "BR"

        # Mexican indicators
        if any(pattern in name_lower for pattern in self.country_indicators["MX"]["patterns"][:5]):
            return "MX"

        # Argentinian indicators
        if any(pattern in name_lower for pattern in self.country_indicators["AR"]["patterns"][:3]):
            return "AR"

        # Spanish Caribbean
        if any(
            pattern in name_lower
            for pattern in self.country_indicators["ES_CARIBBEAN"]["patterns"][:3]
        ):
            return "CU"  # or DR, PR - hard to distinguish

        return None

    def _estimate_language(self, name: str) -> str:
        """Estimate primary language (Spanish or Portuguese)."""
        name_lower = name.lower()

        # Portuguese indicators
        if any(c in name_lower for c in "ãàâõ") or any(
            p in name_lower for p in ["da ", "das ", "do ", "dos "]
        ):
            return "Portuguese"

        # Default to Spanish for Latin America
        return "Spanish"

    def _split_iberian_surnames(self, name: str) -> Optional[Dict[str, str]]:
        """
        Rule 1: Iberian Dual Surname Split – stop-words yield primary and secondary surnames.

        This function implements the V7 linguistic rule for splitting Iberian names into
        their components using stop-words to identify boundaries.

        Examples:
        - "García de la Vega, María" → primary: "García", secondary: "de la Vega", given: "María"
        - "Santos dos Reis, João" → primary: "Santos", secondary: "dos Reis", given: "João"
        - "González Pérez, Carmen" → primary: "González", secondary: "Pérez", given: "Carmen"
        - "María del Carmen González Pérez" → given: "María del Carmen", primary: "González", secondary: "Pérez"

        Args:
            name: Full name in either "Family, Given" or "Given Family" format

        Returns:
            Dictionary with 'primary', 'secondary', and 'given' keys, or None if not Iberian pattern
        """
        if not name:
            return None

        # Handle "Family, Given" format
        if ", " in name:
            family_part, given_part = name.split(", ", 1)

            # Split family part into primary and secondary surnames
            surname_split = self._split_family_surnames(family_part)
            if surname_split:
                return {
                    "primary": surname_split["primary"],
                    "secondary": surname_split.get("secondary", ""),
                    "given": given_part,
                }
        else:
            # Handle "Given Family" format
            # This is more complex as we need to identify where given names end
            words = name.split()
            if len(words) < 2:
                return None

            # Try to find where surnames start by looking for capital letters after lowercase
            # and checking for known patterns
            given_end_idx = self._find_given_name_boundary(words)

            if given_end_idx > 0 and given_end_idx < len(words):
                given_part = " ".join(words[:given_end_idx])
                family_part = " ".join(words[given_end_idx:])

                surname_split = self._split_family_surnames(family_part)
                if surname_split:
                    return {
                        "primary": surname_split["primary"],
                        "secondary": surname_split.get("secondary", ""),
                        "given": given_part,
                    }

        return None

    def _split_family_surnames(self, family_part: str) -> Optional[Dict[str, str]]:
        """
        Split family names into primary and secondary using stop-words.

        Args:
            family_part: The family name portion (may contain dual surnames)

        Returns:
            Dictionary with 'primary' and optionally 'secondary' surnames
        """
        words = family_part.split()
        if not words:
            return None

        # Single word - just primary surname
        if len(words) == 1:
            return {"primary": words[0]}

        # Look for stop-words to split surnames
        for i, word in enumerate(words):
            word_lower = word.lower()

            # Check for multi-word stop-words first (e.g., "de la", "de los")
            if i < len(words) - 1:
                two_word = f"{word_lower} {words[i+1].lower()}"
                if i < len(words) - 2:
                    three_word = f"{two_word} {words[i+2].lower()}"
                    if three_word in self.surname_stop_words:
                        # Found three-word stop-word
                        if i > 0:
                            return {
                                "primary": " ".join(words[:i]),
                                "secondary": " ".join(words[i:]),
                            }

                if two_word in self.surname_stop_words:
                    # Found two-word stop-word
                    if i > 0:
                        return {"primary": " ".join(words[:i]), "secondary": " ".join(words[i:])}

            # Check for single-word stop-words
            if word_lower in self.surname_stop_words:
                if i > 0:
                    return {"primary": " ".join(words[:i]), "secondary": " ".join(words[i:])}

        # No stop-words found - for dual surnames, assume last word is secondary
        if len(words) == 2:
            return {"primary": words[0], "secondary": words[1]}
        elif len(words) > 2:
            # Complex case - might be compound surname or multiple surnames
            # Conservative approach: treat last word as secondary, rest as primary
            return {"primary": " ".join(words[:-1]), "secondary": words[-1]}

        return {"primary": family_part}

    def _find_given_name_boundary(self, words: List[str]) -> int:
        """
        Find the boundary between given names and surnames in a word list.

        This is complex for Spanish/Portuguese names as given names can be compound
        (e.g., "María del Carmen", "José Antonio").

        Args:
            words: List of words in the name

        Returns:
            Index where surnames begin
        """
        # Common compound given name patterns
        compound_given_patterns = ["maría del", "maria del", "josé", "jose", "juan", "ana", "luis"]

        # If we have a compound given name pattern, find where it ends
        name_lower = " ".join(words).lower()
        for pattern in compound_given_patterns:
            if name_lower.startswith(pattern):
                # Count words in the compound pattern
                pattern_words = pattern.split()

                # Check if followed by more given name parts
                if len(words) > len(pattern_words):
                    next_word = words[len(pattern_words)].lower()
                    if next_word in ["carmen", "antonio", "manuel", "isabel", "teresa"]:
                        return len(pattern_words) + 1
                    elif next_word in self.surname_stop_words:
                        # Stop-word might be part of given name
                        if len(words) > len(pattern_words) + 1:
                            return len(pattern_words) + 2

                return len(pattern_words)

        # Default heuristic: given names are typically 1-2 words
        # unless there are particles
        if len(words) >= 3:
            # Check if second word is a particle (might be part of given name)
            if words[1].lower() in self.surname_stop_words:
                return 3  # Given name includes particle
            else:
                return 2  # Standard two-part given name

        return 1  # Single given name
