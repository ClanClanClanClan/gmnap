#!/usr/bin/env python3
"""
GMNAP Project Organization Script

Organizes the project structure according to specs v6 requirements.
Cleans up scattered files, optimizes directory structure, and ensures compliance.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict
import json
import subprocess


class ProjectOrganizer:
    def __init__(self, root_dir: Path = None):
        self.root = root_dir or Path.cwd()
        self.changes_made = []

    def log_change(self, change: str):
        """Log a change made during organization."""
        self.changes_made.append(change)
        print(f"✅ {change}")

    def organize_scattered_files(self):
        """Organize scattered files in root directory."""
        print("🗂️ Organizing scattered files...")

        # Create organization directories
        org_dirs = [
            "analysis",
            "debug_tools",
            "test_results",
            "reports",
            "archive",
            "tools/cli",
        ]

        for dir_path in org_dirs:
            full_path = self.root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

        # Move files by pattern
        file_moves = {
            "realistic_test_results_*.json": "test_results/",
            "*audit*.py": "analysis/",
            "*audit*.md": "analysis/",
            "debug_*.py": "debug_tools/",
            "test_*.py": "test_results/",
            "profile_*.py": "debug_tools/",
            "IMPLEMENTATION_*.md": "reports/",
            "FINAL_*.md": "reports/",
        }

        for pattern, target_dir in file_moves.items():
            target_path = self.root / target_dir
            target_path.mkdir(parents=True, exist_ok=True)

            for file_path in self.root.glob(pattern):
                if file_path.is_file():
                    try:
                        shutil.move(str(file_path), str(target_path / file_path.name))
                        self.log_change(f"Moved {file_path.name} to {target_dir}")
                    except Exception as e:
                        print(f"⚠️ Failed to move {file_path.name}: {e}")

    def complete_directory_structure(self):
        """Complete missing directory structure per specs."""
        print("📁 Completing directory structure...")

        required_dirs = [
            # Core source directories
            "src/authorities/tier2",
            "src/regions/f_groups",
            "src/regions/h_groups",
            "src/regions/special",
            # Testing directories per specs section 8
            "tests/property",
            "tests/fixtures",
            "tests/sea_roundtrip",
            "tests/concurrency",
            "tests/memory_peak",
            "tests/msc_provenance",
            "tests/fake_api",
            "tests/stress",
            "tests/integration",
            "tests/secret_scan",
            # Developer tooling
            "tools/cli",
            "tools/dictionaries",
            "tools/dev_container",
            # Documentation organization
            "docs/api",
            "docs/tutorials",
            "docs/examples",
            # Config and data
            "config/weights",
            "config/diaspora",
            # Analysis and reports
            "analysis/reports",
            "analysis/metrics",
            # Archive for old files
            "archive/old_tests",
            "archive/deprecated",
        ]

        for dir_path in required_dirs:
            full_path = self.root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                self.log_change(f"Created directory: {dir_path}")

                # Create __init__.py for Python packages
                if "src/" in dir_path or "tests/" in dir_path:
                    init_file = full_path / "__init__.py"
                    if not init_file.exists():
                        init_file.write_text('"""Package initialization."""\n')

    def create_missing_config_files(self):
        """Create missing configuration files per specs."""
        print("⚙️ Creating missing configuration files...")

        # Create diaspora.yaml template
        diaspora_file = self.root / "config" / "diaspora.yaml"
        if not diaspora_file.exists():
            diaspora_content = """# Diaspora overlay configuration
# Maps country codes to region changes based on date ranges
# Format: country -> [{region: code, range: "start-end"}]

# Example: Thailand mathematicians
"TH":
  - {region: "E6", range: "-2015"}
  - {region: "A1", range: "2016-"}

# Add more diaspora mappings as needed
"""
            diaspora_file.write_text(diaspora_content)
            self.log_change("Created config/diaspora.yaml template")

        # Create weights.yaml template
        weights_file = self.root / "config" / "weights.yaml"
        if not weights_file.exists():
            weights_content = """# Confidence score weights (must sum to 1.0)
