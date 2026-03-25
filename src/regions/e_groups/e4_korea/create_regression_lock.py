#!/usr/bin/env python3
"""
Regression Lock System: Save all currently successful cases as protected baseline
This ensures no future optimization can break existing working functionality.
"""

import yaml
import json
import sys

sys.path.append("src")
from converter import eng2kor, kor2eng, eng2kor_nbest, _enhanced_dice


def find_hangul(variants):
    """Extract Korean text from variant list"""
    for v in variants:
        if any("\uac00" <= c <= "\ud7af" for c in v):
            return v.replace(" ", "")
    return None


def test_case_passes(rr, ko_expected):
    """Test if a case currently passes our system"""
    if not rr or not ko_expected:
        return False

    # Test conversion
    ko = eng2kor(rr)
    hypos = eng2kor_nbest(rr, n=3)

    if ko_expected in hypos:
        ko = ko_expected
    elif ko != ko_expected:
        return False  # Conversion failure

    # Test roundtrip
    rr2 = kor2eng(ko, rr) or ""
    dice_score = _enhanced_dice(rr, rr2)

    return dice_score >= 0.90  # Roundtrip success


def create_regression_lock():
    """Create regression lock files for all datasets"""

    datasets = {
        "math": "data/korean.yaml",
        "diverse": "data/diverse.yaml",  # Note: May need different path
        "independent": "data/expanded_independent_validation_dataset.json",
    }

    total_locked = 0

    for dataset_name, data_file in datasets.items():
        print(f"Processing {dataset_name} dataset...")

        try:
            # Load data based on file type
            if data_file.endswith(".yaml"):
                with open(data_file, "r", encoding="utf8") as f:
                    data = yaml.safe_load(f)
            else:
                with open(data_file, "r", encoding="utf8") as f:
                    data = json.load(f)

            successful_cases = []
            tested = 0

            for case_name, info in data.items():
                tested += 1

                # Extract canonical latin and expected korean
                if isinstance(info, dict):
                    rr = info.get("CanonicalLatin")
                    ko_expected = find_hangul(info.get("AllCommonVariants", []))
                else:
                    continue  # Skip malformed entries

                if not rr or not ko_expected:
                    continue

                # Test if currently passes
                if test_case_passes(rr, ko_expected):
                    successful_cases.append(
                        {
                            "name": case_name,
                            "input": rr,
                            "expected_korean": ko_expected,
                            "dataset": dataset_name,
                        }
                    )

            # Save regression lock
            lock_file = f"{dataset_name}_lock.json"
            with open(lock_file, "w", encoding="utf8") as f:
                json.dump(successful_cases, f, ensure_ascii=False, indent=2)

            success_rate = len(successful_cases) / tested * 100 if tested > 0 else 0
            print(
                f"✅ {dataset_name}: Locked {len(successful_cases)}/{tested} cases ({success_rate:.1f}%)"
            )
            total_locked += len(successful_cases)

        except FileNotFoundError:
            print(f"⚠️  {dataset_name}: File {data_file} not found - skipping")
        except Exception as e:
            print(f"❌ {dataset_name}: Error processing - {e}")

    print("\n=== REGRESSION LOCK SUMMARY ===")
    print(f"Total cases locked: {total_locked}")
    print(f"Lock files created: {[f'{name}_lock.json' for name in datasets.keys()]}")
    print("\n✅ Regression protection established!")
    print("These cases MUST always pass in future optimizations.")


if __name__ == "__main__":
    create_regression_lock()
