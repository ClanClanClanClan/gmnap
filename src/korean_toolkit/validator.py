"""
Korean Validator Module - Consolidates validation scripts
Replaces: validate_*.py scripts
"""

import re
from typing import Dict, List, Any


class KoreanValidator:
    """Unified Korean validation system."""

    def __init__(self):
        self.validation_rules = {
            "hangul": self._validate_hangul,
            "romanization": self._validate_romanization,
            "roundtrip": self._validate_roundtrip,
            "mappings": self._validate_mappings,
            "format": self._validate_format,
            "completeness": self._validate_completeness,
        }

        # Hangul Unicode ranges
        self.HANGUL_SYLLABLES = (0xAC00, 0xD7A3)
        self.HANGUL_JAMO = (0x1100, 0x11FF)
        self.HANGUL_COMPAT = (0x3130, 0x318F)

    def validate(self, data: Any, rules: str = "all") -> Dict[str, Any]:
        """
        Main validation entry point.
        Replaces all validate_*.py scripts.

        Args:
            data: Data to validate
            rules: Validation rules to apply or "all"

        Returns:
            Validation results
        """
        if rules == "all":
            results = {}
            for name, validator in self.validation_rules.items():
                try:
                    results[name] = validator(data)
                except Exception as e:
                    results[name] = {"valid": False, "error": str(e)}
            return results

        if rules not in self.validation_rules:
            raise ValueError(f"Unknown validation rule: {rules}")

        return self.validation_rules[rules](data)

    def _validate_hangul(self, text: str) -> Dict[str, Any]:
        """
        Validate Hangul text.
        Replaces: validate_hangul.py
        """
        if not isinstance(text, str):
            return {"valid": False, "error": "Input must be string"}

        issues = []
        stats = {
            "total_chars": len(text),
            "hangul_chars": 0,
            "non_hangul": 0,
            "spaces": text.count(" "),
        }

        for char in text:
            code = ord(char)

            # Check if character is Hangul
            is_hangul = (
                (self.HANGUL_SYLLABLES[0] <= code <= self.HANGUL_SYLLABLES[1])
                or (self.HANGUL_JAMO[0] <= code <= self.HANGUL_JAMO[1])
                or (self.HANGUL_COMPAT[0] <= code <= self.HANGUL_COMPAT[1])
            )

            if is_hangul:
                stats["hangul_chars"] += 1
            elif not char.isspace():
                stats["non_hangul"] += 1
                issues.append(f"Non-Hangul character: '{char}' (U+{code:04X})")

        return {
            "valid": len(issues) == 0,
            "issues": issues[:10],  # Limit to first 10 issues
            "stats": stats,
            "hangul_percentage": (
                (stats["hangul_chars"] / stats["total_chars"] * 100)
                if stats["total_chars"] > 0
                else 0
            ),
        }

    def _validate_romanization(self, data: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate romanization mappings.
        Replaces: validate_romanization.py
        """
        issues = []
        valid_count = 0

        for hangul, roman in data.items():
            # Check Hangul side
            hangul_check = self._validate_hangul(hangul)
            if not hangul_check["valid"]:
                issues.append(f"Invalid Hangul: {hangul}")
                continue

            # Check romanization side
            if not self._is_valid_romanization(roman):
                issues.append(f"Invalid romanization: {hangul} -> {roman}")
                continue

            valid_count += 1

        total = len(data)
        return {
            "valid": len(issues) == 0,
            "valid_count": valid_count,
            "total_count": total,
            "validity_rate": (valid_count / total * 100) if total > 0 else 0,
            "issues": issues[:20],  # Limit issues
        }

    def _validate_roundtrip(self, test_cases: List[Dict]) -> Dict[str, Any]:
        """
        Validate round-trip conversion.
        Replaces: validate_roundtrip.py, validate_tolerant.py
        """
        successes = 0
        failures = []

        for case in test_cases:
            original = case.get("original", "")
            converted = case.get("converted", "")
            roundtrip = case.get("roundtrip", "")

            if original == roundtrip:
                successes += 1
            else:
                failures.append(
                    {
                        "original": original,
                        "converted": converted,
                        "roundtrip": roundtrip,
                        "match": self._calculate_similarity(original, roundtrip),
                    }
                )

        total = len(test_cases)
        return {
            "valid": len(failures) == 0,
            "success_count": successes,
            "failure_count": len(failures),
            "success_rate": (successes / total * 100) if total > 0 else 0,
            "failures": failures[:10],  # Limit to first 10 failures
        }

    def _validate_mappings(self, mappings: List[Dict]) -> Dict[str, Any]:
        """
        Validate mapping structure and content.
        Replaces: validate_mappings.py, validate_fixed.py
        """
        issues = []
        valid_mappings = []

        required_fields = ["hangul", "roman"]
        optional_fields = ["weight", "context", "tags"]

        for i, mapping in enumerate(mappings):
            mapping_issues = []

            # Check required fields
            for field in required_fields:
                if field not in mapping:
                    mapping_issues.append(f"Missing required field: {field}")
                elif not mapping[field]:
                    mapping_issues.append(f"Empty required field: {field}")

            # Validate field contents
            if "hangul" in mapping:
                hangul_check = self._validate_hangul(mapping["hangul"])
                if not hangul_check["valid"]:
                    mapping_issues.append("Invalid Hangul content")

            if "roman" in mapping and not self._is_valid_romanization(mapping["roman"]):
                mapping_issues.append("Invalid romanization")

            if "weight" in mapping:
                try:
                    weight = float(mapping["weight"])
                    if weight < 0 or weight > 100:
                        mapping_issues.append(f"Weight out of range: {weight}")
                except (ValueError, TypeError):
                    mapping_issues.append("Invalid weight value")

            if mapping_issues:
                issues.append(f"Mapping {i}: {', '.join(mapping_issues)}")
            else:
                valid_mappings.append(mapping)

        return {
            "valid": len(issues) == 0,
            "valid_count": len(valid_mappings),
            "total_count": len(mappings),
            "issues": issues[:20],
            "validity_rate": (
                (len(valid_mappings) / len(mappings) * 100) if mappings else 0
            ),
        }

    def _validate_format(self, data: Any) -> Dict[str, Any]:
        """
        Validate data format.
        Replaces: validate_format.py
        """
        issues = []

        if isinstance(data, list):
            if not data:
                issues.append("Empty list")
            elif not all(isinstance(item, dict) for item in data):
                issues.append("List contains non-dict items")

        elif isinstance(data, dict):
            if not data:
                issues.append("Empty dictionary")

        elif isinstance(data, str):
            if not data.strip():
                issues.append("Empty or whitespace-only string")
            # Check for valid CSV format
            if "\n" in data:
                lines = data.strip().split("\n")
                col_counts = [len(line.split(",")) for line in lines]
                if len(set(col_counts)) > 1:
                    issues.append("Inconsistent column count in CSV")
        else:
            issues.append(f"Unexpected data type: {type(data).__name__}")

        return {
            "valid": len(issues) == 0,
            "format_type": type(data).__name__,
            "issues": issues,
        }

    def _validate_completeness(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data completeness.
        Replaces: validate_completeness.py
        """
        missing = []
        coverage = {}

        # Check for expected components
        expected_components = [
            "syllable_mappings",
            "character_mappings",
            "surname_mappings",
            "given_name_mappings",
        ]

        for component in expected_components:
            if component not in data:
                missing.append(component)
            else:
                # Calculate coverage
                items = data[component]
                if isinstance(items, (list, dict)):
                    coverage[component] = len(items)
                else:
                    coverage[component] = 0

        # Calculate overall completeness
        completeness = (
            (len(expected_components) - len(missing)) / len(expected_components) * 100
        )

        return {
            "valid": len(missing) == 0,
            "completeness": completeness,
            "missing_components": missing,
            "coverage": coverage,
        }

    # Helper methods
    def _is_valid_romanization(self, text: str) -> bool:
        """Check if text is valid romanization."""
        if not text:
            return False

        # Allow letters, spaces, hyphens, apostrophes
        pattern = r"^[A-Za-z\s\-']+$"
        return bool(re.match(pattern, text))

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings."""
        if not str1 or not str2:
            return 0.0

        # Simple character-based similarity
        matches = sum(1 for c1, c2 in zip(str1, str2) if c1 == c2)
        max_len = max(len(str1), len(str2))

        return (matches / max_len) if max_len > 0 else 0.0
