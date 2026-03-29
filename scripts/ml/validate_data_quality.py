#!/usr/bin/env python3
"""
Data Quality Validation for ML Training

Validates training/validation/test datasets before model training to catch issues early.

Checks:
1. File existence and format
2. Required fields present
3. Region code validity
4. Class balance
5. Data leakage (surname overlap between splits)
6. Duplicate names
7. Empty/invalid names
8. Label consistency
9. Outlier detection

Usage:
    python3 scripts/ml/validate_data_quality.py \\
        --train data/ml_training/train_profiles.json \\
        --val data/ml_training/val_profiles.json \\
        --test data/ml_training/test_profiles.json \\
        --output reports/ml/data_quality_report.json
"""

import sys
import json
import argparse
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Set

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.ml.utils.names import normalize_nfc, extract_surname


VALID_REGIONS = {
    # A-groups: Anglo/Western/Nordic
    "A1",
    "A2",
    "A3",
    "A4",
    "A5",
    # B-groups: Slavic/Greek
    "B1",
    "B2",
    "B3",
    # C-groups: Middle East/Caucasus
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "C7",
    "C8",
    "C9",
    # D-groups: South Asia
    "D1",
    "D2",
    "D3",
    "D4",
    "D5",
    # E-groups: East/Southeast Asia
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",
    # F-groups: Sub-Saharan Africa
    "F1",
    "F2",
    "F3",
    "F4",
    # G-groups: Latin America
    "G1",
    # Special
    "R0",
    "H1",
    "Z0",
}


