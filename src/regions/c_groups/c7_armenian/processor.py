"""
Armenian (C7) regional processor.

Implements Armenian patronymic handling (-ian/-yan suffixes), Armenian script support,
and diaspora naming patterns worldwide.
Features: Armenian script detection, patronymic variants, diaspora adaptations.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional
from ...base_enhanced import EnhancedRegionSpec as RegionSpec


class C7_Armenian(RegionSpec):
    """Handler for C7 - Armenian."""

    def __init__(self):
        super().__init__(
            code="C7",
            yaml_files=["c7_armenian.yaml"],
            scripts=["Armenian", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ISO 9985", "Hübschmann-Meillet"],
        )

        # Armenian Unicode range (U+0530-U+058F)
        self.armenian_range = (0x0530, 0x058F)

        # Armenian patronymic suffixes with cultural variations
        self.patronymic_suffixes = {
            # Eastern Armenian (standard)
            "-yan": {"meaning": "son/descendant of", "region": "Eastern", "frequency": "high"},
            "-ian": {"meaning": "son/descendant of", "region": "Diaspora", "frequency": "high"},
            # Western Armenian variations
            "-ean": {"meaning": "son/descendant of", "region": "Western", "frequency": "medium"},
            "-yan": {"meaning": "son/descendant of", "region": "Eastern", "frequency": "high"},
            # Regional variations
            "-jyan": {"meaning": "son/descendant of", "region": "Regional", "frequency": "low"},
            "-cian": {"meaning": "son/descendant of", "region": "Diaspora", "frequency": "low"},
            "-sian": {"meaning": "son/descendant of", "region": "Diaspora", "frequency": "low"},
        }

        # Common Armenian given names for detection
        self.armenian_given_names = {
            # Traditional male names
            "hayk",
            "aram",
            "tigran",
            "artashes",
            "levon",
            "armen",
            "vahram",
            "sarkis",
            "grigor",
            "mesrop",
            "nerses",
            "sahak",
            "hovhannes",
            "petros",
            "pavlos",
            # Traditional female names
            "armine",
            "silva",
            "gohar",
            "anahit",
            "arpi",
            "shoghakat",
            "hripsime",
            "gayane",
            "marine",
            "mariam",
            "ana",
            "yeghisabet",
            "anush",
            "shushan",
            # Modern names
            "serzh",
            "vahe",
            "ruzan",
            "tsovinar",
            "aren",
            "nayiri",
            "aida",
        }

        # Armenian family name roots (without suffixes)
        self.armenian_name_roots = {
            "sargs",
            "sarks",
            "karapet",
            "garabed",
            "tovmas",
            "khachatr",
            "gaspar",
            "manuk",
            "naghash",
            "petros",
            "avetis",
            "krikor",
            "mesrop",
            "hovhann",
            "boghos",
            "nigoghos",
            "ohan",
            "hagop",
            "vartan",
            "dikran",
            "aram",
        }

        # Armenian script characters for detection
        self.armenian_characters = set(chr(i) for i in range(0x0530, 0x058F + 1))

        # Common titles to remove
        self.titles = {
            # Armenian traditional
            "baron",
            "tikin",
            "oriord",
            "պարոն",
            "տիկին",
            "օրիորդ",
            # Academic (Armenian)
            "professor",
            "doctor",
            "engineer",
            "պրոֆեսոր",
            "դոկտոր",
            "ինժեներ",
            # Religious (Armenian Apostolic)
            "catholicos",
            "archbishop",
            "bishop",
            "vardapet",
            "կաթողիկոս",
            "արքեպիսկոպոս",
            "եպիսկոպոս",
            "վարդապետ",
            # Western titles
            "mr",
            "mr.",
            "mrs",
            "mrs.",
            "ms",
            "ms.",
            "dr",
            "dr.",
            "prof",
            "prof.",
            "պրն.",
            "տկն.",
        }

        # Diaspora community patterns
        self.diaspora_patterns = {
            "american": {
                "suffix_adaptations": {"-yan": "-ian", "-ean": "-ian"},
                "characteristics": ["anglicized", "standardized_spelling"],
            },
            "french": {
                "suffix_adaptations": {"-yan": "-ian", "-ean": "-éan"},
                "characteristics": ["french_phonetics", "accent_preservation"],
            },
            "middle_eastern": {
                "suffix_adaptations": {"-yan": "-yan"},  # Often preserved
                "characteristics": ["arabic_influence", "traditional_forms"],
            },
            "south_american": {
                "suffix_adaptations": {"-yan": "-yan", "-ian": "-ian"},
                "characteristics": ["spanish_phonetics", "adapted_spelling"],
            },
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Apply V7 security validation and graceful edge case handling."""
        # Use comprehensive V7 security validation from base class
        # This includes all 7 required security checks:
        # 1. Dangerous characters, 2. DoS protection (length limits)
        # 3. SQL injection patterns, 4. XSS patterns
        # 5. Command injection patterns, 6. Path traversal patterns
        # 7. Native field validation
        self.apply_security_and_validation_checks(entry)

        # Handle legitimate edge cases gracefully
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # Don't fail - just skip cleaning if no name available
            return

        # Apply region-specific cleaning rules here
        # This is a stub implementation - region-specific logic should be added
        pass

    def _clean_name(self, name: str) -> str:
        """Clean a single Armenian name string."""
        if not name:
            return name

        # Remove titles
        name = self._remove_titles(name)

        # Normalize Armenian script and Latin mix
        name = self._normalize_armenian_latin_mix(name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        # Normalize whitespace
        name = re.sub(r"\s+", " ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove Armenian titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            # Remove periods and check against titles
            clean_word = word.rstrip(".,").lower()
            if clean_word not in self.titles:
                cleaned.append(word)

        return " ".join(cleaned)

    def _normalize_armenian_latin_mix(self, text: str) -> str:
        """Normalize mixed Armenian script and Latin text."""
        # Ensure proper Unicode normalization
        text = unicodedata.normalize("NFC", text)

        # Handle common Armenian-Latin mixing issues
        # (Add specific rules as needed for Armenian script handling)

        return text

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with C7-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Detect Armenian script usage
        if "CanonicalNative" in entry and entry["CanonicalNative"]:
            armenian_script_detected = self._detect_armenian_script(entry["CanonicalNative"])
            components["armenian_script_detected"] = armenian_script_detected

        # Armenian patronymic analysis
        patronymic_info = self._analyze_armenian_patronymic(canonical)
        if patronymic_info:
            components.update(patronymic_info)

            # Set family name type based on patronymic
            entry["FamilyNameType"] = "patronymic"

        # Armenian given name detection
        given_name_info = self._analyze_armenian_given_name(canonical)
        if given_name_info:
            components.update(given_name_info)

        # Diaspora community detection
        diaspora_info = self._detect_diaspora_community(canonical)
        if diaspora_info:
            components["diaspora_community"] = diaspora_info

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate patronymic variants
        if patronymic_info:
            variants = self._generate_armenian_patronymic_variants(canonical, patronymic_info)
            for variant in variants:
                if variant != canonical:
                    entry["Variants"]["Synthesised"].append(
                        {"str": variant, "type": "armenian-patronymic-variant"}
                    )

        # Generate order swap variant
        if components.get("family_name") and components.get("given_name"):
            family_given = f"{components['family_name']}, {components['given_name']}"
            if family_given != canonical:
                entry["Variants"]["Synthesised"].append({"str": family_given, "type": "order-swap"})

    def _detect_armenian_script(self, text: str) -> bool:
        """Detect if text contains Armenian script characters."""
        for char in text:
            if ord(char) in range(self.armenian_range[0], self.armenian_range[1] + 1):
                return True
        return False

    def _analyze_armenian_patronymic(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Analyze Armenian patronymic patterns.

        Armenian surnames typically end in -ian, -yan, -ean, etc.
        These indicate "son/descendant of [root name]".
        """
        name_lower = name.lower()

        for suffix, info in self.patronymic_suffixes.items():
            if name_lower.endswith(suffix):
                # Extract root name (remove suffix)
                root = name_lower[: -len(suffix)]

                # Check if root matches known Armenian name patterns
                is_armenian_root = (
                    root in self.armenian_name_roots
                    or len(root) >= 3  # Armenian roots are typically longer
                )

                if is_armenian_root:
                    return {
                        "patronymic_suffix": suffix,
                        "patronymic_root": root,
                        "patronymic_meaning": info["meaning"],
                        "patronymic_region": info["region"],
                        "patronymic_frequency": info["frequency"],
                        "is_armenian_patronymic": True,
                    }

        return None

    def _analyze_armenian_given_name(self, name: str) -> Optional[Dict[str, str]]:
        """Analyze if given name is Armenian."""
        # Extract potential given name
        if ", " in name:
            parts = name.split(", ", 1)
            given_part = parts[1] if len(parts) > 1 else ""
        else:
            parts = name.split(None, 1)
            given_part = parts[0] if parts else ""

        given_lower = given_part.lower()

        if given_lower in self.armenian_given_names:
            return {"armenian_given_name": given_part, "armenian_given_name_verified": True}

        # Check for partial matches (nicknames, shortened forms)
        for armenian_name in self.armenian_given_names:
            if (given_lower.startswith(armenian_name[:3]) and len(given_lower) >= 3) or (
                armenian_name.startswith(given_lower) and len(given_lower) >= 3
            ):
                return {
                    "armenian_given_name": given_part,
                    "armenian_given_name_verified": False,
                    "armenian_given_name_match": armenian_name,
                }

        return None

    def _detect_diaspora_community(self, name: str) -> Optional[str]:
        """Detect likely diaspora community based on name patterns."""
        name_lower = name.lower()

        # American diaspora patterns (strong -ian preference)
        if name_lower.endswith("-ian") and not name_lower.endswith("-jian"):
            return "american"

        # French diaspora patterns (accent preservation, -éan forms)
        if "é" in name_lower or "è" in name_lower or name_lower.endswith("-éan"):
            return "french"

        # Eastern Armenian patterns (prefer -yan)
        if name_lower.endswith("-yan") and not name_lower.endswith("-jyan"):
            return "eastern_armenian"

        # Western Armenian patterns (-ean suffix)
        if name_lower.endswith("-ean"):
            return "western_armenian"

        return None

    def _generate_armenian_patronymic_variants(
        self, name: str, patronymic_info: Dict[str, Any]
    ) -> List[str]:
        """Generate Armenian patronymic variants."""
        variants = []
        root = patronymic_info["patronymic_root"]
        current_suffix = patronymic_info["patronymic_suffix"]

        # Generate variants with different suffix forms
        suffix_variants = ["-ian", "-yan", "-ean"]

        for suffix in suffix_variants:
            if suffix != current_suffix:
                # Replace the suffix
                variant = name[: -len(current_suffix)] + suffix
                variants.append(variant)

        # Generate shortened form (root name only)
        if ", " in name:
            parts = name.split(", ", 1)
            given_part = parts[1] if len(parts) > 1 else ""
            if given_part:
                root_only_variant = f"{root.title()}, {given_part}"
                variants.append(root_only_variant)

        return variants

    def validate(self, entry: Dict[str, Any]) -> None:
        """Apply V7 security validation with DoS protection."""
        # Use comprehensive security validation from base class
        # This includes all 7 required security checks:
        # 1. Dangerous characters
        # 2. DoS protection (length limits)
        # 3. SQL injection patterns
        # 4. XSS patterns
        # 5. Command injection patterns
        # 6. Path traversal patterns
        # 7. Native field validation
        self.apply_security_and_validation_checks(entry)

        # Handle legitimate edge cases
        canonical = self.get_canonical_name(entry)
        if canonical and len(canonical.strip()) == 1:
            # Single character names are edge cases but valid
            self.logger.warning(f"Single character name: {canonical}")

        # Apply region-specific validation here
        pass

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for C7 names."""
        canonical = entry.get("CanonicalLatin", "")

        # Extract family name for sorting
        if ", " in canonical:
            family = canonical.split(", ")[0]
        else:
            # For patronymic surnames, use the full surname
            parts = canonical.split()
            if len(parts) >= 2:
                family = parts[-1]  # Last part is likely surname
            else:
                family = canonical

        # Normalize for sorting (handle Armenian diacritics)
        family_normalized = unicodedata.normalize("NFD", family.lower())

        # Remove diacritics for consistent sorting
        family_clean = "".join(
            char for char in family_normalized if unicodedata.category(char) != "Mn"
        )

        return family_clean

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components for Armenian names."""
        components = {}

        if ", " in name:
            # Comma-separated format: "Family, Given"
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated format: "Given Family" or "Given Middle Family"
            parts = name.split()
            if len(parts) >= 2:
                components["given_name"] = parts[0].strip()
                if len(parts) == 2:
                    components["family_name"] = parts[1].strip()
                else:
                    # Multiple parts - last is likely family name
                    components["family_name"] = parts[-1].strip()
                    components["middle_name"] = " ".join(parts[1:-1]).strip()
            else:
                # Single name
                components["family_name"] = name.strip()
                components["given_name"] = ""

        return components
