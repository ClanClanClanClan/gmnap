#!/usr/bin/env python3
"""Run comprehensive auto-fix analysis on diverse dataset failures"""

import yaml
import sys
import pathlib
import json
from collections import defaultdict, Counter

# Add necessary paths
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
# Try to import converter_v6 first, fall back to regular converter
try:
    from converter_v6 import eng2kor, kor2eng
except ImportError:
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
    from converter import eng2kor, kor2eng

# Import auto-fix components
from auto_fix_system import PatternAnalyzer, FixGenerator, LearningSystem, SafetyChecker


def load_datasets():
    """Load both mathematician and diverse datasets"""
    datasets = {}

    # Load mathematician dataset
    with open("../data/korean.yaml", "r", encoding="utf-8") as f:
        datasets["mathematician"] = yaml.safe_load(f)

    # Load diverse dataset
    with open("../data/korean_diverse_test.yaml", "r", encoding="utf-8") as f:
        datasets["diverse"] = yaml.safe_load(f)

    return datasets


def test_dataset(data, dataset_name):
    """Test a dataset and collect failures"""
    failures = []
    correct = 0
    total = 0

    for name, entry in data.items():
        canonical = entry.get("CanonicalLatin")
        expected = entry.get("Hangul")

        if canonical and expected:
            total += 1
            try:
                actual = eng2kor(canonical)
                if actual == expected:
                    correct += 1
                else:
                    failures.append(
                        {
                            "name": canonical,
                            "expected": expected,
                            "actual": actual,
                            "type": "eng→kor",
                            "category": entry.get("Categories", ["Other"])[0],
                            "dataset": dataset_name,
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
                        "dataset": dataset_name,
                        "error": str(e),
                    }
                )

    accuracy = (correct / total * 100) if total > 0 else 0
    return failures, accuracy, total


def analyze_fixes_with_confidence(failures, analyzer, fix_generator):
    """Analyze failures and generate fixes with confidence scores"""
    analyzed_failures = []

    for failure in failures:
        analysis = analyzer.analyze_failure(
            failure["name"], failure["expected"], failure["actual"], failure["type"]
        )
        analysis["dataset"] = failure["dataset"]
        analysis["category"] = failure["category"]
        analyzed_failures.append(analysis)

    # Sort by confidence
    analyzed_failures.sort(key=lambda x: x["confidence"], reverse=True)

    return analyzed_failures


def calculate_accuracy_improvement(fixes, total_entries):
    """Calculate potential accuracy improvement"""
    # Count unique names that would be fixed
    fixed_names = set()
    for fix in fixes:
        fixed_names.update(fix.get("affected_names", []))

    improvement = len(fixed_names) / total_entries * 100
    return improvement, len(fixed_names)


def test_safety_on_working_names(fixes, datasets):
    """Test if fixes would break currently working names"""
    conflicts = []

    # Create a mapping of proposed fixes
    fix_map = {}
    for fix in fixes:
        if fix["type"] == "add_mapping":
            fix_map[fix["romanization"]] = fix["hangul"]

    # Test all currently working names
    for dataset_name, data in datasets.items():
        for name, entry in data.items():
            canonical = entry.get("CanonicalLatin")
            expected = entry.get("Hangul")

            if canonical and expected:
                try:
                    current = eng2kor(canonical)
                    if current == expected:
                        # This name currently works
                        # Check if any fix would affect it
                        canonical_lower = canonical.lower()
                        for rom, new_hangul in fix_map.items():
                            if rom in canonical_lower:
                                # Simulate the effect
                                parts = canonical_lower.split("_")
                                if parts[0] == rom:
                                    # This is a surname match
                                    if not expected.startswith(new_hangul):
                                        conflicts.append(
                                            {
                                                "name": canonical,
                                                "current_output": current,
                                                "expected": expected,
                                                "would_become": new_hangul + expected[1:],
                                                "fix": f"{rom} → {new_hangul}",
                                                "dataset": dataset_name,
                                            }
                                        )
                except:
                    pass

    return conflicts


