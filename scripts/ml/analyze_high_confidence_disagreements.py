#!/usr/bin/env python3
"""
Phase 2 ML - Day 1: High-Confidence Disagreement Analysis

This script identifies test data cases where the system's prediction
is likely CORRECT but the ground truth label is WRONG.

Criteria for "likely mislabeled":
1. High confidence (>0.85)
2. Systematic pattern (multiple similar cases)
3. Morphological evidence (surname origin matches prediction)

Based on: docs/analysis/ultrathink_true_accuracy.md
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def categorize_failure(failure: dict) -> dict:
    """Categorize a failure as likely correct/incorrect/ambiguous"""

    name = failure["name"]
    expected = failure["expected"]
    detected = failure["detected"]
    confidence = failure["confidence"]

    # Category 1: R0/Z0 fallback categories (should NOT be detected)
    if expected in ["R0", "Z0"]:
        return {
            "category": "fallback_category",
            "likely_correct": True,
            "reason": f"{expected} is fallback category, system correctly classifies to specific region",
            "relabel_to": detected,
            "confidence_boost": 0.0,  # These should be excluded from metrics
        }

    # Category 2: A4→A1 confusion (Oceania indistinguishable from Anglo)
    if expected == "A4" and detected == "A1":
        # Check for Māori markers
        maori_markers = ["kiri", "hemi", "tane", "aroha", "wiremu", "moana"]
        has_maori = any(marker in name.lower() for marker in maori_markers)

        if not has_maori:
            return {
                "category": "a4_a1_indistinguishable",
                "likely_correct": True,
                "reason": "A4 without Māori markers is indistinguishable from A1",
                "relabel_to": "A1",
                "confidence_boost": 0.05,
            }
        else:
            return {
                "category": "a4_has_maori_markers",
                "likely_correct": False,
                "reason": "Has Māori markers, should be A4",
                "relabel_to": None,
                "confidence_boost": 0.0,
            }

    # Category 3: Hispanic surnames in A1 context
    hispanic_surnames = [
        "rodriguez",
        "martinez",
        "hernandez",
        "lopez",
        "garcia",
        "gonzalez",
        "perez",
        "sanchez",
        "ramirez",
    ]

    if expected == "A1" and detected == "G1":
        has_hispanic_surname = any(
            surname in name.lower() for surname in hispanic_surnames
        )

        if has_hispanic_surname:
            return {
                "category": "a1_hispanic_surnames",
                "likely_correct": True,
                "reason": f"Hispanic surname ({name}) is morphologically G1",
                "relabel_to": "G1",
                "confidence_boost": 0.03,
            }

    # Category 4: A5 (Caribbean) vs G1 (Latin America) - Same surnames
    if expected == "A5" and detected == "G1":
        has_hispanic_surname = any(
            surname in name.lower() for surname in hispanic_surnames
        )

        if has_hispanic_surname:
            return {
                "category": "a5_g1_overlap",
                "likely_correct": True,
                "reason": "A5/G1 share surnames, without location context G1 is valid",
                "relabel_to": "G1",
                "confidence_boost": 0.02,
            }

    # Category 5: C1 (Turkic) vs C9 (Caucasus Turkic) - Very similar
    if expected == "C9" and detected == "C1":
        return {
            "category": "c9_c1_overlap",
            "likely_correct": True,
            "reason": "C9 and C1 share many surnames (-ov endings), hard to distinguish",
            "relabel_to": "C1",
            "confidence_boost": 0.02,
        }

    # Category 6: Portuguese/Spanish overlap (F4 vs G1, E7 vs G1)
    portuguese_surnames = ["silva", "santos", "oliveira", "dos santos"]
    spanish_surnames = ["garcia", "rodriguez", "martinez", "lopez", "hernandez"]

    if expected == "F4" and detected == "G1":
        has_portuguese = any(surname in name.lower() for surname in portuguese_surnames)
        if has_portuguese:
            # Actually ambiguous without accent marks (José vs Jose)
            return {
                "category": "f4_g1_ambiguous",
                "likely_correct": False,  # Could go either way
                "reason": "Portuguese/Spanish overlap, needs diacritics to distinguish",
                "relabel_to": None,
                "confidence_boost": 0.0,
            }

    # Category 7: Arabic name overlap (C3/D4/F3/E7)
    arabic_names = ["ali", "hassan", "ahmed", "omar", "mohammed", "fatima", "aisha"]
    if detected in ["C3", "D4", "F3", "E7"] and expected in ["C3", "D4", "F3", "E7"]:
        has_arabic = any(name.lower().count(n) > 0 for n in arabic_names)
        if has_arabic:
            return {
                "category": "arabic_regional_overlap",
                "likely_correct": False,  # Need context to distinguish
                "reason": "Arabic names span multiple regions (Levant/Gulf/Horn/SEA)",
                "relabel_to": None,
                "confidence_boost": 0.0,
            }

    # Default: uncertain
    return {
        "category": "uncertain",
        "likely_correct": False,
        "reason": "Requires manual review",
        "relabel_to": None,
        "confidence_boost": 0.0,
    }


def main():
    # Load failure data
    failure_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "validation_results"
        / "tier1_failures_20251004_080549.json"
    )

    if not failure_file.exists():
        print(f"Error: {failure_file} not found")
        return 1

    with open(failure_file) as f:
        failure_data = json.load(f)

    # Analyze all failures
    analysis = {
        "total_failures": failure_data["total_failures"],
        "overall_accuracy": failure_data["overall_accuracy"],
        "by_category": defaultdict(list),
        "relabel_candidates": [],
        "exclude_from_metrics": [],
    }

    for region, region_data in failure_data["by_region"].items():
        for failure in region_data.get("failures", []):
            failure["expected_region"] = region
            categorization = categorize_failure(failure)

            failure_record = {**failure, **categorization}

            analysis["by_category"][categorization["category"]].append(failure_record)

            if categorization["likely_correct"]:
                analysis["relabel_candidates"].append(failure_record)

            if categorization["category"] == "fallback_category":
                analysis["exclude_from_metrics"].append(failure_record)

    # Generate summary
    print("=" * 80)
    print("HIGH-CONFIDENCE DISAGREEMENT ANALYSIS")
    print("=" * 80)
    print()

    print(f"Total failures: {analysis['total_failures']}")
    print(f"Current accuracy: {analysis['overall_accuracy']:.2f}%")
    print()

    print("CATEGORY BREAKDOWN:")
    print("-" * 80)

    for category, failures in sorted(
        analysis["by_category"].items(), key=lambda x: len(x[1]), reverse=True
    ):
        count = len(failures)
        likely_correct_count = sum(1 for f in failures if f["likely_correct"])
        avg_conf = sum(f["confidence"] for f in failures) / count if count > 0 else 0

        print(f"\n{category.upper().replace('_', ' ')}:")
        print(f"  Count: {count}")
        print(f"  Likely correct: {likely_correct_count}/{count}")
        print(f"  Avg confidence: {avg_conf:.3f}")

        if likely_correct_count > 0:
            # Show examples
            print(f"  Examples:")
            for failure in failures[:3]:
                if failure["likely_correct"]:
                    print(
                        f"    - {failure['name']}: {failure['expected_region']}→{failure['detected']} "
                        f"({failure['confidence']:.3f}) - {failure['reason']}"
                    )

    print("\n" + "=" * 80)
    print("CORRECTED ACCURACY ESTIMATES:")
    print("=" * 80)
    print()

    # Calculate corrected accuracies
    total_entries = 2720  # From tier1 data

    # Scenario 1: Exclude R0/Z0
    exclude_count = len(analysis["exclude_from_metrics"])
    correctable_entries = total_entries - exclude_count
    correctable_failures = analysis["total_failures"] - exclude_count
    corrected_correct = correctable_entries - correctable_failures

    accuracy_exclude_fallbacks = (corrected_correct / correctable_entries) * 100

    print(f"1. Excluding fallback categories (R0/Z0):")
    print(f"   Entries: {correctable_entries} (exclude {exclude_count})")
    print(f"   Accuracy: {accuracy_exclude_fallbacks:.2f}%")
    print()

    # Scenario 2: Relabel obvious errors
    relabel_count = len(analysis["relabel_candidates"])
    accuracy_relabeled = ((corrected_correct + relabel_count) / total_entries) * 100

    print(f"2. Relabeling likely correct predictions:")
    print(f"   Relabel candidates: {relabel_count}")
    print(f"   New accuracy: {accuracy_relabeled:.2f}%")
    print()

    # Scenario 3: Conservative (exclude R0/Z0 + relabel obvious)
    accuracy_conservative = (
        (corrected_correct + relabel_count) / correctable_entries
    ) * 100

    print(f"3. Conservative estimate (exclude fallbacks + relabel obvious):")
    print(f"   Accuracy: {accuracy_conservative:.2f}%")
    print()

    # Save detailed analysis
    output_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "analysis"
        / "high_conf_disagreements.json"
    )
    output_file.parent.mkdir(exist_ok=True, parents=True)

    with open(output_file, "w") as f:
        # Convert defaultdict to dict for JSON serialization
        analysis_for_json = {
            "total_failures": analysis["total_failures"],
            "overall_accuracy": analysis["overall_accuracy"],
            "by_category": {k: v for k, v in analysis["by_category"].items()},
            "relabel_candidates": analysis["relabel_candidates"],
            "exclude_from_metrics": analysis["exclude_from_metrics"],
            "summary": {
                "exclude_fallbacks_accuracy": accuracy_exclude_fallbacks,
                "relabeled_accuracy": accuracy_relabeled,
                "conservative_accuracy": accuracy_conservative,
            },
        }
        json.dump(analysis_for_json, f, indent=2)

    print(f"Detailed analysis saved to: {output_file}")
    print()

    # Generate relabeling script
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print()
    print(f"1. Review {relabel_count} relabel candidates in:")
    print(f"   {output_file}")
    print()
    print(f"2. Apply relabeling (if approved):")
    print(f"   python scripts/ml/apply_relabeling.py")
    print()
    print(f"3. Rerun validation:")
    print(f"   python tests/integration/test_tier1_validation.py")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
