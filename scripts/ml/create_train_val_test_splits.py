#!/usr/bin/env python3
"""
Create Train/Validation/Test Splits from Real Mathematician Data

Splits 9,912 collected profiles into:
- Train: 70% (~6,938)
- Validation: 15% (~1,487)
- Test: 15% (~1,487)

Stratified by region to ensure balanced representation.
"""

import sys
import json
import random
from pathlib import Path
from collections import defaultdict

# Country code to region mapping (ISO 3166-1 alpha-2)
COUNTRY_TO_REGION = {
    # A1 - Anglo-Sphere
    "US": "A1",
    "GB": "A1",
    "CA": "A1",
    "AU": "A1",
    "NZ": "A1",
    "IE": "A1",
    # A2 - Western Europe
    "DE": "A2",
    "FR": "A2",
    "IT": "A2",
    "ES": "A2",
    "PT": "A2",
    "BE": "A2",
    "NL": "A2",
    "CH": "A2",
    "AT": "A2",
    "LU": "A2",
    # A3 - Nordic/Baltic
    "SE": "A3",
    "NO": "A3",
    "DK": "A3",
    "FI": "A3",
    "IS": "A3",
    "EE": "A3",
    "LV": "A3",
    "LT": "A3",
    # A4 - Oceania
    # (AU, NZ already in A1)
    # A5 - Caribbean
    "JM": "A5",
    "TT": "A5",
    "BB": "A5",
    # B1 - East Slavic
    "RU": "B1",
    "UA": "B1",
    "BY": "B1",
    # B2 - South Slavic/Central Europe
    "PL": "B2",
    "CZ": "B2",
    "SK": "B2",
    "HU": "B2",
    "SI": "B2",
    "HR": "B2",
    "RS": "B2",
    "BA": "B2",
    "MK": "B2",
    "BG": "B2",
    "RO": "B2",
    # B3 - Greek
    "GR": "B3",
    "CY": "B3",
    # C1 - Turkic
    "TR": "C1",
    "AZ": "C1",
    "KZ": "C1",
    "UZ": "C1",
    "TM": "C1",
    "KG": "C1",
    # C2 - Persian/Tajik
    "IR": "C2",
    "AF": "C2",
    "TJ": "C2",
    # C3 - Arabic Levant/Nile
    "EG": "C3",
    "IQ": "C3",
    "SY": "C3",
    "LB": "C3",
    "JO": "C3",
    "PS": "C3",
    # C4 - Arabic Gulf
    "SA": "C4",
    "AE": "C4",
    "QA": "C4",
    "KW": "C4",
    "BH": "C4",
    "OM": "C4",
    "YE": "C4",
    # C5 - Arabic Maghreb
    "MA": "C5",
    "DZ": "C5",
    "TN": "C5",
    "LY": "C5",
    # C6 - Hebrew/Diaspora
    "IL": "C6",
    # C7 - Armenian
    "AM": "C7",
    # C8 - Georgian
    "GE": "C8",
    # D1 - South Asia Hindi Belt
    "IN": "D1",
    # D3 - South Asia Bengali
    "BD": "D3",
    # D4 - Pakistan/Urdu
    "PK": "D4",
    # D5 - Sinhala
    "LK": "D5",
    # E1 - Sinophone Mainland
    "CN": "E1",
    # E2 - Traditional Chinese
    "TW": "E2",
    "HK": "E2",
    "MO": "E2",
    # E3 - Japan
    "JP": "E3",
    # E4 - Korea
    "KR": "E4",
    "KP": "E4",
    # E5 - Vietnam
    "VN": "E5",
    # E6 - Mainland SEA
    "TH": "E6",
    "MM": "E6",
    "LA": "E6",
    "KH": "E6",
    # E7 - Maritime SEA
    "MY": "E7",
    "SG": "E7",
    "ID": "E7",
    "PH": "E7",
    "BN": "E7",
    # F1 - SSA Francophone
    "SN": "F1",
    "CI": "F1",
    "ML": "F1",
    "BF": "F1",
    "NE": "F1",
    "TD": "F1",
    "CM": "F1",
    "CG": "F1",
    "CD": "F1",
    "GA": "F1",
    "BJ": "F1",
    "TG": "F1",
    # F2 - SSA Anglophone
    "NG": "F2",
    "GH": "F2",
    "KE": "F2",
    "UG": "F2",
    "TZ": "F2",
    "ZA": "F2",
    "ZW": "F2",
    "ZM": "F2",
    "MW": "F2",
    "BW": "F2",
    "LS": "F2",
    "SZ": "F2",
    # F3 - Horn of Africa
    "ET": "F3",
    "ER": "F3",
    "SO": "F3",
    "DJ": "F3",
    # F4 - Lusophone Africa
    "AO": "F4",
    "MZ": "F4",
    "GW": "F4",
    "CV": "F4",
    "ST": "F4",
    # G1 - Latin America
    "MX": "G1",
    "BR": "G1",
    "AR": "G1",
    "CL": "G1",
    "CO": "G1",
    "VE": "G1",
    "PE": "G1",
    "EC": "G1",
    "BO": "G1",
    "PY": "G1",
    "UY": "G1",
    "GT": "G1",
    "HN": "G1",
    "SV": "G1",
    "NI": "G1",
    "CR": "G1",
    "PA": "G1",
    "CU": "G1",
    "DO": "G1",
    "PR": "G1",
    "HT": "G1",
}