# Used for calculating overall entry confidence

id_score: 0.35          # Authority ID matches
script_certainty: 0.25  # Script detection confidence
msc_match: 0.20         # MSC code alignment
region_confidence: 0.15 # Regional processing confidence
name_consistency: 0.05  # Name variant consistency
"""
            weights_file.write_text(weights_content)
            self.log_change("Created config/weights.yaml template")

    def create_makefile_targets(self):
        """Create comprehensive Makefile per specs."""
        print("🔨 Creating Makefile targets...")

        makefile_content = """# GMNAP Makefile - Specs v6 Compliance

.PHONY: help quick full extreme test lint update-sources clean audit

help:
	@echo "GMNAP - Global Mathematician-Name Authority Project"
	@echo ""
	@echo "Available targets:"
	@echo "  quick        - Run pipeline in Quick mode (tier-0 APIs only)"
	@echo "  full         - Run pipeline in Full mode (tier-0 + tier-1)"
	@echo "  extreme      - Run pipeline in Extreme mode (all tiers)"
	@echo "  test         - Run test suite"
	@echo "  lint         - Run code linting"
	@echo "  audit        - Run comprehensive audit"
	@echo "  update-sources - Update authority source configurations"
	@echo "  clean        - Clean cache and temporary files"

# Pipeline execution modes
quick:
	python3 -m src.core.pipeline_v6 --mode quick

full:
	python3 -m src.core.pipeline_v6 --mode full

extreme:
	python3 -m src.core.pipeline_v6 --mode extreme --force-extreme

# Testing
test:
	pytest tests/ -v

test-hardcore:
	pytest tests/hardcore/ -v

test-integration:
	pytest tests/integration/ -v

# Code quality
lint:
	black src/ tests/
	ruff check src/ tests/
	isort src/ tests/
	yamllint docs/ config/

# Analysis
audit:
	python3 analysis/comprehensive_audit.py

audit-quick:
	python3 analysis/comprehensive_audit.py --quick-test

# Maintenance
update-sources:
	python3 scripts/update_source_manifest.py

