#!/usr/bin/env python3
"""Run auto-fix analysis on diverse dataset failures"""

import yaml
import sys
import pathlib
import json
from collections import defaultdict, Counter

# Add the parent directory to path (where converter_v6.py is)
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

# Import auto-fix components
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from auto_fix_system import PatternAnalyzer, FixGenerator, LearningSystem, SafetyChecker

# Add the src directory to the path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
from converter import eng2kor, kor2eng


def collect_all_failures():
    """Collect failures from both datasets"""
    failures = []

    # Load diverse dataset
    with open("../data/korean_diverse_test.yaml", "r", encoding="utf-8") as f:
        diverse_data = yaml.safe_load(f)

    # Test diverse dataset
    for name, entry in diverse_data.items():
        canonical = entry.get("CanonicalLatin")
        expected = entry.get("Hangul")

        if canonical and expected:
            try:
                actual = eng2kor(canonical)
                if actual != expected:
                    failures.append(
                        {
                            "name": canonical,
                            "expected": expected,
                            "actual": actual,
                            "type": "eng→kor",
                            "category": entry.get("Categories", ["Other"])[0],
                            "dataset": "diverse",
                        }
                    )
            except Exception as e:
                failures.append(
                    {
                        "name": canonical,
                        "expected": expected,
                        "actual": None,
                        "type": "eng→kor",
                        "category": entry.get("Categories", ["Other"])[0],
                        "dataset": "diverse",
                        "error": str(e),
                    }
                )

    return failures


