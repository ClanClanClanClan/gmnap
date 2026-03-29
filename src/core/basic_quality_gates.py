"""
Basic Quality Gates for GMNAP V7 Step 1.2
Simple, working quality checks for basic pipeline validation
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class BasicValidationResult:
    """Result of a basic validation check"""

    passed: bool
    score: float  # 0.0 to 1.0
    gate_name: str
    details: Dict[str, Any]
    errors: List[str]


class BasicQualityGates:
    """
    Basic quality gate system for Step 1.2
    Implements 3 simple, working quality checks:
    1. Required fields check
    2. Format validation
    3. Basic consistency check
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def validate_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Run basic quality checks on an entry"""

        # Quality Check 1: Required Fields
        required_result = self._check_required_fields(entry)

        # Quality Check 2: Format Validation
        format_result = self._check_format_validation(entry)

        # Quality Check 3: Basic Consistency
        consistency_result = self._check_basic_consistency(entry)

        # Aggregate results
        all_results = [required_result, format_result, consistency_result]
        passed = all([r.passed for r in all_results])
        avg_score = sum(r.score for r in all_results) / len(all_results)
        all_errors = []
        for r in all_results:
            all_errors.extend(r.errors)

        return {
            "passed": passed,
            "score": avg_score,
            "gates": {
                "required_fields": {
                    "passed": required_result.passed,
                    "score": required_result.score,
                    "details": required_result.details,
                    "errors": required_result.errors,
                },
                "format_validation": {
                    "passed": format_result.passed,
                    "score": format_result.score,
                    "details": format_result.details,
                    "errors": format_result.errors,
                },
                "basic_consistency": {
                    "passed": consistency_result.passed,
                    "score": consistency_result.score,
                    "details": consistency_result.details,
                    "errors": consistency_result.errors,
                },
            },
            "summary": {
                "gates_run": 3,
                "gates_passed": sum(1 for r in all_results if r.passed),
                "total_errors": len(all_errors),
            },
        }

    def _check_required_fields(self, entry: Dict[str, Any]) -> BasicValidationResult:
        """Check for basic required fields"""
        errors = []
        details = {}

        # Basic required field: CanonicalLatin
        if "CanonicalLatin" not in entry or not entry["CanonicalLatin"]:
            errors.append("Missing required field: CanonicalLatin")
        else:
            canonical = entry["CanonicalLatin"]
            if not isinstance(canonical, str) or len(canonical.strip()) == 0:
                errors.append("CanonicalLatin must be a non-empty string")

        # Track field presence
        details["has_canonical_latin"] = bool(entry.get("CanonicalLatin"))
        details["total_fields"] = len(entry)
        details["field_list"] = list(entry.keys())

        # Score: 1.0 if no errors, 0.5 if has CanonicalLatin but invalid format, 0.0 if missing
        if len(errors) == 0:
            score = 1.0
        elif "CanonicalLatin" in entry:
            score = 0.5  # Present but invalid format
        else:
            score = 0.0  # Missing required field

        return BasicValidationResult(
            passed=len(errors) == 0,
            score=score,
            gate_name="required_fields",
            details=details,
            errors=errors,
        )

    def _check_format_validation(self, entry: Dict[str, Any]) -> BasicValidationResult:
        """Basic format validation checks"""
        errors = []
        details = {}
        checks_passed = 0
        total_checks = 0

        canonical_latin = entry.get("CanonicalLatin", "")

        if canonical_latin:
            # Check 1: No suspicious characters (basic security)
            total_checks += 1
            suspicious_chars = ["<", ">", "{", "}", "\\", "|", "^", "`"]
            has_suspicious = any(char in canonical_latin for char in suspicious_chars)
            if has_suspicious:
                errors.append(f"Contains suspicious characters: {canonical_latin}")
            else:
                checks_passed += 1

            # Check 2: Reasonable length (1-150 characters)
            total_checks += 1
            if len(canonical_latin) > 150:
                errors.append(
                    f"CanonicalLatin too long: {len(canonical_latin)} characters"
                )
            elif len(canonical_latin) < 1:
                errors.append("CanonicalLatin is empty")
            else:
                checks_passed += 1

            # Check 3: Basic name format (contains letters)
            total_checks += 1
            if not re.search(r"[a-zA-Z]", canonical_latin):
                errors.append("CanonicalLatin must contain at least one letter")
            else:
                checks_passed += 1

        # Check numeric fields if present
        if "BirthYear" in entry:
            total_checks += 1
            birth_year = entry["BirthYear"]
            if isinstance(birth_year, int) and 1000 <= birth_year <= 2030:
                checks_passed += 1
            else:
                errors.append(f"Invalid BirthYear: {birth_year}")

        details["format_checks_passed"] = checks_passed
        details["total_format_checks"] = total_checks
        details["canonical_length"] = len(canonical_latin) if canonical_latin else 0

        score = checks_passed / total_checks if total_checks > 0 else 0.0

        return BasicValidationResult(
            passed=len(errors) == 0,
            score=score,
            gate_name="format_validation",
            details=details,
            errors=errors,
        )

    def _check_basic_consistency(self, entry: Dict[str, Any]) -> BasicValidationResult:
        """Basic consistency checks"""
        errors = []
        warnings = []
        details = {}
        consistency_score = 1.0

        canonical_latin = entry.get("CanonicalLatin", "")

        if canonical_latin:
            # Check 1: Name doesn't start/end with whitespace
            if canonical_latin.startswith(" ") or canonical_latin.endswith(" "):
                errors.append("CanonicalLatin has leading/trailing whitespace")
                consistency_score -= 0.3

            # Check 2: No excessive whitespace
            if "  " in canonical_latin:  # Double spaces
                warnings.append("CanonicalLatin contains multiple consecutive spaces")
                consistency_score -= 0.1

            # Check 3: Basic punctuation consistency
            comma_count = canonical_latin.count(",")
            if comma_count > 2:
                warnings.append(f"Unusual comma count: {comma_count}")
                consistency_score -= 0.1

        # Check 4: Field type consistency
        for field, value in entry.items():
            if field == "BirthYear" and value is not None:
                if not isinstance(value, int):
                    errors.append(
                        f"BirthYear should be integer, got {type(value).__name__}"
                    )
                    consistency_score -= 0.3

        details["consistency_score"] = max(0.0, consistency_score)
        details["warnings_count"] = len(warnings)

        return BasicValidationResult(
            passed=len(errors) == 0,
            score=max(0.0, consistency_score),
            gate_name="basic_consistency",
            details=details,
            errors=errors,
        )

    async def validate_batch(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a batch of entries with basic quality checks"""
        results = []

        for entry in entries:
            result = await self.validate_entry(entry)
            results.append(
                {
                    "entry_identifier": entry.get("CanonicalLatin", "unknown"),
                    "validation": result,
                }
            )

        # Calculate batch statistics
        total_entries = len(entries)
        passed_entries = sum(1 for r in results if r["validation"]["passed"])
        avg_score = (
            sum(r["validation"]["score"] for r in results) / total_entries
            if total_entries > 0
            else 0.0
        )

        return {
            "batch_results": results,
            "summary": {
                "total_entries": total_entries,
                "passed_entries": passed_entries,
                "failed_entries": total_entries - passed_entries,
                "validation_rate": (
                    (passed_entries / total_entries * 100) if total_entries > 0 else 0
                ),
                "average_score": avg_score,
            },
            "gate_details": {
                "total_gates": 3,
                "gate_names": [
                    "required_fields",
                    "format_validation",
                    "basic_consistency",
                ],
                "implementation": "basic_step_1_2",
            },
        }
