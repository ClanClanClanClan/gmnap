"""
Sinhala (D5) regional processor.

Implements Sri Lankan name handling for Sinhala and Tamil communities,
with colonial Portuguese/Dutch/British influences and Buddhist naming patterns.
Features: Sinhala script, Tamil coordination, initial patterns, Ge names.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional
from ...base_enhanced import EnhancedRegionSpec as RegionSpec, RegionRuleError


class D5_Sinhala(RegionSpec):
    """Handler for D5 - Sinhala (Sri Lanka)."""

    def __init__(self):
        super().__init__(
            code="D5",
            yaml_files=["d5_sinhala.yaml"],
            scripts=["Sinhala", "Tamil", "Latin"],
            mixed_scripts=True,
            canonical_order="Given Family",
            romanisation_standards=["ISO 15919"],
        )

        # Sinhala Unicode range (U+0D80-U+0DFF)
        self.sinhala_range = (0x0D80, 0x0DFF)

        # Tamil Unicode range (U+0B80-U+0BFF) - coordinate with D2
        self.tamil_range = (0x0B80, 0x0BFF)

        # Common Sinhala surnames
        self.sinhala_surnames = {
            # Portuguese origin
            "perera",
            "fernando",
            "silva",
            "de silva",
            "de alwis",
            "de mel",
            "de costa",
            "de zoysa",
            "rodrigo",
            "mendis",
            "almeida",
            # Sinhala origin
            "jayawardena",
            "wickremasinghe",
            "senanayake",
            "dissanayake",
            "gunasekara",
            "rajapaksa",
            "kumaratunga",
            "bandaranaike",
            "ekanayake",
            "tennakoon",
            "herath",
            "munasinghe",
            "wijesinghe",
            "samaraweera",
            "jayasuriya",
            "ranatunga",
            "karunaratne",
            # Dutch/Burgher origin
            "ondaatje",
            "bartholomeusz",
            "peiris",
            "van dort",
            "de kretser",
            "jansz",
            "kelaart",
            "schokman",
        }

        # Common Tamil surnames (Sri Lankan specific)
        self.tamil_surnames = {
            "selvarajah",
            "sivarajah",
            "rajaratnam",
            "balasubramaniam",
            "kadirgamar",
            "ponnambalam",
            "navaratnam",
            "kanagasabai",
            "thambiah",
            "coomaraswamy",
            "arulanantham",
            "sinnathamby",
        }

        # Ge names (house/ancestral names)
        self.ge_names = {
            "waduge",
            "appuhamilage",
            "mudiyanselage",
            "rajakaruna",
            "heenkenda",
            "liyanage",
            "pathiranage",
            "vidanage",
            "gamaralalage",
            "nanayakkarage",
            "wijewardene",
            "ranasinghege",
        }

        # Buddhist monastic titles
        self.buddhist_titles = {
            "ven.",
            "venerable",
            "bhikkhu",
            "thero",
            "hamuduruwo",
            "අතිපූජ්‍ය",
            "පූජ්‍ය",
            "භික්ෂු",
            "හාමුදුරුවෝ",
        }

        # Academic and professional titles
        self.titles = {
            # Academic
            "prof",
            "prof.",
            "professor",
            "dr",
            "dr.",
            "doctor",
            "eng",
            "eng.",
            # Sri Lankan honorifics
            "deshamanya",
            "deshabandu",
            "vidya jyothi",
            "kala keerthi",
            # Standard
            "mr",
            "mr.",
            "mrs",
            "mrs.",
            "miss",
            "ms",
            "ms.",
            # Sinhala titles
            "මහතා",
            "මහත්මිය",
            "මෙනවිය",
        }

        # Common Sinhala given names
        self.sinhala_given_names = {
            # Male
            "mahinda",
            "ranil",
            "gotabaya",
            "maithripala",
            "sajith",
            "chandana",
            "namal",
            "basil",
            "chamal",
            "dinesh",
            "prasanna",
            "nimal",
            "sunil",
            "gamini",
            "lalith",
            "upul",
            "rohan",
            # Female
            "chandrika",
            "rosy",
            "sirimavo",
            "kusum",
            "malini",
            "sriyani",
            "kamani",
            "damayanthi",
            "pushpa",
            "nanda",
            "soma",
            "wimala",
        }

        # Initial pattern components
        self.common_initials = {
            # Ge name initials
            "w": "waduge",
            "a": "appuhamilage",
            "m": "mudiyanselage",
            "r": "rajakaruna",
            "h": "heenkenda",
            "l": "liyanage",
            # Colonial name initials
            "d": "don/de",
            "j": "james/john",
            "p": "peter/perera",
            "s": "silva/solomon",
            "f": "fernando/francis",
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

                # Explicit carriage return check (CR is always dangerous)
                #                 if '\r' in raw_input:
                #                     raise RegionRuleError(f"Carriage return in {field}: {raw_input[:50]}...")

                # Normalize tabs and newlines (V7 edge case) BEFORE security check
                if "\t" in raw_input:
                    raw_input = raw_input.replace("\t", " ")
                    entry[field] = raw_input
                if "\n" in raw_input:
                    raw_input = raw_input.replace("\n", " ")
                if "\r" in raw_input:
                    raw_input = raw_input.replace("\r", " ")
                    entry[field] = raw_input
                    entry[field] = raw_input

                if self.has_security_risks_lenient(raw_input):
                    raise RegionRuleError(
                        f"Name contains dangerous characters: {raw_input[:50]}..."
                    )

        # More flexible: try to get any available name
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # Don't fail - just skip cleaning if no name available
            return

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
        """Clean a single Sri Lankan name string."""
        if not name:
            return name

        # Remove titles (including Buddhist titles)
        name = self._remove_titles(name)

        # Preserve initial dots pattern
        name = self._normalize_initials(name)

        # Normalize particles (De, Van, etc.)
        name = self._normalize_particles(name)

        # Normalize punctuation
        name = re.sub(r"\s*,\s*", ", ", name)

        # Normalize whitespace using base class method
        name = self.normalize_whitespace_characters(name)

        return name.strip()

    def _remove_titles(self, text: str) -> str:
        """Remove Sri Lankan titles from text."""
        if not text:
            return text

        words = text.split()
        cleaned = []

        for word in words:
            word_lower = word.lower().rstrip(".,")
            # Check against all title sets
            if (
                word_lower not in self.titles
                and word_lower not in self.buddhist_titles
                and word not in self.titles  # Check original case too
                and word not in self.buddhist_titles
            ):
                cleaned.append(word)

        return " ".join(cleaned)

    def _normalize_initials(self, name: str) -> str:
        """Normalize Sri Lankan initial patterns (W.D., S.W.R.D., etc.)."""
        # Pattern for initials: single letter followed by dot
        # Preserve the specific spacing and dot patterns
        initial_pattern = r"\b([A-Z])\.(?=[A-Z]\.|\s)"

        # Ensure consistent spacing after dots
        name = re.sub(initial_pattern + r"\s*", r"\1. ", name)

        # Remove extra spaces between initials
        name = re.sub(r"([A-Z]\.) +([A-Z]\.)", r"\1\2", name)

        return name

    def _normalize_particles(self, name: str) -> str:
        """Normalize colonial particles (De, Van, etc.)."""
        # Portuguese particles
        name = re.sub(r"\bde\s+([A-Z])", r"De \1", name, flags=re.IGNORECASE)
        name = re.sub(r"\bda\s+([A-Z])", r"Da \1", name, flags=re.IGNORECASE)

        # Dutch particles
        name = re.sub(r"\bvan\s+([A-Z])", r"Van \1", name, flags=re.IGNORECASE)
        name = re.sub(r"\bvon\s+([A-Z])", r"Von \1", name, flags=re.IGNORECASE)

        return name

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with D5-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Extract components
        components = self._extract_components(canonical)

        # Detect scripts
        script_info = self._detect_scripts(entry)
        if script_info:
            components.update(script_info)

        # Analyze initial patterns
        initial_info = self._analyze_initials(canonical)
        if initial_info:
            components.update(initial_info)

        # Detect ethnic/linguistic community
        community = self._detect_community(canonical)
        if community:
            components["sri_lankan_community"] = community

        # Analyze Ge names
        ge_name_info = self._analyze_ge_names(canonical)
        if ge_name_info:
            components.update(ge_name_info)

        # Colonial influence detection
        colonial_info = self._detect_colonial_influence(canonical)
        if colonial_info:
            components["colonial_influence"] = colonial_info

        # Buddhist naming detection
        if self._has_buddhist_elements(canonical):
            components["buddhist_naming"] = True

        # Add to RegionalExtras
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"].update(components)

        # Generate variants
        if "Variants" not in entry:
            entry["Variants"] = {"Observed": [], "Synthesised": []}
        if "Synthesised" not in entry["Variants"]:
            entry["Variants"]["Synthesised"] = []

        # Generate initial expansion variants
        if initial_info and initial_info.get("has_initials"):
            expanded_variants = self._generate_expanded_initial_variants(
                canonical, initial_info
            )
            for variant in expanded_variants:
                if variant != canonical:
                    entry["Variants"]["Synthesised"].append(
                        {"str": variant, "type": "initial-expansion"}
                    )

        # Generate order swap variant
        if components.get("family_name") and components.get("given_name"):
            family_given = f"{components['family_name']}, {components['given_name']}"
            if family_given != canonical:
                entry["Variants"]["Synthesised"].append(
                    {"str": family_given, "type": "order-swap"}
                )

    def _detect_scripts(self, entry: Dict[str, Any]) -> Dict[str, bool]:
        """Detect which scripts are used in the entry."""
        script_info = {}

        # Check CanonicalNative for Sinhala/Tamil scripts
        native = entry.get("CanonicalNative", "")
        if native:
            has_sinhala = any(
                ord(c) in range(self.sinhala_range[0], self.sinhala_range[1] + 1)
                for c in native
            )
            has_tamil = any(
                ord(c) in range(self.tamil_range[0], self.tamil_range[1] + 1)
                for c in native
            )

            if has_sinhala:
                script_info["sinhala_script_detected"] = True
            if has_tamil:
                script_info["tamil_script_detected"] = True

        return script_info

    def _analyze_initials(self, name: str) -> Optional[Dict[str, Any]]:
        """Analyze Sri Lankan initial patterns (W.D., S.W.R.D., etc.)."""
        # Pattern for detecting initials
        initial_pattern = r"^((?:[A-Z]\.)+)\s*(.+)$"
        match = re.match(initial_pattern, name)

        if match:
            initials = match.group(1)
            rest_of_name = match.group(2)

            # Count number of initials
            initial_count = initials.count(".")

            return {
                "has_initials": True,
                "initials": initials,
                "initial_count": initial_count,
                "main_name": rest_of_name,
                "possible_ge_name_initials": initial_count
                >= 2,  # Multiple initials often include Ge names
            }

        return None

    def _detect_community(self, name: str) -> Optional[str]:
        """Detect likely ethnic/linguistic community."""
        name_lower = name.lower()

        # Check surnames
        family_name = self._extract_family_name(name)
        if family_name:
            family_lower = family_name.lower()

            if family_lower in self.sinhala_surnames:
                # Further classify by origin
                if family_lower in [
                    "perera",
                    "fernando",
                    "silva",
                    "de silva",
                    "de mel",
                    "de alwis",
                ]:
                    return "sinhala_portuguese"
                elif family_lower in [
                    "ondaatje",
                    "bartholomeusz",
                    "van dort",
                    "de kretser",
                ]:
                    return "burgher"
                else:
                    return "sinhala"

            elif family_lower in self.tamil_surnames:
                return "sri_lankan_tamil"

        # Check given names
        given_parts = name_lower.split()[0] if name_lower else ""
        if given_parts in self.sinhala_given_names:
            return "sinhala"

        # Default based on patterns
        if any(name_lower.endswith(suffix) for suffix in ["rajah", "ratnam", "swamy"]):
            return "tamil"

        return None

    def _analyze_ge_names(self, name: str) -> Optional[Dict[str, Any]]:
        """Analyze Ge names (house/ancestral names)."""
        name_lower = name.lower()

        # Check for full Ge names
        for ge_name in self.ge_names:
            if ge_name in name_lower:
                return {"has_ge_name": True, "ge_name": ge_name, "ge_name_type": "full"}

        # Check if initials might represent Ge names
        initial_info = self._analyze_initials(name)
        if initial_info and initial_info.get("possible_ge_name_initials"):
            return {
                "has_ge_name": True,
                "ge_name_type": "abbreviated",
                "ge_name_in_initials": True,
            }

        return None

    def _detect_colonial_influence(self, name: str) -> Optional[str]:
        """Detect colonial influences in naming."""
        name_lower = name.lower()

        # Portuguese influence
        if any(
            part in name_lower for part in ["de ", "da ", "fernando", "perera", "silva"]
        ):
            return "portuguese"

        # Dutch influence
        if any(part in name_lower for part in ["van ", "von ", "ondaatje", "kelaart"]):
            return "dutch"

        # British influence (harder to detect, often in structure)
        if re.search(r"\b[A-Z]\.[A-Z]\.[A-Z]\.", name):  # Multiple initials
            return "british_administrative"

        return None

    def _has_buddhist_elements(self, name: str) -> bool:
        """Check for Buddhist naming elements."""
        name_lower = name.lower()

        # Check for monastic titles
        for title in self.buddhist_titles:
            pass
        # Check for Buddhist name elements
        buddhist_elements = ["dhamma", "dharma", "bodhi", "ratna", "siri", "ananda"]
        return any(element in name_lower for element in buddhist_elements)

    def _generate_expanded_initial_variants(
        self, name: str, initial_info: Dict[str, Any]
    ) -> List[str]:
        """Generate variants with expanded initials."""
        variants = []

        if not initial_info or not initial_info.get("has_initials"):
            return variants

        initials = initial_info["initials"]
        main_name = initial_info["main_name"]

        # For now, just generate a variant without the initials
        # In a full implementation, we might expand based on common patterns
        variants.append(main_name)

        # If it looks like W.D. pattern, might be Waduge Don
        if initials == "W.D.":
            variants.append(f"Waduge Don {main_name}")
        elif initials == "J.R.":
            variants.append(f"Junius Richard {main_name}")
        elif initials == "S.W.R.D.":
            variants.append(f"Solomon West Ridgeway Dias {main_name}")

        return variants

    def validate(self, entry: Dict[str, Any]) -> None:
        """Apply V7 security validation with DoS protection."""
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # No name to validate - that's OK, just skip
            return

        # SECURITY: Check for dangerous characters first
        if self.has_security_risks_lenient(canonical):
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
        """Generate sort key for D5 names."""
        canonical = entry.get("CanonicalLatin", "")

        # Extract family name for sorting
        family = self._extract_family_name(canonical)

        if not family:
            # If no clear family name, use whole name
            family = canonical

        # Normalize for sorting
        family_normalized = unicodedata.normalize("NFD", family.lower())

        # Remove diacritics
        family_clean = "".join(
            char for char in family_normalized if unicodedata.category(char) != "Mn"
        )

        # Handle particles specially for sorting
        # "De Silva" should sort under "S" not "D"
        if family_clean.startswith("de "):
            family_clean = family_clean[3:]
        elif family_clean.startswith("van "):
            family_clean = family_clean[4:]

        return family_clean

    def _extract_family_name(self, name: str) -> Optional[str]:
        """Extract family name from full name."""
        if ", " in name:
            return name.split(", ")[0]

        # Skip initials
        name_parts = name.split()
        non_initial_parts = [p for p in name_parts if not p.endswith(".")]

        if non_initial_parts:
            # Last non-initial part is likely family name
            return non_initial_parts[-1]

        return None

    # Removed _has_security_risks method - using base class has_security_risks_lenient instead
    def _extract_components(self, name: str) -> Dict[str, Any]:
        """Extract name components for Sri Lankan names."""
        components = {}

        # Handle initials first
        initial_match = re.match(r"^((?:[A-Z]\.)+)\s*(.+)$", name)
        if initial_match:
            components["initials"] = initial_match.group(1)
            rest = initial_match.group(2)
        else:
            rest = name

        if ", " in rest:
            # Comma format: "Family, Given"
            parts = rest.split(", ", 1)
            components["family_name"] = parts[0].strip()
            components["given_name"] = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Space-separated
            parts = rest.split()
            if len(parts) >= 2:
                # Check for particles
                if len(parts) >= 3 and parts[-2].lower() in ["de", "van", "da"]:
                    # Family name includes particle
                    components["family_name"] = f"{parts[-2]} {parts[-1]}"
                    components["given_name"] = " ".join(parts[:-2])
                else:
                    components["family_name"] = parts[-1]
                    components["given_name"] = " ".join(parts[:-1])
            else:
                components["family_name"] = rest.strip()
                components["given_name"] = ""

        return components
