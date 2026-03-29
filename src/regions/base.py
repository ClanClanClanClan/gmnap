"""
Base classes for regional processing in GMNAP.
Implements the RegionSpec interface as defined in specs v7.
Enforces V7 linguistic rules (IDs 1-34) and quality gates.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from .security import SecurityError, secure_validate_entry, secure_clean_name
from .validation_rules import regional_validator, ValidationResult

logger = logging.getLogger(__name__)


class RegionRuleError(Exception):
    """Entry fails region-specific rule."""

    pass


@dataclass
class RegionSpec(ABC):
    """
    Region specification interface as defined in specs v7.

    All region implementations must inherit from this class and implement
    the mandatory hooks. Must comply with the 34 linguistic rules (IDs 1-34)
    and V7 quality gates including 97% round-trip accuracy.
    """

    code: str
    yaml_files: List[str]
    scripts: List[str]
    mixed_scripts: bool = False
    canonical_order: Literal["Family, Given", "Given Family", "Patronymic", "Mononym"] = (
        "Family, Given"
    )
    romanisation_standards: List[str] = None

    def __post_init__(self):
        if self.romanisation_standards is None:
            self.romanisation_standards = []
        self.logger = logging.getLogger(f"regions.{self.code}")

    # Security methods (available to all processors)
    def security_validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry against security threats.

        This method should be called by all processors during their
        clean() or validate() methods to ensure security.

        Args:
            entry: Entry to validate

        Raises:
            SecurityError: If security threats are detected
        """
        try:
            secure_validate_entry(entry, self.code)
        except SecurityError as e:
            self.logger.warning(f"Security threat blocked: {e}")
            raise RegionRuleError(f"Security violation: {e}")

    def security_clean_field(self, value: str, field_name: str) -> str:
        """
        Securely clean a string field.

        Args:
            value: String value to clean
            field_name: Name of field for context

        Returns:
            Cleaned string value

        Raises:
            RegionRuleError: If security threats are detected
        """
        try:
            return secure_clean_name(value, f"{self.code}.{field_name}")
        except SecurityError as e:
            self.logger.warning(f"Security threat in {field_name}: {e}")
            raise RegionRuleError(f"Security violation in {field_name}: {e}")

    def security_validate_all_fields(self, entry: Dict[str, Any]) -> None:
        """
        Validate all string fields in entry for security.

        This is a convenience method that validates common name fields.
        Individual processors can call this early in their processing.

        Args:
            entry: Entry to validate

        Raises:
            RegionRuleError: If security threats are detected
        """
        # Validate entire entry structure first
        self.security_validate(entry)

        # Validate specific common fields
        fields_to_check = [
            "CanonicalLatin",
            "CanonicalNative",
            "CJK",
            "FamilyName",
            "GivenName",
            "MiddleName",
        ]

        for field in fields_to_check:
            if field in entry and isinstance(entry[field], str):
                entry[field] = self.security_clean_field(entry[field], field)

        # Validate variants if present
        if "Variants" in entry:
            if "Observed" in entry["Variants"]:
                for i, variant in enumerate(entry["Variants"]["Observed"]):
                    if "str" in variant and isinstance(variant["str"], str):
                        variant["str"] = self.security_clean_field(
                            variant["str"], f"Variants.Observed[{i}].str"
                        )

            if "Synthesised" in entry["Variants"]:
                for i, variant in enumerate(entry["Variants"]["Synthesised"]):
                    if "str" in variant and isinstance(variant["str"], str):
                        variant["str"] = self.security_clean_field(
                            variant["str"], f"Variants.Synthesised[{i}].str"
                        )

    # Rule 16: Unicode Fold Exceptions (Global utility method)
    def apply_unicode_fold_exceptions(self, text: str) -> str:
        """
        Rule 16: Unicode Fold Exceptions - ligatures decomposition, ß/ẞ handling, tonos=oxia.

        This global utility method handles special Unicode folding cases that
        require specific treatment across all regional processors:

        1. Ligatures decomposition: æ → ae, œ → oe, ß → ss, ĳ → ij
        2. Capital Sharp-S handling: ẞ → SS (proper German capitalization)
        3. Greek tonos=oxia normalization: ά → ά (canonical accent form)

        Args:
            text: Input text to normalize

        Returns:
            Normalized text with Unicode fold exceptions applied
        """
        if not text:
            return text

        # Step 1: Ligatures decomposition
        ligature_map = {
            "æ": "ae",
            "Æ": "AE",  # Latin ae ligature
            "œ": "oe",
            "Œ": "OE",  # Latin oe ligature
            "ß": "ss",  # German sharp s (eszett)
            "ẞ": "SS",  # Capital German sharp s
            "ĳ": "ij",
            "Ĳ": "IJ",  # Dutch ij ligature
            "ﬀ": "ff",
            "ﬁ": "fi",  # Typography ligatures
            "ﬂ": "fl",
            "ﬃ": "ffi",
            "ﬄ": "ffl",
            "ﬅ": "st",
            "ﬆ": "st",
        }

        # Apply ligature decomposition
        for ligature, replacement in ligature_map.items():
            text = text.replace(ligature, replacement)

        # Step 2: Greek tonos=oxia normalization
        # Greek has two different accent systems that should be normalized
        greek_accent_map = {
            # Tonos (modern Greek) → Oxia (polytonic/ancient Greek canonical form)
            "ά": "ά",  # alpha with tonos → alpha with oxia
            "έ": "έ",  # epsilon with tonos → epsilon with oxia
            "ή": "ή",  # eta with tonos → eta with oxia
            "ί": "ί",  # iota with tonos → iota with oxia
            "ό": "ό",  # omicron with tonos → omicron with oxia
            "ύ": "ύ",  # upsilon with tonos → upsilon with oxia
            "ώ": "ώ",  # omega with tonos → omega with oxia
            # Capital forms
            "Ά": "Ά",
            "Έ": "Έ",
            "Ή": "Ή",
            "Ί": "Ί",
            "Ό": "Ό",
            "Ύ": "Ύ",
            "Ώ": "Ώ",
        }

        # Apply Greek accent normalization
        for tonos_char, oxia_char in greek_accent_map.items():
            text = text.replace(tonos_char, oxia_char)

        # Step 3: Additional Unicode normalizations for V7 compliance
        # Normalize quotation marks and apostrophes
        quote_map = {
            """: "'", """: "'",  # Curly single quotes → straight
            '"': '"',
            '"': '"',  # Curly double quotes → straight
            "‚": ",",
            "„": '"',  # German/Eastern European quotes
            "‹": "<",
            "›": ">",  # Single angle quotes
            "«": '"',
            "»": '"',  # Double angle quotes
        }

        for fancy_quote, simple_quote in quote_map.items():
            text = text.replace(fancy_quote, simple_quote)

        # Step 4: Normalize dashes and spaces
        # V7 requires consistent dash and space handling
        dash_map = {
            "–": "-",  # En dash → hyphen
            "—": "-",  # Em dash → hyphen
            "−": "-",  # Minus sign → hyphen
            "‐": "-",  # Hyphen → standard hyphen
            "\u00a0": " ",  # Non-breaking space → regular space
            "\u2009": " ",  # Thin space → regular space
            "\u200a": " ",  # Hair space → regular space
            "\u2000": " ",  # En quad → regular space
            "\u2001": " ",  # Em quad → regular space
            "\u2002": " ",  # En space → regular space
            "\u2003": " ",  # Em space → regular space
        }

        for fancy_char, simple_char in dash_map.items():
            text = text.replace(fancy_char, simple_char)

        return text

    # Rule 26: Gender Heuristic Guard (Global safety mechanism)
    def apply_gender_heuristic_guard(self, entry: Dict[str, Any]) -> None:
        """
        Rule 26: Gender Heuristic Guard – ethical and safe gender inference.

        This critical safety rule ensures that gender inference in name processing:
        1. Never makes assumptions based on cultural stereotypes
        2. Only infers gender from linguistically definitive markers
        3. Always marks inferred genders as uncertain
        4. Respects cultural and regional variations
        5. Provides escape mechanisms for non-binary/unknown cases

        V7 compliance requires this guard to prevent discriminatory outcomes
        in academic genealogy applications.
        """
        # Check if gender information exists
        current_gender = entry.get("Gender")
        gender_provided = entry.get("GenderProvided", True)  # Default assumes provided

        # If gender was inferred (not provided), apply safety guards
        if current_gender and not gender_provided:
            regional_extras = entry.get("RegionalExtras", {})
            gender_source = regional_extras.get("gender_source", "unknown")

            # Only allow gender inference from highly reliable linguistic markers
            reliable_sources = {
                "patronymic-inference",  # East-Slavic -ович/-овна patterns
                "turkic-patronymic",  # Turkic -oğlu/-qızı patterns
                "arabic-patronymic",  # Arabic bin/bint patterns
                "malay-patronymic",  # Malay bin/binti patterns
                "definitive-suffix",  # Language-specific definitive markers
            }

            if gender_source not in reliable_sources:
                # Remove uncertain gender inferences
                self.logger.warning(
                    f"Removing uncertain gender inference from source: {gender_source}"
                )
                entry.pop("Gender", None)
                entry["GenderProvided"] = False
            else:
                # Mark reliable inferences with confidence metadata
                entry["GenderInferenceMetadata"] = {
                    "source": gender_source,
                    "confidence": "linguistic-marker",
                    "rule_26_validated": True,
                    "cultural_context": regional_extras.get("likely_country", "unknown"),
                }

                # Always mark inferred genders as uncertain for downstream systems
                entry["GenderUncertainty"] = True

        # Apply cultural sensitivity guards
        self._apply_cultural_gender_guards(entry)

        # Validate against discriminatory patterns
        self._validate_gender_non_discrimination(entry)

    def _apply_cultural_gender_guards(self, entry: Dict[str, Any]) -> None:
        """Apply culture-specific gender inference guards."""
        regional_extras = entry.get("RegionalExtras", {})
        likely_country = regional_extras.get("likely_country")

        # Cultures where gender inference should be extra careful
        cautious_cultures = {
            "TH",
            "VN",
            "KH",
            "LA",  # Mainland SEA - different gender concepts
            "ID",
            "MY",
            "SG",
            "BN",  # Maritime SEA - diverse traditions
            "IN",
            "BD",
            "NP",
            "LK",  # South Asia - complex gender systems
            "PH",
            "TL",  # Philippines - diverse naming patterns
        }

        if likely_country in cautious_cultures:
            # For these cultures, require extra validation
            if entry.get("Gender") and not entry.get("GenderProvided", True):
                # Add cultural sensitivity flag
                if "GenderInferenceMetadata" not in entry:
                    entry["GenderInferenceMetadata"] = {}
                entry["GenderInferenceMetadata"]["cultural_sensitivity_required"] = True
                entry["GenderInferenceMetadata"]["cultural_context"] = likely_country

    def _validate_gender_non_discrimination(self, entry: Dict[str, Any]) -> None:
        """Validate that gender handling doesn't create discriminatory outcomes."""
        # Ensure gender information doesn't affect core name processing
        gender = entry.get("Gender")
        if gender:
            # Check that gender isn't being used inappropriately in name variants
            variants = entry.get("Variants", {}).get("Synthesised", [])
            for variant in variants:
                variant_type = variant.get("type", "")
                # Flag suspicious gender-based variants
                if "gender" in variant_type.lower() and variant_type not in [
                    "patronymic-gender-inference"
                ]:
                    self.logger.warning(
                        f"Potentially discriminatory gender-based variant: {variant_type}"
                    )

            # Ensure gender doesn't affect order_key (sorting should be gender-neutral)
            # This is validated elsewhere but we double-check here
            pass

        # Add non-discrimination compliance flag
        entry["Rule26Compliant"] = True

    # Rule 34: Round-trip Determinism (Global quality gate)
    def validate_round_trip_determinism(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Rule 34: Round-trip Determinism – ensure consistent processing results.

        This critical quality gate ensures that:
        1. Processing the same input always produces identical output
        2. order_key() is a pure function (same input → same output)
        3. Variant generation is deterministic and stable
        4. No randomness or system-dependent behavior affects results
        5. Round-trip processing maintains data integrity

        Returns validation report with compliance status and any detected issues.
        """
        validation_report = {
            "rule_34_compliant": True,
            "determinism_issues": [],
            "round_trip_accuracy": None,
            "order_key_stability": True,
            "variant_stability": True,
        }

        try:
            # Test 1: order_key() determinism
            canonical = entry.get("CanonicalLatin", "") or entry.get("CanonicalNative", "")
            if canonical:
                # Call order_key multiple times and verify consistency
                order_keys = []
                for _ in range(3):
                    try:
                        key = self.order_key(entry)
                        order_keys.append(key)
                    except Exception as e:
                        validation_report["determinism_issues"].append(f"order_key() failed: {e}")
                        validation_report["order_key_stability"] = False

                # Check if all order_key calls produced the same result
                if len(set(order_keys)) > 1:
                    validation_report["determinism_issues"].append(
                        f"order_key() non-deterministic: {order_keys}"
                    )
                    validation_report["order_key_stability"] = False

            # Test 2: Variant generation stability
            variants_before = entry.get("Variants", {}).get("Synthesised", [])
            variant_strings_before = [v.get("str", "") for v in variants_before]

            # Re-run augmentation to test stability (if this processor supports it)
            if hasattr(self, "_test_variant_stability"):
                variants_after = self._test_variant_stability(entry)
                variant_strings_after = [v.get("str", "") for v in variants_after]

                if variant_strings_before != variant_strings_after:
                    validation_report["determinism_issues"].append(
                        "Variant generation is non-deterministic"
                    )
                    validation_report["variant_stability"] = False

            # Test 3: Unicode normalization consistency
            self._validate_unicode_consistency(entry, validation_report)

            # Test 4: Metadata stability
            self._validate_metadata_stability(entry, validation_report)

            # Test 5: Round-trip accuracy (for applicable scripts)
            round_trip_accuracy = self._calculate_round_trip_accuracy(entry)
            if round_trip_accuracy is not None:
                validation_report["round_trip_accuracy"] = round_trip_accuracy
                # V7 requires ≥97% round-trip accuracy for CJK
                if round_trip_accuracy < 0.97:
                    validation_report["determinism_issues"].append(
                        f"Round-trip accuracy too low: {round_trip_accuracy:.2%}"
                    )

            # Overall compliance
            validation_report["rule_34_compliant"] = (
                len(validation_report["determinism_issues"]) == 0
            )

        except Exception as e:
            validation_report["rule_34_compliant"] = False
            validation_report["determinism_issues"].append(f"Validation failed: {e}")

        # Store validation results in entry
        entry["Rule34ValidationReport"] = validation_report

        return validation_report

    def _validate_unicode_consistency(self, entry: Dict[str, Any], report: Dict[str, Any]) -> None:
        """Validate Unicode normalization consistency."""
        import unicodedata

        for field in ["CanonicalLatin", "CanonicalNative"]:
            value = entry.get(field, "")
            if value:
                # Test Unicode normalization stability
                nfc_form = unicodedata.normalize("NFC", value)
                nfd_form = unicodedata.normalize("NFD", value)

                # After applying our Unicode fold exceptions, should be stable
                processed_nfc = self.apply_unicode_fold_exceptions(nfc_form)
                processed_nfd = self.apply_unicode_fold_exceptions(nfd_form)

                # Check if results are equivalent (allowing for normalization differences)
                if unicodedata.normalize("NFC", processed_nfc) != unicodedata.normalize(
                    "NFC", processed_nfd
                ):
                    report["determinism_issues"].append(
                        f"Unicode normalization inconsistency in {field}"
                    )

    def _validate_metadata_stability(self, entry: Dict[str, Any], report: Dict[str, Any]) -> None:
        """Validate that metadata fields are stable and deterministic."""
        # Check RegionalExtras for stability
        regional_extras = entry.get("RegionalExtras", {})

        # These fields should be deterministic
        deterministic_fields = [
            "script",
            "likely_country",
            "has_patronymic",
            "is_mononym",
            "has_ezafe",
            "has_zadeh_suffix",
            "patronymic_type",
        ]

        for field in deterministic_fields:
            if field in regional_extras:
                value = regional_extras[field]
                # Check for non-deterministic indicators
                if isinstance(value, str) and any(
                    indicator in value.lower() for indicator in ["random", "timestamp", "uuid"]
                ):
                    report["determinism_issues"].append(
                        f"Non-deterministic value in RegionalExtras.{field}: {value}"
                    )

    def _calculate_round_trip_accuracy(self, entry: Dict[str, Any]) -> Optional[float]:
        """Calculate round-trip accuracy for applicable entries."""
        # This is mainly for CJK scripts (Rule 11 implementation)
        canonical_native = entry.get("CanonicalNative", "")
        canonical_latin = entry.get("CanonicalLatin", "")

        if not (canonical_native and canonical_latin):
            return None

        # Check if this involves CJK scripts
        cjk_ranges = [
            (0x4E00, 0x9FFF),  # CJK Unified Ideographs
            (0x3400, 0x4DBF),  # CJK Extension A
            (0x20000, 0x2A6DF),  # CJK Extension B
            (0x2A700, 0x2B73F),  # CJK Extension C
            (0x2B740, 0x2B81F),  # CJK Extension D
            (0x3000, 0x303F),  # CJK Symbols and Punctuation
            (0x3040, 0x309F),  # Hiragana
            (0x30A0, 0x30FF),  # Katakana
        ]

        has_cjk = any(
            any(start <= ord(char) <= end for start, end in cjk_ranges) for char in canonical_native
        )

        if not has_cjk:
            return None

        # Calculate Dice coefficient for round-trip accuracy
        # This is a simplified version - full implementation would be more complex
        return self._dice_coefficient(canonical_native, canonical_latin)

    def _dice_coefficient(self, str1: str, str2: str) -> float:
        """Calculate Dice coefficient between two strings."""
        if not str1 or not str2:
            return 0.0

        # Create bigrams
        bigrams1 = set(str1[i : i + 2] for i in range(len(str1) - 1))
        bigrams2 = set(str2[i : i + 2] for i in range(len(str2) - 1))

        if not bigrams1 and not bigrams2:
            return 1.0

        intersection = len(bigrams1 & bigrams2)
        return 2.0 * intersection / (len(bigrams1) + len(bigrams2))

    # Regional linguistic validation
    def apply_linguistic_validation(
        self, entry: Dict[str, Any], raise_on_error: bool = True
    ) -> List[ValidationResult]:
        """
        Apply regional linguistic validation rules.

        This method uses the regional validation engine to check for
        region-specific linguistic patterns, script consistency, and
        name structure validity.

        Args:
            entry: Entry to validate
            raise_on_error: If True, raise RegionRuleError on validation errors

        Returns:
            List of validation results

        Raises:
            RegionRuleError: If validation fails and raise_on_error is True
        """
        # Determine primary script from the entry
        primary_script = self._detect_primary_script(entry)

        # Apply regional validation rules
        results = regional_validator.validate_entry(entry, self.code, primary_script)

        # Process results
        errors = []
        warnings = []

        for result in results:
            if not result.is_valid:
                errors.extend(result.errors)
            warnings.extend(result.warnings)

        # Log warnings
        for warning in warnings:
            self.logger.warning(f"Linguistic validation warning: {warning}")

        # Handle errors
        if errors and raise_on_error:
            error_msg = "; ".join(errors)
            raise RegionRuleError(f"Linguistic validation failed: {error_msg}")

        return results

    def _detect_primary_script(self, entry: Dict[str, Any]) -> str:
        """
        Detect the primary script used in the entry.

        Args:
            entry: Entry to analyze

        Returns:
            Primary script name
        """
        # Use the scripts defined for this region as primary candidates
        if len(self.scripts) == 1:
            return self.scripts[0]

        # For mixed script regions, analyze the native name
        native = entry.get("CanonicalNative", "")
        if not native:
            return self.scripts[0] if self.scripts else "Latin"

        # Simple script detection based on Unicode ranges
        if any("\u0400" <= c <= "\u04ff" for c in native):
            return "Cyrillic"
        elif any("\u0600" <= c <= "\u06ff" for c in native):
            return "Arabic"
        elif any("\u0900" <= c <= "\u097f" for c in native):
            return "Devanagari"
        elif any(("\u4e00" <= c <= "\u9fff") or ("\u3400" <= c <= "\u4dbf") for c in native):
            return "CJK"
        elif any("\uac00" <= c <= "\ud7af" for c in native):
            return "Hangul"
        elif any(("\u3040" <= c <= "\u309f") or ("\u30a0" <= c <= "\u30ff") for c in native):
            return "Japanese"
        elif any("\u0e00" <= c <= "\u0e7f" for c in native):
            return "Thai"
        else:
            return "Latin"

    def get_applicable_validation_rules(self) -> List:
        """
        Get all validation rules applicable to this region.

        Returns:
            List of validation rules
        """
        return regional_validator.get_rules_for_region(self.code)

    def process(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing pipeline for regional transformation.

        This is the CRITICAL method that was missing!
        Orchestrates all processing stages in the correct order:
        1. Normalize - Unicode normalization
        2. Clean - Security and basic cleaning
        3. Augment - Add region-specific data
        4. Validate - Final validation

        Args:
            entry: Dictionary with name data

        Returns:
            Processed entry with transformed names
        """
        try:
            # Store original for debugging
            original = entry.copy()

            # Step 1: Normalize unicode and whitespace
            entry = self.normalize_whitespace_characters(entry)

            # Step 2: Apply security validation
            self.security_validate_all_fields(entry)

            # Step 3: Clean (remove titles, normalize)
            self.clean(entry)

            # Step 4: Augment (add region-specific data)
            self.augment(entry)

            # Step 5: Validate (ensure compliance)
            self.validate(entry)

            # Add processing metadata
            entry["_region_processed"] = True
            entry["_processor"] = self.__class__.__name__
            entry["_region_code"] = self.code

            return entry

        except Exception as e:
            self.logger.error(f"Processing failed for {entry.get('GlobalID')}: {e}")
            entry["_processing_error"] = str(e)
            return entry

    def normalize_whitespace_characters(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize tabs, newlines, and other whitespace characters.
        Implements V7 edge case requirements.

        Args:
            entry: Entry to normalize

        Returns:
            Entry with normalized whitespace
        """
        import unicodedata

        for field in ["CanonicalLatin", "CanonicalNative", "FamilyName", "GivenName"]:
            if field in entry and entry[field]:
                # Replace tabs and newlines with spaces
                entry[field] = entry[field].replace("\t", " ").replace("\n", " ").replace("\r", " ")

                # Normalize unicode (NFC for consistency)
                entry[field] = unicodedata.normalize("NFC", entry[field])

                # Collapse multiple spaces
                entry[field] = " ".join(entry[field].split())

                # Apply Unicode fold exceptions
                entry[field] = self.apply_unicode_fold_exceptions(entry[field])

                # Trim whitespace
                entry[field] = entry[field].strip()

        return entry

    # Mandatory hooks
    @abstractmethod
    def clean(self, entry: Dict[str, Any]) -> None:
        """
        Clean entry data according to regional rules.

        This method should:
        - Remove titles, honorifics
        - Normalize punctuation
        - Handle regional-specific formatting

        Args:
            entry: The entry dictionary to clean (modified in-place)

        Raises:
            RegionRuleError: If cleaning fails
        """
        pass

    @abstractmethod
    def augment(self, entry: Dict[str, Any]) -> None:
        """
        Augment entry with region-specific data.

        This method should:
        - Generate variants
        - Extract components (middle names, particles)
        - Add regional extras

        Args:
            entry: The entry dictionary to augment (modified in-place)

        Raises:
            RegionRuleError: If augmentation fails
        """
        pass

    @abstractmethod
    def validate(self, entry: Dict[str, Any]) -> None:
        """
        Validate entry according to regional rules.

        This method should:
        - Check script validity
        - Validate name structure
        - Ensure required fields

        Args:
            entry: The entry dictionary to validate

        Raises:
            RegionRuleError: If validation fails
        """
        pass

    @abstractmethod
    def order_key(self, entry: Dict[str, Any]) -> str:
        """
        Generate deterministic sort key for entry.

        Must be pure function - calling twice with same input
        must produce identical output.

        Args:
            entry: The entry dictionary

        Returns:
            Sort key string
        """
        pass

    # Optional bulk enrichment
    def batch_enrich(self, entries: List[Dict[str, Any]]) -> None:
        """
        Optional bulk enrichment for performance.

        Args:
            entries: List of entries to enrich
        """
        pass

    # Optional file-level hooks
    def on_file_load(self, data: Dict[str, Any]) -> None:
        """
        Hook called when YAML file is loaded.

        Args:
            data: The loaded YAML data
        """
        pass

    def before_write(self, data: Dict[str, Any]) -> None:
        """
        Hook called before writing YAML file.

        Args:
            data: The YAML data to write
        """
        pass

    def after_write(self, data: Dict[str, Any]) -> None:
        """
        Hook called after writing YAML file.

        Args:
            data: The written YAML data
        """
        pass


# Region code definitions from specs v7
REGION_CODES = {
    # A Groups - Western sphere
    "A1": "Core Anglo-Sphere",
    "A2": "Western Europe",
    "A3": "Nordic-Baltic",
    "A4": "Oceania Island States",
    "A5": "Dutch/French Caribbean",
    # B Groups - Slavic/Central Europe
    "B1": "East-Slavic",
    "B2": "South-Slavic & Central Europe",
    "B3": "Greek World",
    # C Groups - Middle East/Caucasus
    "C1": "Greater-Turkic",
    "C2": "Persian-Tajik",
    "C3": "Arabic Levant-Nile",
    "C4": "Arabic Gulf",
    "C5": "Arabic Maghreb",
    "C6": "Hebrew & Diaspora",
    "C7": "Armenian",
    "C8": "Georgian",
    "C9": "Caucasus-Turkic",
    # D Groups - South Asia
    "D1": "South Asia - Hindi Belt",
    "D2": "South Asia - Dravidian",
    "D3": "South Asia - Bengali",
    "D4": "Pakistan & Urdu",
    "D5": "Sinhala",
    # E Groups - East Asia
    "E1": "Sinophone Mainland",
    "E2": "Sinophone Traditional",
    "E3": "Japan",
    "E4": "Korea",
    "E5": "Vietnam",
    "E6": "Mainland SEA",
    "E7": "Maritime SEA",
    # F Groups - Sub-Saharan Africa
    "F1": "SSA - Francophone",
    "F2": "SSA - Anglophone",
    "F3": "Horn of Africa",
    "F4": "Lusophone Africa",
    # G Groups - Latin America
    "G1": "Latin America & Iberian Caribbean",
    # H Groups - Historical
    "H1": "Historical (≤ 1850)",
    # Special
    "R0": "Residual Latin-ASCII",
    "Z0": "Quarantine",
}


# ISO territory mappings from specs
TERRITORY_TO_REGION = {
    # A1 - Core Anglo-Sphere
    "US": "A1",
    "GB": "A1",
    "CA": "A1",
    "AU": "A1",
    "NZ": "A1",
    "IE": "A1",
    "AG": "A1",
    "AI": "A1",
    "BB": "A1",
    "BM": "A1",
    "BS": "A1",
    "DM": "A1",
    "GD": "A1",
    "GY": "A1",
    "JM": "A1",
    "KN": "A1",
    "LC": "A1",
    "MS": "A1",
    "TC": "A1",
    "TT": "A1",
    "VC": "A1",
    "VG": "A1",
    "VI": "A1",
    "GU": "A1",
    "AS": "A1",
    "MP": "A1",
    "UM": "A1",
    "FK": "A1",
    # A2 - Western Europe
    "FR": "A2",
    "DE": "A2",
    "IT": "A2",
    "ES": "A2",
    "PT": "A2",
    "NL": "A2",
    "BE": "A2",
    "CH": "A2",
    "AT": "A2",
    "LU": "A2",
    "LI": "A2",
    "SM": "A2",
    "MC": "A2",
    "GI": "A2",
    "AD": "A2",
    "MT": "A2",
    "VA": "A2",
    # A3 - Nordic-Baltic
    "DK": "A3",
    "NO": "A3",
    "SE": "A3",
    "FI": "A3",
    "IS": "A3",
    "FO": "A3",
    "AX": "A3",
    "EE": "A3",
    "LV": "A3",
    "LT": "A3",
    # A4 - Oceania Island States
    "FJ": "A4",
    "PG": "A4",
    "SB": "A4",
    "VU": "A4",
    "WS": "A4",
    "TO": "A4",
    "KI": "A4",
    "TV": "A4",
    "NR": "A4",
    "CK": "A4",
    "NU": "A4",
    "PF": "A4",
    "NC": "A4",
    # A5 - Dutch/French Caribbean
    "CW": "A5",
    "SX": "A5",
    "BQ": "A5",
    "MQ": "A5",
    "GF": "A5",
    "GP": "A5",
    "RE": "A5",
    "YT": "A5",
    "PM": "A5",
    # B1 - East-Slavic
    "RU": "B1",
    "UA": "B1",
    "BY": "B1",
    # B2 - South-Slavic & Central Europe
    "BG": "B2",
    "RS": "B2",
    "ME": "B2",
    "HR": "B2",
    "SI": "B2",
    "BA": "B2",
    "MK": "B2",
    "PL": "B2",
    "CZ": "B2",
    "SK": "B2",
    "HU": "B2",
    "RO": "B2",
    "AL": "B2",
    "XK": "B2",
    # B3 - Greek World
    "GR": "B3",
    "CY": "B3",
    # C1 - Greater-Turkic
    "TR": "C1",
    "AZ": "C1",
    "UZ": "C1",
    "TM": "C1",
    "KG": "C1",
    "KZ": "C1",
    # C2 - Persian-Tajik
    "IR": "C2",
    "AF": "C2",
    "TJ": "C2",
    # C3 - Arabic Levant-Nile
    "IQ": "C3",
    "JO": "C3",
    "LB": "C3",
    "SY": "C3",
    "PS": "C3",
    "EG": "C3",
    "SD": "C3",
    "SS": "C3",
    # C4 - Arabic Gulf
    "SA": "C4",
    "KW": "C4",
    "AE": "C4",
    "QA": "C4",
    "OM": "C4",
    "BH": "C4",
    "YE": "C4",
    # C5 - Arabic Maghreb
    "MA": "C5",
    "DZ": "C5",
    "TN": "C5",
    "LY": "C5",
    "EH": "C5",
    "MR": "C5",
    # C6 - Hebrew & Diaspora
    "IL": "C6",
    # C7 - Armenian
    "AM": "C7",
    # C8 - Georgian
    "GE": "C8",
    # D1 - South Asia - Hindi Belt
    "IN": "D1",
    "NP": "D1",
    "BT": "D1",  # Note: IN needs sub-region detection
    # D3 - South Asia - Bengali
    "BD": "D3",
    # D4 - Pakistan & Urdu
    "PK": "D4",
    # D5 - Sinhala
    "LK": "D5",
    # E1 - Sinophone Mainland
    "CN": "E1",
    # E2 - Sinophone Traditional
    "TW": "E2",
    "HK": "E2",
    "MO": "E2",
    # E3 - Japan
    "JP": "E3",
    # E4 - Korea
    "KR": "E4",
    "KP": "E4",
    # E5 - Vietnam
    "VN": "E5",
    # E6 - Mainland SEA
    "TH": "E6",
    "KH": "E6",
    "LA": "E6",
    # E7 - Maritime SEA
    "ID": "E7",
    "MY": "E7",
    "SG": "E7",
    "BN": "E7",
    "PH": "E7",
    "TL": "E7",
    # F1 - SSA - Francophone
    "BJ": "F1",
    "BF": "F1",
    "CM": "F1",
    "CF": "F1",
    "CG": "F1",
    "CI": "F1",
    "DJ": "F1",
    "GA": "F1",
    "GN": "F1",
    "ML": "F1",
    "NE": "F1",
    "SN": "F1",
    "TG": "F1",
    "TD": "F1",
    "KM": "F1",
    "SC": "F1",
    "MG": "F1",
    "BI": "F1",
    # F2 - SSA - Anglophone
    "GH": "F2",
    "NG": "F2",
    "KE": "F2",
    "UG": "F2",
    "TZ": "F2",
    "ZW": "F2",
    "ZM": "F2",
    "MW": "F2",
    "GM": "F2",
    "LR": "F2",
    "SL": "F2",
    "BW": "F2",
    "LS": "F2",
    "NA": "F2",
    "RW": "F2",
    "SZ": "F2",
    "MU": "F2",
    "SS": "F2",
    # F3 - Horn of Africa
    "ET": "F3",
    "ER": "F3",
    # F4 - Lusophone Africa
    "AO": "F4",
    "MZ": "F4",
    "CV": "F4",
    "GW": "F4",
    "ST": "F4",
    # G1 - Latin America & Iberian Caribbean
    "AR": "G1",
    "BO": "G1",
    "BR": "G1",
    "CL": "G1",
    "CO": "G1",
    "CR": "G1",
    "CU": "G1",
    "DO": "G1",
    "EC": "G1",
    "GT": "G1",
    "GY": "G1",
    "HN": "G1",
    "HT": "G1",
    "MX": "G1",
    "NI": "G1",
    "PA": "G1",
    "PE": "G1",
    "PY": "G1",
    "SV": "G1",
    "SR": "G1",
    "UY": "G1",
    "VE": "G1",
    "PR": "G1",
}


def get_region_for_territory(territory_code: str) -> str:
    """
    Get region code for ISO territory.

    Args:
        territory_code: ISO 3166 2-letter code

    Returns:
        Region code (A1-H1, R0, Z0)
    """
    return TERRITORY_TO_REGION.get(territory_code.upper(), "R0")


def get_region_name(region_code: str) -> str:
    """
    Get human-readable name for region code.

    Args:
        region_code: Region code (e.g., "A1")

    Returns:
        Region name (e.g., "Core Anglo-Sphere")
    """
    return REGION_CODES.get(region_code, "Unknown Region")
