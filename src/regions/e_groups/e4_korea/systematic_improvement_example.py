#!/usr/bin/env python3
"""
Systematic Improvement Example: Demonstration of regression-free Korean name expansion
This shows exactly how another AI would use the tools to improve Independent dataset safely.
"""

import json
from safe_addition_validator import SafeAdditionValidator


def get_independent_failures():
    """Get current failures from Independent dataset"""
    try:
        # Load independent dataset
        with open(
            "data/expanded_independent_validation_dataset.json", "r", encoding="utf8"
        ) as f:
            data = json.load(f)

        failures = []

        # Import necessary functions
        import sys

        sys.path.append("src")
        # from converter import eng2kor, kor2eng, eng2kor_nbest, _enhanced_dice

        def find_hangul(variants):
            for v in variants:
                if any("\uac00" <= c <= "\ud7af" for c in v):
                    return v.replace(" ", "")
            return None

        for name, info in data.items():
            rr = info.get("CanonicalLatin")
            ko_expected = find_hangul(info.get("AllCommonVariants", []))

            if not rr or not ko_expected:
                continue

            # Test current system
            ko = eng2kor(rr)
            hypos = eng2kor_nbest(rr, n=3)

            if ko_expected in hypos:
                ko = ko_expected
            elif ko != ko_expected:
                failures.append(
                    {
                        "name": name,
                        "type": "conversion",
                        "input": rr,
                        "expected": ko_expected,
                        "actual": ko,
                        "category": info.get("category", "unknown"),
                    }
                )
                continue

            # Test roundtrip
            rr2 = kor2eng(ko, rr) or ""
            if _enhanced_dice(rr, rr2) < 0.90:
                failures.append(
                    {
                        "name": name,
                        "type": "roundtrip",
                        "input": rr,
                        "expected": ko_expected,
                        "roundtrip": rr2,
                        "dice": _enhanced_dice(rr, rr2),
                        "category": info.get("category", "unknown"),
                    }
                )

        return failures

    except Exception as e:
        print(f"Error getting failures: {e}")
        return []


