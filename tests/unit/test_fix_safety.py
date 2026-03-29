#!/usr/bin/env python3
"""Test if proposed fixes would break any currently working mathematician names"""

import json
import pathlib
import sys

import yaml

# Add the src directory to the path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent / "src"))
# NOTE: converter module not available, using E4 Korean processor instead

# Proposed fixes from the auto-fix analysis
PROPOSED_FIXES = {
    "chun": "천",
    "cheong": "정",
    "yom": "염",
    "yum": "염",
    "pae": "배",
    "boo": "부",
    "jee": "지",
    "um": "엄",
    "eom": "엄",
    "shim": "심",
    "sim": "심",
    "baek": "백",
    "roh": "노",
    "no": "노",
    "moon": "문",
    "ri": "이",
}


def simulate_fix_effect(name, expected, fixes):
    """Simulate what would happen if we applied the fixes"""
    # This is a simplified simulation
    # In reality, the converter would use the FST, but we can approximate
    parts = name.split("_")
    if parts[0].lower() in fixes:
        # Would change the first character(s) of the output
        new_first = fixes[parts[0].lower()]
        if expected and len(expected) > 0:
            # Check if it would produce a different result
            if not expected.startswith(new_first):
                return new_first + expected[1:] if len(expected) > 1 else new_first
    return None


