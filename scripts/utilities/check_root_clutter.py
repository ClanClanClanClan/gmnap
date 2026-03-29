#!/usr/bin/env python3
"""
Check for root directory clutter and suggest proper locations for files.
Run this before commits to ensure clean root directory.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Define what files are allowed in root
ALLOWED_ROOT_FILES = {
    # Standard project files
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    # Build and config
    "Makefile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    # Python requirements
    "requirements.txt",
    "requirements.in",
    "requirements-dev.txt",
    "requirements-dev.in",
    # Testing
    "pytest.ini",
    "tox.ini",
    "noxfile.py",
    # CI/CD
    ".travis.yml",
    ".gitlab-ci.yml",
    "azure-pipelines.yml",
    "Jenkinsfile",
    # Git and dev tools
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".pre-commit-config.yaml",
    ".pre-commit-config.yml",
    # Linting
    ".flake8",
    ".pylintrc",
    ".yamllint",
    ".markdownlint.json",
    # Project specific
    "CLAUDE.md",  # AI instructions
    "apply_overlays.sh",  # Deployment script
}

# Define patterns and their suggested locations
FILE_PATTERNS: Dict[str, str] = {
    # Test files
    "test_*.py": "tests/",
    "*_test.py": "tests/",
    "*test*.py": "tests/",
    "test_*.sh": "tests/",
    # Documentation
    "*_REPORT.md": "docs/reports/",
    "*_STATUS.md": "docs/reports/",
    "*_AUDIT.md": "docs/audits/",
    "*_ANALYSIS.md": "docs/audits/",
    "*_PLAN.md": "docs/plans/",
    "*_GUIDE.md": "docs/guides/",
    "ULTRA*.md": "docs/reports/",
    "FINAL_*.md": "docs/reports/",
    "CLEANUP_*.md": "docs/cleanup/",
    "V7_*.md": "docs/compliance/",
    "KOREAN_*.md": "docs/implementation/",
    "PRODUCTION_*.md": "docs/deployment/",
    "OPTIMIZATION_*.md": "docs/performance/",
    # Scripts
    "debug_*.py": "scripts/analysis/",
    "analyze_*.py": "scripts/analysis/",
    "benchmark_*.py": "scripts/analysis/",
    "systematic_*.py": "scripts/analysis/",
    "ultraudit*.py": "scripts/analysis/",
    "apply_*.py": "scripts/utilities/",
    "fix_*.py": "scripts/fixes/",
    "*.sh": "scripts/",
    # Data files
    "*.csv": "data/",
    "*.json": "data/",
    "*.yaml": "config/",
    "*.yml": "config/",
    # Temporary files
    "temp_*": "tmp/",
    "tmp_*": "tmp/",
    "scratch_*": "tmp/",
    "draft_*": "drafts/",
    "wip_*": "wip/",
    "TODO_*": "docs/todos/",
}


def check_root_clutter(root_path: Path = Path(".")) -> Tuple[List[str], Dict[str, str]]:
    """
    Check for files that shouldn't be in root directory.

    Returns:
        Tuple of (clean_files, problematic_files_with_suggestions)
    """
    clean = []
    problematic = {}

    # Get all files in root (not directories)
    for item in root_path.iterdir():
        if item.is_file():
            filename = item.name

            # Skip hidden files (start with .)
            if filename.startswith("."):
                continue

            # Check if file is allowed
            if filename in ALLOWED_ROOT_FILES:
                clean.append(filename)
                continue

            # Check against patterns
            suggested_location = None
            for pattern, location in FILE_PATTERNS.items():
                if match_pattern(filename, pattern):
                    suggested_location = location
                    break

            if suggested_location:
                problematic[filename] = suggested_location
            else:
                # Unknown file type - suggest generic location
                if filename.endswith(".py"):
                    problematic[filename] = "scripts/ or src/"
                elif filename.endswith(".md"):
                    problematic[filename] = "docs/"
                elif filename.endswith((".txt", ".log", ".out")):
                    problematic[filename] = "logs/ or data/"
                else:
                    problematic[filename] = "resources/ or data/"

    return clean, problematic


def match_pattern(filename: str, pattern: str) -> bool:
    """Simple pattern matching (supports * wildcard)."""
    import fnmatch

    return fnmatch.fnmatch(filename, pattern)


def print_report(clean: List[str], problematic: Dict[str, str]) -> int:
    """
    Print clutter report and return exit code.

    Returns:
        0 if root is clean, 1 if there's clutter
    """
    total_files = len(clean) + len(problematic)

    print("=" * 60)
    print("ROOT DIRECTORY CLUTTER CHECK")
    print("=" * 60)
    print(f"\nTotal files in root: {total_files}")
    print(f"✅ Clean files: {len(clean)}")
    print(f"❌ Files that should be moved: {len(problematic)}")

    if problematic:
        print("\n" + "=" * 60)
        print("FILES THAT SHOULD BE MOVED:")
        print("=" * 60)

        for filename, location in sorted(problematic.items()):
            print(f"\n📄 {filename}")
            print(f"   → Move to: {location}")

        print("\n" + "=" * 60)
        print("SUGGESTED COMMANDS:")
        print("=" * 60)

        # Group by destination
        moves_by_dest = {}
        for filename, location in problematic.items():
            if location not in moves_by_dest:
                moves_by_dest[location] = []
            moves_by_dest[location].append(filename)

        for location, files in sorted(moves_by_dest.items()):
            print(f"\n# Move to {location}")
            print(f"mkdir -p {location}")
            for f in files[:3]:  # Show first 3 as examples
                print(f"mv {f} {location}")
            if len(files) > 3:
                print(f"# ... and {len(files) - 3} more files")

        print("\n" + "=" * 60)
        print("❌ ROOT DIRECTORY HAS CLUTTER")
        print("Please move the files to their appropriate locations.")
        print("=" * 60)
        return 1
    else:
        print("\n" + "=" * 60)
        print("✅ ROOT DIRECTORY IS CLEAN!")
        print("=" * 60)
        return 0


def main():
    """Main entry point."""
    # Check if we're in the project root
    if not Path("src").exists() or not Path("tests").exists():
        print("⚠️  Warning: This script should be run from the project root directory.")
        print("   Current directory:", os.getcwd())
        response = input("Continue anyway? (y/n): ")
        if response.lower() != "y":
            sys.exit(1)

    clean, problematic = check_root_clutter()
    exit_code = print_report(clean, problematic)

    # If running in CI mode, exit with appropriate code
    if os.environ.get("CI"):
        sys.exit(exit_code)

    return exit_code


if __name__ == "__main__":
    exit_code = main()
    if exit_code == 0:
        print("\n✨ Great job keeping the root directory clean!")
    else:
        print("\n💡 Tip: Run 'make organize' to automatically organize files.")
