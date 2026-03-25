"""
A5 - Dutch/French Caribbean region implementation.

Covers: CW, SX, BQ (Dutch Caribbean) + MQ, GF, GP, RE, YT, PM (French Caribbean)
(Curaçao, Sint Maarten, Bonaire, Sint Eustatius, Saba +
Martinique, French Guiana, Guadeloupe, Réunion, Mayotte, Saint Pierre and Miquelon)

Features: Creole particle handling, apostrophe normalization,
          French/Dutch colonial patterns, Caribbean-specific surnames.
"""

import re
from typing import Any, Dict, Optional

from ...base import RegionRuleError, RegionSpec


class A5CaribbeanProcessor(RegionSpec):
    """
    Dutch/French Caribbean region (A5).

    Handles Caribbean naming conventions:
    - Creole particles (di, d', l', la, ti, etc.)
    - Apostrophe normalization in contractions
    - French colonial patterns (de, du, des)
    - Dutch colonial patterns (van, de, ter)
    - Caribbean-specific compound surnames
    - African-influenced naming patterns
    - Hyphenated given names (rule #23)
    """

    def __init__(self):
        super().__init__(
            code="A5",
            yaml_files=["a5_caribbean.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=[],
        )

        # Caribbean special characters
        self.caribbean_chars = {
            "à",
            "À",
            "è",
            "È",
            "é",
            "É",
            "ê",
            "Ê",
            "ë",
            "Ë",
            "ï",
            "Ï",
            "î",
            "Î",
            "ò",
            "Ò",
            "ô",
            "Ô",
            "ù",
            "Ù",
            "û",
            "Û",
            "ç",
            "Ç",
            "ñ",
            "Ñ",
        }

        # Apostrophe variations (important for Creole)
        self.apostrophe_chars = {"'", "'", "'", "`", "ʼ"}

        self.allowed_chars = self.caribbean_chars | self.apostrophe_chars

        # Creole particles (often with apostrophes)
        self.creole_particles = {
            # French-based Creole
            "d'",
            "D'",
            "l'",
            "L'",  # contractions
            "di",
            "Di",  # "of" in some Creoles
            "la",
            "La",  # definite article
            "ti",
            "Ti",  # "petit/little" (common nickname prefix)
            "man",
            "Man",  # Creole form
            # Less common but present
            "zot",
            "Zot",  # "their/them" in some Creoles
            "mo",
            "Mo",  # "my" in some Creoles
        }

        # Colonial particles
        self.french_particles = {"de", "du", "des", "de la", "d'", "le", "la", "les"}

        self.dutch_particles = {
            "van",
            "van der",
            "van den",
            "van de",
            "de",
            "der",
            "den",
            "ter",
            "te",
            "ten",
        }

        # Common Caribbean surname patterns
        self.caribbean_surnames = {
            # French Caribbean
            "Césaire",
            "Fanon",
            "Bissainthe",
            "Desvarieux",
            "Kassav",
            "Théodore",
            "Baptiste",
            "Saint-Prix",
            "Sainte-Rose",
            # Dutch Caribbean
            "Martina",
            "Croes",
            "Tromp",
            "Winklaar",
            "Eman",
            # African-origin
            "Toussaint",
            "Dessalines",
            "Christophe",
            "Pétion",
            # Common religious-origin
            "Saint-Jean",
            "Saint-Louis",
            "Saint-Pierre",
            "Emmanuel",
            # Plantation-era
            "Beauregard",
            "Bellegarde",
            "Delafosse",
            "Duvalier",
        }

        # Common Caribbean first names
        self.caribbean_first_names = {
            # French influence
            "Jean",
            "Marie",
            "Pierre",
            "Jacques",
            "François",
            "Thérèse",
            "Marguerite",
            "Céleste",
            "Émilie",
            # Diminutives/nicknames
            "Ti-Jean",
            "Ti-Pierre",
            "Man-Marie",
            # Dutch influence
            "Johannes",
            "Willem",
            "Hendrik",
            "Cornelis",
            # African-influenced
            "Ayizan",
            "Erzulie",
            "Agwe",
            "Legba",
            # Modern Caribbean
            "Eddy",
            "Jimmy",
            "Claude",
            "Serge",
        }

        # Titles to remove
        self.titles = {
            # French
            "M",
            "M.",
            "Mme",
            "Mlle",
            "Dr",
            "Dr.",
            "Me",
            # Dutch
            "Dhr",
            "Dhr.",
            "Mw",
            "Mw.",
            "Mej",
            "Mej.",
            # English (common due to tourism/international business)
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Miss",
            # Religious
            "Père",
            "Soeur",
            "Fr",
            "Fr.",
            "Sr",
            "Sr.",
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to A5 rules."""
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
        """Clean a single name string."""
        # Input validation - ensure it's a string
        if not isinstance(name, str):
            raise RegionRuleError(f"Name must be string, not {type(name).__name__}")

        if not name:
            return name

        # Security: filter out dangerous control characters (except safe whitespace)
        if any(ord(c) < 32 and c not in "\t\n\r " for c in name):
            raise RegionRuleError("Name contains dangerous control characters")

        # Normalize apostrophes
        name = self._normalize_apostrophes(name)

        # Remove titles
        name = self._remove_titles(name)

        # Normalize whitespace (but preserve apostrophe spacing)
        name = re.sub(r"\s+", " ", name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        # Handle special Creole contractions
        name = self._normalize_creole_contractions(name)

        return name.strip()

    def _normalize_apostrophes(self, text: str) -> str:
        """Normalize various apostrophe characters to standard form."""
        # Use the typographic apostrophe as standard
        standard_apostrophe = "'"

        for apos in self.apostrophe_chars:
            if apos != standard_apostrophe:
                text = text.replace(apos, standard_apostrophe)

        return text

    def _normalize_creole_contractions(self, text: str) -> str:
        """Normalize common Creole contractions."""
        # Ensure consistent spacing around contracted particles
        # d'Andre → d'Andre (no space)
        # l' Ecole → l'Ecole (no space)
        text = re.sub(r"([dlDL])\s*'\s*", r"\1'", text)

        return text

    def _remove_titles(self, text: str) -> str:
        """Remove titles from beginning of name."""
        if not text:
            return text

        words = text.split()

        # Remove titles from beginning
        while words and words[0] in self.titles:
            words.pop(0)

        return " ".join(words)

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with A5-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate synthesized variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Add no-apostrophe variant (common in databases)
        no_apostrophe = self._remove_apostrophes(canonical)
        if no_apostrophe != canonical:
            entry["Variants"]["Synthesised"].append({"str": no_apostrophe, "type": "no-apostrophe"})

        # Add ASCII variant
        ascii_variant = self._generate_ascii_variant(canonical)
        if ascii_variant != canonical:
            entry["Variants"]["Synthesised"].append({"str": ascii_variant, "type": "ascii-lossy"})

        # Add hyphenated initials variant (Rule #23)
        if components.get("has_hyphenated_given"):
            initials_variant = self._generate_initials_variant(canonical, components)
            if initials_variant:
                entry["Variants"]["Synthesised"].append(
                    {"str": initials_variant, "type": "hyphenated-initials"}
                )

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components with Caribbean-specific handling."""
        components = {}

        # Detect colonial influence
        has_french = self._detect_french_influence(name)
        has_dutch = self._detect_dutch_influence(name)
        has_creole = self._detect_creole_elements(name)

        if has_french:
            components["colonial_influence"] = "french"
        elif has_dutch:
            components["colonial_influence"] = "dutch"
        elif has_creole:
            components["colonial_influence"] = "creole"
        else:
            components["colonial_influence"] = "mixed"

        if "," in name:
            # Western format: Family, Given
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Try to split Given Family
            words = name.split()

            # Check for particles at beginning (might be part of given name)
            if words and words[0].lower() in self.creole_particles:
                # Ti-Jean Baptiste → given: Ti-Jean, family: Baptiste
                # But could also be a family particle
                # Need more sophisticated logic
                if len(words) >= 3:
                    # Assume first 2 words are given if starts with particle
                    given = " ".join(words[:2])
                    family = " ".join(words[2:])
                else:
                    given = words[0] if len(words) > 1 else ""
                    family = words[-1] if len(words) > 1 else words[0]
            else:
                # Standard Western order
                if len(words) >= 2:
                    given = " ".join(words[:-1])
                    family = words[-1]
                else:
                    given = ""
                    family = name

        components["family_name"] = family
        components["given_name"] = given

        # Check for hyphenated given names (Rule #23)
        if "-" in given:
            components["has_hyphenated_given"] = True
            given_parts = given.split()
            hyphenated_parts = []
            for part in given_parts:
                if "-" in part:
                    hyphenated_parts.append(part)
            components["hyphenated_given_parts"] = hyphenated_parts

        # Extract particles from family name
        family_words = family.split()
        particles_found = []
        main_surname = []

        i = 0
        while i < len(family_words):
            word = family_words[i]
            word_lower = word.lower()

            # Check for multi-word particles
            if i < len(family_words) - 1:
                two_word = f"{word_lower} {family_words[i+1].lower()}"
                if two_word in self.french_particles or two_word in self.dutch_particles:
                    particles_found.append(f"{word} {family_words[i+1]}")
                    i += 2
                    continue

            # Single word particles
            if (
                word_lower in self.french_particles
                or word_lower in self.dutch_particles
                or word_lower in self.creole_particles
            ):
                particles_found.append(word)
            else:
                main_surname.append(word)
            i += 1

        if particles_found:
            components["particles"] = particles_found
            components["main_surname"] = " ".join(main_surname)

        # Check for Saint- compounds (common in Caribbean)
        if any(part.startswith("Saint-") or part.startswith("Sainte-") for part in family_words):
            components["has_saint_compound"] = True

        # Check for African-influenced patterns
        if has_creole or any(
            word in ["Toussaint", "Dessalines", "Christophe"] for word in family_words
        ):
            components["has_african_influence"] = True

        return components

    def _detect_french_influence(self, name: str) -> bool:
        """Detect French colonial influence in name."""
        name_lower = name.lower()

        # Check for French particles
        for particle in self.french_particles:
            if f" {particle} " in name_lower or name_lower.startswith(f"{particle} "):
                return True

        # Check for French diacritics
        french_chars = {"é", "è", "ê", "ë", "à", "ç", "ù", "û", "î", "ï", "ô"}
        if any(char in name for char in french_chars):
            return True

        # Check for typical French Caribbean surnames
        french_surnames = {
            "Baptiste",
            "Césaire",
            "Théodore",
            "François",
            "Saint-Jean",
            "Saint-Louis",
            "Saint-Pierre",
        }
        return any(surname in name for surname in french_surnames)

    def _detect_dutch_influence(self, name: str) -> bool:
        """Detect Dutch colonial influence in name."""
        name_lower = name.lower()

        # Check for Dutch particles
        for particle in self.dutch_particles:
            if f" {particle} " in name_lower or name_lower.startswith(f"{particle} "):
                return True

        # Check for typical Dutch Caribbean surnames
        dutch_surnames = {"Martina", "Croes", "Tromp", "Winklaar", "Eman"}
        return any(surname in name for surname in dutch_surnames)

    def _detect_creole_elements(self, name: str) -> bool:
        """Detect Creole elements in name."""
        # Check for Creole particles
        for particle in self.creole_particles:
            if particle in name:
                return True

        # Check for Ti- prefix (common Creole diminutive)
        if re.search(r"\bTi-", name):
            return True

        return False

    def _remove_apostrophes(self, name: str) -> str:
        """Remove apostrophes from name (for variant generation)."""
        # Don't just remove - handle contractions properly
        # d'Andre → dAndre or D Andre (depending on context)

        # For contractions, remove apostrophe without space
        result = re.sub(r"([dlDL])'([A-Z])", r"\1\2", name)

        # For other apostrophes, replace with space
        result = result.replace("'", " ")

        # Clean up extra spaces
        result = " ".join(result.split())

        return result

    def _generate_ascii_variant(self, name: str) -> str:
        """Generate ASCII variant of name."""
        replacements = {
            "à": "a",
            "À": "A",
            "è": "e",
            "È": "E",
            "é": "e",
            "É": "E",
            "ê": "e",
            "Ê": "E",
            "ë": "e",
            "Ë": "E",
            "ï": "i",
            "Ï": "I",
            "î": "i",
            "Î": "I",
            "ò": "o",
            "Ò": "O",
            "ô": "o",
            "Ô": "O",
            "ù": "u",
            "Ù": "U",
            "û": "u",
            "Û": "U",
            "ç": "c",
            "Ç": "C",
            "ñ": "n",
            "Ñ": "N",
            """: "'",
            """: "'",
            "œ": "oe",
            "Œ": "OE",
            "æ": "ae",
            "Æ": "AE",
        }

        result = name
        for char, replacement in replacements.items():
            result = result.replace(char, replacement)

        # Final normalization
        import unicodedata

        result = unicodedata.normalize("NFKD", result)
        result = result.encode("ascii", "ignore").decode("ascii")

        return result

    def _generate_initials_variant(self, name: str, components: Dict[str, Any]) -> Optional[str]:
        """Generate variant with hyphenated names as initials (Rule #23)."""
        if not components.get("has_hyphenated_given"):
            return None

        family = components.get("family_name", "")
        given = components.get("given_name", "")

        if not given or not family:
            return None

        # Process hyphenated parts
        given_parts = given.split()
        processed_parts = []

        for part in given_parts:
            if "-" in part:
                # Jean-Pierre → J.-P.
                hyphen_parts = part.split("-")
                initials = "-".join(p[0].upper() + "." for p in hyphen_parts if p)
                processed_parts.append(initials)
            else:
                processed_parts.append(part)

        new_given = " ".join(processed_parts)
        return f"{family}, {new_given}"

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to A5 rules."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        # Check for valid characters
        if not self._is_valid_caribbean_name(canonical):
            invalid_chars = (
                set(canonical)
                - set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz ,.-'")
                - self.allowed_chars
            )
            if invalid_chars:
                raise RegionRuleError(f"Invalid characters in name: {invalid_chars}")

        # Validate structure
        if "," in canonical:
            parts = canonical.split(",")
            if len(parts) != 2:
                raise RegionRuleError(f"Invalid comma usage in name: {canonical}")
            if not parts[0].strip() or not parts[1].strip():
                raise RegionRuleError(f"Empty name component: {canonical}")

        # Validate apostrophe usage
        # Should not have space before apostrophe in contractions
        if re.search(r"\s'[A-Z]", canonical):
            # This might be valid for some names, so just log warning
            pass  # Could add warning log here

        # Check for unbalanced apostrophes (common data error)
        apostrophe_count = canonical.count("'")
        if apostrophe_count > 4:  # Arbitrary threshold
            # Might indicate data corruption
            pass  # Could add warning

    def _is_valid_caribbean_name(self, name: str) -> bool:
        """Check if name contains valid Caribbean characters."""
        # Allow basic Latin, Caribbean special characters, and common punctuation
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ,.-'")
        allowed.update(self.allowed_chars)

        return all(c in allowed for c in name)

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Get family and given names
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Use main surname if particles exist (French rule #22: particles retained)
        # This differs from some other regions where particles are dropped
        if family:
            sort_key = f"{family}, {given}".strip(", ")
        else:
            sort_key = entry.get("CanonicalLatin", "")

        # Normalize for sorting
        # Remove apostrophes for consistent ordering
        sort_key = sort_key.replace("'", "")

        # Convert to uppercase and normalize
        sort_key = " ".join(sort_key.split()).upper()

        # Handle diacritics for sorting
        sort_replacements = {
            "À": "A",
            "È": "E",
            "É": "E",
            "Ê": "E",
            "Ë": "E",
            "Ï": "I",
            "Î": "I",
            "Ò": "O",
            "Ô": "O",
            "Ù": "U",
            "Û": "U",
            "Ç": "C",
            "Ñ": "N",
        }

        for char, replacement in sort_replacements.items():
            sort_key = sort_key.replace(char, replacement)

        return sort_key