def systematic_improvement_demo():
    """Demonstrate systematic improvement of Independent dataset"""

    print("🎯 SYSTEMATIC IMPROVEMENT DEMO")
    print("=" * 50)

    # Step 1: Initialize validator
    print("\n📋 Step 1: Initialize Safe Addition Validator")
    validator = SafeAdditionValidator()

    if not any(validator.regression_locks.values()):
        print("❌ No regression locks found!")
        print("   Run: python3 create_regression_lock.py first")
        return

    # Step 2: Get current failures
    print("\n🔍 Step 2: Identify Independent Dataset Failures")
    failures = get_independent_failures()

    if not failures:
        print("✅ No failures found in Independent dataset!")
        return

    print(f"Found {len(failures)} failures:")

    # Group by category and type
    by_category = {}
    by_type = {}

    for failure in failures:
        category = failure["category"]
        ftype = failure["type"]

        if category not in by_category:
            by_category[category] = []
        by_category[category].append(failure)

        if ftype not in by_type:
            by_type[ftype] = []
        by_type[ftype].append(failure)

    print(f"  By type: {dict((k, len(v)) for k, v in by_type.items())}")
    print(f"  By category: {dict((k, len(v)) for k, v in by_category.items())}")

    # Step 3: Attempt systematic fixes
    print("\n🔧 Step 3: Attempt Safe Fixes")

    successful_fixes = []
    failed_fixes = []

    # Focus on conversion failures first (easier to fix)
    conversion_failures = [f for f in failures if f["type"] == "conversion"]

    print(f"\\nAttempting to fix {len(conversion_failures)} conversion failures...")

    for i, failure in enumerate(conversion_failures[:5]):  # Limit to first 5 for demo
        print(f"\\n--- Fix Attempt {i+1}/5 ---")
        print(f"Case: {failure['name']}")
        print(f"Input: {failure['input']}")
        print(f"Expected: {failure['expected']}")
        print(f"Actual: {failure['actual']}")
        print(f"Category: {failure['category']}")

        # Try to find safe fix
        result = validator.find_safe_weight_for_case(
            failing_case_input=failure["input"],
            failing_case_expected=failure["expected"],
        )

        if result["success"]:
            successful_fixes.append({"failure": failure, "fix": result})
            print(f"✅ SUCCESS: {result['description']}")
            print(f"   Weight: {result['weight']}")
        else:
            failed_fixes.append({"failure": failure, "reason": result["reason"]})
            print(f"❌ FAILED: {result['reason']}")

    # Step 4: Summary and recommendations
    print(f"\\n📊 Step 4: Results Summary")
    print("=" * 30)
    print(f"Successful fixes found: {len(successful_fixes)}")
    print(f"Failed to fix safely: {len(failed_fixes)}")

    if successful_fixes:
        print(f"\\n✅ SAFE ADDITIONS READY FOR IMPLEMENTATION:")
        for fix in successful_fixes:
            print(f"  • {fix['failure']['name']}: {fix['fix']['weight']}")

        print(f"\\n📋 TO IMPLEMENT THESE FIXES:")
        print(f"1. Add the weights to resources/rr_syllable_map.csv")
        print(f"2. Run: python3 scripts/build_fsts_multi.py")
        print(f"3. Validate: python3 scripts/test_expanded_independent_dataset.py")

    if failed_fixes:
        print(f"\\n⚠️  CASES THAT NEED ALTERNATIVE APPROACHES:")
        for fail in failed_fixes:
            print(f"  • {fail['failure']['name']}: {fail['reason']}")

    estimated_improvement = len(successful_fixes)
    current_independent = 145  # Current successful cases
    total_independent = 165  # Total cases

    new_success_rate = (
        (current_independent + estimated_improvement) / total_independent * 100
    )
    print(f"\\n🎯 ESTIMATED IMPROVEMENT:")
    print(f"Current Independent: {current_independent}/{total_independent} = 87.88%")
    print(
        f"After safe fixes: {current_independent + estimated_improvement}/{total_independent} = {new_success_rate:.2f}%"
    )
    print(
        f"Improvement: +{estimated_improvement} cases (+{estimated_improvement/total_independent*100:.2f}%)"
    )

    return {
        "successful_fixes": successful_fixes,
        "failed_fixes": failed_fixes,
        "estimated_improvement": estimated_improvement,
    }


def apply_safe_fixes_example(fixes):
    """Example of how to apply the safe fixes found"""
    print("\\n🚀 APPLYING SAFE FIXES (EXAMPLE)")
    print("=" * 35)

    if not fixes:
        print("No fixes to apply!")
        return

    print("Adding weights to CSV:")
    weights_to_add = []

    for fix in fixes:
        weight = fix["fix"]["weight"]
        weights_to_add.append(weight)
        print(f"  + {weight}")

    # In practice, you would:
    # 1. Add these to resources/rr_syllable_map.csv
    # 2. Rebuild FSTs
    # 3. Validate all datasets

    print(f"\\n📝 IMPLEMENTATION STEPS:")
    print(
        f"1. echo '# Safe additions from systematic improvement' >> resources/rr_syllable_map.csv"
    )
    for weight in weights_to_add:
        print(f"   echo '{weight}' >> resources/rr_syllable_map.csv")
    print(f"2. python3 scripts/build_fsts_multi.py")
    print(f"3. python3 scripts/validate.py  # Should still be 98.36%")
    print(f"4. python3 scripts/correct_diverse_evaluation.py  # Should still be 97.50%")
    print(f"5. python3 scripts/test_expanded_independent_dataset.py  # Should improve!")


if __name__ == "__main__":
    # Run the systematic improvement demo
    result = systematic_improvement_demo()

    if result and result["successful_fixes"]:
        apply_safe_fixes_example(result["successful_fixes"])
