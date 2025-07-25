#!/usr/bin/env python3
"""
Validation utilities for Korean round-trip conversion.
Implements Dice coefficient measurement per GMNAP v6.1 specs.
"""

import unicodedata
from typing import Tuple, List, Dict
from dataclasses import dataclass
import json


@dataclass 
class ValidationResult:
    """Result of a round-trip validation"""
    original: str
    converted: str
    back_converted: str
    dice_score: float
    passes_threshold: bool
    details: Dict[str, any] = None


def normalize_for_comparison(text: str) -> str:
    """
    Normalize text for comparison per GMNAP specs.
    Apply NFC normalization and casefold.
    """
    # Apply NFC normalization
    nfc_normalized = unicodedata.normalize('NFC', text)
    # Apply casefolding for case-insensitive comparison
    return nfc_normalized.casefold()


def calculate_dice_coefficient(str1: str, str2: str) -> float:
    """
    Calculate Dice coefficient between two strings.
    
    Dice coefficient = 2 * |intersection| / (|set1| + |set2|)
    
    Args:
        str1: First string
        str2: Second string
        
    Returns:
        Dice coefficient between 0 and 1
    """
    # Normalize both strings
    norm1 = normalize_for_comparison(str1)
    norm2 = normalize_for_comparison(str2)
    
    # If both empty, they're identical
    if not norm1 and not norm2:
        return 1.0
    
    # If one is empty, they're completely different
    if not norm1 or not norm2:
        return 0.0
    
    # Calculate character-level bigrams for better matching
    def get_bigrams(text):
        if len(text) < 2:
            return {text}
        return {text[i:i+2] for i in range(len(text) - 1)}
    
    bigrams1 = get_bigrams(norm1)
    bigrams2 = get_bigrams(norm2)
    
    # Calculate intersection
    intersection = bigrams1 & bigrams2
    
    # Calculate Dice coefficient
    if len(bigrams1) + len(bigrams2) == 0:
        return 0.0
    
    dice = 2.0 * len(intersection) / (len(bigrams1) + len(bigrams2))
    return dice


def validate_round_trip(
    romanized: str,
    to_hangul_fn,
    to_roman_fn,
    threshold: float = 0.97
) -> ValidationResult:
    """
    Validate round-trip conversion accuracy.
    
    Args:
        romanized: Original romanized Korean text
        to_hangul_fn: Function to convert romanized to Hangul
        to_roman_fn: Function to convert Hangul back to romanized
        threshold: Minimum Dice coefficient required (default 0.97 per specs)
        
    Returns:
        ValidationResult with conversion details
    """
    # Convert to Hangul
    hangul = to_hangul_fn(romanized)
    
    # Convert back to romanized
    back_converted = to_roman_fn(hangul)
    
    # Calculate Dice coefficient
    dice_score = calculate_dice_coefficient(romanized, back_converted)
    
    # Check if it passes threshold
    passes = dice_score >= threshold
    
    # Prepare details
    details = {
        "normalized_original": normalize_for_comparison(romanized),
        "normalized_back": normalize_for_comparison(back_converted),
        "threshold": threshold
    }
    
    return ValidationResult(
        original=romanized,
        converted=hangul,
        back_converted=back_converted,
        dice_score=dice_score,
        passes_threshold=passes,
        details=details
    )


def batch_validate(
    test_cases: List[str],
    to_hangul_fn,
    to_roman_fn,
    threshold: float = 0.97
) -> Tuple[float, List[ValidationResult]]:
    """
    Validate multiple test cases and return overall accuracy.
    
    Args:
        test_cases: List of romanized Korean names to test
        to_hangul_fn: Function to convert romanized to Hangul
        to_roman_fn: Function to convert Hangul back to romanized
        threshold: Minimum Dice coefficient required
        
    Returns:
        Tuple of (overall_accuracy, individual_results)
    """
    results = []
    passed = 0
    
    for test_case in test_cases:
        result = validate_round_trip(test_case, to_hangul_fn, to_roman_fn, threshold)
        results.append(result)
        if result.passes_threshold:
            passed += 1
    
    accuracy = passed / len(test_cases) if test_cases else 0.0
    
    return accuracy, results


