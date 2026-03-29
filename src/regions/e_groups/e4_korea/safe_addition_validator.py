#!/usr/bin/env python3
"""
Safe Addition Validator: Test proposed changes without breaking existing functionality
This is the core tool for regression-free expansion of the Korean name system.
"""

import json
import shutil
import subprocess
import sys

sys.path.append("src")
# from converter import eng2kor, kor2eng, eng2kor_nbest, _enhanced_dice


class SafeAdditionValidator:
    def __init__(self):
        """Initialize validator with regression locks"""
        self.regression_locks = self.load_regression_locks()
        self.backup_files = {}

    def load_regression_locks(self):
        """Load all regression lock files"""
        locks = {}
        for dataset in ["math", "diverse", "independent"]:
            try:
                with open(f"{dataset}_lock.json", "r", encoding="utf8") as f:
                    locks[dataset] = json.load(f)
                print(f"✅ Loaded {len(locks[dataset])} locked cases for {dataset}")
            except FileNotFoundError:
                print(f"⚠️  No lock file found for {dataset} - run create_regression_lock.py first")
                locks[dataset] = []
        return locks

    def create_backups(self):
        """Backup current system state"""
        files_to_backup = [
            "resources/rr_syllable_map.csv",
            "src/converter.py",
            "scripts/validate.py",
        ]

        for file_path in files_to_backup:
            backup_path = f"{file_path}.backup_temp"
            try:
                shutil.copy2(file_path, backup_path)
                self.backup_files[file_path] = backup_path
            except Exception as e:
                print(f"⚠️  Could not backup {file_path}: {e}")

    def restore_backups(self):
        """Restore system to previous state"""
        for original, backup in self.backup_files.items():
            try:
                shutil.copy2(backup, original)
            except Exception as e:
                print(f"❌ Failed to restore {original}: {e}")

        # Rebuild FSTs after restoration
        self.rebuild_fsts()

    def rebuild_fsts(self):
        """Rebuild FST files after changes"""
        try:
            result = subprocess.run(
                ["python3", "scripts/build_fsts_multi.py"], capture_output=True, text=True
            )
            if result.returncode != 0:
                print(f"⚠️  FST rebuild warning: {result.stderr}")
        except Exception as e:
            print(f"❌ FST rebuild failed: {e}")

    def test_case_passes(self, case):
        """Test if a locked case still passes"""
        try:
            rr = case["input"]
            ko_expected = case["expected_korean"]

            # Test conversion
            ko = eng2kor(rr)
            hypos = eng2kor_nbest(rr, n=3)

            if ko_expected in hypos:
                ko = ko_expected
            elif ko != ko_expected:
                return False, f"Conversion failed: {rr} → {ko} (expected {ko_expected})"

            # Test roundtrip
            rr2 = kor2eng(ko, rr) or ""
            dice_score = _enhanced_dice(rr, rr2)

            if dice_score < 0.90:
                return False, f"Roundtrip failed: {rr} → {rr2} (dice={dice_score:.3f})"

            return True, "OK"

        except Exception as e:
            return False, f"Error testing case: {e}"

    def validate_no_regression(self):
        """Test all locked cases to ensure no regression"""
        regressions = []

        for dataset_name, locked_cases in self.regression_locks.items():
            dataset_regressions = []

            for case in locked_cases:
                passes, reason = self.test_case_passes(case)
                if not passes:
                    dataset_regressions.append(
                        {
                            "case_name": case["name"],
                            "input": case["input"],
                            "expected": case["expected_korean"],
                            "reason": reason,
                        }
                    )

            if dataset_regressions:
                regressions.append(
                    {
                        "dataset": dataset_name,
                        "count": len(dataset_regressions),
                        "total_locked": len(locked_cases),
                        "failures": dataset_regressions,
                    }
                )

        return regressions

    def add_csv_weights(self, new_weights):
        """Add new weights to CSV file"""
        try:
            with open("resources/rr_syllable_map.csv", "a", encoding="utf8") as f:
                f.write("\n# Safe addition validation weights\n")
                for weight_entry in new_weights:
                    f.write(f"{weight_entry}\n")
            return True
        except Exception as e:
            print(f"❌ Failed to add weights: {e}")
            return False

    def test_proposed_addition(
        self, proposed_weights=None, proposed_equivalences=None, description="Proposed change"
    ):
        """Test a proposed addition for safety"""
        print(f"\n🧪 Testing: {description}")

        # Create backups
        self.create_backups()

        try:
            # Apply proposed changes
            if proposed_weights:
                if not self.add_csv_weights(proposed_weights):
                    return {"safe": False, "reason": "Failed to apply weights"}

            if proposed_equivalences:
                # Note: This would require modifying converter.py
                # For now, we focus on weight additions
                print("⚠️  Equivalence modifications not yet implemented")

            # Rebuild FSTs with changes
            self.rebuild_fsts()

            # Test for regressions
            regressions = self.validate_no_regression()

            if not regressions:
                result = {"safe": True, "reason": "No regressions detected", "regressions": []}
                print("✅ SAFE: No regressions detected")
            else:
                total_regressions = sum(r["count"] for r in regressions)
                result = {
                    "safe": False,
                    "reason": f"{total_regressions} regressions detected",
                    "regressions": regressions,
                }
                print(f"❌ UNSAFE: {total_regressions} regressions detected")
                for reg in regressions:
                    print(f"  {reg['dataset']}: {reg['count']}/{reg['total_locked']} cases broken")

        except Exception as e:
            result = {"safe": False, "reason": f"Error during testing: {e}", "regressions": []}

        finally:
            # Always restore backups
            self.restore_backups()

        return result

    def find_safe_weight_for_case(self, failing_case_input, failing_case_expected, max_attempts=5):
        """Try to find a safe weight addition for a specific failing case"""
        print(f"\n🔍 Finding safe fix for: {failing_case_input} → {failing_case_expected}")

        # Extract syllables from the failing case to target specific patterns
        approaches = [
            # Conservative syllable-specific weights
            (
                f"{failing_case_expected[0]},{failing_case_input.split(',')[0].strip().lower()},-1.5,SN,S",
                "Conservative surname weight",
            ),
            (
                f"{failing_case_expected[-1]},{failing_case_input.split()[-1].lower()},-1.5,GN,G",
                "Conservative given weight",
            ),
            # Medium strength weights
            (
                f"{failing_case_expected[0]},{failing_case_input.split(',')[0].strip().lower()},-2.5,SN,S",
                "Medium surname weight",
            ),
            (
                f"{failing_case_expected[-1]},{failing_case_input.split()[-1].lower()},-2.5,GN,G",
                "Medium given weight",
            ),
            # Strong weights (last resort)
            (
                f"{failing_case_expected[0]},{failing_case_input.split(',')[0].strip().lower()},-3.5,SN,S",
                "Strong surname weight",
            ),
        ]

        for weight_entry, description in approaches:
            result = self.test_proposed_addition(
                proposed_weights=[weight_entry],
                description=f"{description} for {failing_case_input}",
            )

            if result["safe"]:
                return {"success": True, "weight": weight_entry, "description": description}

        return {"success": False, "reason": "All approaches cause regressions"}


# Example usage functions
def example_test_weight_addition():
    """Example: Test adding a specific weight"""
    validator = SafeAdditionValidator()

    # Test adding a conservative weight
    test_weight = "테스트,test,-1.5,GN,G"
    result = validator.test_proposed_addition(
        proposed_weights=[test_weight], description="Example conservative weight addition"
    )

    print(f"Result: {result}")
    return result


def example_find_safe_fix():
    """Example: Find safe fix for a failing case"""
    validator = SafeAdditionValidator()

    # Example failing case (replace with actual failing case)
    result = validator.find_safe_weight_for_case(
        failing_case_input="Kim, David", failing_case_expected="김데이비드"
    )

    print(f"Safe fix result: {result}")
    return result


if __name__ == "__main__":
    print("Safe Addition Validator - Regression-Free Korean Name Expansion")
    print("Available functions:")
    print("1. example_test_weight_addition() - Test a specific weight")
    print("2. example_find_safe_fix() - Find safe fix for failing case")
    print(
        "\nTo use: python3 -c 'from safe_addition_validator import *; example_test_weight_addition()'"
    )
