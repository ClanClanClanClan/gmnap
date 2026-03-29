#!/usr/bin/env python3
"""
ULTRATHINK Documentation Audit System
Comprehensively audits ALL documentation for relevance, accuracy, and redundancy
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import re


class UltrathinkDocsAuditor:
    def __init__(self):
        self.docs_dir = Path("docs")
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "total_files": 0,
            "total_size_bytes": 0,
            "categories": defaultdict(list),
            "duplicates": [],
            "obsolete": [],
            "current": [],
            "suspicious": [],
            "empty": [],
            "by_folder": defaultdict(dict),
        }
        self.hash_map = defaultdict(list)

    def audit_all(self):
        """Perform comprehensive audit of ALL documentation"""
        print("=" * 80)
        print("ULTRATHINK DOCUMENTATION AUDIT")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}\n")

        # Step 1: Collect all files
        all_files = list(self.docs_dir.rglob("*"))
        doc_files = [f for f in all_files if f.is_file()]

        print(f"📂 Found {len(doc_files)} documentation files")
        print(f"📂 Found {len([f for f in all_files if f.is_dir()])} directories\n")

        # Step 2: Analyze each file
        for filepath in doc_files:
            self.analyze_file(filepath)

        # Step 3: Detect duplicates
        self.find_duplicates()

        # Step 4: Categorize by relevance
        self.categorize_documents()

        # Step 5: Generate report
        self.generate_report()

        # Step 6: Save detailed results
        self.save_results()

    def analyze_file(self, filepath):
        """Analyze a single documentation file"""
        rel_path = filepath.relative_to(self.docs_dir)
        folder = str(rel_path.parent)

        try:
            stat = filepath.stat()
            size = stat.st_size

            self.results["total_files"] += 1
            self.results["total_size_bytes"] += size

            # Check if empty
            if size == 0:
                self.results["empty"].append(str(rel_path))
                return

            # Calculate hash for duplicate detection
            if size < 1024 * 1024:  # Only hash files < 1MB
                with open(filepath, "rb") as f:
                    content = f.read()
                    file_hash = hashlib.sha256(content).hexdigest()
                    self.hash_map[file_hash].append(str(rel_path))

            # Read first few lines to check content
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    first_lines = f.read(500).lower()

                # Check for obsolete markers
                obsolete_markers = [
                    "deprecated",
                    "obsolete",
                    "old",
                    "backup",
                    "archive",
                    "do not use",
                    "outdated",
                    "legacy",
                    "superseded",
                    "2024",
                    "2023",
                    "temporary",
                    "temp",
                    "test",
                ]

                for marker in obsolete_markers:
                    if marker in first_lines or marker in str(rel_path).lower():
                        self.results["obsolete"].append(str(rel_path))
                        break

                # Check for current/relevant markers
                current_markers = [
                    "2025-09",
                    "v7",
                    "production",
                    "current",
                    "latest",
                    "final",
                    "spec",
                    "guide",
                    "api",
                    "readme",
                ]

                for marker in current_markers:
                    if marker in first_lines or marker in str(rel_path).lower():
                        self.results["current"].append(str(rel_path))
                        break

            except:
                self.results["suspicious"].append(str(rel_path))

            # Track by folder
            if folder not in self.results["by_folder"]:
                self.results["by_folder"][folder] = {"count": 0, "size": 0, "files": []}

            self.results["by_folder"][folder]["count"] += 1
            self.results["by_folder"][folder]["size"] += size
            self.results["by_folder"][folder]["files"].append(
                {"name": filepath.name, "size": size}
            )

        except Exception as e:
            print(f"Error analyzing {filepath}: {e}")

    def find_duplicates(self):
        """Find duplicate files by content hash"""
        for file_hash, files in self.hash_map.items():
            if len(files) > 1:
                self.results["duplicates"].append(
                    {"hash": file_hash[:8], "files": files}
                )

    def categorize_documents(self):
        """Categorize documents by type and relevance"""
        categories = {
            "Archive": r"archive|old|backup|2024|2023",
            "Korean": r"korean|korea|e4|hangul|romaniz",
            "V7 Compliance": r"v7|compliance|spec",
            "Testing": r"test|audit|report|results",
            "Technical": r"architecture|design|api|schema",
            "Guides": r"guide|readme|howto|tutorial",
            "Handover": r"handover|handoff|transition",
            "Implementation": r"implement|plan|roadmap",
            "Expert": r"expert|fix|patch|solution",
            "Historical": r"historical|legacy|old",
        }

        for filepath in self.docs_dir.rglob("*"):
            if not filepath.is_file():
                continue

            rel_path = str(filepath.relative_to(self.docs_dir)).lower()

            for category, pattern in categories.items():
                if re.search(pattern, rel_path):
                    self.results["categories"][category].append(
                        str(filepath.relative_to(self.docs_dir))
                    )
                    break

    def generate_report(self):
        """Generate comprehensive audit report"""
        print("\n" + "=" * 80)
        print("AUDIT RESULTS")
        print("=" * 80)

        # Summary stats
        print(f"\n📊 SUMMARY:")
        print(f"  Total files: {self.results['total_files']}")
        print(f"  Total size: {self.results['total_size_bytes'] / (1024*1024):.2f} MB")
        print(f"  Empty files: {len(self.results['empty'])}")
        print(f"  Duplicates: {len(self.results['duplicates'])} sets")
        print(f"  Obsolete: {len(self.results['obsolete'])} files")
        print(f"  Current: {len(self.results['current'])} files")
        print(f"  Suspicious: {len(self.results['suspicious'])} files")

        # By folder analysis
        print(f"\n📁 BY FOLDER (sorted by size):")
        sorted_folders = sorted(
            self.results["by_folder"].items(), key=lambda x: x[1]["size"], reverse=True
        )

        for folder, info in sorted_folders[:10]:
            size_mb = info["size"] / (1024 * 1024)
            print(f"  {folder:40} {info['count']:3} files, {size_mb:6.2f} MB")

        # Categories
        print(f"\n🏷️ BY CATEGORY:")
        for category, files in self.results["categories"].items():
            print(f"  {category:20} {len(files):3} files")

        # Duplicates
        if self.results["duplicates"]:
            print(f"\n🔄 DUPLICATES FOUND:")
            for dup_set in self.results["duplicates"][:5]:
                print(f"  Hash {dup_set['hash']}:")
                for f in dup_set["files"]:
                    print(f"    - {f}")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")

        # Check archive folder
        archive_size = sum(
            info["size"]
            for folder, info in self.results["by_folder"].items()
            if "archive" in folder.lower()
        )
        if archive_size > 0:
            print(
                f"  ⚠️ Archive folder contains {archive_size/(1024*1024):.2f} MB - consider external storage"
            )

        # Check for old content
        if len(self.results["obsolete"]) > 20:
            print(
                f"  ⚠️ {len(self.results['obsolete'])} obsolete files detected - cleanup recommended"
            )

        # Check for duplicates
        if len(self.results["duplicates"]) > 5:
            print(
                f"  ⚠️ {len(self.results['duplicates'])} duplicate sets found - deduplication needed"
            )

        # Empty files
        if self.results["empty"]:
            print(
                f"  ⚠️ {len(self.results['empty'])} empty files found - should be removed"
            )

        # Korean processor specific
        korean_files = self.results["categories"].get("Korean", [])
        if korean_files:
            print(f"\n🇰🇷 KOREAN PROCESSOR DOCUMENTATION:")
            print(f"  Found {len(korean_files)} Korean-related documents")
            print(f"  Fix pack location: expert/korean_processor_fix_pack_2025-09-17/")

    def save_results(self):
        """Save detailed results to JSON"""
        output_file = f"docs_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Convert defaultdicts to regular dicts for JSON
        save_data = {
            "timestamp": self.results["timestamp"],
            "total_files": self.results["total_files"],
            "total_size_bytes": self.results["total_size_bytes"],
            "total_size_mb": self.results["total_size_bytes"] / (1024 * 1024),
            "categories": dict(self.results["categories"]),
            "duplicates": self.results["duplicates"],
            "obsolete": self.results["obsolete"],
            "current": self.results["current"],
            "suspicious": self.results["suspicious"],
            "empty": self.results["empty"],
            "by_folder": dict(self.results["by_folder"]),
        }

        with open(output_file, "w") as f:
            json.dump(save_data, f, indent=2)

        print(f"\n📄 Detailed results saved to: {output_file}")

        # Generate cleanup script
        if self.results["empty"] or self.results["duplicates"]:
            self.generate_cleanup_script()

    def generate_cleanup_script(self):
        """Generate script to clean up identified issues"""
        cleanup_file = "cleanup_docs.sh"

        with open(cleanup_file, "w") as f:
            f.write("#!/bin/bash\n")
            f.write("# ULTRATHINK Documentation Cleanup Script\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")

            if self.results["empty"]:
                f.write("# Remove empty files\n")
                for empty_file in self.results["empty"]:
                    f.write(f"rm 'docs/{empty_file}'\n")
                f.write("\n")

            if self.results["duplicates"]:
                f.write("# Handle duplicates (keeping first, removing others)\n")
                for dup_set in self.results["duplicates"]:
                    files = dup_set["files"]
                    f.write(f"# Duplicate set (hash {dup_set['hash']}):\n")
                    f.write(f"# Keeping: docs/{files[0]}\n")
                    for dup_file in files[1:]:
                        f.write(f"rm 'docs/{dup_file}'\n")
                    f.write("\n")

        os.chmod(cleanup_file, 0o755)
        print(f"🧹 Cleanup script generated: {cleanup_file}")


if __name__ == "__main__":
    auditor = UltrathinkDocsAuditor()
    auditor.audit_all()
