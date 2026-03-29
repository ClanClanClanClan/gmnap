#!/usr/bin/env python3
"""
Project Cleanup Script - GMNAP v7
Organizes files and cleans up the project structure
"""

import os
import shutil
from pathlib import Path
import json
from datetime import datetime


class ProjectCleaner:
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.root = Path(".")
        self.moves = []
        self.deletes = []
        self.creates = []

    def log(self, action, message):
        prefix = "[DRY RUN]" if self.dry_run else "[EXECUTE]"
        print(f"{prefix} {action}: {message}")

    def ensure_dir(self, path):
        """Create directory if it doesn't exist"""
        path = Path(path)
        if not path.exists():
            self.creates.append(str(path))
            if not self.dry_run:
                path.mkdir(parents=True, exist_ok=True)
            self.log("CREATE", f"Directory: {path}")

    def move_file(self, src, dst):
        """Move file from src to dst"""
        src, dst = Path(src), Path(dst)
        if src.exists():
            self.moves.append((str(src), str(dst)))
            if not self.dry_run:
                self.ensure_dir(dst.parent)
                shutil.move(str(src), str(dst))
            self.log("MOVE", f"{src} -> {dst}")
        else:
            self.log("SKIP", f"File not found: {src}")

    def delete_file(self, path):
        """Delete file or directory"""
        path = Path(path)
        if path.exists():
            self.deletes.append(str(path))
            if not self.dry_run:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            self.log("DELETE", str(path))

    def cleanup_root_documentation(self):
        """Move documentation files from root to docs/"""
        print("\n=== Cleaning Root Documentation ===")

        # Create target directories
        self.ensure_dir("docs/v7_compliance")
        self.ensure_dir("docs/audits")
        self.ensure_dir("docs/reports")

        # Move V7 documentation
        for file in self.root.glob("V7_*.md"):
            self.move_file(file, f"docs/v7_compliance/{file.name}")

        # Move audit reports
        for file in self.root.glob("*AUDIT*.md"):
            self.move_file(file, f"docs/audits/{file.name}")

        # Move other reports
        for file in self.root.glob("ULTRA*.md"):
            self.move_file(file, f"docs/reports/{file.name}")

        for file in self.root.glob("*COMPLIANCE*.md"):
            if file.exists():  # Check if not already moved
                self.move_file(file, f"docs/reports/{file.name}")

    def cleanup_root_scripts(self):
        """Move Python scripts from root to appropriate directories"""
        print("\n=== Cleaning Root Scripts ===")

        # Create target directories
        self.ensure_dir("tests/scripts")
        self.ensure_dir("debug_tools")
        self.ensure_dir("tools")
        self.ensure_dir("scripts/fixes")
        self.ensure_dir("scripts")

        # Move test scripts
        for file in self.root.glob("test_*.py"):
            if file.name != "test_v7_integration.py":  # Keep main test
                self.move_file(file, f"tests/scripts/{file.name}")

        # Move debug scripts
        for file in self.root.glob("debug_*.py"):
            self.move_file(file, f"debug_tools/{file.name}")

        # Move check scripts
        for file in self.root.glob("check_*.py"):
            self.move_file(file, f"tools/{file.name}")

        # Move fix scripts
        for file in self.root.glob("fix_*.py"):
            self.move_file(file, f"scripts/fixes/{file.name}")

        # Move quick scripts
        for file in self.root.glob("quick_*.py"):
            self.move_file(file, f"scripts/{file.name}")

    def cleanup_root_data(self):
        """Move data files from root to data/"""
        print("\n=== Cleaning Root Data Files ===")

        # Create target directory
        self.ensure_dir("data/results")
        self.ensure_dir("data/mappings")

        # Move test result files
        for file in self.root.glob("*test_results*.json"):
            self.move_file(file, f"data/results/{file.name}")

        # Move other JSON files
        for file in [
            "baseline_scan.json",
            "missing_v4_components.json",
            "validation_test_results.json",
            "korean_given_name_mappings.json",
        ]:
            if Path(file).exists():
                if "mapping" in file:
                    self.move_file(file, f"data/mappings/{file}")
                else:
                    self.move_file(file, f"data/results/{file}")

    def consolidate_cache_directories(self):
        """Merge all cache_thread_* directories into cache/threads/"""
        print("\n=== Consolidating Cache Directories ===")

        self.ensure_dir("cache/threads")

        # Move cache_thread_* contents
        for i in range(5):
            cache_dir = Path(f"cache_thread_{i}")
            if cache_dir.exists():
                for item in cache_dir.iterdir():
                    dst = Path(f"cache/threads/thread_{i}") / item.name
                    self.move_file(item, dst)
                self.delete_file(cache_dir)

        # Move cache_security_test
        if Path("cache_security_test").exists():
            for item in Path("cache_security_test").iterdir():
                dst = Path("cache/security") / item.name
                self.move_file(item, dst)
            self.delete_file("cache_security_test")

    def remove_backup_files(self):
        """Remove backup and old files"""
        print("\n=== Removing Backup Files ===")

        patterns = ["*.bak", "*_backup*", "*_old*", "*~"]

        for pattern in patterns:
            for file in Path(".").rglob(pattern):
                # Skip archive directory
                if "archive" not in str(file):
                    self.delete_file(file)

    def archive_old_docs(self):
        """Archive old documentation"""
        print("\n=== Archiving Old Documentation ===")

        archive_dir = Path("docs/archive")
        if archive_dir.exists() and len(list(archive_dir.iterdir())) > 100:
            # Create timestamped archive
            timestamp = datetime.now().strftime("%Y%m%d")
            archive_name = f"docs/archive_{timestamp}.tar.gz"

            if not self.dry_run:
                import tarfile

                with tarfile.open(archive_name, "w:gz") as tar:
                    tar.add(archive_dir, arcname="archive")

            self.log("ARCHIVE", f"Created {archive_name}")

            # Move to historical
            self.ensure_dir("docs/historical")
            self.move_file(archive_name, f"docs/historical/{archive_name}")

    def generate_report(self):
        """Generate cleanup report"""
        print("\n=== Cleanup Report ===")
        print(f"Directories created: {len(self.creates)}")
        print(f"Files moved: {len(self.moves)}")
        print(f"Files deleted: {len(self.deletes)}")

        if self.dry_run:
            print("\nThis was a DRY RUN. No files were actually moved or deleted.")
            print("Run with --execute to perform the cleanup.")

        # Save report
        report = {
            "timestamp": datetime.now().isoformat(),
            "dry_run": self.dry_run,
            "creates": self.creates,
            "moves": [(s, d) for s, d in self.moves],
            "deletes": self.deletes,
        }

        report_file = f"cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {report_file}")

    def run(self):
        """Run all cleanup tasks"""
        print("=" * 60)
        print("GMNAP PROJECT CLEANUP")
        print("Mode: " + ("DRY RUN" if self.dry_run else "EXECUTE"))
        print("=" * 60)

        self.cleanup_root_documentation()
        self.cleanup_root_scripts()
        self.cleanup_root_data()
        self.consolidate_cache_directories()
        self.remove_backup_files()
        self.archive_old_docs()
        self.generate_report()

        print("\n" + "=" * 60)
        print("CLEANUP COMPLETE")
        print("=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Clean up GMNAP project structure")
    parser.add_argument(
        "--execute", action="store_true", help="Actually perform cleanup (default is dry run)"
    )
    args = parser.parse_args()

    cleaner = ProjectCleaner(dry_run=not args.execute)
    cleaner.run()


if __name__ == "__main__":
    main()