def main():
    print("Auto-Fix System Analysis for Diverse Dataset Failures")
    print("=" * 80)

    # Collect all failures
    print("\n1. Collecting Failures")
    print("-" * 80)
    failures = collect_all_failures()
    print(f"Found {len(failures)} total failures")

    # Initialize auto-fix components
    analyzer = PatternAnalyzer()
    fix_generator = FixGenerator(analyzer)
    learning_system = LearningSystem()
    safety_checker = SafetyChecker()

    # Analyze failures
    print("\n2. Analyzing Failures")
    print("-" * 80)

    analyzed_failures = []
    for failure in failures:
        analysis = analyzer.analyze_failure(
            failure["name"], failure["expected"], failure["actual"], failure["type"]
        )
        analysis["category"] = failure["category"]
        analyzed_failures.append(analysis)

    # Sort by confidence
    analyzed_failures.sort(key=lambda x: x["confidence"], reverse=True)

    # Show top 10 highest confidence fixes
    print("\nTop 10 Highest Confidence Fixes:")
    print("-" * 80)
    for i, analysis in enumerate(analyzed_failures[:10]):
        print(f"\n{i+1}. {analysis['name']}")
        print(f"   Expected: {analysis['expected']}, Actual: {analysis['actual']}")
        print(f"   Confidence: {analysis['confidence']:.2f}")
        print(f"   Category: {analysis['category']}")
        if analysis["suggestions"]:
            print(f"   Best suggestion: {analysis['suggestions'][0]['reason']}")

    # Generate fixes
    print("\n\n3. Generating High-Confidence Fixes")
    print("-" * 80)

    fixes = fix_generator.generate_fixes(analyzed_failures)
    safe_fixes = safety_checker.check_safety(fixes)

    # Filter high-confidence fixes
    high_conf_fixes = [f for f in safe_fixes if f.get("confidence", 0) > 0.8]

    print(f"\nTotal fixes generated: {len(fixes)}")
    print(f"High-confidence fixes (>0.8): {len(high_conf_fixes)}")

    # Show detailed high-confidence fixes
    print("\nDetailed High-Confidence Fixes:")
    for i, fix in enumerate(high_conf_fixes[:10]):
        print(f"\n{i+1}. {fix['romanization']} → {fix['hangul']}")
        print(f"   Confidence: {fix.get('confidence', 0):.2f}")
        print(f"   Safety score: {fix.get('safety_score', 0):.2f}")
        print(f"   Would fix {len(fix['affected_names'])} names:")
        for name in fix["affected_names"][:3]:
            print(f"     - {name}")
        if len(fix["affected_names"]) > 3:
            print(f"     ... and {len(fix['affected_names']) - 3} more")

    # Calculate accuracy improvement
    print("\n\n4. Potential Accuracy Improvement")
    print("-" * 80)

    # Count unique names that would be fixed
    fixed_names = set()
    for fix in high_conf_fixes:
        fixed_names.update(fix.get("affected_names", []))

    total_diverse = 200  # From the test output
    improvement = len(fixed_names) / total_diverse * 100
    current_accuracy = 82.50  # From the test output

    print(f"\nCurrent diverse dataset accuracy: {current_accuracy}%")
    print(f"Number of failures that would be fixed: {len(fixed_names)}")
    print(f"Potential accuracy improvement: +{improvement:.2f} percentage points")
    print(f"New estimated accuracy: {current_accuracy + improvement:.2f}%")

    # Test safety on mathematician dataset
    print("\n\n5. Safety Check on Mathematician Dataset")
    print("-" * 80)

    # Load mathematician dataset
    with open("../data/korean.yaml", "r", encoding="utf-8") as f:
        math_data = yaml.safe_load(f)

    # Test if any working names would break
    conflicts = 0
    conflict_examples = []

    fix_map = {
        fix["romanization"]: fix["hangul"]
        for fix in high_conf_fixes
        if fix["type"] == "add_mapping"
    }

    for name, entry in math_data.items():
        canonical = entry.get("CanonicalLatin")
        expected = entry.get("Hangul")

        if canonical and expected:
            try:
                current = eng2kor(canonical)
                if current == expected:
                    # This currently works - check if it would break
                    canonical_lower = canonical.lower()
                    for rom, new_hangul in fix_map.items():
                        if rom in canonical_lower.split("_"):
                            # Check if this is a surname position
                            parts = canonical.split("_")
                            if parts[0].lower() == rom and not expected.startswith(
                                new_hangul
                            ):
                                conflicts += 1
                                conflict_examples.append(
                                    {
                                        "name": canonical,
                                        "current": current,
                                        "would_change_to": new_hangul + expected[1:],
                                        "fix": f"{rom} → {new_hangul}",
                                    }
                                )
                                if len(conflict_examples) >= 5:
                                    break
            except:
                pass

        if len(conflict_examples) >= 5:
            break

    if conflicts > 0:
        print(
            f"\n⚠️  WARNING: {conflicts} working mathematician names might be affected"
        )
        print("\nExamples of potential conflicts:")
        for ex in conflict_examples:
            print(
                f"  - {ex['name']}: {ex['current']} → {ex['would_change_to']} (due to {ex['fix']})"
            )
    else:
        print(
            "\n✓ No conflicts detected - mathematician dataset names would remain correct"
        )

    # Risk vs Reward Analysis
    print("\n\n6. Risk vs Reward Analysis")
    print("-" * 80)

    risk_score = conflicts / 733 * 100  # 733 mathematician names
    reward_score = improvement

    print(f"\nRisk Score: {risk_score:.2f}% (mathematician names that might break)")
    print(f"Reward Score: {reward_score:.2f}% (diverse dataset accuracy improvement)")
    print(f"Net Benefit: {reward_score - risk_score:.2f} percentage points")

    if reward_score > risk_score * 2:
        print("\n✅ RECOMMENDATION: Apply high-confidence fixes")
        print("   The improvement significantly outweighs the risk.")
    elif reward_score > risk_score:
        print("\n⚠️  RECOMMENDATION: Apply fixes with careful review")
        print("   The improvement outweighs the risk, but review is needed.")
    else:
        print("\n❌ RECOMMENDATION: Do not apply fixes automatically")
        print("   The risk outweighs the potential benefit.")

    # Generate implementation commands
    print("\n\n7. Implementation Commands (if approved)")
    print("-" * 80)

    if high_conf_fixes:
        commands = fix_generator.generate_fix_commands(high_conf_fixes[:5])
        print("\nSample commands for first 5 fixes:")
        for cmd in commands:
            print(cmd)

    # Save detailed report
    report = {
        "summary": {
            "total_failures": len(failures),
            "high_confidence_fixes": len(high_conf_fixes),
            "current_accuracy": current_accuracy,
            "potential_improvement": improvement,
            "new_accuracy": current_accuracy + improvement,
            "conflicts": conflicts,
            "risk_score": risk_score,
            "reward_score": reward_score,
            "recommendation": (
                "APPLY"
                if reward_score > risk_score * 2
                else "REVIEW" if reward_score > risk_score else "REJECT"
            ),
        },
        "top_10_fixes": [
            {
                "romanization": f["romanization"],
                "hangul": f["hangul"],
                "confidence": f.get("confidence", 0),
                "safety_score": f.get("safety_score", 0),
                "affected_count": len(f.get("affected_names", [])),
            }
            for f in high_conf_fixes[:10]
        ],
        "analyzed_failures": [
            {
                "name": af["name"],
                "expected": af["expected"],
                "actual": af["actual"],
                "confidence": af["confidence"],
                "category": af["category"],
            }
            for af in analyzed_failures[:20]
        ],
    }

    with open("auto_fix_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n\nFull report saved to: auto_fix_report.json")


if __name__ == "__main__":
    main()