def main():
    print("Automated Fix System Analysis Report")
    print("=" * 80)

    # Load datasets
    print("\n1. Loading Datasets")
    print("-" * 80)
    datasets = load_datasets()
    print(f"Loaded {len(datasets['mathematician'])} mathematician entries")
    print(f"Loaded {len(datasets['diverse'])} diverse dataset entries")

    # Test both datasets
    print("\n2. Testing Datasets")
    print("-" * 80)

    math_failures, math_accuracy, math_total = test_dataset(
        datasets["mathematician"], "mathematician"
    )
    div_failures, div_accuracy, div_total = test_dataset(datasets["diverse"], "diverse")

    print(f"Mathematician dataset: {math_accuracy:.2f}% accuracy ({len(math_failures)} failures)")
    print(f"Diverse dataset: {div_accuracy:.2f}% accuracy ({len(div_failures)} failures)")

    # Focus on diverse dataset failures
    all_failures = div_failures  # + math_failures if you want both

    # Initialize auto-fix components
    analyzer = PatternAnalyzer()
    fix_generator = FixGenerator(analyzer)
    learning_system = LearningSystem()
    safety_checker = SafetyChecker()

    # Analyze failures
    print("\n3. Analyzing Failures with Auto-Fix System")
    print("-" * 80)

    analyzed_failures = analyze_fixes_with_confidence(all_failures, analyzer, fix_generator)

    # Show top 10 highest confidence fixes
    print("\nTop 10 Highest Confidence Fixes:")
    for i, analysis in enumerate(analyzed_failures[:10]):
        print(f"\n{i+1}. {analysis['name']}")
        print(f"   Expected: {analysis['expected']}, Actual: {analysis['actual']}")
        print(f"   Confidence: {analysis['confidence']:.2f}")
        print(f"   Category: {analysis['category']}")
        if analysis["suggestions"]:
            print("   Best suggestion: " + analysis["suggestions"][0]["reason"])

    # Generate fixes
    print("\n4. Generating Fixes")
    print("-" * 80)

    fixes = fix_generator.generate_fixes(analyzed_failures)
    safe_fixes = safety_checker.check_safety(fixes)

    # Filter high-confidence fixes
    high_conf_fixes = [f for f in safe_fixes if f.get("confidence", 0) > 0.8]

    print(f"\nGenerated {len(fixes)} total fixes")
    print(f"High-confidence fixes (>0.8): {len(high_conf_fixes)}")

    # Show high-confidence fixes
    print("\nHigh-Confidence Fixes:")
    for fix in high_conf_fixes[:10]:
        print(f"\n- {fix['romanization']} → {fix['hangul']}")
        print(f"  Confidence: {fix.get('confidence', 0):.2f}")
        print(f"  Safety score: {fix.get('safety_score', 0):.2f}")
        print(f"  Would fix: {', '.join(fix['affected_names'][:3])}")
        if len(fix["affected_names"]) > 3:
            print(f"  ... and {len(fix['affected_names']) - 3} more")

    # Calculate accuracy improvement
    print("\n5. Potential Accuracy Improvement")
    print("-" * 80)

    improvement, num_fixes = calculate_accuracy_improvement(high_conf_fixes, div_total)
    print(f"\nApplying {len(high_conf_fixes)} high-confidence fixes would:")
    print(f"- Fix {num_fixes} failing names")
    print(f"- Improve accuracy by {improvement:.2f} percentage points")
    print(f"- New estimated accuracy: {div_accuracy + improvement:.2f}%")

    # Test safety
    print("\n6. Safety Analysis")
    print("-" * 80)

    conflicts = test_safety_on_working_names(high_conf_fixes, datasets)

    if conflicts:
        print(f"\n⚠️  WARNING: {len(conflicts)} potential conflicts found!")
        print("\nFirst 5 conflicts:")
        for i, conflict in enumerate(conflicts[:5]):
            print(f"\n{i+1}. {conflict['name']} ({conflict['dataset']} dataset)")
            print(f"   Currently: {conflict['current_output']} ✓")
            print(f"   Would become: {conflict['would_become']} ✗")
            print(f"   Due to fix: {conflict['fix']}")
    else:
        print("\n✓ No conflicts found - all currently working names would remain correct!")

    # Risk vs Reward Analysis
    print("\n7. Risk vs Reward Analysis")
    print("-" * 80)

    total_names = math_total + div_total
    risk_score = len(conflicts) / total_names * 100
    reward_score = improvement

    print(f"\nRisk Score: {risk_score:.2f}% (names that would break)")
    print(f"Reward Score: {reward_score:.2f}% (accuracy improvement)")
    print(f"Net Benefit: {reward_score - risk_score:.2f} percentage points")

    if reward_score > risk_score * 2:
        print(
            "\n✓ RECOMMENDATION: Apply high-confidence fixes (reward significantly outweighs risk)"
        )
    elif reward_score > risk_score:
        print("\n⚠️  RECOMMENDATION: Consider applying fixes with manual review")
    else:
        print("\n✗ RECOMMENDATION: Do not apply fixes (risk outweighs reward)")

    # Generate fix commands
    print("\n8. Implementation Commands")
    print("-" * 80)

    if high_conf_fixes:
        commands = fix_generator.generate_fix_commands(high_conf_fixes)
        print("\nTo apply high-confidence fixes:")
        for cmd in commands[:10]:
            print(cmd)

        if len(commands) > 10:
            print(f"\n... and {len(commands) - 10} more commands")

    # Save detailed report
    report = {
        "summary": {
            "mathematician_accuracy": math_accuracy,
            "diverse_accuracy": div_accuracy,
            "total_failures": len(all_failures),
            "high_confidence_fixes": len(high_conf_fixes),
            "potential_improvement": improvement,
            "conflicts": len(conflicts),
            "risk_score": risk_score,
            "reward_score": reward_score,
        },
        "top_fixes": [
            {
                "romanization": f["romanization"],
                "hangul": f["hangul"],
                "confidence": f.get("confidence", 0),
                "safety_score": f.get("safety_score", 0),
                "affected_count": len(f.get("affected_names", [])),
            }
            for f in high_conf_fixes[:10]
        ],
        "conflicts": conflicts[:10],
    }

    with open("auto_fix_analysis_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n\nDetailed report saved to: auto_fix_analysis_report.json")


if __name__ == "__main__":
    main()
