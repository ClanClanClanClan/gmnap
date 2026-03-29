#!/usr/bin/env python3
"""
Comprehensive cleanup of the GMNAP project
"""

import os
import shutil
from pathlib import Path
from datetime import datetime


def cleanup_backup_files():
    """Remove backup and temporary files"""
    patterns = [
        "*.backup*",
        "*.bak",
        "*~",
        "*.tmp",
        "*.pyc",
        "__pycache__",
        "*.orig",
        "*.swp",
        ".DS_Store",
    ]

    removed_count = 0
    for pattern in patterns:
        for filepath in Path(".").rglob(pattern):
            try:
                if filepath.is_file():
                    filepath.unlink()
                elif filepath.is_dir():
                    shutil.rmtree(filepath)
                removed_count += 1
                print(f"  ✅ Removed: {filepath}")
            except Exception as e:
                print(f"  ⚠️  Could not remove {filepath}: {e}")

    return removed_count


def cleanup_test_cache():
    """Clean pytest cache and temp directories"""
    cache_dirs = [
        ".pytest_cache",
        ".coverage",
        "htmlcov",
        ".hypothesis",
        "test-results",
        "test_cache*",
    ]

    removed_count = 0
    for cache_dir in cache_dirs:
        for dirpath in Path(".").rglob(cache_dir):
            try:
                shutil.rmtree(dirpath)
                removed_count += 1
                print(f"  ✅ Removed cache: {dirpath}")
            except Exception as e:
                print(f"  ⚠️  Could not remove {dirpath}: {e}")

    return removed_count


def cleanup_obsolete_dirs():
    """Remove obsolete and archive directories older than needed"""
    obsolete_patterns = [
        "tests/unit/obsolete",
        "tests/integration/obsolete",
        "scripts/archive_*",
        "docs/archive/old_versions",
    ]

    removed_count = 0
    for pattern in obsolete_patterns:
        for dirpath in Path(".").glob(pattern):
            if dirpath.exists():
                try:
                    shutil.rmtree(dirpath)
                    removed_count += 1
                    print(f"  ✅ Removed obsolete: {dirpath}")
                except Exception as e:
                    print(f"  ⚠️  Could not remove {dirpath}: {e}")

    return removed_count


def cleanup_duplicate_test_files():
    """Remove duplicate test files with similar names"""
    test_dirs = ["tests/unit", "tests/integration"]

    duplicates = []
    for test_dir in test_dirs:
        if not Path(test_dir).exists():
            continue

        test_files = {}
        for filepath in Path(test_dir).rglob("test_*.py"):
            base_name = filepath.stem.replace("test_", "")

            # Check for variations like test_foo, test_foo_fixed, test_foo_v2, etc.
            core_name = base_name.split("_")[0] if "_" in base_name else base_name

            if core_name not in test_files:
                test_files[core_name] = []
            test_files[core_name].append(filepath)

        # Find potential duplicates
        for core_name, files in test_files.items():
            if len(files) > 1:
                # Keep the shortest name (likely the original)
                files.sort(key=lambda x: len(x.name))
                for dup_file in files[1:]:
                    if (
                        "fixed" in dup_file.name
                        or "v2" in dup_file.name
                        or "backup" in dup_file.name
                    ):
                        duplicates.append(dup_file)

    removed_count = 0
    for dup_file in duplicates:
        try:
            print(f"  ✅ Removed duplicate: {dup_file}")
            dup_file.unlink()
            removed_count += 1
        except Exception as e:
            print(f"  ⚠️  Could not remove {dup_file}: {e}")

    return removed_count


def organize_docs():
    """Organize documentation files"""
    # Move old audit reports to archive
    audit_files = list(Path(".").glob("*AUDIT*.md"))
    audit_files += list(Path(".").glob("*_REPORT*.md"))
    audit_files += list(Path(".").glob("V7_*.md"))

    archive_dir = Path("docs/archive") / datetime.now().strftime("%Y-%m-%d")
    archive_dir.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    for audit_file in audit_files:
        if audit_file.exists() and audit_file.is_file():
            try:
                dest = archive_dir / audit_file.name
                shutil.move(str(audit_file), str(dest))
                print(f"  ✅ Archived: {audit_file.name}")
                moved_count += 1
            except Exception as e:
                print(f"  ⚠️  Could not archive {audit_file}: {e}")

    return moved_count


def cleanup_empty_dirs():
    """Remove empty directories"""
    removed_count = 0
    for dirpath, dirnames, filenames in os.walk(".", topdown=False):
        if dirpath.startswith("./.git"):
            continue

        if not dirnames and not filenames:
            try:
                os.rmdir(dirpath)
                removed_count += 1
                print(f"  ✅ Removed empty dir: {dirpath}")
            except Exception:
                pass  # Directory not empty or permission issue

    return removed_count


def main():
    print("🧹 COMPREHENSIVE PROJECT CLEANUP")
    print("=" * 60)

    total_removed = 0

    print("\n📁 Cleaning backup files...")
    total_removed += cleanup_backup_files()

    print("\n📁 Cleaning test cache...")
    total_removed += cleanup_test_cache()

    print("\n📁 Cleaning obsolete directories...")
    total_removed += cleanup_obsolete_dirs()

    print("\n📁 Cleaning duplicate test files...")
    total_removed += cleanup_duplicate_test_files()

    print("\n📁 Organizing documentation...")
    moved = organize_docs()

    print("\n📁 Cleaning empty directories...")
    total_removed += cleanup_empty_dirs()

    print("\n" + "=" * 60)
    print(f"✅ CLEANUP COMPLETE")
    print(f"  - Items removed: {total_removed}")
    print(f"  - Docs archived: {moved}")

    # Show current project stats
    print("\n📊 PROJECT STATS AFTER CLEANUP:")
    os.system("find . -name '*.py' -type f | wc -l | xargs echo '  - Python files:'")
    os.system(
        "find tests -name 'test_*.py' -type f | wc -l | xargs echo '  - Test files:'"
    )
    os.system("du -sh . | cut -f1 | xargs echo '  - Total size:'")


if __name__ == "__main__":
    main()
