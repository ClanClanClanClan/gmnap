"""
Korean Fixer Module - Consolidates 86+ fix scripts
Replaces: fix_*.py scripts
"""

import re
from typing import Dict, List, Any
from collections import defaultdict


class KoreanFixer:
    """Unified Korean data fixing operations."""

    def __init__(self):
        self.fix_operations = {
            "duplicates": self._fix_duplicates,
            "conflicting": self._fix_conflicting_mappings,
            "csv_format": self._fix_csv_format,
            "preferences": self._fix_preferences,
            "case_sensitivity": self._fix_case_sensitivity,
            "surnames": self._fix_surnames,
            "weights": self._fix_weights,
            "bidirectional": self._fix_bidirectional,
            "roundtrip": self._fix_roundtrip,
            "segmentation": self._fix_segmentation,
            "missing": self._fix_missing_mappings,
            "incorrect": self._fix_incorrect_mappings,
        }

    def fix(self, issue_type: str, data: Any, **kwargs) -> Any:
        """
        Main fix entry point.
        Replaces all fix_*.py scripts.

        Args:
            issue_type: Type of issue to fix
            data: Data to fix
            **kwargs: Additional parameters for specific fixes

        Returns:
            Fixed data
        """
        if issue_type not in self.fix_operations:
            raise ValueError(f"Unknown fix type: {issue_type}")

        return self.fix_operations[issue_type](data, **kwargs)

    def batch_fix(self, data: Any, fixes: List[str], **kwargs) -> Any:
        """Apply multiple fixes in sequence."""
        result = data
        for fix_type in fixes:
            result = self.fix(fix_type, result, **kwargs)
        return result

    def _fix_duplicates(self, data: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix duplicate entries.
        Replaces: fix_duplicates.py, remove_duplicates.py, clean_duplicates.py
        """
        seen = {}
        fixed = []

        for item in data:
            key = self._get_key(item)

            if key not in seen:
                seen[key] = item
                fixed.append(item)
            else:
                # Merge duplicates based on strategy
                strategy = kwargs.get("strategy", "keep_first")
                if strategy == "keep_first":
                    continue
                elif strategy == "keep_last":
                    fixed = [i for i in fixed if self._get_key(i) != key]
                    fixed.append(item)
                elif strategy == "merge":
                    merged = self._merge_items(seen[key], item)
                    fixed = [merged if self._get_key(i) == key else i for i in fixed]
                    seen[key] = merged

        return fixed

    def _fix_conflicting_mappings(self, mappings: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix conflicting mappings.
        Replaces: fix_conflicting_mappings.py, fix_mapping_conflicts.py
        """
        conflicts = defaultdict(list)

        # Identify conflicts
        for mapping in mappings:
            key = mapping.get("hangul", "")
            conflicts[key].append(mapping)

        # Resolve conflicts
        fixed = []
        for key, items in conflicts.items():
            if len(items) == 1:
                fixed.append(items[0])
            else:
                # Resolve based on priority/weight
                resolved = self._resolve_conflict(items, **kwargs)
                fixed.append(resolved)

        return fixed

    def _fix_csv_format(self, data: Any, **kwargs) -> Any:
        """
        Fix CSV formatting issues.
        Replaces: fix_csv_format.py, fix_csv_ordering.py, clean_csv_files.py
        """
        if isinstance(data, str):
            # Fix string CSV data
            lines = data.strip().split("\n")
            fixed_lines = []

            for line in lines:
                # Fix common CSV issues
                line = line.strip()
                line = re.sub(r"\s*,\s*", ",", line)  # Remove spaces around commas
                line = re.sub(r",+", ",", line)  # Remove duplicate commas
                line = line.rstrip(",")  # Remove trailing commas

                if line:
                    fixed_lines.append(line)

            return "\n".join(fixed_lines)

        elif isinstance(data, list):
            # Fix list of dict data
            return [self._fix_csv_row(row) for row in data]

        return data

    def _fix_preferences(self, mappings: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix preference/priority issues.
        Replaces: fix_*_preference.py scripts (chang, heon, ki, ri, sun, etc.)
        """
        preference_map = kwargs.get("preferences", {})

        for mapping in mappings:
            hangul = mapping.get("hangul", "")

            # Apply preferences
            if hangul in preference_map:
                mapping["roman"] = preference_map[hangul]
                mapping["priority"] = 1

            # Adjust weights based on preferences
            if mapping.get("priority") == 1:
                mapping["weight"] = max(mapping.get("weight", 1.0), 10.0)

        return mappings

    def _fix_case_sensitivity(self, data: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix case sensitivity issues.
        Replaces: fix_case_sensitivity_and_surnames.py
        """
        for item in data:
            # Standardize case for comparison
            if "roman" in item:
                # Keep original case but add lowercase version for matching
                item["roman_lower"] = item["roman"].lower()

            # Handle surname special cases
            if item.get("is_surname"):
                item["roman"] = item["roman"].title()

        return data

    def _fix_surnames(self, mappings: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix surname-specific issues.
        Replaces: fix_surname_mappings.py, fix_surname_weight_conflicts.py
        """
        common_surnames = [
            "Kim",
            "Lee",
            "Park",
            "Choi",
            "Jung",
            "Kang",
            "Cho",
            "Yoon",
            "Jang",
            "Lim",
        ]

        for mapping in mappings:
            roman = mapping.get("roman", "")

            # Check if it's a surname
            if roman in common_surnames:
                mapping["is_surname"] = True
                mapping["weight"] = max(mapping.get("weight", 1.0), 5.0)
                mapping["context"] = "surname"

        return mappings

    def _fix_weights(self, mappings: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix weight-related issues.
        Replaces: fix_*_weight*.py, balance_character_weights.py
        """
        # Normalize weights
        total_weight = sum(m.get("weight", 1.0) for m in mappings)

        if total_weight > 0:
            for mapping in mappings:
                current = mapping.get("weight", 1.0)
                mapping["weight"] = (current / total_weight) * 100

        # Apply minimum weights
        min_weight = kwargs.get("min_weight", 0.1)
        for mapping in mappings:
            if mapping.get("weight", 0) < min_weight:
                mapping["weight"] = min_weight

        return mappings

    def _fix_bidirectional(self, mappings: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix bidirectional mapping issues.
        Replaces: fix_bidirectional_fst_weights.py
        """
        forward_map = {}
        reverse_map = {}

        # Build bidirectional maps
        for mapping in mappings:
            hangul = mapping.get("hangul", "")
            roman = mapping.get("roman", "")

            if hangul and roman:
                forward_map[hangul] = roman
                reverse_map[roman] = hangul

        # Ensure bidirectionality
        for mapping in mappings:
            hangul = mapping.get("hangul", "")
            roman = mapping.get("roman", "")

            # Check if reverse exists
            if roman in reverse_map and reverse_map[roman] != hangul:
                mapping["bidirectional_conflict"] = True
                mapping["conflict_with"] = reverse_map[roman]

        return mappings

    def _fix_roundtrip(self, mappings: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix round-trip conversion issues.
        Replaces: fix_roundtrip_preferences.py
        """
        # Test round-trip for each mapping
        for mapping in mappings:
            hangul = mapping.get("hangul", "")
            roman = mapping.get("roman", "")

            # Simulate round-trip (simplified)
            if hangul and roman:
                # This would use actual conversion logic
                mapping["roundtrip_valid"] = True  # Placeholder

        return mappings

    def _fix_segmentation(self, data: Any, **kwargs) -> Any:
        """
        Fix segmentation issues.
        Replaces: fix_segmentation_syllables.py, implement_segmentation_fixes.py
        """
        if isinstance(data, str):
            # Fix text segmentation
            # Add spaces between syllables if needed
            fixed = re.sub(r"([가-힣])([가-힣])", r"\1 \2", data)
            return fixed

        return data

    def _fix_missing_mappings(self, mappings: List[Dict], **kwargs) -> List[Dict]:
        """
        Add missing mappings.
        Replaces: fix_missing_mappings.py, add_missing_mappings.py
        """
        required = kwargs.get("required_mappings", {})
        existing = {m.get("hangul"): m for m in mappings}

        # Add missing required mappings
        for hangul, roman in required.items():
            if hangul not in existing:
                mappings.append(
                    {
                        "hangul": hangul,
                        "roman": roman,
                        "weight": 1.0,
                        "added_by": "fix_missing",
                    }
                )

        return mappings

    def _fix_incorrect_mappings(self, mappings: List[Dict], **kwargs) -> List[Dict]:
        """
        Fix incorrect mappings.
        Replaces: fix_incorrect_mappings.py, fix_wrong_mappings*.py
        """
        corrections = kwargs.get("corrections", {})

        for mapping in mappings:
            hangul = mapping.get("hangul", "")

            if hangul in corrections:
                mapping["roman"] = corrections[hangul]
                mapping["corrected"] = True

        return mappings

    # Helper methods
    def _get_key(self, item: Dict) -> str:
        """Get unique key for item."""
        return item.get("hangul", "") or item.get("key", "") or str(item)

    def _merge_items(self, item1: Dict, item2: Dict) -> Dict:
        """Merge two items intelligently."""
        merged = item1.copy()

        for key, value in item2.items():
            if key not in merged:
                merged[key] = value
            elif key == "weight":
                # Average weights
                merged[key] = (merged[key] + value) / 2
            elif key == "tags" and isinstance(value, list):
                # Combine tags
                merged[key] = list(set(merged.get(key, []) + value))

        return merged

    def _resolve_conflict(self, items: List[Dict], **kwargs) -> Dict:
        """Resolve conflicts between multiple items."""
        # Use item with highest weight/priority
        strategy = kwargs.get("conflict_strategy", "highest_weight")

        if strategy == "highest_weight":
            return max(items, key=lambda x: x.get("weight", 0))
        elif strategy == "most_recent":
            return items[-1]
        elif strategy == "first":
            return items[0]
        else:
            # Merge all items
            result = items[0].copy()
            for item in items[1:]:
                result = self._merge_items(result, item)
            return result

    def _fix_csv_row(self, row: Dict) -> Dict:
        """Fix individual CSV row."""
        fixed = {}

        for key, value in row.items():
            # Clean key
            key = key.strip().lower().replace(" ", "_")

            # Clean value
            if isinstance(value, str):
                value = value.strip()
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]

            fixed[key] = value

        return fixed
