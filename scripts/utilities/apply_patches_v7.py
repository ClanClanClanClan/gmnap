#!/usr/bin/env python3
"""
Apply V7 patches in the correct order
Triple-checks everything as requested
"""

import subprocess
import sys
from pathlib import Path


def apply_patch(patch_file, dry_run=False):
    """Apply a single patch file"""
    cmd = ["patch", "-p1"]
    if dry_run:
        cmd.append("--dry-run")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Applying patch: {patch_file}")

    try:
        with open(patch_file, "r") as f:
            result = subprocess.run(cmd, stdin=f, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"  ✓ Patch {'would apply' if dry_run else 'applied'} successfully")
            if result.stdout:
                for line in result.stdout.strip().split("\n")[:5]:  # Show first 5 lines
                    print(f"    {line}")
            return True
        else:
            print(f"  ✗ Patch failed:")
            if result.stderr:
                for line in result.stderr.strip().split("\n")[:10]:
                    print(f"    {line}")
            return False
    except Exception as e:
        print(f"  ✗ Error applying patch: {e}")
        return False


def main():
    """Apply all patches in order"""

    # Define patch order based on push numbering
    # Initial patches from gmnap_v7_patch_2025-08-31
    initial_patches = [
        "reparation_plan/gmnap_v7_patch_2025-08-31/patches/pipeline_v7.patch",
        "reparation_plan/gmnap_v7_patch_2025-08-31/patches/streaming_v7.patch",
        "reparation_plan/gmnap_v7_patch+authority_2025-08-31/patches/pipeline_stage4.patch",
    ]

    # Push patches in numerical order
    push_patches = [
        # Push 1
        "reparation_plan/gmnap_v7_push1_REBUILD_2025-09-01/patches/pipeline_stage0_1.patch",
        # Push 2
        "reparation_plan/gmnap_v7_push2_REBUILD_2025-09-01/patches/pipeline_stage2.patch",
        "reparation_plan/gmnap_v7_superbundle_2025-09-01/overlays/push2/patches/pipeline_stage2_3.patch",
        # Push 3 (no patches found for push3)
        # Push 4
        "reparation_plan/gmnap_v7_push4_REBUILD_2025-09-01/patches/pipeline_stage5_6.patch",
        # Push 5
        "reparation_plan/gmnap_v7_push5_REBUILD_2025-09-01/patches/pipeline_stage4.patch",
        "reparation_plan/gmnap_v7_superbundle_2025-09-01/overlays/push5/patches/pipeline_stage5_duckdb.patch",
        # Push 6
        "reparation_plan/gmnap_v7_push6_REBUILD_2025-09-01/patches/authority_manager_tier1.patch",
        # Push 7
        "reparation_plan/gmnap_v7_push7_REBUILD_2025-09-01/patches/pipeline_stage1b_8.patch",
        "reparation_plan/gmnap_v7_push7_REBUILD_2025-09-01/patches/region_b1_fix.patch",
        # Push 8
        "reparation_plan/gmnap_v7_push8_2025-09-01/patches/pipeline_stage9.patch",
        "reparation_plan/gmnap_v7_superbundle_2025-09-01/overlays/push8/patches/pipeline_stage9.patch",
        "reparation_plan/gmnap_v7_superbundle_2025-09-01/overlays/push8/patches/streaming_v7_schema_gate.patch",
        # Push 9
        "reparation_plan/gmnap_v7_push9_2025-09-01/patches/pipeline_stage9_dbapply.patch",
        "reparation_plan/gmnap_v7_superbundle_2025-09-01/overlays/push9/patches/stage9_edges.patch",
        # Push 10
        "reparation_plan/gmnap_v7_push10_2025-09-01/patches/pipeline_stage10_hardening.patch",
        "reparation_plan/gmnap_v7_superbundle_2025-09-01/overlays/push10/patches/pipeline_stage10_refresh.patch",
        # Push 11
        "reparation_plan/gmnap_v7_push11_2025-09-01/patches/pipeline_stage11.patch",
        "reparation_plan/gmnap_v7_superbundle_2025-09-01/overlays/push11/patches/pipeline_stage11.patch",
        # Push 12
        "reparation_plan/gmnap_v7_push12_2025-09-01/patches/pipeline_stage12_metrics.patch",
        "reparation_plan/gmnap_v7_superbundle_2025-09-01/overlays/push12/patches/pipeline_stage12_metrics.patch",
    ]

    all_patches = initial_patches + push_patches

    # Filter to only existing patches
    existing_patches = []
    missing_patches = []
    for patch in all_patches:
        if Path(patch).exists():
            existing_patches.append(patch)
        else:
            missing_patches.append(patch)

    print(f"\nFound {len(existing_patches)} patches to apply")
    if missing_patches:
        print(f"Missing {len(missing_patches)} patches:")
        for patch in missing_patches[:5]:  # Show first 5
            print(f"  - {patch}")
        if len(missing_patches) > 5:
            print(f"  ... and {len(missing_patches) - 5} more")

    if not existing_patches:
        print("\n✗ No patches found to apply")
        return 1

    # First do a dry run
    print("\n" + "=" * 70)
    print("PHASE 1: DRY RUN - Testing if patches will apply cleanly")
    print("=" * 70)

    all_good = True
    failed_patches = []
    for i, patch in enumerate(existing_patches, 1):
        print(f"\n[{i}/{len(existing_patches)}]", end=" ")
        if not apply_patch(patch, dry_run=True):
            all_good = False
            failed_patches.append(patch)

    if not all_good:
        print("\n" + "=" * 70)
        print(f"✗ {len(failed_patches)} patches would fail:")
        for patch in failed_patches:
            print(f"  - {patch}")
        print("\nPlease fix conflicts first or skip these patches.")
        return 1

    print("\n" + "=" * 70)
    print("✓ All patches would apply cleanly!")
    print("=" * 70)

    # Ask for confirmation
    response = input(f"\nReady to apply {len(existing_patches)} patches? (yes/no): ")

    if response.lower() != "yes":
        print("Aborted by user")
        return 0

    # Apply patches for real
    print("\n" + "=" * 70)
    print("PHASE 2: ACTUAL APPLICATION")
    print("=" * 70)

    successfully_applied = []
    for i, patch in enumerate(existing_patches, 1):
        print(f"\n[{i}/{len(existing_patches)}]", end=" ")
        if apply_patch(patch, dry_run=False):
            successfully_applied.append(patch)
        else:
            print(f"\n✗ Failed to apply patch {patch}")
            print(
                f"Successfully applied {len(successfully_applied)} patches before failure"
            )
            print("Stopping here to avoid further issues")
            return 1

    print("\n" + "=" * 70)
    print(f"✓ Successfully applied {len(successfully_applied)} patches!")
    print("=" * 70)

    # Verify the system after patches
    print("\nRunning post-patch verification...")
    result = subprocess.run(
        ["python3", "v7_systematic_check.py"], capture_output=True, text=True
    )

    # Show just the summary
    lines = result.stdout.split("\n")
    summary_started = False
    for line in lines:
        if "SUMMARY" in line:
            summary_started = True
        if summary_started:
            print(line)

    return 0


if __name__ == "__main__":
    sys.exit(main())
