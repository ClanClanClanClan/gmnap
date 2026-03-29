#!/usr/bin/env python3
"""
ULTRATHINK COMPREHENSIVE CLEANUP SCRIPT
Cleans, organizes, and optimizes the entire GMNAP codebase
"""

import os
import shutil
import hashlib
from pathlib import Path
from collections import defaultdict
import json


class UltrathinkCleaner:
    def __init__(self):
        self.root = Path(".")
        self.stats = {
            "cache_files_removed": 0,
            "duplicate_files_found": 0,
            "backup_files_removed": 0,
            "test_results_removed": 0,
            "empty_dirs_removed": 0,
            "markdown_files_reviewed": 0,
            "python_files_checked": 0,
            "total_space_freed_mb": 0,
        }
        self.duplicates = defaultdict(list)
        self.to_delete = []
        self.to_reorganize = []

    def scan_all_files(self):
        """Scan entire codebase for issues"""
        print("🔍 SCANNING ENTIRE CODEBASE...")

        # Patterns to clean
        cache_patterns = [
            "**/__pycache__",
            "**/*.pyc",
            "**/*.pyo",
            "**/*.pyd",
            "**/*~",
            "**/.DS_Store",
            "**/*.swp",
            "**/*.swo",
            "**/.pytest_cache",
            "**/node_modules",
            "**/.coverage",
            "**/*.egg-info",
            "**/build",
            "**/dist",
            "**/.mypy_cache",
            "**/.ruff_cache",
            "**/.hypothesis",
        ]

        backup_patterns = [
            "**/*.bak",
            "**/*.backup*",
            "**/*_backup*",
            "**/*.old",
            "**/*.orig",
            "**/*.save",
            "**/*_old.*",
            "**/*_copy.*",
            "**/*.tmp",
        ]

        test_result_patterns = [
            "**/test_results*.json",
            "**/validation_results*.json",
            "**/audit_results*.json",
            "**/report_*.json",
            "**/*_test_output.json",
            "**/*_audit_*.json",
            "**/realistic_test_results*.json",
        ]

        # Find cache files
        for pattern in cache_patterns:
            for path in self.root.glob(pattern):
                if ".venv" not in str(path) and ".git" not in str(path):
                    self.to_delete.append(path)
                    self.stats["cache_files_removed"] += 1

        # Find backup files
        for pattern in backup_patterns:
            for path in self.root.glob(pattern):
                if ".venv" not in str(path) and ".git" not in str(path):
                    self.to_delete.append(path)
                    self.stats["backup_files_removed"] += 1

        # Find test result files
        for pattern in test_result_patterns:
            for path in self.root.glob(pattern):
                if ".venv" not in str(path) and ".git" not in str(path):
                    self.to_delete.append(path)
                    self.stats["test_results_removed"] += 1

    def find_duplicate_files(self):
        """Find duplicate files by content hash"""
        print("🔍 FINDING DUPLICATE FILES...")

        file_hashes = defaultdict(list)

        for path in self.root.glob("**/*.py"):
            if ".venv" not in str(path) and ".git" not in str(path):
                if path.is_file():
                    try:
                        with open(path, "rb") as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                            file_hashes[file_hash].append(path)
                    except:
                        pass

        # Find duplicates
        for file_hash, paths in file_hashes.items():
            if len(paths) > 1:
                self.duplicates[file_hash] = paths
                self.stats["duplicate_files_found"] += len(paths) - 1

    def clean_empty_directories(self):
        """Remove empty directories"""
        print("🔍 CLEANING EMPTY DIRECTORIES...")

        for root, dirs, files in os.walk(".", topdown=False):
            if ".venv" not in root and ".git" not in root:
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if not any(dir_path.iterdir()):
                            self.to_delete.append(dir_path)
                            self.stats["empty_dirs_removed"] += 1
                    except:
                        pass

    def analyze_documentation(self):
        """Analyze excessive documentation"""
        print("🔍 ANALYZING DOCUMENTATION...")

        # Find all markdown files
        md_files = list(self.root.glob("**/*.md"))
        md_files = [
            f for f in md_files if ".venv" not in str(f) and ".git" not in str(f)
        ]

        # Group by directory
        docs_by_dir = defaultdict(list)
        for md_file in md_files:
            docs_by_dir[md_file.parent].append(md_file)

        # Find directories with excessive docs
        for directory, files in docs_by_dir.items():
            if len(files) > 5:  # More than 5 MD files in one directory
                print(f"  📁 {directory}: {len(files)} markdown files")
                self.stats["markdown_files_reviewed"] += len(files)

    def identify_redundant_scripts(self):
        """Identify redundant/duplicate scripts"""
        print("🔍 IDENTIFYING REDUNDANT SCRIPTS...")

        # Common redundant patterns in Korean scripts
        korean_scripts = (
            list(Path("scripts/korean").glob("*.py"))
            if Path("scripts/korean").exists()
            else []
        )
        korean_src = (
            list(Path("src/regions/e_groups/e4_korea").glob("**/*.py"))
            if Path("src/regions/e_groups/e4_korea").exists()
            else []
        )

        # Find similar named files
        name_groups = defaultdict(list)
        for script in korean_scripts + korean_src:
            base_name = script.stem.lower()
            # Remove common suffixes
            for suffix in [
                "_v2",
                "_v3",
                "_final",
                "_fixed",
                "_new",
                "_old",
                "_backup",
                "_test",
            ]:
                base_name = base_name.replace(suffix, "")
            name_groups[base_name].append(script)

        # Report duplicates
        for name, paths in name_groups.items():
            if len(paths) > 1:
                print(f"  🔁 Similar files for '{name}':")
                for path in paths:
                    print(f"     - {path}")

    def generate_cleanup_plan(self):
        """Generate cleanup plan"""
        print("\n" + "=" * 80)
        print("ULTRATHINK CLEANUP PLAN")
        print("=" * 80)

        # Calculate space to be freed
        total_size = 0
        for path in self.to_delete:
            try:
                if path.is_file():
                    total_size += path.stat().st_size
            except:
                pass

        self.stats["total_space_freed_mb"] = total_size / (1024 * 1024)

        print(f"\n📊 STATISTICS:")
        print(f"  • Cache files to remove: {self.stats['cache_files_removed']}")
        print(f"  • Backup files to remove: {self.stats['backup_files_removed']}")
        print(f"  • Test result files to remove: {self.stats['test_results_removed']}")
        print(f"  • Empty directories to remove: {self.stats['empty_dirs_removed']}")
        print(f"  • Duplicate files found: {self.stats['duplicate_files_found']}")
        print(f"  • Space to be freed: {self.stats['total_space_freed_mb']:.2f} MB")

        print(f"\n📁 FILES TO DELETE: {len(self.to_delete)}")
        if self.to_delete:
            print("  First 20 files:")
            for path in list(self.to_delete)[:20]:
                print(f"    • {path}")

        if self.duplicates:
            print(f"\n🔁 DUPLICATE FILES:")
            for i, (hash_val, paths) in enumerate(list(self.duplicates.items())[:5]):
                print(f"  Group {i+1}:")
                for path in paths:
                    print(f"    • {path}")

    def execute_cleanup(self, dry_run=True):
        """Execute the cleanup"""
        if dry_run:
            print("\n⚠️  DRY RUN MODE - No files will be deleted")
            print("Run with execute_cleanup(dry_run=False) to actually delete files")
        else:
            print("\n🗑️  EXECUTING CLEANUP...")
            deleted = 0
            for path in self.to_delete:
                try:
                    if path.is_file():
                        path.unlink()
                    elif path.is_dir():
                        shutil.rmtree(path)
                    deleted += 1
                except Exception as e:
                    print(f"  ❌ Could not delete {path}: {e}")

            print(f"\n✅ Deleted {deleted} files/directories")
            print(f"✅ Freed {self.stats['total_space_freed_mb']:.2f} MB")

    def suggest_reorganization(self):
        """Suggest folder reorganization"""
        print("\n" + "=" * 80)
        print("SUGGESTED REORGANIZATION")
        print("=" * 80)

        suggestions = [
            (
                "Move all test data to data/test/",
                [
                    "data/expanded_independent_validation_dataset.json",
                    "data/independent_validation_dataset.json",
                    "datasets/*",
                ],
            ),
            (
                "Consolidate Korean scripts",
                [
                    "scripts/korean/* -> src/regions/e_groups/e4_korea/tools/",
                    "Remove duplicate analysis scripts",
                ],
            ),
            (
                "Archive old documentation",
                [
                    "docs/archive/* -> separate archive repo",
                    "docs/handover/* -> docs/archive/",
                    "docs/cleanup/* -> docs/archive/",
                ],
            ),
            (
                "Consolidate configuration",
                [
                    "config/*.push*.yaml -> config/deployment/",
                    "config/*.extreme.yaml -> config/testing/",
                    "config/stage*.yaml -> config/stages/",
                ],
            ),
            (
                "Clean test structure",
                [
                    "tests/unit/korean/* -> tests/regional/e4_korea/",
                    "tests/integration/test_korean*.py -> tests/regional/e4_korea/",
                    "Remove duplicate test files",
                ],
            ),
        ]

        for suggestion, details in suggestions:
            print(f"\n📦 {suggestion}")
            for detail in details:
                print(f"   • {detail}")

    def run(self):
        """Run complete cleanup analysis"""
        print("=" * 80)
        print("ULTRATHINK COMPREHENSIVE CLEANUP SYSTEM")
        print("=" * 80)

        self.scan_all_files()
        self.find_duplicate_files()
        self.clean_empty_directories()
        self.analyze_documentation()
        self.identify_redundant_scripts()
        self.generate_cleanup_plan()
        self.suggest_reorganization()

        # Save report
        report_path = Path("ULTRATHINK_CLEANUP_REPORT.json")
        with open(report_path, "w") as f:
            json.dump(
                {
                    "stats": self.stats,
                    "files_to_delete": [str(p) for p in self.to_delete[:100]],
                    "duplicate_groups": {
                        k: [str(p) for p in v]
                        for k, v in list(self.duplicates.items())[:10]
                    },
                },
                f,
                indent=2,
            )

        print(f"\n📄 Full report saved to: {report_path}")
        print("\n⚡ To execute cleanup, run:")
        print("   cleaner.execute_cleanup(dry_run=False)")

        return self


if __name__ == "__main__":
    cleaner = UltrathinkCleaner()
    cleaner.run()

    # Uncomment to actually execute cleanup
    # response = input("\n⚠️  Execute cleanup? (yes/no): ")
    # if response.lower() == 'yes':
    #     cleaner.execute_cleanup(dry_run=False)
