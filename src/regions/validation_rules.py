"""
Regional linguistic validation rules for GMNAP.
Provides region-specific validation logic and patterns.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    field: str
    rule_id: str


@dataclass
class RegionalValidationRule:
    """A region-specific validation rule."""

    id: str
    name: str
    description: str
    regions: List[str]  # Region codes this rule applies to
    scripts: List[str]  # Scripts this rule applies to
    pattern: Optional[str] = None  # Regex pattern
    validator: Optional[callable] = None  # Custom validation function
    severity: str = "error"  # error or warning
    enabled: bool = True


class RegionalValidationEngine:
    """
    Engine for regional linguistic validation rules.

    Implements region-specific validation for names, scripts, and patterns.
    """

    def __init__(self):
        self.rules: Dict[str, RegionalValidationRule] = {}
        self._load_core_rules()
        self._load_script_rules()
        self._load_region_specific_rules()

    def _load_core_rules(self):
        """Load core validation rules that apply across regions."""

        core_rules = [
            RegionalValidationRule(
                id="core_name_balance",
                name="Name Component Balance",
                description="Check if surname/given name ratio is reasonable",
                regions=["*"],  # All regions
                scripts=["*"],
                validator=self._validate_name_balance,
            ),
            RegionalValidationRule(
                id="core_script_consistency",
                name="Script Consistency",
                description="Ensure consistent script usage within names",
                regions=["*"],
                scripts=["*"],
                validator=self._validate_script_consistency,
            ),
            RegionalValidationRule(
                id="core_no_mixed_direction",
                name="Text Direction Consistency",
                description="Prevent mixing LTR and RTL scripts inappropriately",
                regions=["*"],
                scripts=["*"],
                validator=self._validate_text_direction,
            ),
            RegionalValidationRule(
                id="core_particle_position",
                name="Particle Position",
                description="Validate particle placement in names",
                regions=["*"],
                scripts=["Latin"],
                validator=self._validate_particle_position,
            ),
        ]

        for rule in core_rules:
            self.rules[rule.id] = rule

    def _load_script_rules(self):
        """Load script-specific validation rules."""

        script_rules = [
            # Latin script rules
            RegionalValidationRule(
                id="latin_no_excessive_capitals",
                name="No Excessive Capitals",
                description="Prevent ALL CAPS or eXcEsSiVe capitalization",
                regions=["*"],
                scripts=["Latin"],
                pattern=r"^[A-Z\s]+$|[A-Z]{5,}",
                severity="warning",
            ),
            RegionalValidationRule(
                id="latin_valid_apostrophes",
                name="Valid Apostrophe Usage",
                description="Ensure apostrophes are used correctly",
                regions=["A1", "A2", "G1"],  # Anglo, Western Europe, Latin America
                scripts=["Latin"],
                pattern=r"(?<!\w)'(?!\w)|(?<=\s)'|'(?=\s)|^'|'$",
                severity="warning",
            ),
            # Cyrillic script rules
            RegionalValidationRule(
                id="cyrillic_no_latin_mix",
                name="No Cyrillic-Latin Mixing",
                description="Prevent mixing Cyrillic with Latin lookalikes",
                regions=["B1", "B2"],  # Slavic regions
                scripts=["Cyrillic"],
                validator=self._validate_no_cyrillic_latin_mix,
            ),
            # Arabic script rules
            RegionalValidationRule(
                id="arabic_valid_structure",
                name="Valid Arabic Name Structure",
                description="Validate Arabic name components",
                regions=["C3", "C4", "C5"],  # Arabic regions
                scripts=["Arabic"],
                validator=self._validate_arabic_structure,
            ),
            # CJK rules
            RegionalValidationRule(
                id="cjk_character_validity",
                name="Valid CJK Characters",
                description="Ensure CJK characters are from appropriate blocks",
                regions=["E1", "E3", "E4"],  # China, Japan, Korea
                scripts=["CJK"],
                validator=self._validate_cjk_characters,
            ),
            # Devanagari rules
            RegionalValidationRule(
                id="devanagari_valid_combinations",
                name="Valid Devanagari Combinations",
                description="Check for valid consonant-vowel combinations",
                regions=["D1", "D2"],  # South Asian regions
                scripts=["Devanagari"],
                validator=self._validate_devanagari_combinations,
            ),
        ]

        for rule in script_rules:
            self.rules[rule.id] = rule

    def _load_region_specific_rules(self):
        """Load region-specific validation rules."""

        region_rules = [
            # Anglo sphere specific
            RegionalValidationRule(
                id="a1_surname_prefixes",
                name="Valid Anglo Surname Prefixes",
                description="Validate Mac/Mc/O' prefixes",
                regions=["A1"],
                scripts=["Latin"],
                pattern=r"^(Ma?c|O')[a-z]",  # Must be followed by lowercase
                severity="error",
            ),
            # Western Europe specific
            RegionalValidationRule(
                id="a2_particle_validation",
                name="Valid European Particles",
                description="Validate von/van/de/di particles",
                regions=["A2"],
                scripts=["Latin"],
                validator=self._validate_european_particles,
            ),
            # East Asian specific
            RegionalValidationRule(
                id="e1_chinese_name_length",
                name="Chinese Name Length",
                description="Chinese names typically 2-4 characters",
                regions=["E1"],
                scripts=["CJK"],
                validator=self._validate_chinese_name_length,
            ),
            RegionalValidationRule(
                id="e3_japanese_reading_presence",
                name="Japanese Reading Presence",
                description="Japanese names should have readings",
                regions=["E3"],
                scripts=["CJK"],
                validator=self._validate_japanese_readings,
            ),
            RegionalValidationRule(
                id="e4_korean_syllable_blocks",
                name="Korean Syllable Validity",
                description="Validate Hangul syllable blocks",
                regions=["E4"],
                scripts=["Hangul"],
                validator=self._validate_korean_syllables,
            ),
            # Arabic regions
            RegionalValidationRule(
                id="c3_c4_patronymic_chain",
                name="Arabic Patronymic Chain",
                description="Validate ibn/bin/bint chains",
                regions=["C3", "C4"],
                scripts=["Arabic"],
                validator=self._validate_arabic_patronymic,
            ),
            # South Asian
            RegionalValidationRule(
                id="d1_hindi_name_structure",
                name="Hindi Name Structure",
                description="Validate Hindi/Devanagari name patterns",
                regions=["D1"],
                scripts=["Devanagari"],
                validator=self._validate_hindi_structure,
            ),
        ]

        for rule in region_rules:
            self.rules[rule.id] = rule

    def validate_entry(
        self, entry: Dict[str, Any], region_code: str, script: str
    ) -> List[ValidationResult]:
        """
        Validate an entry against regional rules.

        Args:
            entry: Entry to validate
            region_code: Region code
            script: Primary script

        Returns:
            List of validation results
        """
        results = []

        # Filter applicable rules
        applicable_rules = []
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            # Check if rule applies to this region
            if "*" not in rule.regions and region_code not in rule.regions:
                continue

            # Check if rule applies to this script
            if "*" not in rule.scripts and script not in rule.scripts:
                continue

            applicable_rules.append(rule)

        # Apply each rule
        for rule in applicable_rules:
            try:
                if rule.pattern:
                    # Pattern-based validation
                    result = self._apply_pattern_rule(entry, rule)
                elif rule.validator:
                    # Function-based validation
                    result = rule.validator(entry, rule)
                else:
                    continue

                if result:
                    results.append(result)

            except Exception as e:
                logger.error(f"Error applying rule {rule.id}: {e}")
                results.append(
                    ValidationResult(
                        is_valid=False,
                        errors=[f"Rule {rule.id} failed: {str(e)}"],
                        warnings=[],
                        field="unknown",
                        rule_id=rule.id,
                    )
                )

        return results

    def _apply_pattern_rule(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Apply a pattern-based validation rule."""
        fields_to_check = ["CanonicalLatin", "CanonicalNative"]
        errors = []
        warnings = []

        for field in fields_to_check:
            if field in entry and entry[field]:
                value = entry[field]
                if re.search(rule.pattern, value):
                    message = f"{field}: {rule.description}"
                    if rule.severity == "error":
                        errors.append(message)
                    else:
                        warnings.append(message)

        if errors or warnings:
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                field=",".join(fields_to_check),
                rule_id=rule.id,
            )

        return None

    # Validation functions
    def _validate_name_balance(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Check if name components are balanced."""
        canonical = entry.get("CanonicalLatin", "")

        # Very rough heuristic - names with many commas might be problematic
        comma_count = canonical.count(",")
        if comma_count > 3:
            return ValidationResult(
                is_valid=False,
                errors=[f"Excessive name components ({comma_count + 1} parts)"],
                warnings=[],
                field="CanonicalLatin",
                rule_id=rule.id,
            )

        # Check for very long single components
        parts = canonical.split(",")
        for part in parts:
            if len(part.strip()) > 50:
                return ValidationResult(
                    is_valid=False,
                    errors=[f"Name component too long: {len(part.strip())} chars"],
                    warnings=[],
                    field="CanonicalLatin",
                    rule_id=rule.id,
                )

        return None

    def _validate_script_consistency(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Ensure consistent script usage."""
        native = entry.get("CanonicalNative", "")
        if not native:
            return None

        # Detect scripts in the name
        scripts = set()
        for char in native:
            script = unicodedata.name(char, "").split()[0] if char.strip() else None
            if script:
                scripts.add(script)

        # Too many different scripts might indicate an issue
        if len(scripts) > 2:
            return ValidationResult(
                is_valid=False,
                errors=[f"Mixed scripts detected: {', '.join(scripts)}"],
                warnings=[],
                field="CanonicalNative",
                rule_id=rule.id,
            )

        return None

    def _validate_text_direction(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Check for mixed text directions."""
        native = entry.get("CanonicalNative", "")
        if not native:
            return None

        has_rtl = bool(re.search(r"[\u0590-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]", native))
        has_ltr = bool(re.search(r"[A-Za-z\u0400-\u04FF]", native))

        if has_rtl and has_ltr:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=["Mixed RTL/LTR scripts detected"],
                field="CanonicalNative",
                rule_id=rule.id,
            )

        return None

    def _validate_particle_position(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate particle placement."""
        canonical = entry.get("CanonicalLatin", "")

        # Check for particles at the beginning of surnames
        if canonical.startswith(("de ", "van ", "von ", "del ", "della ", "di ")):
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=["Particle at beginning - verify sort order"],
                field="CanonicalLatin",
                rule_id=rule.id,
            )

        return None

    def _validate_no_cyrillic_latin_mix(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Prevent Cyrillic-Latin mixing."""
        native = entry.get("CanonicalNative", "")
        if not native:
            return None

        cyrillic_chars = set(re.findall(r"[\u0400-\u04FF]", native))
        latin_chars = set(re.findall(r"[A-Za-z]", native))

        if cyrillic_chars and latin_chars:
            # Check if they're lookalikes
            lookalikes = {
                "А": "A",
                "В": "B",
                "С": "C",
                "Е": "E",
                "Н": "H",
                "К": "K",
                "М": "M",
                "О": "O",
                "Р": "P",
                "Т": "T",
                "Х": "X",
            }

            suspicious = any(c in lookalikes for c in cyrillic_chars)
            if suspicious:
                return ValidationResult(
                    is_valid=False,
                    errors=["Suspicious Cyrillic-Latin character mixing"],
                    warnings=[],
                    field="CanonicalNative",
                    rule_id=rule.id,
                )

        return None

    def _validate_arabic_structure(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate Arabic name structure."""
        native = entry.get("CanonicalNative", "")
        if not native or not re.search(r"[\u0600-\u06FF]", native):
            return None

        # Check for required components
        warnings = []

        # Check if it's just a single word (might be incomplete)
        words = native.split()
        if len(words) == 1:
            warnings.append("Single-word Arabic name - may be incomplete")

        # Check for very long chains
        if len(words) > 8:
            warnings.append(f"Very long Arabic name ({len(words)} words)")

        if warnings:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=warnings,
                field="CanonicalNative",
                rule_id=rule.id,
            )

        return None

    def _validate_cjk_characters(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate CJK character usage."""
        native = entry.get("CanonicalNative", "")
        if not native:
            return None

        # Define valid Unicode blocks for CJK
        cjk_blocks = [
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            (0x3400, 0x4DBF),  # CJK Extension A
            (0x20000, 0x2A6DF),  # CJK Extension B
            (0x2A700, 0x2B73F),  # CJK Extension C
            (0x2B740, 0x2B81F),  # CJK Extension D
            (0x2B820, 0x2CEAF),  # CJK Extension E
            (0xF900, 0xFAFF),  # CJK Compatibility
            (0x3040, 0x309F),  # Hiragana
            (0x30A0, 0x30FF),  # Katakana
            (0xAC00, 0xD7AF),  # Hangul Syllables
        ]

        warnings = []
        for char in native:
            code = ord(char)
            is_valid_cjk = any(start <= code <= end for start, end in cjk_blocks)

            # Check for private use area (suspicious)
            if 0xE000 <= code <= 0xF8FF or 0xF0000 <= code <= 0xFFFFF:
                warnings.append(f"Private use character detected: U+{code:04X}")

        if warnings:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=warnings,
                field="CanonicalNative",
                rule_id=rule.id,
            )

        return None

    def _validate_devanagari_combinations(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate Devanagari combining sequences."""
        native = entry.get("CanonicalNative", "")
        if not native or not re.search(r"[\u0900-\u097F]", native):
            return None

        # Check for invalid combining sequences
        errors = []

        # Check for multiple consecutive viramas (्)
        if re.search(r"्{2,}", native):
            errors.append("Multiple consecutive viramas detected")

        # Check for vowel signs without base consonants
        if re.match(r"^[\u093E-\u094C\u0962-\u0963]", native):
            errors.append("Vowel sign without base consonant")

        if errors:
            return ValidationResult(
                is_valid=False, errors=errors, warnings=[], field="CanonicalNative", rule_id=rule.id
            )

        return None

    def _validate_european_particles(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate European name particles."""
        canonical = entry.get("CanonicalLatin", "")

        # Common particles and their expected capitalization
        particles = {
            "von": "lowercase expected",
            "van": "lowercase expected",
            "Van": "capitalized OK for Dutch",
            "de": "lowercase expected",
            "De": "capitalized OK at start",
            "del": "lowercase expected",
            "della": "lowercase expected",
            "di": "lowercase expected",
            "Di": "capitalized OK for Italian",
            "da": "lowercase expected",
            "das": "lowercase expected",
            "dos": "lowercase expected",
            "du": "lowercase expected",
            "der": "lowercase expected",
            "ter": "lowercase expected",
            "ten": "lowercase expected",
            "zu": "lowercase expected",
            "zur": "lowercase expected",
            "af": "lowercase expected",
        }

        warnings = []
        parts = canonical.split()

        for i, part in enumerate(parts):
            if part in particles:
                # Check position and capitalization rules
                if i == 0 and part[0].islower():
                    warnings.append(f"Particle '{part}' at start should be capitalized")
                elif i > 0 and part in ["Von", "Van"] and "Dutch" not in entry.get("Notes", ""):
                    warnings.append(f"Particle '{part}' - verify if Dutch origin")

        if warnings:
            return ValidationResult(
                is_valid=True, errors=[], warnings=warnings, field="CanonicalLatin", rule_id=rule.id
            )

        return None

    def _validate_chinese_name_length(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate Chinese name length."""
        native = entry.get("CanonicalNative", "")
        if not native:
            return None

        # Remove spaces and count characters
        chars = native.replace(" ", "")
        cjk_chars = [c for c in chars if 0x4E00 <= ord(c) <= 0x9FFF]

        if cjk_chars:
            if len(cjk_chars) < 2:
                return ValidationResult(
                    is_valid=False,
                    errors=["Chinese name too short (less than 2 characters)"],
                    warnings=[],
                    field="CanonicalNative",
                    rule_id=rule.id,
                )
            elif len(cjk_chars) > 4:
                return ValidationResult(
                    is_valid=True,
                    errors=[],
                    warnings=[f"Unusually long Chinese name ({len(cjk_chars)} characters)"],
                    field="CanonicalNative",
                    rule_id=rule.id,
                )

        return None

    def _validate_japanese_readings(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Check for Japanese reading information."""
        if "JapaneseReading" not in entry.get("Metadata", {}):
            native = entry.get("CanonicalNative", "")
            # Check if it contains kanji
            if native and re.search(r"[\u4E00-\u9FFF]", native):
                return ValidationResult(
                    is_valid=True,
                    errors=[],
                    warnings=["Japanese name with kanji but no reading provided"],
                    field="CanonicalNative",
                    rule_id=rule.id,
                )

        return None

    def _validate_korean_syllables(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate Korean Hangul syllables."""
        native = entry.get("CanonicalNative", "")
        if not native:
            return None

        errors = []
        warnings = []

        for char in native:
            code = ord(char)
            # Check if it's in Hangul syllables block
            if 0xAC00 <= code <= 0xD7AF:
                continue
            # Check if it's Hangul Jamo (components)
            elif 0x1100 <= code <= 0x11FF or 0x3130 <= code <= 0x318F:
                warnings.append("Hangul Jamo components detected - should use composed syllables")
            # Check compatibility Jamo
            elif 0x3130 <= code <= 0x318F:
                errors.append("Hangul compatibility Jamo detected - use standard syllables")

        if errors or warnings:
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                field="CanonicalNative",
                rule_id=rule.id,
            )

        return None

    def _validate_arabic_patronymic(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate Arabic patronymic chains."""
        canonical = entry.get("CanonicalLatin", "")
        native = entry.get("CanonicalNative", "")

        warnings = []

        # Check Latin version
        if canonical:
            # Check for multiple ibn/bin
            ibn_count = len(re.findall(r"\b(ibn|bin|bint)\b", canonical, re.I))
            if ibn_count > 3:
                warnings.append(f"Long patronymic chain ({ibn_count} ibn/bin/bint)")

            # Check for inconsistent spacing
            if re.search(r"\b(ibn|bin|bint)[A-Z]", canonical):
                warnings.append("Missing space after ibn/bin/bint")

        if warnings:
            return ValidationResult(
                is_valid=True, errors=[], warnings=warnings, field="CanonicalLatin", rule_id=rule.id
            )

        return None

    def _validate_hindi_structure(
        self, entry: Dict[str, Any], rule: RegionalValidationRule
    ) -> Optional[ValidationResult]:
        """Validate Hindi/Devanagari name structure."""
        native = entry.get("CanonicalNative", "")
        if not native or not re.search(r"[\u0900-\u097F]", native):
            return None

        warnings = []

        # Check for mixing with Latin
        if re.search(r"[A-Za-z]", native):
            warnings.append("Mixed Devanagari and Latin scripts")

        # Check for common title/honorifics that shouldn't be in canonical
        honorifics = ["श्री", "श्रीमती", "कुमारी", "डॉ", "प्रो"]
        for honorific in honorifics:
            if honorific in native:
                warnings.append(f"Honorific '{honorific}' detected in canonical name")

        if warnings:
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=warnings,
                field="CanonicalNative",
                rule_id=rule.id,
            )

        return None

    def get_rules_for_region(self, region_code: str) -> List[RegionalValidationRule]:
        """Get all rules applicable to a specific region."""
        applicable = []
        for rule in self.rules.values():
            if "*" in rule.regions or region_code in rule.regions:
                applicable.append(rule)
        return applicable

    def get_rules_for_script(self, script: str) -> List[RegionalValidationRule]:
        """Get all rules applicable to a specific script."""
        applicable = []
        for rule in self.rules.values():
            if "*" in rule.scripts or script in rule.scripts:
                applicable.append(rule)
        return applicable


# Global instance
regional_validator = RegionalValidationEngine()
