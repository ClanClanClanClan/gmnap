#!/usr/bin/env python3
"""
F2 Sub-Saharan Africa Anglophone Region Processor for GMNAP v7
Minimal V7-compliant stub implementation.
"""

import re
import unicodedata
from typing import Any, Dict

from ...base_enhanced import EnhancedRegionSpec as RegionSpec
from ...base_enhanced import RegionRuleError


class F2_SSAAnglophone(RegionSpec):
    """F2 Sub-Saharan Africa Anglophone region processor."""

    def __init__(self):
        super().__init__(
            code="F2",
            yaml_files=["f2_ssa_anglophone.yaml"],
            scripts=["Latin"],
            mixed_scripts=False,
            canonical_order="Given Family",
            romanisation_standards=["BGN/PCGN"],
        )

    def clean(self, entry: Dict[str, Any]) -> None:
        # Apply enhanced base security and normalization
        super().clean(entry)

        """Clean entry according to F2 rules."""
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
                            # Normalize tab to space (V7 edge case)
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

        # Security validation first

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
        """Clean a single F2 name string."""
        if not name:
            return name

        # Basic whitespace normalization
        name = re.sub(r"\s+", " ", name.strip())

        return name

    def augment(self, entry: Dict[str, Any]) -> None:
        # Ensure idempotency
        super().augment(entry)

        """Augment entry with F2-specific data."""
        canonical = entry.get("CanonicalLatin", "")
        if not canonical:
            return

        # Basic regional metadata
        if "RegionalExtras" not in entry:
            entry["RegionalExtras"] = {}

        entry["RegionalExtras"]["region_group"] = "sub_saharan_africa"
        entry["RegionalExtras"]["colonial_influence"] = "english"

    def validate(self, entry: Dict[str, Any]) -> None:
        """Validate entry according to V7 standards."""
        # Use graceful degradation for missing canonical fields
        canonical = self.get_canonical_name(entry)
        if not canonical:
            if not self.has_sufficient_name_data(entry):
                raise RegionRuleError("Entry must have at least one name field")
            else:
                # Has sufficient data but no processable name - skip strict validation
                return

        canonical_latin = entry.get("CanonicalLatin", "").strip()
        canonical_native = entry.get("CanonicalNative", "").strip()

        # Name must have minimum length
        name_to_validate = canonical_latin if canonical_latin else canonical_native
        if len(name_to_validate) < 1:
            raise RegionRuleError("Name cannot be empty")

        # Check for valid Unicode categories
        if not self._has_valid_unicode_categories(name_to_validate):
            raise RegionRuleError(
                f"Name contains invalid characters: {name_to_validate}"
            )

    def order_key(self, entry: Dict[str, Any]) -> str:
        """Generate sort key for F2 names."""
        canonical = entry.get("CanonicalLatin", "")

        # Simple family name extraction for sorting
        if ", " in canonical:
            family = canonical.split(", ")[0]
        else:
            parts = canonical.split()
            family = parts[-1] if parts else canonical

        # Normalize for sorting
        return unicodedata.normalize("NFD", family.lower())

    def _has_valid_unicode_categories(self, text: str) -> bool:
        """Check if text contains only valid Unicode categories."""
        valid_categories = {
            "Lu",
            "Ll",
            "Lt",
            "Lm",
            "Lo",  # Letters
            "Nd",
            "Nl",
            "No",  # Numbers
            "Zs",
            "Zl",
            "Zp",  # Separators
            "Pc",
            "Pd",
            "Pe",
            "Pf",
            "Pi",
            "Po",
            "Ps",  # Punctuation
            "Mn",
            "Mc",
            "Me",  # Marks
        }

        return all(unicodedata.category(char) in valid_categories for char in text)
