#!/usr/bin/env python3
"""
ULTRATHINK DEEP REORGANIZATION
Complete restructuring and optimization of GMNAP codebase
"""

import os
import shutil
from pathlib import Path
import hashlib


class DeepReorganizer:
    def __init__(self):
        self.root = Path(".")
        self.actions = []

    def analyze_korean_consolidation(self):
        """Analyze and consolidate Korean scripts"""
        print("\n📦 KOREAN SCRIPT CONSOLIDATION PLAN:")

        # Find all Korean-related files
        korean_locations = [
            Path("scripts/korean"),
            Path("src/regions/e_groups/e4_korea/scripts"),
            Path("src/regions/e_groups/e4_korea/backups"),
            Path("src/regions/e_groups/e4_korea"),
        ]

        all_korean_files = {}
        for location in korean_locations:
            if location.exists():
                for file in location.glob("**/*.py"):
                    if ".venv" not in str(file):
                        # Get file hash to detect duplicates
                        with open(file, "rb") as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()

                        base_name = file.name
                        if base_name not in all_korean_files:
                            all_korean_files[base_name] = []
                        all_korean_files[base_name].append((file, file_hash))

        # Identify duplicates and consolidation plan
        consolidation_target = Path("src/regions/e_groups/e4_korea/tools")

        print(f"\n  Target directory: {consolidation_target}")
        print(f"  Found {len(all_korean_files)} unique file names across all locations")

        duplicate_count = 0
        for name, locations in all_korean_files.items():
            if len(locations) > 1:
                unique_hashes = set(h for _, h in locations)
                if len(unique_hashes) == 1:
                    duplicate_count += 1
                    print(f"\n  🔁 DUPLICATE: {name}")
                    for path, _ in locations:
                        print(f"      - {path.relative_to(self.root)}")
                    self.actions.append(
                        ("consolidate_duplicate", name, locations[0][0], consolidation_target)
                    )
                else:
                    print(f"\n  ⚠️  CONFLICT: {name} has {len(unique_hashes)} different versions")
                    for path, hash_val in locations:
                        print(f"      - {path.relative_to(self.root)} [{hash_val[:8]}]")

        print(f"\n  Total pure duplicates: {duplicate_count}")

    def analyze_test_consolidation(self):
        """Analyze and consolidate test files"""
        print("\n📦 TEST FILE CONSOLIDATION PLAN:")

        # Find Korean tests scattered around
        korean_tests = []
        korean_tests.extend(self.root.glob("tests/unit/korean/*.py"))
        korean_tests.extend(self.root.glob("tests/integration/test_korean*.py"))
        korean_tests.extend(self.root.glob("tests/unit/test_*korea*.py"))

        if korean_tests:
            target = Path("tests/regional/e4_korea")
            print(f"\n  Korean tests to move to {target}:")
            for test in korean_tests:
                print(f"    • {test.relative_to(self.root)}")
                self.actions.append(("move", test, target / test.name))

        # Find other misplaced tests
        scattered_tests = {
            "tests/unit/test_*region*.py": "tests/regional/",
            "tests/unit/test_*authority*.py": "tests/authority/",
            "tests/integration/test_v7*.py": "tests/v7/",
        }

        for pattern, target_dir in scattered_tests.items():
            matches = list(self.root.glob(pattern))
            if matches:
                print(f"\n  Move {len(matches)} files matching {pattern} to {target_dir}")
                for match in matches[:3]:  # Show first 3
                    print(f"    • {match.name}")
                if len(matches) > 3:
                    print(f"    ... and {len(matches) - 3} more")

    def analyze_documentation_cleanup(self):
        """Analyze documentation for cleanup"""
        print("\n📚 DOCUMENTATION CLEANUP PLAN:")

        # Count docs in each category
        doc_categories = {
            "Archive": list(self.root.glob("docs/archive/**/*.md")),
            "Exports": list(self.root.glob("data/exports/*.md")),
            "Reports": list(self.root.glob("docs/reports/*.md")),
            "Audits": list(self.root.glob("docs/audits/**/*.md")),
            "Handover": list(self.root.glob("docs/handover/*.md")),
            "Root level": list(self.root.glob("*.md")),
        }

        for category, files in doc_categories.items():
            if files:
                print(f"\n  {category}: {len(files)} files")
                # Check for old/outdated files
                old_keywords = ["2025-07", "2025-08", "BACKUP", "OLD", "ARCHIVE", "HANDOFF"]
                old_files = [f for f in files if any(k in str(f).upper() for k in old_keywords)]
                if old_files:
                    print(f"    • {len(old_files)} appear outdated (contain date/backup keywords)")
                    for old_file in old_files[:3]:
                        print(f"      - {old_file.name}")
                    if len(old_files) > 3:
                        print(f"      ... and {len(old_files) - 3} more")

    def analyze_config_reorganization(self):
        """Analyze config file organization"""
        print("\n⚙️ CONFIGURATION REORGANIZATION PLAN:")

        config_files = list(Path("config").glob("*.yaml"))

        # Categorize configs
        categories = {"deployment": [], "testing": [], "stages": [], "core": []}

        for config in config_files:
            name = config.name.lower()
            if "push" in name or "deploy" in name:
                categories["deployment"].append(config)
            elif "extreme" in name or "test" in name:
                categories["testing"].append(config)
            elif "stage" in name:
                categories["stages"].append(config)
            else:
                categories["core"].append(config)

        for category, files in categories.items():
            if files and category != "core":
                print(f"\n  Move to config/{category}/:")
                for file in files:
                    print(f"    • {file.name}")
                    self.actions.append(("move", file, Path("config") / category / file.name))

    def find_truly_unused_files(self):
        """Find files that are truly unused"""
        print("\n🔍 FINDING TRULY UNUSED FILES:")

        # Files that are likely unused
        patterns_to_check = [
            "**/test_*.json",  # Old test output
            "**/*_backup*",  # Backup files
            "**/*.bak",  # Backup files
            "**/*_old.*",  # Old versions
            "**/archive/**/*",  # Archived files
        ]

        unused = []
        for pattern in patterns_to_check:
            for file in self.root.glob(pattern):
                if ".venv" not in str(file) and ".git" not in str(file):
                    unused.append(file)

        if unused:
            print(f"  Found {len(unused)} potentially unused files")
            print("  Examples:")
            for file in unused[:5]:
                print(f"    • {file.relative_to(self.root)}")
            if len(unused) > 5:
                print(f"    ... and {len(unused) - 5} more")

    def check_empty_directories(self):
        """Find empty or nearly empty directories"""
        print("\n📁 EMPTY/SPARSE DIRECTORIES:")

        empty_dirs = []
        sparse_dirs = []

        for root, dirs, files in os.walk("."):
            if ".venv" not in root and ".git" not in root:
                path = Path(root)
                # Count non-init files
                real_files = [f for f in files if f != "__init__.py" and not f.startswith(".")]

                if not dirs and not real_files:
                    empty_dirs.append(path)
                elif not dirs and len(real_files) <= 1:
                    sparse_dirs.append(path)

        if empty_dirs:
            print(f"\n  Empty directories: {len(empty_dirs)}")
            for dir_path in empty_dirs[:5]:
                print(f"    • {dir_path.relative_to(self.root)}")
                self.actions.append(("remove_empty", dir_path))

        if sparse_dirs:
            print(f"\n  Sparse directories (≤1 file): {len(sparse_dirs)}")
            for dir_path in sparse_dirs[:5]:
                print(f"    • {dir_path.relative_to(self.root)}")

    def generate_action_summary(self):
        """Generate summary of all actions to take"""
        print("\n" + "=" * 80)
        print("ACTION SUMMARY")
        print("=" * 80)

        action_types = {}
        for action in self.actions:
            action_type = action[0]
            if action_type not in action_types:
                action_types[action_type] = []
            action_types[action_type].append(action)

        for action_type, actions in action_types.items():
            print(f"\n{action_type.upper()}: {len(actions)} actions")
            for action in actions[:3]:
                if action_type == "move":
                    print(f"  • Move {action[1].name} to {action[2]}")
                elif action_type == "consolidate_duplicate":
                    print(f"  • Consolidate {action[1]} to {action[3]}")
                elif action_type == "remove_empty":
                    print(f"  • Remove empty dir: {action[1]}")
            if len(actions) > 3:
                print(f"  ... and {len(actions) - 3} more")

    def execute_reorganization(self, dry_run=True):
        """Execute the reorganization"""
        if dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made")
            print("Run with execute_reorganization(dry_run=False) to apply changes")
        else:
            print("\n🚀 EXECUTING REORGANIZATION...")

            for action in self.actions:
                action_type = action[0]

                try:
                    if action_type == "move":
                        _, source, target = action
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(source), str(target))
                        print(f"  ✓ Moved {source.name} to {target}")

                    elif action_type == "consolidate_duplicate":
                        _, name, source, target_dir = action
                        target_dir.mkdir(parents=True, exist_ok=True)
                        target = target_dir / name
                        if not target.exists():
                            shutil.copy2(str(source), str(target))
                            print(f"  ✓ Consolidated {name} to {target_dir}")

                    elif action_type == "remove_empty":
                        _, path = action
                        if path.exists() and not any(path.iterdir()):
                            path.rmdir()
                            print(f"  ✓ Removed empty dir: {path}")

                except Exception as e:
                    print(f"  ✗ Failed {action_type}: {e}")

            print("\n✅ Reorganization complete!")

    def run(self):
        """Run complete reorganization analysis"""
        print("=" * 80)
        print("ULTRATHINK DEEP REORGANIZATION ANALYSIS")
        print("=" * 80)

        self.analyze_korean_consolidation()
        self.analyze_test_consolidation()
        self.analyze_documentation_cleanup()
        self.analyze_config_reorganization()
        self.find_truly_unused_files()
        self.check_empty_directories()
        self.generate_action_summary()

        return self


if __name__ == "__main__":
    reorganizer = DeepReorganizer()
    reorganizer.run()

    # Uncomment to execute
    # response = input("\n⚠️  Execute reorganization? (yes/no): ")
    # if response.lower() == 'yes':
    #     reorganizer.execute_reorganization(dry_run=False)
