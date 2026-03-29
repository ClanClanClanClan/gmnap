#!/usr/bin/env python3
"""
Smart Test Consolidation - Keep ALL relevant tests, remove only true duplicates
"""

import os
import hashlib
import shutil
from pathlib import Path
from collections import defaultdict
import ast


class SmartTestConsolidator:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.test_root = Path("tests")
        self.file_hashes = {}
        self.test_functions = defaultdict(list)
        self.duplicates = []
        self.kept_tests = []

    def get_file_hash(self, filepath):
        """Get MD5 hash of file content"""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def extract_test_functions(self, filepath):
        """Extract test function names from Python file"""
        try:
            with open(filepath, "r") as f:
                tree = ast.parse(f.read())

            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith("test_"):
                        functions.append(node.name)
            return functions
        except:
            return []

    def analyze_tests(self):
        """Analyze all test files"""
        print("=== ANALYZING TEST FILES ===\n")

        all_tests = list(self.test_root.rglob("test_*.py")) + list(
            self.test_root.rglob("*_test.py")
        )
        all_tests = [t for t in all_tests if "__pycache__" not in str(t)]

        print(f"Found {len(all_tests)} test files")

        # Group by hash to find exact duplicates
        hash_groups = defaultdict(list)
        for test_file in all_tests:
            file_hash = self.get_file_hash(test_file)
            hash_groups[file_hash].append(test_file)

        # Find true duplicates
        for file_hash, files in hash_groups.items():
            if len(files) > 1:
                print(f"\nDuplicate set (hash: {file_hash[:8]}...):")
                for f in files:
                    print(f"  - {f}")
                # Keep the one with shortest path (likely the organized one)
                keeper = min(files, key=lambda x: len(str(x)))
                self.kept_tests.append(keeper)
                for f in files:
                    if f != keeper:
                        self.duplicates.append(f)

        print(f"\nFound {len(self.duplicates)} duplicate files to remove")
        print(f"Keeping {len(all_tests) - len(self.duplicates)} unique test files")

    def find_similar_tests(self):
        """Find tests with similar names but different content"""
        print("\n=== CHECKING FOR SIMILAR TEST NAMES ===\n")

        all_tests = list(self.test_root.rglob("test_*.py"))
        all_tests = [
            t
            for t in all_tests
            if "__pycache__" not in str(t) and t not in self.duplicates
        ]

        name_groups = defaultdict(list)
        for test_file in all_tests:
            name_groups[test_file.name].append(test_file)

        for name, files in name_groups.items():
            if len(files) > 1:
                # Check if they're actually different
                hashes = set()
                for f in files:
                    hashes.add(self.get_file_hash(f))

                if len(hashes) > 1:
                    print(
                        f"\n'{name}' exists in multiple locations with DIFFERENT content:"
                    )
                    for f in files:
                        functions = self.extract_test_functions(f)
                        print(f"  - {f} ({len(functions)} test functions)")
                        if functions and len(functions) <= 5:
                            print(f"    Functions: {', '.join(functions)}")

    def organize_structure(self):
        """Organize test structure keeping all relevant tests"""
        print("\n=== ORGANIZING TEST STRUCTURE ===\n")

        # Define clear structure
        structure = {
            "unit": "Fast isolated unit tests",
            "integration": "Component integration tests",
            "e2e": "End-to-end pipeline tests",
            "paranoid": "Comprehensive paranoid tests",
            "security": "Security validation tests",
            "performance": "Performance and benchmark tests",
            "regions": "Regional processor tests",
            "property": "Property-based tests",
            "fixtures": "Test data and helpers",
        }

        # Ensure directories exist
        for dir_name in structure:
            dir_path = self.test_root / dir_name
            dir_path.mkdir(exist_ok=True)

        print("Target structure created:")
        for dir_name, desc in structure.items():
            count = len(list((self.test_root / dir_name).glob("*.py")))
            print(f"  {dir_name:15} - {desc} ({count} files)")

    def remove_duplicates(self):
        """Remove only true duplicates"""
        print(f"\n=== REMOVING {len(self.duplicates)} DUPLICATE FILES ===\n")

        for dup in self.duplicates:
            if not self.dry_run:
                dup.unlink()
            print(f"{'[DRY RUN] ' if self.dry_run else ''}Removed: {dup}")

    def consolidate_stages(self):
        """Consolidate stage tests into integration/stages/"""
        print("\n=== CONSOLIDATING STAGE TESTS ===\n")

        stages_dir = self.test_root / "integration" / "stages"
        stages_dir.mkdir(exist_ok=True, parents=True)

        # Already handled in previous run
        stage_dirs = [
            d
            for d in self.test_root.iterdir()
            if d.is_dir() and d.name.startswith("stage")
        ]

        if stage_dirs:
            print(f"Found {len(stage_dirs)} stage directories")
        else:
            print("Stage tests already consolidated")

    def generate_test_report(self):
        """Generate comprehensive test report"""
        print("\n=== TEST INVENTORY REPORT ===\n")

        categories = defaultdict(list)
        all_tests = list(self.test_root.rglob("test_*.py"))
        all_tests = [t for t in all_tests if "__pycache__" not in str(t)]

        for test_file in all_tests:
            category = test_file.parent.name
            if category == "tests":
                category = "root"
            categories[category].append(test_file)

        total_test_functions = 0

        for category, files in sorted(categories.items()):
            print(f"\n{category.upper()} ({len(files)} files):")
            for f in sorted(files)[:5]:  # Show first 5
                functions = self.extract_test_functions(f)
                total_test_functions += len(functions)
                print(f"  - {f.name} ({len(functions)} tests)")
            if len(files) > 5:
                print(f"  ... and {len(files)-5} more files")

        print(f"\n📊 TOTALS:")
        print(f"  Test files: {len(all_tests)}")
        print(f"  Test functions: ~{total_test_functions}")
        print(f"  Categories: {len(categories)}")

    def run(self):
        print("=" * 60)
        print("SMART TEST CONSOLIDATION")
        print("Mode: " + ("DRY RUN" if self.dry_run else "EXECUTE"))
        print("=" * 60)

        # Analyze tests
        self.analyze_tests()

        # Find similar tests
        self.find_similar_tests()

        # Remove only true duplicates
        if self.duplicates:
            self.remove_duplicates()

        # Organize structure
        self.organize_structure()

        # Consolidate stages
        self.consolidate_stages()

        # Generate report
        self.generate_test_report()

        print("\n" + "=" * 60)
        print("SMART CONSOLIDATION COMPLETE")
        print(f"Removed {len(self.duplicates)} true duplicates")
        print(
            f"Kept ALL {len([f for f in self.test_root.rglob('test_*.py') if '__pycache__' not in str(f)])} relevant tests"
        )
        print("=" * 60)


if __name__ == "__main__":
    import sys

    dry_run = "--execute" not in sys.argv
    consolidator = SmartTestConsolidator(dry_run=dry_run)
    consolidator.run()
