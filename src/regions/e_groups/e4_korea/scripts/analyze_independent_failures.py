#!/usr/bin/env python3
"""Analyze independent dataset failures to identify patterns for weight addition."""
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import converter as conv

def analyze_failures():
    # Load test results
    results_path = Path("data/expanded_independent_test_results.json")
    with open(results_path) as f:
        results = json.load(f)
    
    # Collect all failures
    all_failures = []
    for category, data in results["results_by_category"].items():
        all_failures.extend(data.get("failures", []))
    
    print(f"=== INDEPENDENT DATASET FAILURE ANALYSIS ===")
    print(f"Total failures: {len(all_failures)}")
    print(f"Current accuracy: {results['overall_accuracy']:.2f}%")
    print(f"Target: 94%+ (155+ passes from 165 total)\n")
    
    # Group failures by issue type
    by_issue = defaultdict(list)
    for f in all_failures:
        by_issue[f["issue"]].append(f)
    
    print("=== FAILURES BY TYPE ===")
    for issue, cases in by_issue.items():
        print(f"\n{issue}: {len(cases)} cases")
        if issue == "no_conversion":
            print("  These need new mappings in rr_syllable_map.csv:")
            for c in cases[:5]:  # Show first 5
                name = c["name"]
                # Try to identify which syllable fails
                tokens = name.replace(",", "").split()
                for tok in tokens:
                    if not conv.eng2kor(tok.lower()):
                        print(f"    - '{tok.lower()}' from {name}")
        else:  # low_dice_score
            print("  These have partial matches that could be improved:")
            for c in cases[:10]:  # Show first 10
                print(f"    {c['name']}: {c['expected']} → {c['actual']} (dice: {c['dice']:.3f})")
    
    # Analyze specific patterns
    print("\n=== PATTERN ANALYSIS ===")
    
    # Look for specific syllable failures
    failed_syllables = Counter()
    for f in all_failures:
        if f["issue"] == "no_conversion":
            name = f["name"].replace(",", "").lower()
            tokens = name.split()
            for tok in tokens:
                # Test each syllable
                if not conv.eng2kor(tok):
                    failed_syllables[tok] += 1
    
    if failed_syllables:
        print("\nSyllables that need mappings:")
        for syl, count in failed_syllables.most_common(10):
            print(f"  {syl}: {count} occurrences")
    
    # Look for common mismatches in low dice scores
    print("\nCommon character substitutions in low dice scores:")
    substitutions = Counter()
    for f in by_issue["low_dice_score"]:
        expected = f["expected"]
        actual = f["actual"]
        if actual and len(expected) == len(actual):
            for i, (e, a) in enumerate(zip(expected, actual)):
                if e != a:
                    # Find the romanization that produced this
                    name_parts = f["name"].replace(",", "").lower().split()
                    position = "surname" if i == 0 else "given"
                    substitutions[(e, a, position)] += 1
    
    for (exp, act, pos), count in substitutions.most_common(10):
        print(f"  {exp} → {act} ({pos}): {count} times")
    
    # Recommendations
    print("\n=== RECOMMENDATIONS ===")
    print("1. Add mappings for these missing syllables:")
    for syl, _ in failed_syllables.most_common(5):
        print(f"   - {syl}")
    
    print("\n2. Focus on these common patterns:")
    print("   - 'byung' → 병 (not 븅)")
    print("   - 'yeon' → 연 (various contexts)")
    print("   - 'cheong' → 청 (not 정)")
    
    print(f"\n3. With {len(all_failures)} failures, fixing 10+ would achieve 94%+ accuracy")

if __name__ == "__main__":
    analyze_failures()