def generate_validation_report(
    results: List[ValidationResult],
    output_file: str = None
) -> str:
    """
    Generate a detailed validation report.
    
    Args:
        results: List of validation results
        output_file: Optional file to save report
        
    Returns:
        Report as string
    """
    passed = sum(1 for r in results if r.passes_threshold)
    total = len(results)
    accuracy = passed / total if total > 0 else 0.0
    
    report_lines = [
        "Korean Round-trip Validation Report",
        "=" * 50,
        f"Total test cases: {total}",
        f"Passed: {passed}",
        f"Failed: {total - passed}",
        f"Accuracy: {accuracy:.1%}",
        f"Threshold: {results[0].details['threshold'] if results else 0.97}",
        "",
        "Failed Cases:",
        "-" * 50
    ]
    
    # Add failed cases
    failed_cases = [r for r in results if not r.passes_threshold]
    for i, result in enumerate(failed_cases[:20], 1):  # Show first 20 failures
        report_lines.extend([
            f"\n{i}. Original: {result.original}",
            f"   Hangul: {result.converted}",
            f"   Back: {result.back_converted}",
            f"   Dice: {result.dice_score:.3f}"
        ])
    
    if len(failed_cases) > 20:
        report_lines.append(f"\n... and {len(failed_cases) - 20} more failures")
    
    # Add distribution of scores
    report_lines.extend([
        "",
        "Score Distribution:",
        "-" * 50
    ])
    
    score_ranges = {
        "1.00": 0,
        "0.95-0.99": 0,
        "0.90-0.94": 0,
        "0.80-0.89": 0,
        "< 0.80": 0
    }
    
    for result in results:
        score = result.dice_score
        if score == 1.0:
            score_ranges["1.00"] += 1
        elif score >= 0.95:
            score_ranges["0.95-0.99"] += 1
        elif score >= 0.90:
            score_ranges["0.90-0.94"] += 1
        elif score >= 0.80:
            score_ranges["0.80-0.89"] += 1
        else:
            score_ranges["< 0.80"] += 1
    
    for range_name, count in score_ranges.items():
        percentage = count / total * 100 if total > 0 else 0
        report_lines.append(f"  {range_name}: {count} ({percentage:.1f}%)")
    
    report = "\n".join(report_lines)
    
    # Save to file if requested
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
    
    return report


# Testing functions
if __name__ == "__main__":
    # Test Dice coefficient calculation
    print("Dice Coefficient Tests:")
    print("-" * 40)
    
    test_pairs = [
        ("kim", "kim"),
        ("Kim", "kim"),  # Should match after normalization
        ("park", "pak"),
        ("lee", "yi"),
        ("kimtaehyung", "kim taehyung"),
        ("abc", "xyz"),
    ]
    
    for s1, s2 in test_pairs:
        dice = calculate_dice_coefficient(s1, s2)
        print(f"{s1:15} vs {s2:15} = {dice:.3f}")
    
    # Test round-trip validation
    print("\n\nRound-trip Validation Test:")
    print("-" * 40)
    
    # Mock conversion functions
    def mock_to_hangul(roman):
        mapping = {"kim": "김", "park": "박", "lee": "이"}
        return mapping.get(roman.lower(), roman)
    
    def mock_to_roman(hangul):
        mapping = {"김": "kim", "박": "park", "이": "lee"}
        return mapping.get(hangul, hangul)
    
    test_names = ["kim", "park", "lee", "choi"]
    
    for name in test_names:
        result = validate_round_trip(name, mock_to_hangul, mock_to_roman)
        status = "PASS" if result.passes_threshold else "FAIL"
        print(f"{name}: {result.original} → {result.converted} → {result.back_converted} "
              f"(Dice: {result.dice_score:.3f}) [{status}]")