#!/usr/bin/env python3
"""
Auto-Fix System v2: Architecture-Aware Korean Name Fix Generator

This enhanced version understands the converter's segmentation behavior
and generates appropriate fixes based on fix viability.
"""

import json
import csv
from collections import defaultdict, Counter
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set
import unicodedata
import yaml
import sys
import os

# Add src to path
sys.path.insert(0, "../../src")
from segment_fixed import segment
from syllable_lexicon_fixed import LEXICON


class FixType(Enum):
    """Classification of fix types based on architecture compatibility"""

    SINGLE_SYLLABLE = 1  # Works directly (e.g., um → 음)
    MULTI_SYLLABLE = 2  # Blocked by segmentation (e.g., boo → 부)
    COMPOUND_MAPPING = 3  # Needs compound recognition
    PRE_PROCESSOR = 4  # Needs pre-processing override
    LEXICON_UPDATE = 5  # Needs lexicon addition


@dataclass
class Fix:
    """Represents a proposed fix with metadata"""

    pattern: str
    hangul: str
    fix_type: FixType
    confidence: float
    context: str  # 'surname' or 'given'
    test_cases: List[str]
    expected_impact: int
    safety_score: float
    implementation: str
    viable: bool  # Can this fix work with current architecture?


class ArchitectureAwareAnalyzer:
    """Analyzes failures with awareness of converter architecture"""

    def __init__(self):
        self.load_data()
        self.segment_cache = {}

    def load_data(self):
        """Load existing mappings and resources"""
        # Load syllable map
        self.syllable_map = {}
        with open("resources/rr_syllable_map.csv", "r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and not row[0].startswith("#"):
                    hangul, roman = row[0], row[1]
                    self.syllable_map[roman] = hangul

        # Load variant map
        self.variant_map = defaultdict(list)
        with open("resources/variant_map.csv", "r", encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and not row[0].startswith("#"):
                    hangul, roman = row[0], row[1]
                    self.variant_map[hangul].append(roman)

    def test_segmentation(self, text: str) -> List[str]:
        """Test how the segmenter will process this text"""
        if text not in self.segment_cache:
            self.segment_cache[text] = segment(text.lower())
        return self.segment_cache[text]

    def classify_fix(
        self, pattern: str, hangul: str, context: str
    ) -> Tuple[FixType, bool]:
        """Classify fix type and determine if viable with current architecture"""
        # Test segmentation
        segments = self.test_segmentation(pattern)

        # Single syllable - always viable
        if len(segments) == 1 and segments[0] == pattern.lower():
            return FixType.SINGLE_SYLLABLE, True

        # Multi-syllable that gets segmented - not viable without changes
        if len(segments) > 1:
            # Check if it's in lexicon
            if pattern.lower() in LEXICON:
                return FixType.SINGLE_SYLLABLE, True
            else:
                return FixType.MULTI_SYLLABLE, False

        # Compound that needs special handling
        if len(hangul) > 1:
            return FixType.COMPOUND_MAPPING, False

        return FixType.PRE_PROCESSOR, False

    def analyze_failure(
        self, name: str, expected: str, actual: Optional[str], is_surname: bool = False
    ) -> Optional[Fix]:
        """Analyze a single failure and propose fix"""
        if actual is None:
            # Missing mapping
            pattern = name.lower()

            # Check segmentation behavior
            fix_type, viable = self.classify_fix(
                pattern, expected, "surname" if is_surname else "given"
            )

            # Generate implementation based on viability
            if viable:
                impl = f'echo "{expected},{pattern}" >> resources/rr_syllable_map.csv'
            else:
                # Provide alternative implementation strategies
                if fix_type == FixType.MULTI_SYLLABLE:
                    impl = (
                        f'# WARNING: "{pattern}" segments to {self.test_segmentation(pattern)}\n'
                        f"# Option 1: Add to lexicon first\n"
                        f"# Option 2: Use pre-processor override\n"
                        f"# Option 3: Modify segmenter rules"
                    )
                else:
                    impl = f"# Requires architectural change for compound mapping"

            return Fix(
                pattern=pattern,
                hangul=expected,
                fix_type=fix_type,
                confidence=0.9 if viable else 0.5,
                context="surname" if is_surname else "given",
                test_cases=[name],
                expected_impact=1,
                safety_score=1.0,
                implementation=impl,
                viable=viable,
            )

        return None


class EnhancedFixGenerator:
    """Generates fixes with architecture awareness"""

    def __init__(self, analyzer: ArchitectureAwareAnalyzer):
        self.analyzer = analyzer

    def generate_fixes(self, failures: List[Dict]) -> List[Fix]:
        """Generate fixes for a list of failures"""
        fixes = []
        fix_patterns = defaultdict(list)

        print(f"Analyzing {len(failures)} failures...")

        # Group failures by pattern
        for failure in failures:
            name = failure["name"]
            fail_type = failure.get("fail_type", "eng→kor")

            if fail_type == "eng→kor":
                expected = failure.get("expected")
                actual = failure.get("actual")

                print(
                    f"  Processing: {name} -> expected '{expected}', actual '{actual}'"
                )

                if not expected:
                    print(f"    Skipping {name}: no expected value")
                    continue

                # Extract name parts
                parts = name.split("_")
                if len(parts) >= 2:
                    surname = parts[0].lower()
                    given_parts = "_".join(parts[1:]).lower().replace("-", "")

                    # Analyze surname failures
                    if actual is None or (
                        actual
                        and len(actual) > 0
                        and len(expected) > 0
                        and actual[0] != expected[0]
                    ):
                        print(
                            f"    Surname issue detected: {surname} -> {expected[0] if expected else 'N/A'}"
                        )
                        fix = self.analyzer.analyze_failure(
                            surname,
                            expected[0] if expected else "",
                            actual[0] if actual and len(actual) > 0 else None,
                            is_surname=True,
                        )
                        if fix:
                            fix_patterns[f"surname_{surname}"].append(fix)
                            print(
                                f"      Generated fix: {fix.pattern} -> {fix.hangul} (viable: {fix.viable})"
                            )

                    # Analyze given name failures
                    if actual and len(expected) > 1 and len(actual) > 1:
                        for i, (exp_char, act_char) in enumerate(
                            zip(expected[1:], actual[1:]), 1
                        ):
                            if exp_char != act_char:
                                print(
                                    f"    Given name issue: char {i+1} {exp_char} != {act_char}"
                                )
                                # Try to find the romanization that caused this
                                name_part = given_parts
                                fix = self.analyzer.analyze_failure(
                                    name_part, exp_char, act_char, is_surname=False
                                )
                                if fix:
                                    fix_patterns[f"given_{name_part}"].append(fix)
                                    print(
                                        f"      Generated fix: {fix.pattern} -> {fix.hangul} (viable: {fix.viable})"
                                    )
                                break

        # Consolidate and rank fixes
        for pattern, fix_list in fix_patterns.items():
            if fix_list:
                # Take the most common fix for this pattern
                fix = fix_list[0]
                fix.expected_impact = len(fix_list)
                fix.test_cases = [f.test_cases[0] for f in fix_list]
                fixes.append(fix)

        # Sort by viability and impact
        fixes.sort(
            key=lambda f: (f.viable, f.expected_impact, f.confidence), reverse=True
        )

        return fixes


def main():
    """Main execution"""
    print("=== Auto-Fix System v2: Architecture-Aware ===\n")

    # Load test results
    print("Loading test results...")
    try:
        with open("data/diverse_failures.json", "r", encoding="utf-8") as f:
            failures = json.load(f)
        print(f"Loaded {len(failures)} failures from diverse dataset")
    except FileNotFoundError:
        print("Diverse failure data not found, run test_diverse_dataset.py first")
        return

    # Initialize system
    analyzer = ArchitectureAwareAnalyzer()
    generator = EnhancedFixGenerator(analyzer)

    # Generate fixes
    print("\nAnalyzing failures with architecture awareness...")
    fixes = generator.generate_fixes(failures)

    # Report results
    print(f"\nGenerated {len(fixes)} fixes:")
    print(f"- Viable fixes: {sum(1 for f in fixes if f.viable)}")
    print(f"- Blocked by architecture: {sum(1 for f in fixes if not f.viable)}")

    print("\n=== VIABLE FIXES (Will Work Now) ===")
    for fix in fixes:
        if fix.viable:
            print(f"\n{fix.pattern} → {fix.hangul}")
            print(f"  Type: {fix.fix_type.name}")
            print(f"  Confidence: {fix.confidence:.2f}")
            print(f"  Impact: {fix.expected_impact} names")
            print(f"  Implementation: {fix.implementation}")

    print("\n=== ARCHITECTURAL BLOCKS (Need Converter Changes) ===")
    for fix in fixes:
        if not fix.viable:
            print(f"\n{fix.pattern} → {fix.hangul}")
            print(f"  Type: {fix.fix_type.name}")
            print(f"  Segmentation: {analyzer.test_segmentation(fix.pattern)}")
            print(f"  Reason: Pattern segments before variant lookup")
            print(f"  Solution:\n{fix.implementation}")

    # Generate implementation script
    print("\n=== IMPLEMENTATION SCRIPT ===")
    print("# Run these commands to apply viable fixes:")
    for fix in fixes:
        if fix.viable:
            print(fix.implementation)

    print("\n# Then rebuild FSTs:")
    print("python3 scripts/build_fsts_multi.py")

    # Summary recommendations
    print("\n=== RECOMMENDATIONS ===")
    viable_count = sum(1 for f in fixes if f.viable)
    blocked_count = sum(1 for f in fixes if not f.viable)

    print(
        f"1. Apply {viable_count} viable fixes immediately (est. +{viable_count * 0.5}% accuracy)"
    )
    print(f"2. {blocked_count} fixes need architecture changes for full benefit")
    print(
        "3. Consider adding pre-segmentation variant checking for multi-syllable patterns"
    )
    print("4. Track blocked patterns for future converter improvements")


if __name__ == "__main__":
    main()
