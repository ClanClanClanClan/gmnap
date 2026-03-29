#!/usr/bin/env python3
"""
Anti-overfitting monitoring system
Detects and prevents overfitting patterns in Korean V5 converter
"""

import yaml
import json
import re
import statistics
from collections import defaultdict, Counter
import argparse
from datetime import datetime, timedelta


class OverfittingDetector:
    """Detect potential overfitting patterns"""

    def __init__(self):
        self.alerts = []
        self.patterns = {
            "full_name_rules": [],
            "suspicious_accuracy": [],
            "test_set_memorization": [],
            "frequency_anomalies": [],
        }

    def check_code_for_overfitting(self, file_paths):
        """Check source code for overfitting patterns"""
        print("Checking source code for overfitting patterns...")

        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Check for full-name rules (BAD pattern from blueprint)
                full_name_patterns = [
                    r'if\s+name\s*==\s*["\'][^"\']+["\']',  # if name == "Kim Jong-un"
                    r'if\s+.*==\s*["\'][^"\']{10,}["\']',  # Long string literals
                    r'["\'][가-힣]{2,}["\'].*==.*["\'][A-Za-z\s-]{10,}["\']',  # Korean to Latin mappings
                ]

                for pattern in full_name_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        self.patterns["full_name_rules"].extend(
                            [
                                {
                                    "file": file_path,
                                    "pattern": match,
                                    "severity": "HIGH",
                                }
                                for match in matches
                            ]
                        )

            except Exception as e:
                print(f"Error checking {file_path}: {e}")

    def check_accuracy_distribution(self, results_file):
        """Check for suspicious accuracy patterns"""
        print("Checking accuracy distribution...")

        try:
            with open(results_file, "r") as f:
                results = json.load(f)

            scores = [r["score"] for r in results if "score" in r]

            if not scores:
                return

            # Check for perfect scores (suspicious)
            perfect_scores = sum(1 for s in scores if s >= 0.999)
            perfect_rate = perfect_scores / len(scores)

            if perfect_rate > 0.8:  # >80% perfect scores is suspicious
                self.patterns["suspicious_accuracy"].append(
                    {
                        "perfect_rate": perfect_rate,
                        "total_scores": len(scores),
                        "severity": "MEDIUM",
                    }
                )

            # Check for bimodal distribution (memorization indicator)
            high_scores = sum(1 for s in scores if s > 0.95)
            low_scores = sum(1 for s in scores if s < 0.5)
            mid_scores = len(scores) - high_scores - low_scores

            if mid_scores < 0.1 * len(scores):  # <10% in middle range
                self.patterns["test_set_memorization"].append(
                    {
                        "high_scores": high_scores,
                        "low_scores": low_scores,
                        "mid_scores": mid_scores,
                        "severity": "HIGH",
                    }
                )

        except Exception as e:
            print(f"Error checking accuracy distribution: {e}")

    def check_frequency_anomalies(self, freq_file):
        """Check syllable frequency for anomalies"""
        print("Checking syllable frequency anomalies...")

        try:
            with open(freq_file, "r", encoding="utf-8") as f:
                freq_data = json.load(f)

            frequencies = list(freq_data.values())

            # Check for artificial frequency spikes
            mean_freq = statistics.mean(frequencies)
            std_freq = statistics.stdev(frequencies)
            threshold = mean_freq + 5 * std_freq  # 5 sigma outliers

            anomalies = []
            for syl, freq in freq_data.items():
                if freq > threshold:
                    anomalies.append(
                        {
                            "syllable": syl,
                            "frequency": freq,
                            "z_score": (freq - mean_freq) / std_freq,
                        }
                    )

            if len(anomalies) > 10:  # More than 10 extreme outliers
                self.patterns["frequency_anomalies"].extend(anomalies)

        except Exception as e:
            print(f"Error checking frequency anomalies: {e}")

    def check_test_set_staleness(self, test_file, max_age_days=30):
        """Check if test set is stale"""
        print("Checking test set staleness...")

        try:
            import os

            stat = os.stat(test_file)
            modified_date = datetime.fromtimestamp(stat.st_mtime)
            age_days = (datetime.now() - modified_date).days

            if age_days > max_age_days:
                self.patterns["test_set_memorization"].append(
                    {
                        "test_file": test_file,
                        "age_days": age_days,
                        "last_modified": modified_date.isoformat(),
                        "severity": "MEDIUM",
                    }
                )

        except Exception as e:
            print(f"Error checking test set staleness: {e}")

    def generate_report(self):
        """Generate overfitting detection report"""
        print("\n=== OVERFITTING DETECTION REPORT ===")

        total_issues = sum(len(patterns) for patterns in self.patterns.values())

        if total_issues == 0:
            print("✅ No overfitting patterns detected")
            return True

        print(f"⚠️  Found {total_issues} potential overfitting issues:")

        # Full-name rules (critical)
        if self.patterns["full_name_rules"]:
            print(
                f"\n🚨 CRITICAL: Full-name rules detected ({len(self.patterns['full_name_rules'])})"
            )
            for rule in self.patterns["full_name_rules"][:5]:  # Show first 5
                print(f"  - {rule['file']}: {rule['pattern']}")

        # Suspicious accuracy
        if self.patterns["suspicious_accuracy"]:
            print(
                f"\n⚠️  Suspicious accuracy patterns ({len(self.patterns['suspicious_accuracy'])})"
            )
            for pattern in self.patterns["suspicious_accuracy"]:
                print(f"  - Perfect score rate: {pattern['perfect_rate']:.1%}")

        # Test set memorization
        if self.patterns["test_set_memorization"]:
            print(
                f"\n⚠️  Test set memorization indicators ({len(self.patterns['test_set_memorization'])})"
            )
            for pattern in self.patterns["test_set_memorization"]:
                if "age_days" in pattern:
                    print(f"  - Stale test set: {pattern['age_days']} days old")
                else:
                    print(
                        f"  - Bimodal distribution: {pattern['high_scores']} high, {pattern['low_scores']} low"
                    )

        # Frequency anomalies
        if self.patterns["frequency_anomalies"]:
            print(
                f"\n⚠️  Frequency anomalies ({len(self.patterns['frequency_anomalies'])})"
            )
            for anomaly in self.patterns["frequency_anomalies"][:3]:  # Show first 3
                print(
                    f"  - {anomaly['syllable']}: {anomaly['frequency']:,} (z={anomaly['z_score']:.1f})"
                )

        # Determine severity
        critical_issues = len(self.patterns["full_name_rules"])
        if critical_issues > 0:
            print(
                f"\n🚨 RESULT: CRITICAL - {critical_issues} critical overfitting patterns found"
            )
            return False
        else:
            print(f"\n⚠️  RESULT: WARNING - {total_issues} potential issues found")
            return True


