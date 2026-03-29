#!/usr/bin/env python3
"""Verify current structure and plan reorganization moves."""

import os
from pathlib import Path
import json


def analyze_directory_structure():
    """Analyze current directory structure vs v7 requirements."""

    root = Path("/Users/dylanpossamai/Dropbox/Work/Maths/gmnap")

    # Check for duplicate structures
    duplicates = {
        "src/core vs src/gmnap/core": {
            "old": (
                list(Path(root / "src/core").glob("*.py")) if (root / "src/core").exists() else []
            ),
            "new": (
                list(Path(root / "src/gmnap/core").glob("*.py"))
                if (root / "src/gmnap/core").exists()
                else []
            ),
        },
        "src/authorities vs src/gmnap/authorities": {
            "old": (
                list(Path(root / "src/authorities").glob("**/*.py"))
                if (root / "src/authorities").exists()
                else []
            ),
            "new": (
                list(Path(root / "src/gmnap/authorities").glob("**/*.py"))
                if (root / "src/gmnap/authorities").exists()
                else []
            ),
        },
    }

    # Check for missing v7 components
    missing_v7 = []
    required_dirs = [
        "src/gmnap/linguistic",
        "src/gmnap/validation",
        "src/gmnap/utils",
        "src/gmnap/authorities/tier1",
        "src/gmnap/authorities/tier2",
        "config",
        "tools/dictionaries",
        "tools/cli",
        "tests/sea_roundtrip",
        "tests/concurrency",
        "tests/memory_peak",
        "tests/msc_provenance",
        "tests/fake_api",
        "tests/secret_scan",
    ]

    for dir_path in required_dirs:
        if not (root / dir_path).exists():
            missing_v7.append(dir_path)

    # Check for misplaced components
    misplaced = {}

    # Check if old src/ directories exist
    old_dirs = ["src/core", "src/authorities", "src/linguistic", "src/utils", "src/validation"]
    for old_dir in old_dirs:
        if (root / old_dir).exists():
            files = list(Path(root / old_dir).glob("**/*.py"))
            if files:
                misplaced[old_dir] = len(files)

    # Check for scattered tests
    scattered_tests = {
        "cleanup_work/test_scripts": (
            len(list(Path(root / "cleanup_work/test_scripts").glob("*.py")))
            if (root / "cleanup_work/test_scripts").exists()
            else 0
        ),
        "korean tests": (
            len(list(Path(root / "src/gmnap/regions/e_groups/e4_korea/tests").glob("*.py")))
            if (root / "src/gmnap/regions/e_groups/e4_korea/tests").exists()
            else 0
        ),
    }

    # Generate report
    report = {
        "duplicates": duplicates,
        "missing_v7_dirs": missing_v7,
        "misplaced_components": misplaced,
        "scattered_tests": scattered_tests,
    }

    return report


def generate_move_commands(report):
    """Generate shell commands for reorganization."""

    commands = []
    root = "/Users/dylanpossamai/Dropbox/Work/Maths/gmnap"

    # Phase 1: Core consolidation
    commands.append("# Phase 1: Core Structure Consolidation")

    if report["misplaced_components"]:
        for old_dir in report["misplaced_components"]:
            new_dir = old_dir.replace("src/", "src/gmnap/")
            commands.append(f"# Move {old_dir} to {new_dir}")
            commands.append(f"mkdir -p {root}/{new_dir}")
            commands.append(f"mv {root}/{old_dir}/* {root}/{new_dir}/ 2>/dev/null || true")
            commands.append(f"rmdir {root}/{old_dir}")
            commands.append("")

    # Create missing directories
    if report["missing_v7_dirs"]:
        commands.append("# Create missing v7 directories")
        for missing_dir in report["missing_v7_dirs"]:
            commands.append(f"mkdir -p {root}/{missing_dir}")
        commands.append("")

    # Phase 2: Test consolidation
    if any(report["scattered_tests"].values()):
        commands.append("# Phase 2: Test Infrastructure Unification")
        if report["scattered_tests"]["korean tests"] > 0:
            commands.append("mkdir -p tests/unit/korean/")
            commands.append(
                "mv src/gmnap/regions/e_groups/e4_korea/tests/* tests/unit/korean/ 2>/dev/null || true"
            )
        if report["scattered_tests"]["cleanup_work/test_scripts"] > 0:
            commands.append(
                "mv cleanup_work/test_scripts/test_*.py tests/integration/ 2>/dev/null || true"
            )
            commands.append(
                "mv cleanup_work/test_scripts/comprehensive_*.py tests/quality_gates/ 2>/dev/null || true"
            )
        commands.append("")

    return commands


def main():
    """Run verification and generate reorganization plan."""

    print("=== GMNAP V7 Architecture Verification ===\n")

    report = analyze_directory_structure()

    # Print analysis
    print("1. DUPLICATE STRUCTURES:")
    for name, data in report["duplicates"].items():
        print(f"   {name}:")
        print(f"   - Old: {len(data['old'])} files")
        print(f"   - New: {len(data['new'])} files")

    print("\n2. MISSING V7 DIRECTORIES:")
    for missing in report["missing_v7_dirs"]:
        print(f"   - {missing}")

    print("\n3. MISPLACED COMPONENTS:")
    for comp, count in report["misplaced_components"].items():
        print(f"   - {comp}: {count} files")

    print("\n4. SCATTERED TESTS:")
    for location, count in report["scattered_tests"].items():
        print(f"   - {location}: {count} files")

    # Generate move commands
    commands = generate_move_commands(report)

    print("\n=== REORGANIZATION COMMANDS ===\n")
    for cmd in commands:
        print(cmd)

    # Save report
    with open("reorganization_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    print("\nReport saved to reorganization_report.json")


if __name__ == "__main__":
    main()
