#!/usr/bin/env python3
"""
Phase 2 ML - Day 1: Apply Test Data Relabeling

Apply high-confidence relabeling corrections to test data.
This fixes 139 mislabeled cases where the system predictions are
actually correct but ground truth is wrong.

Based on: data/analysis/high_conf_disagreements.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    print("=" * 80)
    print("TEST DATA RELABELING")
    print("=" * 80)
    print()

    # Load relabel candidates
    analysis_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "analysis"
        / "high_conf_disagreements.json"
    )

    if not analysis_file.exists():
        print(f"Error: {analysis_file} not found")
        print("Run scripts/ml/analyze_high_confidence_disagreements.py first")
        return 1

    with open(analysis_file) as f:
        analysis = json.load(f)

    relabel_candidates = analysis["relabel_candidates"]

    print(f"Loaded {len(relabel_candidates)} relabel candidates")
    print()

    # Category breakdown
    by_category = defaultdict(int)
    for candidate in relabel_candidates:
        by_category[candidate["category"]] += 1

    print("CATEGORY BREAKDOWN:")
    print("-" * 80)
    for category, count in sorted(
        by_category.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {category.replace('_', ' ').title()}: {count}")
    print()

    # Load test data
    test_file = (
        Path(__file__).parent.parent.parent
        / "data"
        / "test_suites"
        / "tier1_regional_comprehensive.json"
    )

    if not test_file.exists():
        print(f"Error: {test_file} not found")
        return 1

    with open(test_file) as f:
        test_data = json.load(f)

    original_entries = test_data["test_data"]
    total_entries = len(original_entries)

    print(f"Loaded {total_entries} test entries")
    print()

    # Create backup
    backup_file = (
        test_file.parent
        / f"{test_file.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    print(f"Creating backup: {backup_file.name}")
    with open(backup_file, "w") as f:
        json.dump(test_data, f, indent=2)
    print()

    # Create lookup for relabeling
    # Key: (name, original_region) -> new_region
    relabel_map = {}
    for candidate in relabel_candidates:
        name = candidate["name"]
        original_region = candidate["expected"]
        new_region = candidate["relabel_to"]

        if new_region is not None:
            # Normalize regions (remove _synthetic suffix if present)
            key = (name, original_region.upper().replace("_SYNTHETIC", ""))
            relabel_map[key] = new_region

    print(f"Created relabel map with {len(relabel_map)} entries")
    print()

    # Apply relabeling
    print("Applying relabeling...")
    relabeled_count = 0
    relabel_stats = defaultdict(lambda: {"from": [], "to": []})

    for entry in original_entries:
        name = entry["CanonicalNative"]
        original_region = entry["Region"].upper().replace("_SYNTHETIC", "")

        key = (name, original_region)
        if key in relabel_map:
            new_region = relabel_map[key]

            # Update region (preserve _synthetic suffix if present)
            if "_synthetic" in entry["Region"].lower():
                entry["Region"] = f"{new_region}_synthetic"
            else:
                entry["Region"] = new_region

            relabeled_count += 1
            relabel_stats[f"{original_region}→{new_region}"]["from"].append(
                original_region
            )
            relabel_stats[f"{original_region}→{new_region}"]["to"].append(new_region)

    print(f"  Relabeled {relabeled_count} entries")
    print()

    # Save updated test data
    print(f"Saving updated test data to: {test_file}")
    with open(test_file, "w") as f:
        json.dump(test_data, f, indent=2)
    print()

    # Show relabeling statistics
    print("=" * 80)
    print("RELABELING STATISTICS")
    print("=" * 80)
    print()

    print(f"{'Transition':<20} {'Count':>8}")
    print("-" * 80)
    for transition, stats in sorted(
        relabel_stats.items(), key=lambda x: len(x[1]["from"]), reverse=True
    ):
        count = len(stats["from"])
        print(f"{transition:<20} {count:>8}")

    print()
    print(
        f"Total relabeled: {relabeled_count}/{total_entries} ({relabeled_count/total_entries*100:.2f}%)"
    )
    print()

    # Expected accuracy improvement
    original_accuracy = analysis["overall_accuracy"]
    expected_new_accuracy = analysis["summary"]["conservative_accuracy"]
    improvement = expected_new_accuracy - original_accuracy

    print("=" * 80)
    print("EXPECTED IMPACT")
    print("=" * 80)
    print()
    print(f"Original accuracy: {original_accuracy:.2f}%")
    print(f"Expected new accuracy: {expected_new_accuracy:.2f}%")
    print(f"Improvement: +{improvement:.2f}pp")
    print()

    # Next steps
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Rerun validation to confirm accuracy improvement:")
    print("   python scripts/ml/validate_topk_accuracy.py")
    print()
    print("2. If results look good, Day 1 is complete!")
    print()
    print("3. Day 2-3: Collect real Math Genealogy data and retrain")
    print("   python scripts/ml/collect_mathgenealogy_data.py")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