def stratified_sample(data, n_samples):
    """Stratified sampling for test set rotation"""
    import random

    # Group by name length
    groups = defaultdict(list)
    for entry_id, entry in data.items():
        canonical = entry.get("CanonicalLatin", "")
        length_group = len(canonical) // 5  # Group by length buckets
        groups[length_group].append(entry_id)

    # Sample from each group proportionally
    sampled = []
    for group_ids in groups.values():
        group_sample_size = max(1, int(len(group_ids) * n_samples / len(data)))
        if group_sample_size < len(group_ids):
            sampled.extend(random.sample(group_ids, group_sample_size))

    return sampled[:n_samples]


def run_overfitting_check():
    """Run complete overfitting detection"""
    print("=== Anti-Overfitting Monitor ===")

    detector = OverfittingDetector()

    # Check source code
    source_files = [
        "src/v5/fst_helpers.py",
        "src/v5/converter_with_backoff.py",
        "src/v5/variant_generator.py",
        "src/regions/e_groups/e4_korea_v5.py",
    ]
    detector.check_code_for_overfitting(source_files)

    # Check accuracy patterns
    if os.path.exists("validation_results.json"):
        detector.check_accuracy_distribution("validation_results.json")

    # Check frequency data
    if os.path.exists("data/syllable_freq.json"):
        detector.check_frequency_anomalies("data/syllable_freq.json")

    # Check test set staleness
    if os.path.exists("data/korean.yaml"):
        detector.check_test_set_staleness("data/korean.yaml")

    # Generate report
    return detector.generate_report()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor for overfitting patterns")
    parser.add_argument(
        "--source-files",
        nargs="+",
        default=["src/v5/*.py", "src/regions/e_groups/e4_korea*.py"],
        help="Source files to check",
    )
    parser.add_argument(
        "--results-file",
        default="validation_results.json",
        help="Validation results file",
    )

    args = parser.parse_args()

    import os

    success = run_overfitting_check()
    exit(0 if success else 1)
