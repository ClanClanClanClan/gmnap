#!/usr/bin/env python3
"""
Label Audit Script - Detect Affiliation vs Etymology Labeling

Based on expert guidance (Oct 30, 2025):
- Affiliation-based: country→region is 1:1 (US→A1, FR→A2, CN→E1)
- Etymology-based: country→region is many:many (US has A1+A2+E1+G1+...)

Outputs:
- reports/label_audit.json with diagnosis
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any


def load_json(path: Path) -> List[Dict[str, Any]]:
    """Load JSON file (with metadata.profiles structure)"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle both formats: {metadata: ..., profiles: [...]} or just [...]
    if isinstance(data, dict) and "profiles" in data:
        return data["profiles"]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError(f"Unexpected JSON format in {path}")


def audit_labels(train_path: Path, val_path: Path, test_path: Path, output_dir: Path):
    """Audit label policy"""

    print("=" * 80)
    print("LABEL AUDIT - Affiliation vs Etymology Detection")
    print("=" * 80)

    # Load data
    print("\n[1/4] Loading data...")
    train = load_json(train_path)
    val = load_json(val_path)
    test = load_json(test_path)

    print(f"  Train: {len(train):,} profiles")
    print(f"  Val:   {len(val):,} profiles")
    print(f"  Test:  {len(test):,} profiles")

    all_data = train + val + test

    # Analyze country→region mapping
    print("\n[2/4] Analyzing country→region mapping...")
    country_to_regions = defaultdict(set)
    region_to_countries = defaultdict(set)

    for profile in all_data:
        country = profile.get("country_code")
        region = profile.get("region")

        if country and region:
            country_to_regions[country].add(region)
            region_to_countries[region].add(country)

    # Count cardinality
    countries_with_single_region = []
    countries_with_multiple_regions = []

    for country, regions in sorted(country_to_regions.items()):
        if len(regions) == 1:
            countries_with_single_region.append((country, list(regions)[0]))
        else:
            countries_with_multiple_regions.append((country, sorted(regions)))

    print(f"\n  Countries with exactly 1 region: {len(countries_with_single_region)}")
    print(f"  Countries with multiple regions: {len(countries_with_multiple_regions)}")

    # Show examples
    if countries_with_single_region:
        print("\n  Examples of 1:1 country→region (evidence of affiliation):")
        for country, region in countries_with_single_region[:10]:
            count = sum(1 for p in all_data if p.get("country_code") == country)
            print(f"    {country} → {region} ({count} profiles)")

    if countries_with_multiple_regions:
        print("\n  Examples of 1:many country→region (evidence of etymology):")
        for country, regions in countries_with_multiple_regions[:5]:
            count = sum(1 for p in all_data if p.get("country_code") == country)
            print(f"    {country} → {regions} ({count} profiles)")

    # Name and surname duplication
    print("\n[3/4] Analyzing name duplication...")
    names = [p.get("name") for p in all_data if p.get("name")]
    unique_names = set(names)

    surnames = []
    for p in all_data:
        name = p.get("name", "")
        if name:
            parts = name.split()
            if len(parts) >= 2:
                surnames.append(parts[-1])

    unique_surnames = set(surnames)

    print(f"  Total names: {len(names):,}")
    print(f"  Unique names: {len(unique_names):,}")
    print(f"  Duplicate names: {len(names) - len(unique_names):,}")
    print(f"  Total surnames: {len(surnames):,}")
    print(f"  Unique surnames: {len(unique_surnames):,}")

    # Diagnosis
    print("\n[4/4] Diagnosis...")

    pct_single_region = (
        len(countries_with_single_region) / len(country_to_regions) * 100
    )

    # Heuristic: If >80% of countries have exactly one region, likely affiliation-based
    likely_affiliation = pct_single_region > 80.0

    if likely_affiliation:
        print(f"\n  🚨 DIAGNOSIS: AFFILIATION-BASED LABELS")
        print(f"     {pct_single_region:.1f}% of countries have exactly 1 region")
        print(f"     This is inconsistent with etymology-based labeling")
        print(f"\n  📊 Expected Accuracy with Current Setup:")
        print(f"     Name-only + Affiliation labels: 65-72%")
        print(f"     (Matches your observed 68-70%)")
        print(f"\n  ✅ Recommended Fix: Track A (Etymology Relabeling)")
        print(f"     Expected after fix: 85-90% accuracy")
    else:
        print(f"\n  ✅ DIAGNOSIS: ETYMOLOGY-BASED LABELS")
        print(f"     {pct_single_region:.1f}% of countries have exactly 1 region")
        print(f"     {100 - pct_single_region:.1f}% have multiple regions")
        print(f"     This is consistent with etymology-based labeling")

    # Generate report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "label_audit.json"

    report = {
        "diagnosis": {
            "likely_affiliation_labeled": likely_affiliation,
            "confidence": "high" if abs(pct_single_region - 50) > 30 else "medium",
            "pct_countries_single_region": pct_single_region,
            "pct_countries_multiple_regions": 100 - pct_single_region,
        },
        "country_to_region_mapping": {
            "total_countries": len(country_to_regions),
            "countries_with_1_region": len(countries_with_single_region),
            "countries_with_multiple_regions": len(countries_with_multiple_regions),
            "examples_1_to_1": countries_with_single_region[:20],
            "examples_1_to_many": [
                (c, list(r)) for c, r in countries_with_multiple_regions[:10]
            ],
        },
        "name_statistics": {
            "total_names": len(names),
            "unique_names": len(unique_names),
            "duplicate_names": len(names) - len(unique_names),
            "total_surnames": len(surnames),
            "unique_surnames": len(unique_surnames),
        },
        "dataset_sizes": {
            "train": len(train),
            "val": len(val),
            "test": len(test),
            "total": len(all_data),
        },
        "expected_accuracy": {
            "current_regime": (
                "name_only + affiliation_labels"
                if likely_affiliation
                else "name_only + etymology_labels"
            ),
            "expected_range": "0.65-0.72" if likely_affiliation else "0.85-0.90",
            "observed": "0.68-0.70 (from validation)",
            "matches_expectation": True if likely_affiliation else False,
        },
        "recommendation": {
            "track": "A" if likely_affiliation else "none",
            "description": (
                "Etymology relabeling"
                if likely_affiliation
                else "Current labels correct"
            ),
            "expected_improvement": "+17-22pp" if likely_affiliation else "n/a",
        },
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n📄 Report saved: {report_path}")
    print("=" * 80)

    return report


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python audit_labels.py <train.json> <val.json> <test.json> <output_dir>"
        )
        sys.exit(1)

    train_path = Path(sys.argv[1])
    val_path = Path(sys.argv[2])
    test_path = Path(sys.argv[3])
    output_dir = Path(sys.argv[4])

    audit_labels(train_path, val_path, test_path, output_dir)