def load_raw_data():
    """Load the collected raw data."""
    data_path = Path("data/ml_training/openalex_20k_raw.json")

    with open(data_path) as f:
        data = json.load(f)

    return data["profiles"]


def map_to_regions(profiles):
    """
    Map country codes to regions and group by region.

    Returns:
        dict: region_code -> list of profiles
    """
    by_region = defaultdict(list)
    unmapped = []

    for profile in profiles:
        country_code = profile.get("country_code")

        if country_code:
            region = COUNTRY_TO_REGION.get(country_code)

            if region:
                profile["region"] = region
                by_region[region].append(profile)
            else:
                unmapped.append(profile)

    return by_region, unmapped


def stratified_split(by_region, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15):
    """
    Split data stratified by region.

    Args:
        by_region: dict of region -> profiles
        train_ratio: Training set ratio (default 0.70)
        val_ratio: Validation set ratio (default 0.15)
        test_ratio: Test set ratio (default 0.15)

    Returns:
        train, val, test lists
    """
    train = []
    val = []
    test = []

    # For reproducibility
    random.seed(42)

    for region, profiles in by_region.items():
        # Shuffle profiles in this region
        shuffled = profiles.copy()
        random.shuffle(shuffled)

        n = len(shuffled)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)

        train.extend(shuffled[:train_end])
        val.extend(shuffled[train_end:val_end])
        test.extend(shuffled[val_end:])

    # Final shuffle to mix regions
    random.shuffle(train)
    random.shuffle(val)
    random.shuffle(test)

    return train, val, test


def save_splits(train, val, test):
    """Save train/val/test splits to separate files."""
    output_dir = Path("data/ml_training")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save train
    train_path = output_dir / "train_split.json"
    with open(train_path, "w") as f:
        json.dump(
            {
                "metadata": {"total": len(train), "split": "train", "ratio": 0.70},
                "profiles": train,
            },
            f,
            indent=2,
        )

    # Save val
    val_path = output_dir / "val_split.json"
    with open(val_path, "w") as f:
        json.dump(
            {
                "metadata": {"total": len(val), "split": "validation", "ratio": 0.15},
                "profiles": val,
            },
            f,
            indent=2,
        )

    # Save test (HOLD OUT - do not touch until final validation)
    test_path = output_dir / "test_split.json"
    with open(test_path, "w") as f:
        json.dump(
            {
                "metadata": {
                    "total": len(test),
                    "split": "test",
                    "ratio": 0.15,
                    "warning": "HOLD OUT - Do not use until final Phase 3 validation",
                },
                "profiles": test,
            },
            f,
            indent=2,
        )

    return train_path, val_path, test_path


def print_stats(by_region, train, val, test, unmapped):
    """Print statistics about the splits."""
    print(f"\n{'='*80}")
    print("TRAIN/VAL/TEST SPLIT SUMMARY")
    print(f"{'='*80}\n")

    print(f"Total profiles: {sum(len(p) for p in by_region.values())}")
    print(f"Unmapped (no region): {len(unmapped)}")
    print()

    print(f"Train: {len(train)} (70%)")
    print(f"Validation: {len(val)} (15%)")
    print(f"Test: {len(test)} (15%)")
    print()

    # Regional distribution
    print("Regional distribution:")
    region_counts = {}
    for region, profiles in sorted(
        by_region.items(), key=lambda x: len(x[1]), reverse=True
    ):
        region_counts[region] = len(profiles)

    for region, count in region_counts.items():
        train_count = sum(1 for p in train if p.get("region") == region)
        val_count = sum(1 for p in val if p.get("region") == region)
        test_count = sum(1 for p in test if p.get("region") == region)
        print(
            f"  {region}: {count} total ({train_count} train, {val_count} val, {test_count} test)"
        )


def main():
    """Create train/val/test splits."""
    print("=" * 80)
    print("CREATING TRAIN/VAL/TEST SPLITS")
    print("=" * 80)
    print()

    # Load data
    print("Loading raw data...")
    profiles = load_raw_data()
    print(f"✅ Loaded {len(profiles)} profiles\n")

    # Map to regions
    print("Mapping to regions...")
    by_region, unmapped = map_to_regions(profiles)
    print(
        f"✅ Mapped {sum(len(p) for p in by_region.values())} profiles to {len(by_region)} regions"
    )
    if unmapped:
        print(f"⚠️  {len(unmapped)} profiles unmapped\n")

    # Create splits
    print("Creating stratified splits (70/15/15)...")
    train, val, test = stratified_split(by_region)
    print(f"✅ Created splits: {len(train)} train, {len(val)} val, {len(test)} test\n")

    # Save
    print("Saving splits...")
    train_path, val_path, test_path = save_splits(train, val, test)
    print(f"✅ Saved to:")
    print(f"   Train: {train_path}")
    print(f"   Val: {val_path}")
    print(f"   Test: {test_path}")

    # Stats
    print_stats(by_region, train, val, test, unmapped)

    print(f"\n{'='*80}")
    print("✅ SPLITS CREATED SUCCESSFULLY")
    print(f"{'='*80}\n")
    print("⚠️  WARNING: Test split is HELD OUT for final Phase 3 validation only!")
    print("    Use validation split for development and tuning.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
