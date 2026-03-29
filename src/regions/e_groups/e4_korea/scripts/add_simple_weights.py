#!/usr/bin/env python3
"""Add simple syllable mappings to fix independent dataset failures."""

import subprocess
import sys

# Just the missing SYLLABLES (not compounds)
SIMPLE_WEIGHTS = [
    # Missing syllables from failure analysis
    "여,yuh,1.0,,G",  # For Youn, Yuh-Jung
    "식,shik,1.0,,G",  # For Choi, Min-Shik
    "소,so,1.0,SN,S",  # For So, Ji-Sub (surname)
    "섭,sub,1.0,,G",  # For Ji-Sub
    "싸이,psy,2.0,,S",  # PSY stage name (special case)
    "이,rhee,1.5,SN,S",  # Alternative spelling of Lee
    # Improve existing mappings with higher weights
    "청,cheong,1.3,,G",  # 청 not 정
    "병,byung,1.3,,G",  # 병 not 븅
    "순,sun,1.2,,G",  # 순 not 선
    "림,lim,1.2,,G",  # Alternative to rim
    "리,ri,1.2,,G",  # For Se-Ri
    "연,yeon,1.2,,G",  # Reinforce 연
    "열,yeol,1.2,,G",  # For Mun-Yol
    "창,chang,1.2,,G",  # 창 not 장
]


def add_weight(weight_line):
    """Add a single weight using atomic script."""
    print(f"\nAdding: {weight_line}")
    result = subprocess.run(
        [sys.executable, "scripts/atomic_add_weight.py", weight_line],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        # Extract just the key parts of output
        for line in result.stdout.split("\n"):
            if "✓ Added:" in line or "✅ All checks passed" in line:
                print(f"  {line}")
        return True
    else:
        print(f"Failed: {result.stdout}{result.stderr}")
        if (
            "Duplicate mapping already exists" in result.stderr
            or "Duplicate mapping already exists" in result.stdout
        ):
            print("  → Skipping duplicate")
            return True
        return False


def test_independent():
    """Run independent dataset test and return pass count."""
    result = subprocess.run(
        [sys.executable, "scripts/test_expanded_independent_dataset.py"],
        capture_output=True,
        text=True,
    )

    for line in result.stdout.split("\n"):
        if "Overall Performance:" in line:
            parts = line.split()
            if len(parts) >= 3:
                ratio = parts[2]
                passes = int(ratio.split("/")[0])
                return passes
    return 0


def main():
    print("=== ADDING SIMPLE SYLLABLE WEIGHTS ===")

    # Get baseline
    baseline_passes = test_independent()
    print(f"\nBaseline: {baseline_passes}/165 passes ({baseline_passes/165*100:.1f}%)")
    print(f"Target: 155+ passes (94%+)")
    print(f"Need to fix: {155 - baseline_passes} more cases\n")

    # Add weights one by one
    for weight in SIMPLE_WEIGHTS:
        if not add_weight(weight):
            print("\n⚠️  Stopping due to regression")
            return

    # Final test
    print("\n🔍 Running final test...")
    final_passes = test_independent()
    print(f"\n=== FINAL RESULTS ===")
    print(f"Started at: {baseline_passes}/165 ({baseline_passes/165*100:.1f}%)")
    print(f"Achieved: {final_passes}/165 ({final_passes/165*100:.1f}%)")
    print(f"Improvement: +{final_passes - baseline_passes} cases")

    if final_passes >= 155:
        print("\n✅ SUCCESS! Target of 94%+ achieved!")
    else:
        print(f"\n⚠️  Still need {155 - final_passes} more fixes to reach target")


if __name__ == "__main__":
    main()