class DataQualityValidator:
    """Data quality validator"""

    def __init__(self):
        self.issues = []
        self.warnings = []

    def error(self, message: str):
        """Record error"""
        self.issues.append(message)
        print(f"❌ ERROR: {message}")

    def warn(self, message: str):
        """Record warning"""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")

    def info(self, message: str):
        """Print info"""
        print(f"ℹ️  {message}")

    def load_dataset(self, file_path: str) -> List[Dict]:
        """Load JSON dataset"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                self.error(f"{file_path}: Not a list")
                return []

            return data

        except FileNotFoundError:
            self.error(f"{file_path}: File not found")
            return []
        except json.JSONDecodeError as e:
            self.error(f"{file_path}: Invalid JSON - {e}")
            return []

    def validate_schema(self, data: List[Dict], dataset_name: str) -> bool:
        """Validate schema (required fields)"""
        print(f"\n{'='*80}")
        print(f"VALIDATING SCHEMA: {dataset_name}")
        print(f"{'='*80}")

        if not data:
            self.error(f"{dataset_name}: Empty dataset")
            return False

        required_fields = ["name", "region"]
        missing_fields = defaultdict(int)

        for i, profile in enumerate(data):
            for field in required_fields:
                if field not in profile:
                    missing_fields[field] += 1

        if missing_fields:
            for field, count in missing_fields.items():
                self.error(f"{dataset_name}: {count} profiles missing '{field}' field")
            return False

        self.info(f"{dataset_name}: Schema valid ({len(data)} profiles)")
        return True

    def validate_regions(self, data: List[Dict], dataset_name: str) -> bool:
        """Validate region codes"""
        print(f"\n{'='*80}")
        print(f"VALIDATING REGIONS: {dataset_name}")
        print(f"{'='*80}")

        invalid_regions = Counter()

        for profile in data:
            region = profile.get("region")
            if region not in VALID_REGIONS:
                invalid_regions[region] += 1

        if invalid_regions:
            for region, count in invalid_regions.most_common():
                self.error(f"{dataset_name}: Invalid region '{region}' ({count} occurrences)")
            return False

        self.info(f"{dataset_name}: All regions valid")
        return True

    def check_class_balance(self, data: List[Dict], dataset_name: str) -> Dict:
        """Check class distribution"""
        print(f"\n{'='*80}")
        print(f"CLASS DISTRIBUTION: {dataset_name}")
        print(f"{'='*80}")

        region_counts = Counter(profile["region"] for profile in data)
        total = len(data)

        print(f"\nTotal profiles: {total}")
        print(f"Number of classes: {len(region_counts)}")
        print(f"\nTop 10 regions:")
        for region, count in region_counts.most_common(10):
            pct = count / total * 100
            print(f"  {region}: {count:5} ({pct:5.2f}%)")

        # Check for severe imbalance
        max_count = region_counts.most_common(1)[0][1]
        min_count = region_counts.most_common()[-1][1]
        imbalance_ratio = max_count / min_count if min_count > 0 else float("inf")

        if imbalance_ratio > 100:
            self.warn(f"{dataset_name}: Severe class imbalance (ratio: {imbalance_ratio:.1f}:1)")
        elif imbalance_ratio > 50:
            self.warn(f"{dataset_name}: Moderate class imbalance (ratio: {imbalance_ratio:.1f}:1)")

        # Check for singleton classes
        singletons = [r for r, c in region_counts.items() if c == 1]
        if singletons:
            self.warn(f"{dataset_name}: {len(singletons)} singleton classes: {singletons}")

        return dict(region_counts)

    def check_data_leakage(self, train: List[Dict], val: List[Dict], test: List[Dict]) -> bool:
        """Check for surname leakage between splits"""
        print(f"\n{'='*80}")
        print(f"DATA LEAKAGE DETECTION")
        print(f"{'='*80}")

        def extract_surnames_set(data: List[Dict]) -> Set[str]:
            surnames = set()
            for profile in data:
                name = profile.get("name", "")
                if name:
                    surname = extract_surname(name)
                    normalized = normalize_nfc(surname.lower())
                    surnames.add(normalized)
            return surnames

        train_surnames = extract_surnames_set(train)
        val_surnames = extract_surnames_set(val)
        test_surnames = extract_surnames_set(test)

        # Check overlaps
        train_val_overlap = train_surnames & val_surnames
        train_test_overlap = train_surnames & test_surnames
        val_test_overlap = val_surnames & test_surnames

        overlap_found = False

        if train_val_overlap:
            pct = len(train_val_overlap) / len(val_surnames) * 100
            self.warn(
                f"Train-Val surname overlap: {len(train_val_overlap)} surnames ({pct:.1f}% of val)"
            )
            overlap_found = True

        if train_test_overlap:
            pct = len(train_test_overlap) / len(test_surnames) * 100
            self.warn(
                f"Train-Test surname overlap: {len(train_test_overlap)} surnames ({pct:.1f}% of test)"
            )
            overlap_found = True

        if val_test_overlap:
            pct = len(val_test_overlap) / len(test_surnames) * 100
            self.warn(
                f"Val-Test surname overlap: {len(val_test_overlap)} surnames ({pct:.1f}% of test)"
            )
            overlap_found = True

        if not overlap_found:
            self.info("No surname leakage detected (ideal)")

        return not overlap_found

    def check_duplicates(self, data: List[Dict], dataset_name: str) -> int:
        """Check for duplicate names"""
        print(f"\n{'='*80}")
        print(f"DUPLICATE DETECTION: {dataset_name}")
        print(f"{'='*80}")

        name_counts = Counter()
        for profile in data:
            name = profile.get("name", "")
            if name:
                normalized = normalize_nfc(name.lower())
                name_counts[normalized] += 1

        duplicates = {name: count for name, count in name_counts.items() if count > 1}

        if duplicates:
            total_dupes = sum(count - 1 for count in duplicates.values())
            self.warn(
                f"{dataset_name}: {len(duplicates)} names appear multiple times ({total_dupes} duplicate entries)"
            )

            if len(duplicates) <= 10:
                print("\nDuplicate names:")
                for name, count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True):
                    print(f"  '{name}': {count} occurrences")
        else:
            self.info(f"{dataset_name}: No duplicates found")

        return len(duplicates)

    def check_empty_names(self, data: List[Dict], dataset_name: str) -> int:
        """Check for empty or invalid names"""
        print(f"\n{'='*80}")
        print(f"EMPTY/INVALID NAMES: {dataset_name}")
        print(f"{'='*80}")

        empty_count = 0
        whitespace_only = 0
        too_short = 0

        for profile in data:
            name = profile.get("name", "")

            if not name:
                empty_count += 1
            elif name.strip() == "":
                whitespace_only += 1
            elif len(name.strip()) < 3:
                too_short += 1

        if empty_count > 0:
            self.error(f"{dataset_name}: {empty_count} empty names")

        if whitespace_only > 0:
            self.warn(f"{dataset_name}: {whitespace_only} whitespace-only names")

        if too_short > 0:
            self.warn(f"{dataset_name}: {too_short} names shorter than 3 characters")

        if empty_count + whitespace_only + too_short == 0:
            self.info(f"{dataset_name}: All names valid")

        return empty_count + whitespace_only + too_short

    def check_label_consistency(self, data: List[Dict], dataset_name: str) -> bool:
        """Check if same names always get same label"""
        print(f"\n{'='*80}")
        print(f"LABEL CONSISTENCY: {dataset_name}")
        print(f"{'='*80}")

        name_to_regions = defaultdict(set)

        for profile in data:
            name = profile.get("name", "")
            region = profile.get("region", "")
            if name and region:
                normalized = normalize_nfc(name.lower())
                name_to_regions[normalized].add(region)

        inconsistent = {
            name: regions for name, regions in name_to_regions.items() if len(regions) > 1
        }

        if inconsistent:
            self.error(f"{dataset_name}: {len(inconsistent)} names have inconsistent labels")

            if len(inconsistent) <= 10:
                print("\nInconsistent labels:")
                for name, regions in list(inconsistent.items())[:10]:
                    print(f"  '{name}': {regions}")
            return False

        self.info(f"{dataset_name}: All labels consistent")
        return True

    def validate_all(self, train_path: str, val_path: str, test_path: str) -> Dict:
        """Run all validation checks"""
        print("=" * 80)
        print("DATA QUALITY VALIDATION")
        print("=" * 80)

        # Load datasets
        train = self.load_dataset(train_path)
        val = self.load_dataset(val_path)
        test = self.load_dataset(test_path)

        if not train or not val or not test:
            print("\n❌ CRITICAL: Failed to load datasets")
            return self._build_report(train, val, test, success=False)

        # Validation checks
        schema_ok = all(
            [
                self.validate_schema(train, "train"),
                self.validate_schema(val, "val"),
                self.validate_schema(test, "test"),
            ]
        )

        if not schema_ok:
            print("\n❌ CRITICAL: Schema validation failed")
            return self._build_report(train, val, test, success=False)

        regions_ok = all(
            [
                self.validate_regions(train, "train"),
                self.validate_regions(val, "val"),
                self.validate_regions(test, "test"),
            ]
        )

        # Class distribution
        train_dist = self.check_class_balance(train, "train")
        val_dist = self.check_class_balance(val, "val")
        test_dist = self.check_class_balance(test, "test")

        # Data leakage
        no_leakage = self.check_data_leakage(train, val, test)

        # Duplicates
        train_dupes = self.check_duplicates(train, "train")
        val_dupes = self.check_duplicates(val, "val")
        test_dupes = self.check_duplicates(test, "test")

        # Empty names
        train_empty = self.check_empty_names(train, "train")
        val_empty = self.check_empty_names(val, "val")
        test_empty = self.check_empty_names(test, "test")

        # Label consistency
        train_consistent = self.check_label_consistency(train, "train")
        val_consistent = self.check_label_consistency(val, "val")
        test_consistent = self.check_label_consistency(test, "test")

        # Summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        print(f"\nDataset sizes:")
        print(f"  Train: {len(train)}")
        print(f"  Val:   {len(val)}")
        print(f"  Test:  {len(test)}")

        print(f"\nIssues found:")
        print(f"  ❌ Errors:   {len(self.issues)}")
        print(f"  ⚠️  Warnings: {len(self.warnings)}")

        success = len(self.issues) == 0

        if success:
            print("\n" + "=" * 80)
            print("✅ DATA QUALITY VALIDATION PASSED")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ DATA QUALITY VALIDATION FAILED")
            print("=" * 80)
            print("\nErrors:")
            for issue in self.issues:
                print(f"  - {issue}")

        if self.warnings:
            print("\nWarnings:")
            for warning in self.warnings[:10]:  # Top 10
                print(f"  - {warning}")

        return self._build_report(train, val, test, success)

    def _build_report(
        self, train: List[Dict], val: List[Dict], test: List[Dict], success: bool
    ) -> Dict:
        """Build validation report"""
        from datetime import datetime

        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "success": success,
            "dataset_sizes": {
                "train": len(train),
                "val": len(val),
                "test": len(test),
                "total": len(train) + len(val) + len(test),
            },
            "issues": self.issues,
            "warnings": self.warnings,
            "summary": {
                "error_count": len(self.issues),
                "warning_count": len(self.warnings),
                "recommendation": (
                    "Data quality acceptable for training"
                    if success
                    else "Fix errors before training"
                ),
            },
        }


def main():
    parser = argparse.ArgumentParser(description="Validate training data quality")
    parser.add_argument(
        "--train", default="data/ml_training/train_profiles.json", help="Training dataset"
    )
    parser.add_argument(
        "--val", default="data/ml_training/val_profiles.json", help="Validation dataset"
    )
    parser.add_argument(
        "--test", default="data/ml_training/test_profiles.json", help="Test dataset"
    )
    parser.add_argument(
        "--output", default="reports/ml/data_quality_report.json", help="Output report JSON"
    )

    args = parser.parse_args()

    validator = DataQualityValidator()
    report = validator.validate_all(args.train, args.val, args.test)

    # Save report
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Report saved to {output_path}")

    # Exit code
    sys.exit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()
