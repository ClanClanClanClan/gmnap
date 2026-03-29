"""
Georgian (C8) regional processor.

Implements Georgian (Kartvelian) name handling with Mkhedruli script support,
patronymic suffixes (-shvili/-dze), and regional naming patterns.
Features: Georgian script detection, patronymic analysis, regional classification.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional
from ...base_enhanced import EnhancedRegionSpec as RegionSpec


class C8_Georgian(RegionSpec):
    """Handler for C8 - Georgian."""

    def __init__(self):
        super().__init__(
            code="C8",
            yaml_files=["c8_georgian.yaml"],
            scripts=["Georgian", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["National System 2002", "ISO 9984"],
        )

        # Georgian Unicode range (U+10A0-U+10FF)
        self.georgian_range = (0x10A0, 0x10FF)

        # Georgian patronymic and regional suffixes
        self.georgian_suffixes = {
            # Patronymic suffixes
            "-შვილი": {"latin": "-shvili", "meaning": "child of", "type": "patronymic"},
            "-ძე": {"latin": "-dze", "meaning": "son of", "type": "patronymic"},
            "-ია": {"latin": "-ia", "meaning": "of/from", "type": "patronymic"},
            "-ური": {"latin": "-uri", "meaning": "from", "type": "regional"},
            "-ელი": {"latin": "-eli", "meaning": "from (place)", "type": "regional"},
            # Regional suffixes
            "-უა": {"latin": "-ua", "meaning": "Mingrelian", "type": "regional"},
            "-ავა": {"latin": "-ava", "meaning": "Svan", "type": "regional"},
            "-ში": {"latin": "-shi", "meaning": "Laz", "type": "regional"},
            "-ანი": {"latin": "-ani", "meaning": "Kartlian", "type": "regional"},
        }

        # Latin versions of suffixes
        self.latin_suffixes = {
            "-shvili": {"georgian": "-შვილი", "meaning": "child of", "type": "patronymic"},
            "-dze": {"georgian": "-ძე", "meaning": "son of", "type": "patronymic"},
            "-adze": {"georgian": "-აძე", "meaning": "son of", "type": "patronymic"},  # variant
            "-ia": {"georgian": "-ია", "meaning": "of/from", "type": "patronymic"},
            "-uri": {"georgian": "-ური", "meaning": "from", "type": "regional"},
            "-eli": {"georgian": "-ელი", "meaning": "from (place)", "type": "regional"},
            "-ua": {"georgian": "-უა", "meaning": "Mingrelian", "type": "regional"},
            "-ava": {"georgian": "-ავა", "meaning": "Svan", "type": "regional"},
            "-shi": {"georgian": "-ში", "meaning": "Laz", "type": "regional"},
            "-ani": {"georgian": "-ანი", "meaning": "Kartlian", "type": "regional"},
        }

        # Common Georgian given names
        self.georgian_given_names = {
            # Male names
            "giorgi",
            "davit",
            "david",
            "levan",
            "zaza",
            "gela",
            "vakhtang",
            "nikoloz",
            "ioane",
            "pavle",
            "erekle",
            "teimuraz",
            "mikheil",
            "alexandre",
            "akaki",
            "shota",
            "ilia",
            "zurab",
            "mamuka",
            "givi",
            # Female names
            "tamar",
            "nino",
            "mariam",
            "marina",
            "ketevan",
            "rusudan",
            "elene",
            "ia",
            "vardo",
            "gulnara",
            "lali",
            "maia",
            "natia",
            "salome",
            "ana",
            "ekaterine",
            "sofio",
            "nato",
            "lika",
            "eka",
        }

        # Georgian alphabet for script detection
        self.georgian_alphabet = set(chr(i) for i in range(0x10A0, 0x10C5 + 1))

        # Common Georgian surnames (without suffixes)
        self.georgian_surname_roots = {
            "javakh",
            "beri",
            "kaland",
            "gelash",
            "maisur",
            "kvara",
            "gabun",
            "shengel",
            "alaverd",
            "bagrat",
            "arab",
            "kherg",
            "lomi",
            "shevard",
            "chkheidz",
            "tseretl",
            "chikovn",
        }

        # Titles to remove
        self.titles = {
            # Georgian titles
            "ბატონი",
            "ქალბატონი",
            "პროფესორი",
            "დოქტორი",
            # Latin/English titles
            "batoni",
            "qalbatoni",
            "profesori",
            "doqtori",
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
            "professor",
            "doctor",
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
        """Clean a single Georgian name string."""
        if not name:
            return name

        # Remove titles
        name = self._remove_titles(name)

        # Normalize Unicode
        name = unicodedata.normalize("NFC", name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        # Normalize whitespace
        name = re.sub(r"\s+", " ", name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove Georgian titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            # Remove periods and check against titles
            clean_word = word.rstrip(".,").lower()
            # Check both Latin and Georgian titles
            if clean_word not in self.titles and word not in self.titles:
                cleaned.append(word)

        return " ".join(cleaned)

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with C8-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Detect Georgian script usage
        if "CanonicalNative" in entry and entry["CanonicalNative"]:
            georgian_detected = self._detect_georgian_script(entry["CanonicalNative"])
            components["georgian_script_detected"] = georgian_detected

        # Analyze Georgian suffixes
        suffix_info = self._analyze_georgian_suffix(canonical)
        if suffix_info:
            components.update(suffix_info)

            # Set family name type
            if suffix_info["suffix_type"] == "patronymic":
                entry["FamilyNameType"] = "patronymic"
            elif suffix_info["suffix_type"] == "regional":
                entry["FamilyNameType"] = "toponymic"

        # Georgian given name detection
        given_name_info = self._analyze_georgian_given_name(canonical)
        if given_name_info:
            components.update(given_name_info)

        # Regional classification
        regional_info = self._classify_georgian_region(canonical, suffix_info)
        if regional_info:
            components["georgian_region"] = regional_info

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate suffix variants
        if suffix_info:
            variants = self._generate_georgian_suffix_variants(canonical, suffix_info)
            for variant in variants:
                if variant != canonical:
                    entry["Variants"]["Synthesised"].append(
                        {"str": variant, "type": "georgian-suffix-variant"}
                    )

        # Generate order swap variant
        if components.get("family_name") and components.get("given_name"):
            family_given = f"{components['family_name']}, {components['given_name']}"
            if family_given != canonical:
                entry["Variants"]["Synthesised"].append({"str": family_given, "type": "order-swap"})

    def _detect_georgian_script(self, text: str) -> bool:
        """Detect if text contains Georgian script characters."""
        for char in text:
            if ord(char) in range(self.georgian_range[0], self.georgian_range[1] + 1):
                return True
        return False

    def _analyze_georgian_suffix(self, name: str) -> Optional[Dict[str, Any]]:
        """Analyze Georgian patronymic and regional suffixes."""
        name_lower = name.lower()

        # Check Latin suffixes first (more common in international contexts)
        for suffix, info in self.latin_suffixes.items():
            if name_lower.endswith(suffix):
                # Extract root name
                root = name[: -len(suffix)]

                # Validate root (should have meaningful content)
                if len(root) >= 3:
                    return {
                        "georgian_suffix": suffix,
                        "georgian_suffix_georgian": info["georgian"],
                        "georgian_suffix_meaning": info["meaning"],
                        "suffix_type": info["type"],
                        "surname_root": root,
                        "is_georgian_surname": True,
                    }

        # Check Georgian script suffixes if present
        for suffix, info in self.georgian_suffixes.items():
            if name.endswith(suffix):
                root = name[: -len(suffix)]

                if len(root) >= 3:
                    return {
                        "georgian_suffix": suffix,
                        "georgian_suffix_latin": info["latin"],
                        "georgian_suffix_meaning": info["meaning"],
                        "suffix_type": info["type"],
                        "surname_root": root,
                        "is_georgian_surname": True,
                    }

        return None

    def _analyze_georgian_given_name(self, name: str) -> Optional[Dict[str, str]]:
        """Analyze if given name is Georgian."""
        # Extract potential given name
        if ", " in name:
            parts = name.split(", ", 1)
            given_part = parts[1] if len(parts) > 1 else ""
        else:
            parts = name.split(None, 1)
            given_part = parts[0] if parts else ""

        given_lower = given_part.lower()

        # Direct match
        if given_lower in self.georgian_given_names:
            return {"georgian_given_name": given_part, "georgian_given_name_verified": True}

        # Check for variants (e.g., Giorgi/George)
        if given_lower == "george" and "giorgi" in self.georgian_given_names:
            return {
                "georgian_given_name": given_part,
                "georgian_given_name_verified": True,
                "georgian_given_name_native": "Giorgi",
            }

        # Check surname roots in given position (sometimes happens)
        for root in self.georgian_surname_roots:
            if given_lower.startswith(root):
                return {
                    "georgian_given_name": given_part,
                    "georgian_given_name_verified": False,
                    "possible_surname_as_given": True,
                }

        return None

    def _classify_georgian_region(
        self, name: str, suffix_info: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Classify Georgian regional origin based on suffix."""
        if not suffix_info:
            return None

        suffix = suffix_info.get("georgian_suffix", "").lower()

        # Regional classifications
        regional_map = {
            "-ua": "Mingrelia",
            "-ava": "Svaneti",
            "-shi": "Lazeti",
            "-ani": "Kartli",
            "-uri": "Kakheti",
            "-eli": "Regional",  # Generic regional
        }

        return regional_map.get(suffix)

    def _generate_georgian_suffix_variants(
        self, name: str, suffix_info: Dict[str, Any]
    ) -> List[str]:
        """Generate Georgian name variants with different suffixes."""
        variants = []

        if not suffix_info:
            return variants

        root = suffix_info.get("surname_root", "")
        current_suffix = suffix_info.get("georgian_suffix", "")
        suffix_type = suffix_info.get("suffix_type", "")

        # Only generate variants for patronymic suffixes
        if suffix_type == "patronymic" and root:
            # Common patronymic alternatives
            if current_suffix in ["-shvili", "-შვილი"]:
                variants.append(root + "-dze")  # Alternative patronymic
                variants.append(root + "dze")  # Without hyphen
            elif current_suffix in ["-dze", "-ძე"]:
                variants.append(root + "-shvili")  # Alternative patronymic
                variants.append(root + "shvili")  # Without hyphen
            elif current_suffix in ["-ia", "-ია"]:
                variants.append(root + "-shvili")
                variants.append(root + "-dze")

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
        """Generate sort key for C8 names."""
        canonical = entry.get("CanonicalLatin", "")

        # Extract family name for sorting
        if ", " in canonical:
            family = canonical.split(", ")[0]
        else:
            # Space-separated - last part is family
            parts = canonical.split()
            if len(parts) >= 2:
                family = parts[-1]
            else:
                family = canonical

        # Normalize for sorting
        family_normalized = unicodedata.normalize("NFD", family.lower())

        # Remove diacritics for consistent sorting
        family_clean = "".join(
            char for char in family_normalized if unicodedata.category(char) != "Mn"
        )

        return family_clean

    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components for Georgian names."""
        components = {}

        if ", " in name:
            # Comma format: "Family, Given"
            parts = name.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated: "Given Family" or "Given Middle Family"
            parts = name.split()
            if len(parts) >= 2:
                # Check if last part has Georgian suffix
                last_part = parts[-1]
                has_suffix = False

                for suffix in list(self.latin_suffixes.keys()) + list(
                    self.georgian_suffixes.keys()
                ):
                    if last_part.lower().endswith(suffix) or last_part.endswith(suffix):
                        has_suffix = True
                        break

                if has_suffix:
                    # Last part is family name with suffix
                    components["family_name"] = last_part
                    components["given_name"] = parts[0]
                    if len(parts) > 2:
                        components["middle_name"] = " ".join(parts[1:-1])
                else:
                    # Standard Given Family
                    components["given_name"] = parts[0]
                    components["family_name"] = parts[-1]
                    if len(parts) > 2:
                        components["middle_name"] = " ".join(parts[1:-1])
            else:
                # Single name
                components["family_name"] = name.strip()
                components["given_name"] = ""

        return components
