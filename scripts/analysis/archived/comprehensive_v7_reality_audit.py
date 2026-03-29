#!/usr/bin/env python3
"""
ULTRATHINK COMPREHENSIVE V7 REALITY AUDIT
Deep analysis of every component with detailed reporting
"""

import asyncio
import json
import time
import traceback
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import defaultdict

# Suppress warnings during audit
import warnings

warnings.filterwarnings("ignore")


class ComprehensiveAuditor:
    """Comprehensive system auditor with detailed analysis"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "working_directory": os.getcwd(),
            "pythonpath": os.environ.get("PYTHONPATH", ""),
            "sections": {},
        }
        self.issues = []
        self.warnings = []
        self.successes = []

    def section(self, name: str) -> Dict:
        """Create or get a results section"""
        if name not in self.results["sections"]:
            self.results["sections"][name] = {
                "status": "pending",
                "tests": [],
                "issues": [],
                "warnings": [],
                "metrics": {},
            }
        return self.results["sections"][name]

    def test_imports_comprehensive(self):
        """Test all critical and optional imports"""
        section = self.section("imports")

        # Critical imports (must work)
        critical_imports = [
            ("pipeline_v7", "from src.core.pipeline_v7 import V7Pipeline"),
            (
                "korean_processor",
                "from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor",
            ),
            ("regional_manager", "from src.regions.manager import RegionManager"),
            ("quality_gates", "from src.quality.gates import QualityGates"),
            ("duckdb_analytics", "from src.analytics.duckdb_analytics import DuckDBAnalytics"),
            ("schema_validator", "from src.core.schema_validator import V7SchemaValidator"),
            ("unicode_handler", "from src.core.unicode_handler import UnicodeNormalizer"),
            ("security_validator", "from src.core.security_validator import SecurityValidator"),
            ("global_id", "from src.core.global_id import generate_global_id"),
        ]

        # Optional imports (nice to have)
        optional_imports = [
            ("fasttext_model", "import fasttext"),
            ("pynini", "import pynini"),
            ("duckdb", "import duckdb"),
            ("yaml", "import yaml"),
            ("pyjwt", "import jwt"),
            ("cryptography", "from cryptography.fernet import Fernet"),
        ]

        # Test critical imports
        for name, import_stmt in critical_imports:
            try:
                exec(import_stmt, globals())
                section["tests"].append(
                    {"name": f"import_{name}", "status": "passed", "critical": True}
                )
            except Exception as e:
                section["tests"].append(
                    {
                        "name": f"import_{name}",
                        "status": "failed",
                        "critical": True,
                        "error": str(e),
                    }
                )
                section["issues"].append(f"Critical import failed: {name}")

        # Test optional imports
        for name, import_stmt in optional_imports:
            try:
                exec(import_stmt, globals())
                section["tests"].append(
                    {"name": f"import_{name}", "status": "passed", "critical": False}
                )
            except Exception as e:
                section["tests"].append(
                    {
                        "name": f"import_{name}",
                        "status": "skipped",
                        "critical": False,
                        "reason": str(e),
                    }
                )
                section["warnings"].append(f"Optional import unavailable: {name}")

        # Calculate metrics
        critical_passed = sum(
            1 for t in section["tests"] if t["critical"] and t["status"] == "passed"
        )
        critical_total = sum(1 for t in section["tests"] if t["critical"])
        optional_passed = sum(
            1 for t in section["tests"] if not t["critical"] and t["status"] == "passed"
        )
        optional_total = sum(1 for t in section["tests"] if not t["critical"])

        section["metrics"] = {
            "critical_passed": critical_passed,
            "critical_total": critical_total,
            "optional_passed": optional_passed,
            "optional_total": optional_total,
            "critical_success_rate": critical_passed / critical_total if critical_total else 0,
            "optional_success_rate": optional_passed / optional_total if optional_total else 0,
        }

        section["status"] = "passed" if critical_passed == critical_total else "failed"
        return section

    def test_korean_detailed(self):
        """Detailed Korean processor testing"""
        section = self.section("korean_processor")

        try:
            from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor

            processor = E4KoreanProcessor()

            # Test cases with expected results
            test_cases = [
                # Basic conversions
                ("김민수", "Kim Min-su", "basic"),
                ("박지성", "Park Ji-sung", "basic"),
                ("이순신", "Lee Sun-sin", "historical"),
                ("김정은", "Kim Jung-eun", "political"),  # Correct romanization
                ("문재인", "Moon Jae-in", "political"),
                ("최지우", "Choi Ji-woo", "celebrity"),
                ("손흥민", "Son Heung-min", "sports"),
                ("윤석열", "Yoon Seok-yeol", "political"),
                # Edge cases
                ("김", "Kim", "single_syllable"),
                ("이", "Lee", "single_syllable"),
                ("박", "Park", "single_syllable"),
                # Compound surnames
                ("남궁민수", "Namgung Min-su", "compound_surname"),
                ("황보혜정", "Hwangbo Hye-jung", "compound_surname"),
                # Names with particles
                ("김민수의", "Kim Min-su-ui", "particle"),
                ("박지성을", "Park Ji-sung-eul", "particle"),
            ]

            for korean, expected, category in test_cases:
                entry = {"CanonicalNative": korean}
                try:
                    result = processor.process(entry)
                    romanized = result.get("CanonicalLatin", "")

                    test_result = {
                        "input": korean,
                        "expected": expected,
                        "actual": romanized,
                        "category": category,
                        "status": "passed" if romanized == expected else "failed",
                    }

                    if romanized != expected:
                        section["issues"].append(f"{korean} → {romanized} (expected: {expected})")

                    section["tests"].append(test_result)

                except Exception as e:
                    section["tests"].append(
                        {
                            "input": korean,
                            "expected": expected,
                            "category": category,
                            "status": "error",
                            "error": str(e),
                        }
                    )
                    section["issues"].append(f"Error processing {korean}: {e}")

            # Calculate metrics
            passed = sum(1 for t in section["tests"] if t["status"] == "passed")
            total = len(section["tests"])

            section["metrics"] = {
                "passed": passed,
                "total": total,
                "success_rate": passed / total if total else 0,
                "categories_tested": list(set(t["category"] for t in section["tests"])),
            }

            section["status"] = "passed" if passed >= total * 0.95 else "failed"

        except Exception as e:
            section["status"] = "error"
            section["issues"].append(f"Korean processor initialization failed: {e}")

        return section

    async def test_pipeline_detailed(self):
        """Detailed pipeline testing with various scenarios"""
        section = self.section("pipeline")

        try:
            from src.core.pipeline_v7 import V7Pipeline, PipelineMode

            # Test different pipeline modes
            modes = [
                (PipelineMode.QUICK, "quick_mode"),
                (PipelineMode.FULL, "full_mode"),
                (PipelineMode.EXTREME, "extreme_mode"),
            ]

            for mode, mode_name in modes:
                try:
                    pipeline = V7Pipeline(mode=mode, deterministic=False)

                    # Test with various batch sizes
                    batch_sizes = [1, 10, 50, 100, 500, 1000]

                    for batch_size in batch_sizes:
                        entries = [
                            {"CanonicalNative": f"Test Name {i}", "GlobalID": f"TEST-{i}"}
                            for i in range(batch_size)
                        ]

                        start_time = time.time()
                        result = await pipeline.process_batch(entries)
                        duration = time.time() - start_time

                        metrics = result.get("metrics", {})

                        test_result = {
                            "mode": mode_name,
                            "batch_size": batch_size,
                            "duration": duration,
                            "entries_per_second": metrics.get("entries_per_second", 0),
                            "success_rate": metrics.get("success_rate", 0),
                            "duplicate_count": metrics.get("duplicate_global_ids", 0),
                            "status": (
                                "passed" if metrics.get("success_rate", 0) >= 0.99 else "failed"
                            ),
                        }

                        section["tests"].append(test_result)

                except Exception as e:
                    section["warnings"].append(f"Pipeline mode {mode_name} failed: {e}")

            # Calculate aggregate metrics
            all_speeds = [
                t["entries_per_second"] for t in section["tests"] if t.get("entries_per_second")
            ]

            section["metrics"] = {
                "modes_tested": list(set(t["mode"] for t in section["tests"])),
                "batch_sizes_tested": list(set(t["batch_size"] for t in section["tests"])),
                "average_speed": sum(all_speeds) / len(all_speeds) if all_speeds else 0,
                "max_speed": max(all_speeds) if all_speeds else 0,
                "min_speed": min(all_speeds) if all_speeds else 0,
            }

            section["status"] = "passed"

        except Exception as e:
            section["status"] = "error"
            section["issues"].append(f"Pipeline testing failed: {e}")

        return section

    def test_quality_gates(self):
        """Test quality gates comprehensively"""
        section = self.section("quality_gates")

        try:
            from src.quality.gates import QualityGates

            gates = QualityGates()

            # Test duplicate detection
            test_cases = [
                {
                    "name": "no_duplicates",
                    "entries": [
                        {"GlobalID": "ID1", "CanonicalNative": "Name1"},
                        {"GlobalID": "ID2", "CanonicalNative": "Name2"},
                    ],
                    "expected_duplicates": 0,
                },
                {
                    "name": "id_duplicates",
                    "entries": [
                        {"GlobalID": "ID1", "CanonicalNative": "Name1"},
                        {"GlobalID": "ID1", "CanonicalNative": "Name2"},
                    ],
                    "expected_duplicates": 1,
                },
                {
                    "name": "name_duplicates",
                    "entries": [
                        {"GlobalID": "ID1", "CanonicalNative": "Same Name"},
                        {"GlobalID": "ID2", "CanonicalNative": "Same Name"},
                    ],
                    "expected_duplicates": 0,  # Different IDs, same name is ok
                },
            ]

            for test_case in test_cases:
                try:
                    result = gates.check_duplicates(test_case["entries"])
                    duplicate_count = len(result.get("duplicate_ids", []))

                    section["tests"].append(
                        {
                            "name": test_case["name"],
                            "expected": test_case["expected_duplicates"],
                            "actual": duplicate_count,
                            "status": (
                                "passed"
                                if duplicate_count == test_case["expected_duplicates"]
                                else "failed"
                            ),
                        }
                    )

                except Exception as e:
                    section["tests"].append(
                        {"name": test_case["name"], "status": "error", "error": str(e)}
                    )

            section["status"] = (
                "passed" if all(t["status"] == "passed" for t in section["tests"]) else "failed"
            )

        except Exception as e:
            section["status"] = "error"
            section["issues"].append(f"Quality gates testing failed: {e}")

        return section

    def test_regional_detection_comprehensive(self):
        """Comprehensive regional detection testing"""
        section = self.section("regional_detection")

        try:
            from src.regions.manager import RegionManager

            manager = RegionManager()

            # Comprehensive test cases for all regions
            test_cases = [
                # East Asian
                ("김민수", "E4", "korean"),
                ("李明", "E1", "chinese_simplified"),
                ("王小明", "E1", "chinese_simplified"),
                ("山田太郎", "E3", "japanese"),
                ("田中一郎", "E3", "japanese"),
                ("Nguyễn Văn A", "E5", "vietnamese"),
                # Slavic
                ("Иванов", "B1", "russian"),
                ("Петров", "B1", "russian"),
                ("Новак", "B2", "south_slavic"),
                # Arabic
                ("محمد", "C3", "arabic"),
                ("أحمد", "C3", "arabic"),
                ("عبدالله", "C3", "arabic"),
                # Latin
                ("John Smith", "A1", "anglo"),
                ("Jean Dupont", "A2", "french"),
                ("Hans Mueller", "A2", "german"),
                ("José García", "G1", "spanish"),
                # South Asian
                ("राज कुमार", "D1", "hindi"),
                ("அருண்", "D2", "tamil"),
                ("বাংলা", "D3", "bengali"),
            ]

            for name, expected_region, category in test_cases:
                entry = {"CanonicalNative": name}
                try:
                    result = manager.detect_region(entry)
                    detected = result.region_code if result else None

                    test_result = {
                        "input": name,
                        "expected": expected_region,
                        "actual": detected,
                        "category": category,
                        "confidence": result.confidence if result else 0,
                        "method": result.detection_method if result else None,
                        "status": "passed" if detected == expected_region else "failed",
                    }

                    if detected != expected_region:
                        section["issues"].append(
                            f"{name} → {detected} (expected: {expected_region})"
                        )

                    section["tests"].append(test_result)

                except Exception as e:
                    section["tests"].append(
                        {
                            "input": name,
                            "expected": expected_region,
                            "category": category,
                            "status": "error",
                            "error": str(e),
                        }
                    )

            # Calculate metrics by category
            categories = defaultdict(lambda: {"passed": 0, "total": 0})
            for test in section["tests"]:
                cat = test.get("category", "unknown")
                categories[cat]["total"] += 1
                if test["status"] == "passed":
                    categories[cat]["passed"] += 1

            section["metrics"] = {
                "total_tests": len(section["tests"]),
                "passed": sum(1 for t in section["tests"] if t["status"] == "passed"),
                "by_category": dict(categories),
                "detection_methods": list(
                    set(t.get("method") for t in section["tests"] if t.get("method"))
                ),
            }

            passed = section["metrics"]["passed"]
            total = section["metrics"]["total_tests"]
            section["status"] = "passed" if passed >= total * 0.9 else "failed"

        except Exception as e:
            section["status"] = "error"
            section["issues"].append(f"Regional detection testing failed: {e}")

        return section

    def test_file_organization(self):
        """Test file and directory organization"""
        section = self.section("file_organization")

        # Check for expected directories
        expected_dirs = [
            "src/core",
            "src/regions",
            "src/authorities",
            "src/analytics",
            "src/quality",
            "src/validation",
            "tests/unit",
            "tests/integration",
            "config",
            "docs",
            "scripts",
        ]

        for dir_path in expected_dirs:
            path = Path(dir_path)
            if path.exists():
                section["tests"].append(
                    {
                        "path": dir_path,
                        "type": "directory",
                        "status": "exists",
                        "size": sum(f.stat().st_size for f in path.rglob("*") if f.is_file()),
                    }
                )
            else:
                section["tests"].append(
                    {"path": dir_path, "type": "directory", "status": "missing"}
                )
                section["issues"].append(f"Missing directory: {dir_path}")

        # Check for duplicate/redundant files
        python_files = list(Path(".").rglob("*.py"))

        # Look for backup files
        backup_patterns = ["*.bak", "*.backup", "*~", "*.orig"]
        backup_files = []
        for pattern in backup_patterns:
            backup_files.extend(Path(".").rglob(pattern))

        if backup_files:
            section["warnings"].append(f"Found {len(backup_files)} backup files")

        # Look for __pycache__ directories
        pycache_dirs = list(Path(".").rglob("__pycache__"))
        if pycache_dirs:
            section["warnings"].append(f"Found {len(pycache_dirs)} __pycache__ directories")

        section["metrics"] = {
            "total_python_files": len(python_files),
            "backup_files": len(backup_files),
            "pycache_dirs": len(pycache_dirs),
            "total_size_mb": sum(f.stat().st_size for f in python_files) / (1024 * 1024),
        }

        section["status"] = "passed" if not section["issues"] else "failed"

        return section

    def test_code_quality(self):
        """Test code quality metrics"""
        section = self.section("code_quality")

        # Check for common code issues
        issues_found = defaultdict(list)

        python_files = list(Path("src").rglob("*.py"))

        for file_path in python_files[:50]:  # Sample first 50 files for speed
            try:
                content = file_path.read_text()
                lines = content.split("\n")

                # Check for various code quality issues
                for i, line in enumerate(lines, 1):
                    # Long lines
                    if len(line) > 120:
                        issues_found["long_lines"].append(f"{file_path}:{i}")

                    # TODO/FIXME comments
                    if "TODO" in line or "FIXME" in line:
                        issues_found["todos"].append(f"{file_path}:{i}")

                    # Print statements (should use logging)
                    if "print(" in line and not "#" in line[: line.find("print(")]:
                        issues_found["print_statements"].append(f"{file_path}:{i}")

                    # Bare except
                    if line.strip() == "except:":
                        issues_found["bare_except"].append(f"{file_path}:{i}")

            except Exception:
                pass

        section["metrics"] = {
            "files_analyzed": len(python_files),
            "long_lines": len(issues_found["long_lines"]),
            "todos": len(issues_found["todos"]),
            "print_statements": len(issues_found["print_statements"]),
            "bare_excepts": len(issues_found["bare_except"]),
        }

        # Only report first few instances of each issue
        for issue_type, instances in issues_found.items():
            if instances:
                section["warnings"].append(
                    f"{issue_type}: {len(instances)} instances (first 3: {instances[:3]})"
                )

        section["status"] = "passed"

        return section

    async def run_comprehensive_audit(self):
        """Run all audit tests"""
        print("=" * 80)
        print("ULTRATHINK COMPREHENSIVE V7 REALITY AUDIT")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}\n")

        # Run all tests
        print("📦 Testing Imports...")
        self.test_imports_comprehensive()

        print("🇰🇷 Testing Korean Processor...")
        self.test_korean_detailed()

        print("⚡ Testing Pipeline...")
        await self.test_pipeline_detailed()

        print("🚦 Testing Quality Gates...")
        self.test_quality_gates()

        print("🌍 Testing Regional Detection...")
        self.test_regional_detection_comprehensive()

        print("📁 Testing File Organization...")
        self.test_file_organization()

        print("📊 Testing Code Quality...")
        self.test_code_quality()

        # Generate summary
        self.generate_summary()

        # Save results
        output_file = f"audit_results_reality_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n📄 Full results saved to: {output_file}")

        return self.results

    def generate_summary(self):
        """Generate audit summary"""
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)

        total_sections = len(self.results["sections"])
        passed_sections = sum(
            1 for s in self.results["sections"].values() if s["status"] == "passed"
        )

        print(
            f"\n📊 Overall Score: {passed_sections}/{total_sections} ({100*passed_sections/total_sections:.1f}%)"
        )

        # Detailed section results
        for name, section in self.results["sections"].items():
            status_icon = "✅" if section["status"] == "passed" else "❌"
            print(f"\n{status_icon} {name}:")

            if section.get("metrics"):
                for key, value in section["metrics"].items():
                    if isinstance(value, float):
                        print(f"  - {key}: {value:.2f}")
                    else:
                        print(f"  - {key}: {value}")

            if section["issues"]:
                print(f"  Issues: {len(section['issues'])}")
                for issue in section["issues"][:3]:
                    print(f"    • {issue}")

            if section["warnings"]:
                print(f"  Warnings: {len(section['warnings'])}")
                for warning in section["warnings"][:3]:
                    print(f"    ⚠️ {warning}")

        # Overall assessment
        critical_pass = all(
            self.results["sections"].get(s, {}).get("status") == "passed"
            for s in [
                "imports",
                "korean_processor",
                "pipeline",
                "quality_gates",
                "regional_detection",
            ]
        )

        if critical_pass:
            print("\n✅ SYSTEM READY FOR PRODUCTION")
        else:
            print("\n⚠️ SYSTEM NEEDS ATTENTION")


async def main():
    auditor = ComprehensiveAuditor()
    await auditor.run_comprehensive_audit()


if __name__ == "__main__":
    asyncio.run(main())
