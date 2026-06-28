"""
A2 - Western Europe region implementation.

Covers: France, Germany, Italy, Spain, Portugal, Netherlands, Belgium,
Switzerland, Austria, Luxembourg, Liechtenstein, San Marino, Monaco,
Gibraltar, Andorra, Malta, Vatican City.

Features: Latin script with diacritics, Iberian dual surnames,
de/von/van particles, diverse naming conventions.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Set

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


class A2_WesternEurope(RegionSpec):
    """
    Western Europe region (A2).

    Handles Western European naming conventions including:
    - Latin script with diacritics (á, é, í, ó, ú, ñ, ç, etc.)
    - Iberian dual surnames (paternal + maternal)
    - Germanic particles (de, von, van, der, den, etc.)
    - French particles (de, du, des, le, la, etc.)
    - Italian particles (di, da, del, della, etc.)
    - Portuguese/Spanish compound names
    """

    def __init__(self):
        super().__init__(
            code="A2",
            yaml_files=["a2_western_europe.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Family, Given",
            romanisation_standards=["Latin script with diacritics"],
        )

        # Germanic particles
        self.germanic_particles = {
            "von",
            "van",
            "der",
            "den",
            "de",
            "het",
            "ten",
            "ter",
            "te",
            "zum",
            "zur",
            "am",
            "im",
            "zu",
            "auf",
            "unter",
        }

        # Romance particles
        self.romance_particles = {
            "de",
            "del",
            "della",
            "delle",
            "dello",
            "di",
            "da",
            "dal",
            "dalla",
            "du",
            "des",
            "le",
            "la",
            "les",
            "dos",
            "das",
            "do",
            "da",
        }

        # All particles combined
        self.particles = self.germanic_particles | self.romance_particles

        # ---- YAML override extension point: config/regions/a2.yaml ----
        # Lets linguists/ops extend the particle sets without touching
        # Python. RegionSpec.load_yaml_config() returns a SHARED cached
        # dict, so we only READ from it (never mutate), merge any provided
        # particles into the hardcoded defaults, and recompute. Missing
        # file -> {} -> defaults unchanged. This is the first processor to
        # actually consume the (previously dormant) YAML override loader.
        _cfg = self.load_yaml_config()
        if _cfg:
            for _p in _cfg.get("germanic_particles") or []:
                if isinstance(_p, str) and _p.strip():
                    self.germanic_particles.add(_p.strip().lower())
            for _p in _cfg.get("romance_particles") or []:
                if isinstance(_p, str) and _p.strip():
                    self.romance_particles.add(_p.strip().lower())
            self.particles = self.germanic_particles | self.romance_particles

        # Common Western European name patterns
        self.name_patterns = {
            "spanish_dual": re.compile(
                r"^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)(?:\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+))?$"
            ),
            "portuguese_compound": re.compile(
                r"^([A-ZÁÉÍÓÚÀÂÃÇÊÑ][a-záéíóúàâãçêñ]+(?:\s+[a-záéíóúàâãçê]+)*)\s+([A-ZÁÉÍÓÚÀÂÃÇÊÑ][a-záéíóúàâãçêñ]+)(?:\s+([A-ZÁÉÍÓÚÀÂÃÇÊÑ][a-záéíóúàâãçêñ]+))?$"
            ),
            "french_particle": re.compile(
                r"^([A-ZÁÉÈÊËÍÎÏÓÔÖÚÙÛÜŸÑÇ][a-záéèêëíîïóôöúùûüÿñç]+)\s+(de|du|des|le|la|les)\s+([A-ZÁÉÈÊËÍÎÏÓÔÖÚÙÛÜŸÑÇ][a-záéèêëíîïóôöúùûüÿñç]+)$"
            ),
            "german_particle": re.compile(
                r"^([A-ZÄÖÜß][a-zäöüß]+)\s+(von|van|der|den|de|het|ten|ter|te|zum|zur|am|im|zu|auf|unter)\s+([A-ZÄÖÜß][a-zäöüß]+)$"
            ),
            "italian_particle": re.compile(
                r"^([A-ZÁÉÍÓÚ][a-záéíóú]+)\s+(di|da|del|della|delle|dello|dal|dalla)\s+([A-ZÁÉÍÓÚ][a-záéíóú]+)$"
            ),
        }

        # Diacritic patterns for validation (including Hungarian ő, ű)
        self.diacritic_chars = set(
            "áàâäéèêëíìîïóòôöúùûüñçåæøőűÁÀÂÄÉÈÊËÍÌÎÏÓÒÔÖÚÙÛÜÑÇÅÆØŐŰ"
        )

        # Country-specific validation patterns
        self.country_patterns = {
            "ES": {"required_chars": "ñáéíóúü", "dual_surname": True},
            "PT": {"required_chars": "ãàâáçéêíóôõúü", "dual_surname": True},
            "FR": {
                "required_chars": "àâäéèêëïîôöùûüÿç",
                "particles": {"de", "du", "des", "le", "la", "les"},
            },
            "DE": {
                "required_chars": "äöüß",
                "particles": {
                    "von",
                    "van",
                    "der",
                    "den",
                    "de",
                    "zum",
                    "zur",
                    "am",
                    "im",
                    "zu",
                },
            },
            "IT": {
                "required_chars": "àáéèíìîóòúù",
                "particles": {"di", "da", "del", "della", "delle", "dello"},
            },
            "NL": {
                "required_chars": "áéíóúàèëïöü",
                "particles": {"van", "der", "den", "de", "het", "ten", "ter", "te"},
            },
        }

    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean Western European names according to regional conventions.

        - Remove titles and honorifics
        - Normalize diacritics and spacing
        - Handle particles correctly
        - Preserve dual surnames where appropriate
        """
        # SECURITY: Validate input before processing

        self.apply_security_and_validation_checks(entry)

        # SECURITY: Check for dangerous characters BEFORE normalization
        for field in ["CanonicalLatin", "CanonicalNative"]:
            if field in entry and entry[field]:
                value = entry[field]
                for char in value:
                    char_code = ord(char)
                    # Block ALL control characters including tab, LF, CR
                    if char_code < 32:
                        if char_code == 9:
                            # Normalize tab to space (V7 edge case requirement)
                            value = value.replace("\t", " ")
                            entry[field] = value
                            continue  # Skip to next char
                        elif char_code == 10:
                            # Normalize newline to space (V7 edge case)
                            value = value.replace("\n", " ")
                            entry[field] = value
                            continue  # Skip to next char
                        elif char_code == 13:
                            raise RegionRuleError(f"Carriage return in {field}")
                        else:
                            raise RegionRuleError(
                                f"Control character in {field}: U+{char_code:04X}"
                            )
                    if char_code == 127:  # DEL
                        raise RegionRuleError(f"DELETE character in {field}")
                    if char_code in [0x200B, 0x200C, 0x200D, 0xFEFF]:  # Zero-width
                        raise RegionRuleError(
                            f"Zero-width character in {field}: U+{char_code:04X}"
                        )

        # Get canonical name for processing
        canonical = self.get_canonical_name(entry)
        if not canonical:
            # Don't fail - just skip cleaning if no name available
            return

        # Rule 17: Iberian Honorific Strip – Dr., D., Dª removed
        # Remove common titles and honorifics including Iberian patterns
        titles_pattern = re.compile(
            r"\b(Dr\.?|Prof\.?|Sir|Dame|Lord|Lady|Baron|Count|Comte|Duc|Herzog|Fürst|Don|Doña|Dom|Dona|D\.?|Dª\.?|Dña\.?)\s+",
            re.IGNORECASE,
        )
        cleaned = titles_pattern.sub("", canonical)

        # Remove degrees and suffixes
        degrees_pattern = re.compile(
            r"\s+\b(Ph\.?D\.?|M\.?D\.?|Jr\.?|Sr\.?|III?|IV|V)\b", re.IGNORECASE
        )
        cleaned = degrees_pattern.sub("", cleaned)

        # Normalize Unicode (NFC form for consistent diacritics)
        cleaned = unicodedata.normalize("NFC", cleaned)

        # Clean up spacing around particles
        for particle in self.particles:
            # Fix spacing around particles
            pattern = re.compile(rf"\s+\b{re.escape(particle)}\s+", re.IGNORECASE)
            cleaned = pattern.sub(f" {particle} ", cleaned)

        # Normalize tabs and other whitespace characters to regular spaces
        cleaned = self.normalize_whitespace_characters(cleaned)

        # Update whichever field we got the name from
        if "CanonicalLatin" in entry and entry.get("CanonicalLatin"):
            entry["CanonicalLatin"] = cleaned
        elif "CanonicalNative" in entry and entry.get("CanonicalNative"):
            entry["CanonicalNative"] = cleaned

        # Call base class clean AFTER our custom processing
        # This ensures consistency and proper caching
        super().clean(entry)

    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment Western European names with regional variants and metadata.

        - Generate ASCII variants without diacritics
        - Extract particles and handle them properly
        - Create order variants for dual surnames
        - Add country-specific variants
        """
        # Use get_canonical_name for more flexible handling
        # Ensure idempotency
        super().augment(entry)

        canonical = self.get_canonical_name(entry)
        if not canonical:
            # No name to augment - that's OK, skip
            return

        # Initialize variants if not present
        if "VariantsSynthesised" not in entry:
            entry["VariantsSynthesised"] = []

        variants = entry["VariantsSynthesised"]

        # Generate ASCII variant (diacritic removal)
        ascii_variant = self._remove_diacritics(canonical)
        if ascii_variant != canonical:
            variants.append({"str": ascii_variant, "type": "ascii-lossy"})

        # Rule 33: Capital Sharp-S Handling – German ß/ẞ normalization
        sharp_s_variant = self._apply_sharp_s_normalization(canonical)
        if sharp_s_variant != canonical:
            variants.append({"str": sharp_s_variant, "type": "sharp-s-normalized"})

        # Extract and handle particles
        particles_found = self._extract_particles(canonical)
        if particles_found:
            entry["Particles"] = particles_found

            # Generate particle-drop variant
            no_particles = self._remove_particles(canonical)
            if no_particles != canonical:
                variants.append({"str": no_particles, "type": "particle-drop"})

        # Handle dual surnames (Iberian pattern)
        if self._is_dual_surname_pattern(canonical):
            # Generate single surname variants
            single_surname_variants = self._generate_single_surname_variants(canonical)
            for variant in single_surname_variants:
                variants.append({"str": variant, "type": "order-swap"})

        # Generate order swap (Given Family)
        if ", " in canonical:
            family, given = canonical.split(", ", 1)
            swapped = f"{given} {family}"
            variants.append({"str": swapped, "type": "order-swap"})

        # Add regional metadata
        entry["RegionCode"] = "A2"
        entry["RegionFeatures"] = {
            "has_diacritics": self._has_diacritics(canonical),
            "has_particles": bool(particles_found),
            "is_dual_surname": self._is_dual_surname_pattern(canonical),
            "estimated_country": self._estimate_country(canonical),
        }

    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate Western European names using standardized validation.
        """
        # Apply comprehensive security and validation checks from base class
        # This properly normalizes whitespace BEFORE checking for control chars
        self.apply_security_and_validation_checks(entry)

        # A2-specific validation can be added here as needed
        canonical = self.get_canonical_name(entry)
        if not canonical:
            return

        # Validate character set - secure but supports international names
        if not self._has_valid_western_european_characters(canonical):
            invalid_chars = self._get_invalid_characters(canonical)
            # Only warn for borderline international characters, fail for clearly invalid ones
            if invalid_chars:
                dangerous_chars = {
                    c
                    for c in invalid_chars
                    if ord(c) < 32 or ord(c) > 126 and ord(c) not in range(160, 591)
                }
                if dangerous_chars:
                    raise RegionRuleError(
                        f"Invalid characters: {', '.join(dangerous_chars)}"
                    )
                else:
                    self.logger.warning(f"Non-European characters in name: {canonical}")

        # Validate particle usage
        particles_in_name = self._extract_particles(canonical)
        for particle in particles_in_name:
            if particle.lower() not in self.particles:
                self.logger.warning(
                    f"Unknown particle '{particle}' in name: {canonical}"
                )

        # Check for consistent diacritic usage
        if self._has_inconsistent_diacritics(canonical):
            self.logger.warning(f"Inconsistent diacritic usage in name: {canonical}")

    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate sort key for Western European names.

        - Sort by family name first
        - Handle particles correctly in sorting
        - Ignore diacritics for sorting purposes
        """
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return ""

        # Extract family and given names
        if ", " in canonical:
            family, given = canonical.split(", ", 1)
        else:
            # Assume last word is family name
            parts = canonical.split()
            if len(parts) >= 2:
                family = parts[-1]
                given = " ".join(parts[:-1])
            else:
                family = canonical
                given = ""

        # Rule 15 & 22: Remove Germanic particles except d' (which is retained per Rule 22)
        family_for_sort = self._remove_particles_for_sorting(family)

        # Rule 33: Apply sharp-s normalization for proper German sorting
        family_for_sort = self._apply_sharp_s_normalization(family_for_sort)
        given_normalized = self._apply_sharp_s_normalization(given)

        # Remove diacritics for consistent sorting
        family_sort = self._remove_diacritics(family_for_sort).upper()
        given_sort = self._remove_diacritics(given_normalized).upper()

        return f"{family_sort}, {given_sort}"

    def _remove_diacritics(self, text: str) -> str:
        """Remove diacritics from text, keeping base letters."""
        # Decompose characters and remove combining marks
        normalized = unicodedata.normalize("NFD", text)
        ascii_text = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
        return ascii_text

    def _extract_particles(self, name: str) -> List[str]:
        """Extract particles from name."""
        words = name.split()
        particles_found = []

        for word in words:
            if word.lower().rstrip(",") in self.particles:
                particles_found.append(word.rstrip(","))

        return particles_found

    def _remove_particles(self, name: str) -> str:
        """
        Rule 15: Remove Germanic particles (von/van/de) but keep d'.

        This implements the V7 linguistic rule for Germanic particles:
        - Drop: von, van, de, der, den, het, ten, ter, te, etc.
        - Keep: d' (French particle with apostrophe)
        """
        words = name.split()
        filtered_words = []

        for word in words:
            word_clean = word.lower().rstrip(",")

            # Rule 15: Keep d' (French particle)
            if word_clean == "d'" or word.startswith("d'"):
                filtered_words.append(word)
            # Remove other particles
            elif word_clean not in self.particles:
                filtered_words.append(word)

        return " ".join(filtered_words)

    def _remove_particles_for_sorting(self, name: str) -> str:
        """
        Rules 15 & 22: Remove particles for sorting, but keep d'.

        Rule 15: Germanic particles (von/van/de) are dropped
        Rule 22: French d' particle is retained in order_key

        This method is specifically for order_key generation.
        """
        words = name.split()
        filtered_words = []

        for word in words:
            word_clean = word.lower().rstrip(",")

            # Rule 22: Always keep d' in order_key
            if word_clean == "d'" or word.lower().startswith("d'"):
                filtered_words.append(word)
            # Rule 15: Remove Germanic particles
            elif word_clean not in self.germanic_particles:
                filtered_words.append(word)

        return " ".join(filtered_words)

    def _has_diacritics(self, text: str) -> bool:
        """Check if text contains diacritical marks."""
        return any(c in self.diacritic_chars for c in text)

    def _is_dual_surname_pattern(self, name: str) -> bool:
        """Check if name follows Iberian dual surname pattern."""
        # Simple heuristic: if in "Family, Given" format and family has 2+ parts
        if ", " in name:
            family, _ = name.split(", ", 1)
            family_parts = family.split()
            return len(family_parts) >= 2
        return False

    def _generate_single_surname_variants(self, name: str) -> List[str]:
        """Generate variants with single surname from dual surname."""
        if ", " not in name:
            return []

        family, given = name.split(", ", 1)
        family_parts = family.split()

        if len(family_parts) < 2:
            return []

        variants = []
        # First surname only
        variants.append(f"{family_parts[0]}, {given}")
        # Last surname only
        variants.append(f"{family_parts[-1]}, {given}")

        return variants

    def _estimate_country(self, name: str) -> Optional[str]:
        """Estimate likely country based on name characteristics."""
        name_lower = name.lower()

        # Spanish indicators
        if any(c in name_lower for c in "ñáéíóúü") and self._is_dual_surname_pattern(
            name
        ):
            return "ES"

        # Portuguese indicators
        if any(
            c in name_lower for c in "ãàâáçéêíóôõúü"
        ) and self._is_dual_surname_pattern(name):
            return "PT"

        # French indicators
        if any(c in name_lower for c in "àâäéèêëïîôöùûüÿç") or any(
            p in name_lower for p in ["de ", "du ", "des ", "le ", "la "]
        ):
            return "FR"

        # German indicators
        if any(c in name_lower for c in "äöüß") or any(
            p in name_lower for p in ["von ", "van ", "der ", "den "]
        ):
            return "DE"

        # Italian indicators
        if any(p in name_lower for p in ["di ", "da ", "del ", "della "]) or any(
            c in name_lower for c in "àáéèíìîóòúù"
        ):
            return "IT"

        # Dutch indicators
        if any(
            p in name_lower
            for p in ["van ", "der ", "den ", "de ", "het ", "ten ", "ter ", "te "]
        ):
            return "NL"

        return None

    def _has_inconsistent_diacritics(self, name: str) -> bool:
        """Check for inconsistent use of diacritics (basic heuristic)."""
        # This is a simple check - could be enhanced with more sophisticated rules
        ascii_version = self._remove_diacritics(name)
        return len(name) != len(ascii_version) and not self._has_diacritics(name)

    def _apply_sharp_s_normalization(self, name: str) -> str:
        """
        Rule 33: Capital Sharp-S Handling – German ß/ẞ normalization.

        German sharp-s (Eszett) has specific capitalization rules:
        - ß (lowercase sharp-s) → ss (double s)
        - ẞ (capital sharp-s, since 2017) → SS (double S)

        This is critical for German surnames like:
        - Weiß → WEISS (not WEIB)
        - Großmann → GROSSMANN
        - Straße → STRASSE

        The rule ensures proper German name handling in all-caps contexts
        and ASCII-compatible variants for international systems.
        """
        if not name:
            return name

        result = name

        # Apply sharp-s normalization using the global Unicode fold method
        result = self.apply_unicode_fold_exceptions(result)

        # Additional German-specific handling for mixed case preservation
        # When we have mixed case names, preserve the case pattern
        if any(c.isupper() for c in name) and any(c.islower() for c in name):
            # Mixed case - handle carefully
            # Replace ß with ss, ẞ with SS, but preserve surrounding case
            words = result.split()
            normalized_words = []

            for word in words:
                # Check if this word had sharp-s characters
                original_word_idx = name.find(
                    word.replace("ss", "ß").replace("SS", "ẞ")
                )
                if original_word_idx >= 0:
                    original_word = name[
                        original_word_idx : original_word_idx + len(word)
                    ]
                    if "ß" in original_word or "ẞ" in original_word:
                        # This word was affected by sharp-s normalization
                        # Ensure proper case handling
                        if word.isupper():
                            # All caps word - already handled correctly
                            normalized_words.append(word)
                        elif word.islower():
                            # All lowercase word - already handled correctly
                            normalized_words.append(word)
                        else:
                            # Mixed case - preserve pattern
                            normalized_words.append(word)
                    else:
                        normalized_words.append(word)
                else:
                    normalized_words.append(word)

            result = " ".join(normalized_words)

        return result

    def apply_unicode_fold_exceptions(self, text: str) -> str:
        """
        Handle Western European fold exceptions WITHOUT lowercasing.

        The base contract for this method is ligature/sharp-s expansion
        only — it is called from ``normalize_unicode_secure`` which runs
        on the display field ``CanonicalLatin``. An unconditional
        ``casefold()`` here would destroy case information ("Euler" →
        "euler") and was caught by the browser-smoke harness.

        Handled:
        - ß (U+00DF) → ss
        - ẞ (U+1E9E) → SS

        Case preservation is retained so downstream display, ordering,
        and comparison logic (which have their own explicit casefold
        calls) still behave correctly.
        """
        if not text:
            return text

        # Sharp-s expansion, case-preserving.
        result = text.replace("ß", "ss").replace("ẞ", "SS")
        return result

    def _has_security_risks(self, name: str) -> bool:
        """Check for dangerous characters that pose security risks."""
        for char in name:
            # Reject dangerous control characters, but allow formatting chars that can be normalized
            char_code = ord(char)
            if char_code < 32 and char_code not in [
                9,
                10,
                13,
            ]:  # Allow \t, \n, \r for normalization
                return True
            if char_code == 127:  # DEL character
                return True
            # Reject other potentially dangerous Unicode ranges
            if char_code in [0xFEFF, 0x200B, 0x200C, 0x200D]:  # Zero-width characters
                return True
        return False

    def _has_valid_western_european_characters(self, name: str) -> bool:
        """Check if name contains only valid Western European characters (secure)."""
        valid_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,-'."
        )
        # Add European diacritics (but be specific, not overly broad)
        valid_chars.update(self.diacritic_chars)

        return all(c in valid_chars for c in name)

    def _get_invalid_characters(self, name: str) -> Set[str]:
        """Get characters that are not in the valid Western European set."""
        valid_chars = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ,-'."
        )
        valid_chars.update(self.diacritic_chars)
        return set(name) - valid_chars

    def _has_valid_european_characters_old(self, name: str) -> bool:
        """Check if name contains valid characters for Western European names (permissive)."""
        import unicodedata

        for char in name:
            category = unicodedata.category(char)
            # Allow all letters (L*), marks (M*), and spaces (Z*)
            if category.startswith(("L", "M", "Z")):
                continue
            # Allow common punctuation: spaces, hyphens, apostrophes, periods, commas
            if char in " -'.,":
                continue
            # Allow numbers (for names like "John II")
            if category == "Nd":
                continue
            # Reject unusual characters
            return False

        return True
