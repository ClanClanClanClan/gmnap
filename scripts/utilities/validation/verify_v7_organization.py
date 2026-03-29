#!/usr/bin/env python3
"""
V7.0 Project Organization Verification Script

Verifies that the GMNAP project structure complies with v7.0 specifications
and that all files are properly organized.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple


class V7OrganizationVerifier:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: Dict[str, List[str]] = {"compliance": [], "issues": [], "suggestions": []}

    def verify_pipeline_structure(self) -> bool:
        """Verify v7.0 pipeline stages directory structure"""
        expected_stages = [
            "00_config",
            "01_ingest",
            "01b_llm_extract_etd",
            "02_detect_region",
            "03_region_hooks",
            "04_authority_enrich",
            "05_collision_analytics",
            "06_graph_consistency",
            "07_tag_short_forms",
            "08_global_validate",
            "09_write_diff",
            "10_report",
            "11_idempotency_check",
        ]

        pipeline_dir = self.project_root / "src" / "pipeline" / "stages"
        all_stages_exist = True

        for stage in expected_stages:
            stage_path = pipeline_dir / stage
            if stage_path.exists():
                self.results["compliance"].append(f"✅ Pipeline stage {stage} exists")
            else:
                self.results["issues"].append(f"❌ Pipeline stage {stage} missing")
                all_stages_exist = False

        return all_stages_exist

    def verify_scripts_organization(self) -> bool:
        """Verify scripts are properly organized"""
        expected_script_dirs = [
            "scripts/analysis",
            "scripts/fixes",
            "scripts/korean",
            "scripts/testing",
            "scripts/utilities",
            "scripts/v7_migration",
        ]

        all_dirs_exist = True
        for dir_path in expected_script_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                file_count = len(list(full_path.glob("*.py")))
                self.results["compliance"].append(
                    f"✅ {dir_path} exists with {file_count} Python files"
                )
            else:
                self.results["issues"].append(f"❌ {dir_path} missing")
                all_dirs_exist = False

        return all_dirs_exist

    def verify_archive_structure(self) -> bool:
        """Verify archive directories are properly structured"""
        expected_archive_dirs = [
            "archive/audit_reports",
            "archive/comprehensive_reports",
            "archive/v7_compliance_reports",
            "archive/phase_reports",
            "archive/legacy_docs",
            "archive/test_results",
        ]

        all_dirs_exist = True
        for dir_path in expected_archive_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                file_count = len(list(full_path.glob("*")))
                self.results["compliance"].append(f"✅ {dir_path} exists with {file_count} files")
            else:
                self.results["issues"].append(f"❌ {dir_path} missing")
                all_dirs_exist = False

        return all_dirs_exist

    def check_root_cleanliness(self) -> bool:
        """Check that root directory is clean of scattered files"""
        expected_root_files = {
            "CLAUDE.md",
            "README.md",
            "requirements.txt",
            "Dockerfile",
            "docker-compose.yml",
            "Makefile",
            "pytest.ini",
            "init_memgraph.cypher",
        }

        root_files = set()
        for item in self.project_root.iterdir():
            if item.is_file() and not item.name.startswith("."):
                root_files.add(item.name)

        unexpected_files = root_files - expected_root_files
        if not unexpected_files:
            self.results["compliance"].append("✅ Root directory is clean")
            return True
        else:
            for file in unexpected_files:
                if not file.endswith((".tar.gz", ".bak")):  # Allow backup files
                    self.results["issues"].append(f"❌ Unexpected file in root: {file}")
            return len([f for f in unexpected_files if not f.endswith((".tar.gz", ".bak"))]) == 0

    def verify_data_organization(self) -> bool:
        """Verify data directory organization"""
        expected_data_dirs = [
            "data/korean",
            "data/fixtures",
            "data/baselines",
            "data/test_datasets",
            "data/mappings",
        ]

        all_dirs_exist = True
        for dir_path in expected_data_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                self.results["compliance"].append(f"✅ {dir_path} exists")
            else:
                self.results["suggestions"].append(f"⚠️  Consider creating {dir_path}")

        return all_dirs_exist

    def verify_config_structure(self) -> bool:
        """Verify configuration directory structure"""
        config_dir = self.project_root / "config"
        if not config_dir.exists():
            self.results["issues"].append("❌ Config directory missing")
            return False

        expected_config_items = ["regional", "diaspora", "weights"]
        for item in expected_config_items:
            item_path = config_dir / item
            if item_path.exists():
                self.results["compliance"].append(f"✅ Config {item} exists")
            else:
                self.results["suggestions"].append(f"⚠️  Consider creating config/{item}")

        return True

    def run_full_verification(self) -> Tuple[bool, Dict[str, List[str]]]:
        """Run complete v7.0 organization verification"""
        print("🔍 Running v7.0 Project Organization Verification...")
        print(f"📁 Project Root: {self.project_root}")
        print()

        checks = [
            ("Pipeline Structure", self.verify_pipeline_structure),
            ("Scripts Organization", self.verify_scripts_organization),
            ("Archive Structure", self.verify_archive_structure),
            ("Root Cleanliness", self.check_root_cleanliness),
            ("Data Organization", self.verify_data_organization),
            ("Config Structure", self.verify_config_structure),
        ]

        all_passed = True
        for check_name, check_func in checks:
            print(f"🔧 Checking {check_name}...")
            passed = check_func()
            if not passed:
                all_passed = False
            print()

        return all_passed, self.results

    def print_results(self):
        """Print verification results"""
        print("=" * 60)
        print("📊 V7.0 ORGANIZATION VERIFICATION RESULTS")
        print("=" * 60)

        if self.results["compliance"]:
            print("\n✅ COMPLIANCE ACHIEVEMENTS:")
            for item in self.results["compliance"]:
                print(f"   {item}")

        if self.results["issues"]:
            print("\n❌ ISSUES FOUND:")
            for item in self.results["issues"]:
                print(f"   {item}")

        if self.results["suggestions"]:
            print("\n⚠️  SUGGESTIONS:")
            for item in self.results["suggestions"]:
                print(f"   {item}")

        print("\n" + "=" * 60)

        compliance_count = len(self.results["compliance"])
        issue_count = len(self.results["issues"])

        if issue_count == 0:
            print("🎉 V7.0 ORGANIZATION FULLY COMPLIANT!")
        elif compliance_count > issue_count * 2:
            print("✅ V7.0 ORGANIZATION MOSTLY COMPLIANT")
        else:
            print("⚠️  V7.0 ORGANIZATION NEEDS IMPROVEMENT")

        print(f"📊 Summary: {compliance_count} compliant, {issue_count} issues")
        print("=" * 60)


def main():
    """Main verification function"""
    project_root = Path(__file__).parent.parent.parent
    verifier = V7OrganizationVerifier(project_root)

    success, results = verifier.run_full_verification()
    verifier.print_results()

    return 0 if success else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
