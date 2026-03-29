import pytest

#!/usr/bin/env python3
"""
Test the accuracy improvements from ULTRATHINK Phase 3
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Reset FastText to ensure fresh state
import src.regions.manager_optimized as mgr_module

mgr_module._fasttext_model = None
mgr_module._fasttext_load_attempted = False

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_accuracy_improvements():
    """Test the specific accuracy improvements."""

    print("🎯 TESTING ULTRATHINK PHASE 3 ACCURACY IMPROVEMENTS")
    print("=" * 60)

    manager = RegionManager()

    # The exact test cases from our audit
    test_cases = [
        ("김철수", "E4", "Korean - should work"),
        ("山田太郎", "E3", "Japanese - should work"),
        ("محمد الأحمد", "C3", "Arabic Levantine - should work"),
        ("José García", "G1", "Spanish - works now"),
        ("Jean Dupont", "A2", "French - SHOULD BE FIXED"),
        ("Wang Wei", "E1", "Chinese - SHOULD BE FIXED"),
        ("Maria Silva", "G1", "Portuguese - SHOULD BE FIXED"),
        ("John Smith", "A1", "English - should work"),
        ("Иван Петров", "B1", "Russian - should work"),
        ("علی احمدی", "C2", "Persian - should work"),
    ]

    print("🔬 TESTING WITH IMPROVED THRESHOLDS AND PATTERNS:")
    print("   Language threshold: 0.7 -> 0.5")
    print("   ICU threshold: 0.95 -> 0.98")
    print("   Added A2, E1 surname patterns")

    correct_predictions = 0
    improvements = []

    for name, expected, description in test_cases:
        entry = {"name": name}
        result = manager.detect_region(entry, internal=True)

        if result.region_code == expected:
            correct_predictions += 1
            status = "PASS"
        else:
            status = "FAIL"

        confidence = result.confidence
        method = result.detection_method

        print(
            f"  {status} {name:15} -> {result.region_code:3} (exp: {expected}, {method:15}, conf: {confidence:.2f})"
        )

        # Track improvements for specific failed cases
        if (
            name in ["Jean Dupont", "Wang Wei", "Maria Silva"]
            and result.region_code == expected
        ):
            improvements.append(name)

    accuracy = correct_predictions / len(test_cases)
    improvement_rate = len(improvements) / 3  # 3 target cases

    print(f"\n📊 ACCURACY RESULTS:")
    print(f"   Current: {correct_predictions}/{len(test_cases)} = {accuracy:.1%}")
    print(f"   Target fixes: {len(improvements)}/3 = {improvement_rate:.1%}")
    print(f"   Improved cases: {improvements}")

    # Compare to previous 70%
    previous_accuracy = 0.70
    improvement = accuracy - previous_accuracy

    print(f"\n📈 IMPROVEMENT ANALYSIS:")
    print(f"   Previous accuracy: {previous_accuracy:.1%}")
    print(f"   Current accuracy: {accuracy:.1%}")
    print(f"   Improvement: {improvement:+.1%}")

    if accuracy >= 0.85:
        print(f"   🎉 TARGET ACHIEVED: >=85% accuracy")
    elif accuracy >= 0.80:
        print(f"   🎯 EXCELLENT: >=80% accuracy")
    elif improvement > 0:
        print(f"   📈 PROGRESS: Accuracy improved")
    else:
        print(f"   WARN  No improvement detected")

    return {
        "accuracy": accuracy,
        "improvement": improvement,
        "improved_cases": improvements,
        "correct_predictions": correct_predictions,
        "total_cases": len(test_cases),
    }


@pytest.mark.timeout(15)
def test_specific_fixes():
    """Test the specific fixes we implemented."""

    print(f"\n\n🔧 TESTING SPECIFIC FIXES:")
    print("-" * 40)

    manager = RegionManager()

    specific_tests = [
        {
            "name": "Jean Dupont",
            "expected": "A2",
            "test": "Language detection threshold (French 55.8% conf)",
            "should_work": "Language detection should now work at 0.5 threshold",
        },
        {
            "name": "Wang Wei",
            "expected": "E1",
            "test": "Chinese surname pattern matching",
            "should_work": "Should match 'wang' in E1 surname list",
        },
        {
            "name": "Maria Silva",
            "expected": "G1",
            "test": "Portuguese language detection + surname pattern",
            "should_work": "Should match 'silva' pattern or Portuguese language",
        },
    ]

    for test_case in specific_tests:
        print(f"\n🧪 Testing: {test_case['name']}")
        print(f"   Test: {test_case['test']}")
        print(f"   Should work: {test_case['should_work']}")

        entry = {"name": test_case["name"]}
        result = manager.detect_region(entry, internal=True)

        if result.region_code == test_case["expected"]:
            print(
                f"   PASS SUCCESS: {result.region_code} ({result.detection_method}, {result.confidence:.2f})"
            )
        else:
            print(
                f"   FAIL FAILED: {result.region_code} (expected {test_case['expected']})"
            )

            # Debug why it failed
            if result.region_code == "A1" and result.confidence == 0.1:
                print(f"   🔍 Still falling back to A1 default - investigating...")

                # Test language detection directly
                lang_result = manager._detect_by_language(entry)
                if lang_result:
                    print(
                        f"   Language detection: {lang_result.region_code} ({lang_result.confidence:.3f})"
                    )
                else:
                    print(f"   Language detection: None")


def main():
    """Run accuracy improvement tests."""

    results = test_accuracy_improvements()
    test_specific_fixes()

    print(f"\n" + "=" * 60)
    print("🧠 ULTRATHINK PHASE 3: ACCURACY TEST COMPLETE")
    print("=" * 60)

    if results["accuracy"] >= 0.85:
        print(f"🎉 SUCCESS: 85% accuracy target achieved ({results['accuracy']:.1%})")
    elif results["improvement"] > 0:
        print(f"📈 PROGRESS: {results['improvement']:+.1%} improvement achieved")
        print(f"   Need {0.85 - results['accuracy']:.1%} more for 85% target")
    else:
        print(f"WARN  No improvement detected - fixes may need refinement")

    return results


if __name__ == "__main__":
    main()