clean:
	rm -rf cache/output/*
	rm -rf cache/bad_json/*
	rm -rf test_results/realistic_test_results_*.json
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

# Development setup
setup-dev:
	pip install -r requirements.txt
	python3 scripts/setup_dev.sh

# Stats and reporting
stats:
	python3 scripts/generate_stats.py

report:
	python3 scripts/generate_test_report.py
"""

        makefile_path = self.root / "Makefile"
        if makefile_path.exists():
            # Backup existing Makefile
            shutil.copy(str(makefile_path), str(makefile_path.with_suffix(".bak")))

        makefile_path.write_text(makefile_content)
        self.log_change("Created comprehensive Makefile")

    def create_development_tools(self):
        """Create missing development tools."""
        print("🛠️ Creating development tools...")

        # Create setup script
        setup_script = self.root / "scripts" / "setup_dev.sh"
        setup_content = """#!/bin/bash
# GMNAP Development Environment Setup

echo "Setting up GMNAP development environment..."

# Install Python dependencies
pip install -r requirements.txt

# Download FastText model if missing
if [ ! -f "cache/config/lid.176.bin" ]; then
    echo "Downloading FastText language detection model..."
    mkdir -p cache/config
    wget -O cache/config/lid.176.bin.gz https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
    gunzip cache/config/lid.176.bin.gz
fi

# Set up pre-commit hooks
pip install pre-commit
pre-commit install

# Create necessary directories
mkdir -p cache/output cache/bad_json logs data

echo "✅ Development environment setup complete!"
"""
        setup_script.write_text(setup_content)
        setup_script.chmod(0o755)
        self.log_change("Created scripts/setup_dev.sh")

        # Create stats generator
        stats_script = self.root / "scripts" / "generate_stats.py"
        stats_content = '''#!/usr/bin/env python3
"""Generate project statistics and compliance metrics."""

import json
from pathlib import Path
from collections import defaultdict

def generate_stats():
    """Generate comprehensive project statistics."""
    stats = {
        "regions": {"implemented": 0, "total": 43},
        "authorities": {"implemented": 0, "total": 25},
        "linguistic_rules": {"implemented": 0, "total": 34},
        "tests": {"count": 0, "passed": 0},
        "code_quality": {"lines": 0, "files": 0}
    }
    
    # Count implemented regions
    regions_dir = Path("src/regions")
    for group_dir in regions_dir.glob("*_groups"):
        if group_dir.is_dir():
            for region_file in group_dir.glob("*.py"):
                if region_file.name != "__init__.py":
                    stats["regions"]["implemented"] += 1
    
    # Count authority sources
    auth_dir = Path("src/authorities")
    for tier_dir in auth_dir.glob("tier*"):
        if tier_dir.is_dir():
            for auth_file in tier_dir.glob("*.py"):
                if auth_file.name != "__init__.py":
                    stats["authorities"]["implemented"] += 1
    
    # Calculate compliance percentages
    stats["compliance"] = {
        "regions": round(stats["regions"]["implemented"] / stats["regions"]["total"] * 100, 1),
        "authorities": round(stats["authorities"]["implemented"] / stats["authorities"]["total"] * 100, 1),
        "linguistic_rules": round(stats["linguistic_rules"]["implemented"] / stats["linguistic_rules"]["total"] * 100, 1)
    }
    
    print("📊 GMNAP Project Statistics")
    print("=" * 50)
    print(f"Regions: {stats['regions']['implemented']}/{stats['regions']['total']} ({stats['compliance']['regions']}%)")
    print(f"Authority Sources: {stats['authorities']['implemented']}/{stats['authorities']['total']} ({stats['compliance']['authorities']}%)")
    print(f"Linguistic Rules: {stats['linguistic_rules']['implemented']}/{stats['linguistic_rules']['total']} ({stats['compliance']['linguistic_rules']}%)")
    
    # Save stats to file
    stats_file = Path("analysis/project_stats.json")
    stats_file.parent.mkdir(exist_ok=True)
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\\n💾 Stats saved to {stats_file}")

if __name__ == "__main__":
    generate_stats()
'''
        stats_script.write_text(stats_content)
        stats_script.chmod(0o755)
        self.log_change("Created scripts/generate_stats.py")

    def optimize_imports(self):
        """Optimize Python imports throughout the codebase."""
        print("🐍 Optimizing Python imports...")

        try:
            # Run isort on source code
            subprocess.run(
                ["isort", "src/", "tests/"], check=False, capture_output=True
            )
            self.log_change("Optimized imports with isort")
        except FileNotFoundError:
            print("⚠️ isort not found, skipping import optimization")

    def generate_summary_report(self):
        """Generate summary of all changes made."""
        print("\\n📋 Organization Summary")
        print("=" * 50)

        if self.changes_made:
            for change in self.changes_made:
                print(f"✅ {change}")
        else:
            print("No changes needed - project already organized!")

        print(f"\\n🎯 Total changes made: {len(self.changes_made)}")

        # Save summary to file
        summary_file = self.root / "analysis" / "organization_summary.md"
        with open(summary_file, "w") as f:
            f.write("# Project Organization Summary\\n\\n")
            f.write(f"Date: {__import__('datetime').datetime.now().isoformat()}\\n\\n")
            f.write("## Changes Made\\n\\n")
            for change in self.changes_made:
                f.write(f"- {change}\\n")

        print(f"\\n💾 Summary saved to {summary_file}")

    def run_full_organization(self):
        """Run complete project organization."""
        print("🚀 Starting GMNAP Project Organization")
        print("=" * 50)

        self.organize_scattered_files()
        self.complete_directory_structure()
        self.create_missing_config_files()
        self.create_makefile_targets()
        self.create_development_tools()
        self.optimize_imports()
        self.generate_summary_report()

        print("\\n🎉 Project organization complete!")


if __name__ == "__main__":
    organizer = ProjectOrganizer()
    organizer.run_full_organization()