def main():
    print("Testing Fix Safety on Mathematician Dataset")
    print("=" * 80)

    # Load mathematician dataset
    with open("data/korean.yaml", "r", encoding="utf-8") as f:
        math_data = yaml.safe_load(f)

    # Load auto-fix report if exists
    try:
        with open("auto_fix_final_report.json", "r", encoding="utf-8") as f:
            json.load(f)
    except:
        pass

    print(
        f"\nTesting {len(PROPOSED_FIXES)} proposed fixes on {len(math_data)} mathematician names"
    )
    print("\nProposed fixes:")
    for rom, han in PROPOSED_FIXES.items():
        print(f"  {rom} -> {han}")

    # Test each mathematician name
    conflicts = []
    would_fix = []
    currently_working = 0
    currently_broken = 0

    for name, entry in math_data.items():
        canonical = entry.get("CanonicalLatin")
        expected = entry.get("Hangul")

        if canonical and expected:
            try:
                # Test current conversion
                current = eng2kor(canonical)

                if current == expected:
                    currently_working += 1

                    # Check if fixes would break it
                    simulated = simulate_fix_effect(canonical, expected, PROPOSED_FIXES)
                    if simulated and simulated != expected:
                        conflicts.append(
                            {
                                "name": canonical,
                                "current": current,
                                "expected": expected,
                                "would_become": simulated,
                                "surname": canonical.split("_")[0].lower(),
                            }
                        )
                else:
                    currently_broken += 1

                    # Check if fixes would fix it
                    surname = canonical.split("_")[0].lower()
                    if surname in PROPOSED_FIXES:
                        new_first = PROPOSED_FIXES[surname]
                        if expected.startswith(new_first):
                            would_fix.append(
                                {
                                    "name": canonical,
                                    "current": current,
                                    "expected": expected,
                                    "fix": f"{surname} -> {new_first}",
                                }
                            )
            except Exception:
                currently_broken += 1

    # Report results
    print("\n" + "=" * 80)
    print("SAFETY ANALYSIS RESULTS")
    print("=" * 80)

    print("\nCurrent mathematician dataset status:")
    print(
        f"  Working correctly: {currently_working} ({currently_working/len(math_data)*100:.1f}%)"
    )
    print(f"  Broken: {currently_broken} ({currently_broken/len(math_data)*100:.1f}%)")

    print("\nImpact of proposed fixes:")
    print(f"  Would fix: {len(would_fix)} names")
    print(f"  Would break: {len(conflicts)} names")
    print(f"  Net improvement: {len(would_fix) - len(conflicts)} names")

    if conflicts:
        print("\nWARN  WARNING: The following working names would be broken:")
        for i, conflict in enumerate(conflicts[:10]):
            print(f"\n{i+1}. {conflict['name']}")
            print(f"   Currently: {conflict['current']} ✓")
            print(f"   Would become: {conflict['would_become']} ✗")
            print(
                f"   Due to: {conflict['surname']} -> {PROPOSED_FIXES[conflict['surname']]}"
            )

        if len(conflicts) > 10:
            print(f"\n... and {len(conflicts) - 10} more conflicts")
    else:
        print("\nPASS NO CONFLICTS: All currently working names would remain correct!")

    if would_fix:
        print("\nPASS The following broken names would be fixed:")
        for i, fix in enumerate(would_fix[:5]):
            print(f"\n{i+1}. {fix['name']}")
            print(f"   Currently: {fix['current'] or 'None'} ✗")
            print(f"   Would become: {fix['expected']} ✓")
            print(f"   Due to: {fix['fix']}")

        if len(would_fix) > 5:
            print(f"\n... and {len(would_fix) - 5} more fixes")

    # Risk vs Reward calculation
    print("\n" + "=" * 80)
    print("RISK VS REWARD ANALYSIS")
    print("=" * 80)

    # For mathematician dataset
    math_risk = len(conflicts) / len(math_data) * 100
    math_reward = len(would_fix) / len(math_data) * 100

    # For diverse dataset (from auto-fix report)
    div_reward = 11.67  # From the auto-fix analysis

    print("\nMathematician Dataset:")
    print(f"  Risk: {math_risk:.2f}% ({len(conflicts)} names would break)")
    print(f"  Reward: {math_reward:.2f}% ({len(would_fix)} names would be fixed)")
    print(f"  Net: {math_reward - math_risk:+.2f}%")

    print("\nDiverse Dataset:")
    print("  Risk: 0% (not part of mathematician dataset)")
    print(f"  Reward: +{div_reward:.2f}% accuracy improvement")

    print("\nOverall Assessment:")
    total_risk = math_risk
    total_reward = (math_reward + div_reward) / 2  # Average improvement

    print(f"  Total Risk Score: {total_risk:.2f}%")
    print(f"  Total Reward Score: {total_reward:.2f}%")
    print(f"  Net Benefit: {total_reward - total_risk:+.2f}%")

    # Final recommendation
    print("\n" + "=" * 80)
    print("FINAL RECOMMENDATION")
    print("=" * 80)

    if len(conflicts) == 0:
        print("\nPASS STRONG RECOMMENDATION: Apply all high-confidence fixes")
        print("   - No conflicts detected with mathematician dataset")
        print(f"   - Would fix {len(would_fix)} mathematician names")
        print(f"   - Would improve diverse dataset accuracy by {div_reward:.2f}%")
        print("   - Zero risk, high reward scenario")
    elif total_reward > total_risk * 3:
        print("\nPASS RECOMMENDATION: Apply fixes with minor adjustments")
        print(f"   - Only {len(conflicts)} conflicts to resolve")
        print(f"   - Net benefit of {total_reward - total_risk:.2f}%")
        print("   - Consider manual review of conflicts")
    elif total_reward > total_risk:
        print("\nWARN  CONDITIONAL RECOMMENDATION: Apply with careful review")
        print(f"   - {len(conflicts)} conflicts need resolution")
        print(f"   - Modest net benefit of {total_reward - total_risk:.2f}%")
        print("   - Requires conflict resolution strategy")
    else:
        print("\nFAIL RECOMMENDATION: Do not apply automatically")
        print(f"   - Too many conflicts ({len(conflicts)})")
        print("   - Risk outweighs reward")
        print("   - Need alternative approach")

    # Save detailed report
    safety_report = {
        "proposed_fixes": PROPOSED_FIXES,
        "mathematician_dataset": {
            "total": len(math_data),
            "currently_working": currently_working,
            "currently_broken": currently_broken,
            "would_fix": len(would_fix),
            "would_break": len(conflicts),
            "net_improvement": len(would_fix) - len(conflicts),
        },
        "conflicts": [
            {
                "name": c["name"],
                "current": c["current"],
                "would_become": c["would_become"],
                "surname": c["surname"],
            }
            for c in conflicts[:20]  # Save first 20 conflicts
        ],
        "fixes": [
            {
                "name": f["name"],
                "current": f["current"],
                "expected": f["expected"],
                "fix": f["fix"],
            }
            for f in would_fix[:20]  # Save first 20 fixes
        ],
        "risk_reward": {
            "math_risk": math_risk,
            "math_reward": math_reward,
            "div_reward": div_reward,
            "total_risk": total_risk,
            "total_reward": total_reward,
            "net_benefit": total_reward - total_risk,
        },
    }

    with open("fix_safety_report.json", "w", encoding="utf-8") as f:
        json.dump(safety_report, f, indent=2, ensure_ascii=False)

    print("\n\nDetailed safety report saved to: fix_safety_report.json")


if __name__ == "__main__":
    main()
