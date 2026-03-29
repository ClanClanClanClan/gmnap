import pytest

#!/usr/bin/env python3
"""
Test Phase 4A Quick Wins Implementation
Tests the 45-minute improvements for 95% accuracy target
"""

import sys
import json
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.manager_optimized import RegionManager


@pytest.mark.timeout(15)
def test_phase4a_improvements():
    """Test the Phase 4A quick wins: Turkish & Nordic detection improvements."""

    print("🧪 TESTING PHASE 4A QUICK WINS")
    print("=" * 50)

    manager = RegionManager()

    # Test cases including new Turkish and Nordic detection
    test_cases = [
        # Original baseline tests (should still work)
        {"name": "김철수", "expected": "E4", "description": "Korean script"},
        {"name": "山田太郎", "expected": "E3", "description": "Japanese enhanced patterns"},
        {"name": "محمد الأحمد", "expected": "C3", "description": "Arabic Levantine patterns"},
        {"name": "José García", "expected": "G1", "description": "Spanish language"},
        {"name": "Jean Dupont", "expected": "A2", "description": "French language (Phase 3 fix)"},
        {"name": "Wang Wei", "expected": "E1", "description": "Chinese surname pattern"},
        {"name": "Maria Silva", "expected": "A2", "description": "Portuguese surname"},
        {"name": "John Smith", "expected": "A1", "description": "English baseline"},
        {"name": "Иван Петров", "expected": "B1", "description": "Russian script"},
        {"name": "علی احمدی", "expected": "C2", "description": "Persian script"},
        # NEW PHASE 4A TESTS: Turkish detection
        {"name": "Mehmet Yılmaz", "expected": "C1", "description": "Turkish surname pattern (NEW)"},
        {"name": "Ayşe Kaya", "expected": "C1", "description": "Turkish surname pattern (NEW)"},
        {"name": "Mustafa Özkan", "expected": "C1", "description": "Turkish surname pattern (NEW)"},
        # NEW PHASE 4A TESTS: Nordic detection
        {
            "name": "Lars Andersson",
            "expected": "A3",
            "description": "Swedish surname pattern (NEW)",
        },
        {"name": "Erik Nielsen", "expected": "A3", "description": "Danish surname pattern (NEW)"},
        {
            "name": "Ingrid Hansen",
            "expected": "A3",
            "description": "Norwegian surname pattern (NEW)",
        },
        {
            "name": "Mikael Virtanen",
            "expected": "A3",
            "description": "Finnish surname pattern (NEW)",
        },
    ]

    print(f"Testing {len(test_cases)} cases:")
    print("-" * 50)

    correct = 0
    results = []

    for i, case in enumerate(test_cases, 1):
        entry = {"name": case["name"]}
        result = manager.detect_region(entry)

        is_correct = result.region_code == case["expected"]
        if is_correct:
            correct += 1
            status = "PASS"
        else:
            status = "FAIL"

        print(
            f"{i:2}. {status} {case['name']:15} -> {result.region_code:2} ({case['expected']:2}) {case['description']}"
        )
        if not is_correct:
            print(f"     Method: {result.detection_method}, Confidence: {result.confidence:.2f}")

        results.append(
            {
                "name": case["name"],
                "expected": case["expected"],
                "detected": result.region_code,
                "correct": is_correct,
                "confidence": result.confidence,
                "method": result.detection_method,
                "description": case["description"],
            }
        )

    accuracy = correct / len(test_cases)

    print("-" * 50)
    print(f"📊 PHASE 4A RESULTS:")
    print(f"   Correct: {correct}/{len(test_cases)}")
    print(f"   Accuracy: {accuracy:.1%}")
    print(f"   Target: 95%")

    if accuracy >= 0.95:
        print("🎉 SUCCESS: 95% accuracy target ACHIEVED!")
    elif accuracy >= 0.90:
        print("🔥 EXCELLENT: 90%+ accuracy (close to target)")
    else:
        print("WARN  Need improvement to reach 95% target")

    # Show new detections specifically
    new_tests = [r for r in results if "(NEW)" in r["description"]]
    new_correct = sum(1 for r in new_tests if r["correct"])

    print(f"\n🌟 NEW PHASE 4A DETECTION PERFORMANCE:")
    print(
        f"   Turkish detections: {sum(1 for r in new_tests if 'Turkish' in r['description'] and r['correct'])}/3"
    )
    print(
        f"   Nordic detections: {sum(1 for r in new_tests if 'Nordic' in r['description'] or 'Swedish' in r['description'] or 'Danish' in r['description'] or 'Norwegian' in r['description'] or 'Finnish' in r['description'] and r['correct'])}/4"
    )
    print(
        f"   New features accuracy: {new_correct}/{len(new_tests)} ({new_correct/len(new_tests):.1%})"
    )

    # Save detailed results
    with open("phase4a_test_results.json", "w") as f:
        json.dump(
            {
                "timestamp": "2025-08-06",
                "accuracy": accuracy,
                "correct": correct,
                "total": len(test_cases),
                "target_achieved": accuracy >= 0.95,
                "results": results,
            },
            f,
            indent=2,
        )

    print(f"\n💾 Detailed results saved to: phase4a_test_results.json")

    return accuracy


def main():
    """Run Phase 4A validation test."""
    accuracy = test_phase4a_improvements()

    print("\n" + "=" * 60)
    print("🚀 PHASE 4A QUICK WINS VALIDATION COMPLETE")
    print("=" * 60)

    if accuracy >= 0.95:
        print("🎯 MISSION ACCOMPLISHED: Phase 4A achieved 95% accuracy target")
        print("PASS Ready to proceed to Phase 4B: Full C1 Turkish implementation")
    else:
        print(f"📈 Progress made: {accuracy:.1%} accuracy (target: 95%)")
        print("🔧 Consider additional pattern refinements")


if __name__ == "__main__":
    main()
