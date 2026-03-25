"""
Linguistic Rules Engine for GMNAP.
Implements name normalization, validation, and standardization rules.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """Types of linguistic rules."""

    NORMALIZATION = "normalization"
    VALIDATION = "validation"
    STANDARDIZATION = "standardization"
    ROMANIZATION = "romanization"
    TRANSLITERATION = "transliteration"


@dataclass
class LinguisticRule:
    """A linguistic rule for name processing."""

    id: str
    name: str
    type: RuleType
    description: str
    pattern: str
    replacement: str = ""
    priority: int = 100
    enabled: bool = True
    regions: List[str] = None  # Regions this rule applies to
    scripts: List[str] = None  # Scripts this rule applies to


class LinguisticRulesEngine:
    """
    Engine for applying linguistic rules to names.

    Implements essential rules for:
    - Unicode normalization
    - Punctuation standardization
    - Whitespace normalization
    - Case normalization
    - Character validation
    """

    def __init__(self):
        self.rules: Dict[str, LinguisticRule] = {}
        self._load_essential_rules()

    def _load_essential_rules(self):
        """Load essential linguistic rules."""

        # Essential normalization rules
        essential_rules = [
            LinguisticRule(
                id="unicode_nfc",
                name="Unicode NFC Normalization",
                type=RuleType.NORMALIZATION,
                description="Normalize Unicode to NFC form",
                pattern=r".*",
                priority=10,
            ),
            LinguisticRule(
                id="trim_whitespace",
                name="Trim Whitespace",
                type=RuleType.NORMALIZATION,
                description="Remove leading/trailing whitespace",
                pattern=r"^\s+|\s+$",
                replacement="",
                priority=20,
            ),
            LinguisticRule(
                id="normalize_spaces",
                name="Normalize Internal Spaces",
                type=RuleType.NORMALIZATION,
                description="Replace multiple spaces with single space",
                pattern=r"\s+",
                replacement=" ",
                priority=30,
            ),
            LinguisticRule(
                id="normalize_commas",
                name="Normalize Comma Spacing",
                type=RuleType.STANDARDIZATION,
                description="Ensure comma is followed by single space",
                pattern=r",\s*",
                replacement=", ",
                priority=40,
            ),
            LinguisticRule(
                id="remove_extra_punctuation",
                name="Remove Extra Punctuation",
                type=RuleType.NORMALIZATION,
                description="Remove repeated punctuation marks",
                pattern=r"([.,;:]){2,}",
                replacement=r"\1",
                priority=50,
            ),
            LinguisticRule(
                id="normalize_hyphens",
                name="Normalize Hyphens",
                type=RuleType.STANDARDIZATION,
                description="Standardize various dash characters to hyphen",
                pattern=r"[—–−]",
                replacement="-",
                priority=60,
            ),
            LinguisticRule(
                id="normalize_apostrophes",
                name="Normalize Apostrophes",
                type=RuleType.STANDARDIZATION,
                description="Standardize various apostrophe characters",
                pattern=r"[''`´]",
                replacement="'",
                priority=70,
            ),
            LinguisticRule(
                id="remove_control_chars",
                name="Remove Control Characters",
                type=RuleType.NORMALIZATION,
                description="Remove Unicode control characters",
                pattern=r"[\x00-\x1f\x7f-\x9f]",
                replacement="",
                priority=80,
            ),
            LinguisticRule(
                id="validate_name_length",
                name="Validate Name Length",
                type=RuleType.VALIDATION,
                description="Names must be 1-200 characters",
                pattern=r"^.{1,200}$",
                priority=90,
            ),
            LinguisticRule(
                id="fix_comma_space_order",
                name="Fix Comma Space Order",
                type=RuleType.STANDARDIZATION,
                description="Fix names with space before comma",
                pattern=r"\s+,",
                replacement=",",
                priority=45,
            ),
        ]

        for rule in essential_rules:
            self.rules[rule.id] = rule

        logger.info(f"Loaded {len(essential_rules)} essential linguistic rules")

    def apply_rules(
        self, text: str, rule_types: List[RuleType] = None, region: str = None, script: str = None
    ) -> Tuple[str, List[str]]:
        """
        Apply linguistic rules to text.

        Args:
            text: Input text to process
            rule_types: Types of rules to apply (all if None)
            region: Region code to filter rules
            script: Script to filter rules

        Returns:
            Tuple of (processed_text, applied_rule_ids)
        """
        if not text:
            return text, []

        processed = text
        applied_rules = []

        # Filter rules
        applicable_rules = []
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            if rule_types and rule.type not in rule_types:
                continue

            if region and rule.regions and region not in rule.regions:
                continue

            if script and rule.scripts and script not in rule.scripts:
                continue

            applicable_rules.append(rule)

        # Sort by priority
        applicable_rules.sort(key=lambda r: r.priority)

        # Apply rules in order
        for rule in applicable_rules:
            try:
                if rule.id == "unicode_nfc":
                    # Special handling for Unicode normalization
                    new_text = unicodedata.normalize("NFC", processed)
                elif rule.id == "validate_name_length":
                    # Special handling for validation rules
                    if not re.match(rule.pattern, processed):
                        logger.warning(f"Name length validation failed: {len(processed)} chars")
                        continue
                    new_text = processed
                else:
                    # Regular regex replacement
                    new_text = re.sub(rule.pattern, rule.replacement, processed)

                if new_text != processed:
                    applied_rules.append(rule.id)
                    processed = new_text

            except Exception as e:
                logger.error(f"Failed to apply rule {rule.id}: {e}")
                continue

        return processed, applied_rules

    def normalize_name(self, name: str, region: str = None) -> Dict[str, Any]:
        """
        Normalize a name using standard rules.

        Args:
            name: Name to normalize
            region: Region code for context

        Returns:
            Dictionary with normalized name and metadata
        """
        if not name:
            return {"original": name, "normalized": name, "applied_rules": [], "warnings": []}

        warnings = []

        # Apply normalization rules
        normalized, norm_rules = self.apply_rules(
            name, rule_types=[RuleType.NORMALIZATION], region=region
        )

        # Apply standardization rules
        standardized, std_rules = self.apply_rules(
            normalized, rule_types=[RuleType.STANDARDIZATION], region=region
        )

        # Validation
        _, val_rules = self.apply_rules(
            standardized, rule_types=[RuleType.VALIDATION], region=region
        )

        # Check for common issues
        if len(standardized.strip()) == 0:
            warnings.append("Name is empty after normalization")

        if len(standardized) != len(standardized.strip()):
            warnings.append("Name has leading/trailing whitespace")

        if standardized != standardized.strip():
            standardized = standardized.strip()
            norm_rules.append("manual_trim")

        # Check for suspicious patterns
        if re.search(r"\d{3,}", standardized):
            warnings.append("Name contains long number sequence")

        if re.search(r"[^\w\s\-\',.]", standardized):
            warnings.append("Name contains unusual characters")

        all_rules = norm_rules + std_rules + val_rules

        return {
            "original": name,
            "normalized": standardized,
            "applied_rules": all_rules,
            "warnings": warnings,
            "rule_count": len(all_rules),
        }

    def validate_name(self, name: str, region: str = None) -> Dict[str, Any]:
        """
        Validate a name against linguistic rules.

        Args:
            name: Name to validate
            region: Region code for context

        Returns:
            Validation result with errors and warnings
        """
        result = {"valid": True, "errors": [], "warnings": [], "score": 1.0}

        if not name:
            result["valid"] = False
            result["errors"].append("Name is empty")
            result["score"] = 0.0
            return result

        # Check length
        if len(name) > 200:
            result["valid"] = False
            result["errors"].append(f"Name too long: {len(name)} > 200 characters")
            result["score"] -= 0.3

        if len(name.strip()) < 2:
            result["warnings"].append("Name is very short")
            result["score"] -= 0.1

        # Check for invalid characters
        control_chars = re.findall(r"[\x00-\x1f\x7f-\x9f]", name)
        if control_chars:
            result["valid"] = False
            result["errors"].append(f"Contains control characters: {control_chars}")
            result["score"] -= 0.5

        # Check structure
        if not re.search(r"[A-Za-zÀ-ÿА-я\u4e00-\u9fff]", name):
            result["warnings"].append("No alphabetic characters found")
            result["score"] -= 0.2

        # Check for excessive punctuation
        punct_ratio = len(re.findall(r"[^\w\s]", name)) / len(name)
        if punct_ratio > 0.3:
            result["warnings"].append("High punctuation ratio")
            result["score"] -= 0.1

        # Ensure score is non-negative
        result["score"] = max(0.0, result["score"])

        return result

    def get_rule_stats(self) -> Dict[str, Any]:
        """Get statistics about loaded rules."""
        stats = {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules.values() if r.enabled),
            "by_type": {},
            "by_priority": {},
        }

        for rule in self.rules.values():
            # Count by type
            rule_type = rule.type.value
            stats["by_type"][rule_type] = stats["by_type"].get(rule_type, 0) + 1

            # Count by priority range
            priority_range = f"{(rule.priority // 10) * 10}-{(rule.priority // 10) * 10 + 9}"
            stats["by_priority"][priority_range] = stats["by_priority"].get(priority_range, 0) + 1

        return stats

    def add_rule(self, rule: LinguisticRule) -> None:
        """Add a new linguistic rule."""
        self.rules[rule.id] = rule
        logger.info(f"Added rule: {rule.id}")

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule by ID."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule by ID."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
            return True
        return False
