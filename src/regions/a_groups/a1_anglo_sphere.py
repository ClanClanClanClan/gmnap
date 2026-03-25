"""
A1 - Core Anglo-Sphere region implementation.

Covers: US, GB, CA, AU, NZ, IE plus English-Caribbean and Pacific US territories.
Features: Middle initials, generational suffixes, Latin ASCII script.
"""

import re
from typing import Any, Dict, List, Optional

from ..base import RegionRuleError, RegionSpec


class A1_AngloSphere(RegionSpec):
    """
    Core Anglo-Sphere region (A1).

    Handles English-speaking regions with common naming conventions:
    - Middle initials and names
    - Generational suffixes (Jr., Sr., III, etc.)
    - Professional titles (Dr., Prof., etc.)
    - Standard "Family, Given" order
    """

    def __init__(self):
        super().__init__(
            code="A1",
            yaml_files=["a1_anglo_sphere.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=[],
        )

        # Hardcoded defaults
        self.titles = {
            "Dr",
            "Dr.",
            "Doctor",
            "Prof",
            "Prof.",
            "Professor",
            "Mr",
            "Mr.",
            "Mrs",
            "Mrs.",
            "Ms",
            "Ms.",
            "Miss",
            "Sir",
            "Dame",
            "Lord",
            "Lady",
            "Rev",
            "Rev.",
            "Reverend",
            "Fr",
            "Fr.",
            "Father",
            "Col",
            "Col.",
            "Colonel",
            "Capt",
            "Capt.",
            "Captain",
            "Lt",
            "Lt.",
            "Lieutenant",
            "Maj",
            "Maj.",
            "Major",
            "Gen",
            "Gen.",
            "General",
            "Adm",
            "Adm.",
            "Admiral",
        }

        self.generational_suffixes = {
            "Jr",
            "Jr.",
            "Junior",
            "Sr",
            "Sr.",
            "Senior",
            "I",
            "II",
            "III",
            "IV",
            "V",
            "VI",
            "VII",
            "VIII",
            "IX",
            "X",
            "1st",
            "2nd",
            "3rd",
            "4th",
            "5th",
            "Esq",
            "Esq.",
            "Esquire",
            "PhD",
            "Ph.D.",
            "MD",
            "M.D.",
            "JD",
            "J.D.",
        }

        self.particles = {
            "de",
            "di",
            "da",
            "del",
            "della",
            "van",
            "von",
            "der",
            "den",
            "ten",
            "la",
            "le",
            "du",
            "des",
            "of",
            "mac",
            "mc",
            "o'",
            "st",
            "san",
            "santa",
        }

        # Override from YAML config if available
        cfg = self.load_yaml_config()
        if cfg:
            if "titles" in cfg:
                self.titles = set(cfg["titles"])
            if "generational_suffixes" in cfg:
                self.generational_suffixes = set(cfg["generational_suffixes"])
            if "particles" in cfg:
                self.particles = set(cfg["particles"])

    def clean(self, entry: Dict[str, Any]) -> None:
        """Clean entry according to A1 rules."""
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
        if not name:
            return name

        # Preserve original for comparison
        original = name

        # Handle "Family, Given" format
        if "," in name:
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""

            # Clean each part
            family = self._remove_titles_and_suffixes(family)
            given = self._remove_titles_and_suffixes(given)

            # Reconstruct
            name = f"{family}, {given}".strip(", ")
        else:
            # Handle "Given Family" format
            name = self._remove_titles_and_suffixes(name)

        # Normalize whitespace
        name = " ".join(name.split())

        # Normalize punctuation
        name = self._normalize_punctuation(name)

        return name

    def _remove_titles_and_suffixes(self, text: str) -> str:
        """Remove titles and generational suffixes."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        i = 0
        while i < len(words):
            word = words[i]

            # Skip titles at beginning
            if i == 0 and word in self.titles:
                i += 1
                continue

            # Check for generational suffixes at end
            if i == len(words) - 1 and word.rstrip(".,") in self.generational_suffixes:
                break

            # Check for suffixes with comma
            if word.rstrip(".,") in self.generational_suffixes:
                # Skip this and potentially following suffixes
                break

            cleaned.append(word)
            i += 1

        return " ".join(cleaned)

    def _normalize_punctuation(self, name: str) -> str:
        """Normalize punctuation in names."""
        # First, ensure space after comma
        name = re.sub(r",(?! )", ", ", name)

        # Handle initials - add spaces between consecutive initials
        # Pattern: capital letter + period followed by capital letter (no space)
        name = re.sub(r"([A-Z]\.)([A-Z])", r"\1 \2", name)

        # Add periods to isolated single capital letters (initials)
        words = name.split()
        normalized_words = []

        for word in words:
            # Check if it's a single capital letter without a period
            if len(word) == 1 and word.isupper():
                normalized_words.append(word + ".")
            # Check if it's a single capital letter with punctuation (but not period)
            elif (
                len(word) == 2 and word[0].isupper() and word[1] in ",;:" and not word.endswith(".")
            ):
                normalized_words.append(word[0] + ".")
            else:
                normalized_words.append(word)

        name = " ".join(normalized_words)

        # Remove trailing punctuation except periods after initials
        name = re.sub(r"[,;:]$", "", name)

        # Clean up extra spaces
        name = re.sub(r"\s+", " ", name)

        return name.strip()

    def augment(self, entry: Dict[str, Any]) -> None:
        """Augment entry with A1-specific data."""
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

        # Add collapsed initial variant (Rule 18)
        if components.get("middle_initials"):
            collapsed = self._generate_collapsed_variant(canonical, components)
            if collapsed and collapsed != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": collapsed, "type": "initial-collapse"}
                )

        # Add ASCII-only variant
        ascii_variant = self._generate_ascii_variant(canonical)
        if ascii_variant != canonical:
            entry["Variants"]["Synthesised"].append({"str": ascii_variant, "type": "ascii-lossy"})

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components."""
        components = {}

        if "," in name:
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Try to split "Given Family" format
            words = name.split()
            if len(words) >= 2:
                given = " ".join(words[:-1])
                family = words[-1]
            else:
                given = ""
                family = name

        components["family_name"] = family
        components["given_name"] = given

        # Extract middle initials/names
        if given:
            given_parts = given.split()
            if len(given_parts) > 1:
                # First part is given name
                components["first_name"] = given_parts[0]
                # Rest are middle names/initials
                middle = given_parts[1:]
                components["middle_names"] = [m for m in middle if len(m) > 2]
                components["middle_initials"] = [
                    m for m in middle if len(m) <= 2 and m.endswith(".")
                ]

        # Check for particles in family name
        family_words = family.split()
        if len(family_words) > 1:
            particles_found = []
            main_surname = []
            for word in family_words:
                if word.lower() in self.particles:
                    particles_found.append(word)
                else:
                    main_surname.append(word)

            if particles_found:
                components["particles"] = particles_found
                components["main_surname"] = " ".join(main_surname)

        return components

    def _generate_collapsed_variant(self, name: str, components: Dict[str, Any]) -> Optional[str]:
        """
        Rule 18: Anglo Middle-Initial Collapse – John C. clusters with John.

        This rule handles:
        - Middle initials: "John C. Smith" → "John Smith"
        - Hyphenated initials: "John-Claude Smith" → "John Smith"

        The collapsed form is used for clustering/matching purposes.
        """
        given = components.get("given_name", "")
        if not given:
            return None

        # Check for middle initials or hyphenated names
        given_parts = given.split()

        # Pattern 1: Traditional middle initials (e.g., "John C.")
        has_middle_initial = (
            any(
                len(part) <= 2 and (part.endswith(".") or (len(part) == 1 and part.isupper()))
                for part in given_parts[1:]
            )
            if len(given_parts) > 1
            else False
        )

        # Pattern 2: Hyphenated first names that might be initials
        first_name = given_parts[0] if given_parts else ""
        has_hyphenated = "-" in first_name

        if not has_middle_initial and not has_hyphenated:
            return None

        # Extract just the first name component
        if has_hyphenated:
            # For hyphenated names, take the part before the hyphen
            # e.g., "John-Claude" → "John", "Marie-Louise" → "Marie"
            first_name = first_name.split("-")[0]
        else:
            # Just use the first word (non-initial)
            first_name = given_parts[0]

        # Reconstruct the name without middle components
        family = components.get("family_name", "")
        if family:
            return f"{family}, {first_name}"
        else:
            # Handle "Given Family" format
            return first_name

    def _generate_ascii_variant(self, name: str) -> str:
        """Generate ASCII-only variant."""
        # Simple ASCII conversion for A1 (mostly already ASCII)
        import unicodedata

        ascii_name = unicodedata.normalize("NFKD", name)
        ascii_name = ascii_name.encode("ascii", "ignore").decode("ascii")
        return ascii_name

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to A1 rules."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            raise RegionRuleError("Missing CanonicalLatin")

        # Check for valid characters (Latin ASCII expected)
        if not self._is_valid_ascii_name(canonical):
            # Check if it's extended Latin that's acceptable
            if not self._is_valid_extended_latin(canonical):
                raise RegionRuleError(f"Invalid characters in name: {canonical}")

        # Check name structure
        if "," in canonical:
            parts = canonical.split(",")
            if len(parts) != 2:
                raise RegionRuleError(f"Invalid comma usage in name: {canonical}")
            if not parts[0].strip() or not parts[1].strip():
                raise RegionRuleError(f"Empty name component: {canonical}")

        # Validate components
        components = entry.get("RegionalExtras", {})

        # Check family name
        family = components.get("family_name", "")
        if family and len(family) < 2:
            raise RegionRuleError(f"Family name too short: {family}")

        # Check given name
        given = components.get("given_name", "")
        # Allow GlobalID collision suffixes like "--1", "--2" per v7 spec
        if given:
            # Remove collision suffix for validation
            given_without_suffix = re.sub(r"--\d+$", "", given)
            # Only validate if it looks like an Anglo name (all ASCII letters)
            # Non-ASCII names will be handled by other regions
            if (
                given_without_suffix
                and given_without_suffix.replace(".", "")
                .replace("-", "")
                .replace(" ", "")
                .isascii()
            ):
                # For ASCII names, digits are not valid in given names
                if not re.match(r"^[A-Za-z][A-Za-z.\s-]*$", given_without_suffix):
                    raise RegionRuleError(f"Invalid given name format: {given}")

    def _is_valid_ascii_name(self, name: str) -> bool:
        """Check if name contains only ASCII characters."""
        return all(ord(c) < 128 for c in name)

    def _is_valid_extended_latin(self, name: str) -> bool:
        """Check if name contains valid extended Latin characters."""
        # Allow Latin-1 supplement for names like José, François
        for char in name:
            if ord(char) >= 128:
                # Check if it's in Latin-1 Supplement or Latin Extended-A
                if not (0x00C0 <= ord(char) <= 0x00FF or 0x0100 <= ord(char) <= 0x017F):
                    return False
        return True

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate deterministic sort key."""
        components = entry.get("RegionalExtras", {})

        # Primary sort by family name
        family = components.get("family_name", "")
        given = components.get("given_name", "")

        # Handle particles (von, van, de) - typically ignored in sorting
        main_surname = components.get("main_surname", family)

        # Normalize for sorting
        sort_family = main_surname.upper()
        sort_given = given.upper()

        # Remove punctuation for sorting
        sort_family = re.sub(r"[^\w\s]", "", sort_family)
        sort_given = re.sub(r"[^\w\s]", "", sort_given)

        # Generate key
        key = f"{sort_family}, {sort_given}"

        # Ensure determinism by normalizing whitespace
        key = " ".join(key.split())

        return key
