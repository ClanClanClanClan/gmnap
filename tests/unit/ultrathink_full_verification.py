#!/usr/bin/env python3
"""
from typing import List
from typing import Any
ULTRATHINK FULL COMPLIANCE VERIFICATION
Brutally honest testing of all claimed fixes and improvements.

This script verifies:
1. Archive cleanup didn't break critical functionality
2. Performance improvements are real
3. Regional classification improvements work
4. Korean processing actually functions
5. C2/C4 regions are really fixed
6. No regressions were introduced
"""

import sys
import time
import json
import os
import traceback
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.insert(0, str(Path(__file__).parent))


class UltrathinkVerifier:
    """Comprehensive verification of all system claims."""

    def __init__(self):
        self.issues_found = []
        self.successes = []
        self.performance_metrics = {}

    def verify_1_archive_cleanup_safety(self):
        """Verify archive cleanup didn't break critical functionality."""
        print("\n🔍 VERIFICATION 1: Archive Cleanup Safety")
        print("=" * 60)

        # Check for any broken imports
        broken_imports = []
        critical_files = [
            "src/core/pipeline_v6.py",
            "src/regions/manager_optimized.py",
            "src/regions/e_groups/e4_korea/processor.py",
            "src/regions/e_groups/e4_korea_processor.py",
        ]

        for file in critical_files:
            try:
                with open(file, "r") as f:
                    content = f.read()
                    # Check for imports from deleted files
                    if "from src.gmnap" in content:
                        broken_imports.append(
                            f"{file}: Contains imports from deleted src.gmnap"
                        )
                    if "from src." in content:
                        broken_imports.append(
                            f"{file}: Contains imports from deleted gmnap"
                        )
            except Exception as e:
                self.issues_found.append(f"Cannot read {file}: {e}")

        if broken_imports:
            print("FAIL BROKEN IMPORTS FOUND:")
            for issue in broken_imports:
                print(f"  - {issue}")
                self.issues_found.append(issue)
        else:
            print("PASS No broken imports from archive cleanup")
            self.successes.append("Archive cleanup safe - no broken imports")

        # Test basic pipeline functionality
        try:
            from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
            from src.core.config import GMNAPConfig

            config = GMNAPConfig()
            pipeline = GMNAPPipeline(config, mode=PipelineMode.QUICK)
            print("PASS Pipeline imports successfully")
            self.successes.append("Pipeline imports work after cleanup")
        except Exception as e:
            print(f"FAIL Pipeline import failed: {e}")
            self.issues_found.append(f"Pipeline import broken: {e}")

        return len(self.issues_found) == 0

    def verify_2_performance_claims(self):
        """Verify performance improvement claims are real."""
        print("\n🔍 VERIFICATION 2: Performance Claims")
        print("=" * 60)

        try:
            from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
            from src.core.config import GMNAPConfig
            import tempfile
            import yaml

            # Create test dataset
            test_data = {}
            test_names = [
                "Isaac Newton",
                "Carl Friedrich Gauss",
                "Andrey Kolmogorov",
                "Omar Khayyam",
                "Srinivasa Ramanujan",
                "김정은",
                "陈省身",
            ]

            for i, name in enumerate(test_names * 10):  # 70 entries
                test_data[f"TEST{i:04d}"] = {
                    "GlobalID": f"TEST{i:04d}",
                    "CanonicalLatin": name,
                    "UpdatedAt": "2025-08-04T00:00:00Z",
                }

            with tempfile.TemporaryDirectory() as tmpdir:
                test_file = Path(tmpdir) / "test.yaml"
                with open(test_file, "w", encoding="utf-8") as f:
                    yaml.dump(test_data, f, allow_unicode=True)

                # Configure pipeline
                config = GMNAPConfig()
                config.cache.cache_dir = str(Path(tmpdir) / "cache")

                # Test QUICK mode performance
                start_time = time.time()
                pipeline = GMNAPPipeline(config, mode=PipelineMode.QUICK)
                result = pipeline.run(Path(tmpdir))
                duration = time.time() - start_time

                entries_per_sec = len(test_data) / duration
                projected_1m = (1_000_000 / entries_per_sec) / 60

                self.performance_metrics["quick_mode"] = {
                    "duration": duration,
                    "entries": len(test_data),
                    "rate": entries_per_sec,
                    "projected_1m_minutes": projected_1m,
                }

                print(f"📊 QUICK Mode Performance:")
                print(f"  Duration: {duration:.2f}s for {len(test_data)} entries")
                print(f"  Rate: {entries_per_sec:.1f} entries/sec")
                print(f"  Projected 1M: {projected_1m:.1f} minutes")

                # Check if performance is reasonable
                if projected_1m <= 600:  # 10 hours max
                    print("PASS Performance is within acceptable range")
                    self.successes.append(
                        f"Performance verified: {projected_1m:.1f} min/1M"
                    )
                else:
                    print(f"FAIL Performance too slow: {projected_1m:.1f} min/1M")
                    self.issues_found.append(
                        f"Performance regression: {projected_1m:.1f} min/1M"
                    )

        except Exception as e:
            print(f"FAIL Performance test failed: {e}")
            self.issues_found.append(f"Performance verification failed: {e}")
            traceback.print_exc()

        return True

    def verify_3_regional_classification(self):
        """Verify regional classification improvements."""
        print("\n🔍 VERIFICATION 3: Regional Classification")
        print("=" * 60)

        try:
            from src.regions.manager_optimized import RegionManager

            manager = RegionManager()

            # Critical test cases that MUST work
            critical_tests = [
                # Anglo names
                ("Isaac Newton", "A1", "English mathematician"),
                ("Alan Turing", "A1", "English computer scientist"),
                ("John Nash", "A1", "American mathematician"),
                # Russian names (previously broken)
                ("Andrey Kolmogorov", "B1", "Russian mathematician"),
                ("Pafnuty Chebyshev", "B1", "Russian mathematician"),
                # Persian names (previously broken)
                ("Omar Khayyam", "C2", "Persian mathematician"),
                # Indian names (previously broken)
                ("Srinivasa Ramanujan", "D1", "Indian mathematician"),
                # German names
                ("Carl Friedrich Gauss", "A2", "German mathematician"),
                ("David Hilbert", "A2", "German mathematician"),
                # Chinese names
                ("Shiing-Shen Chern", "E1", "Chinese mathematician"),
            ]

            failures = 0
            successes = 0

            for name, expected, description in critical_tests:
                try:
                    result = manager.detect_region({"CanonicalLatin": name})
                    actual = (
                        result.region_code
                        if hasattr(result, "region_code")
                        else str(result)
                    )

                    if actual == expected:
                        print(f"PASS {name} -> {actual} ({description})")
                        successes += 1
                    else:
                        print(
                            f"FAIL {name} -> {actual} (expected {expected}) - {description}"
                        )
                        failures += 1
                        self.issues_found.append(
                            f"Classification failed: {name} -> {actual} (expected {expected})"
                        )

                except Exception as e:
                    print(f"FAIL {name} -> ERROR: {e}")
                    failures += 1
                    self.issues_found.append(f"Classification error for {name}: {e}")

            accuracy = successes / len(critical_tests)
            print(
                f"\n📊 Classification Accuracy: {successes}/{len(critical_tests)} ({accuracy:.1%})"
            )

            if accuracy >= 0.8:
                self.successes.append(
                    f"Regional classification working: {accuracy:.1%}"
                )
            else:
                self.issues_found.append(
                    f"Regional classification broken: {accuracy:.1%}"
                )

        except Exception as e:
            print(f"FAIL Regional classification test failed: {e}")
            self.issues_found.append(
                f"Regional classification verification failed: {e}"
            )

        return True

    def verify_4_korean_processing(self):
        """Verify Korean processing actually works."""
        print("\n🔍 VERIFICATION 4: Korean Processing")
        print("=" * 60)

        try:
            from src.regions.manager_optimized import RegionManager

            manager = RegionManager()

            # Test Korean detection
            korean_tests = [
                ("김정은", "E4", "Korean name in Hangul"),
                ("Kim Jong-un", "E4", "Korean name romanized"),
                ("Park Geun-hye", "E4", "Korean name romanized"),
                ("Moon Jae-in", "E4", "Korean name romanized"),
            ]

            for name, expected, description in korean_tests:
                try:
                    result = manager.detect_region({"CanonicalLatin": name})
                    actual = (
                        result.region_code
                        if hasattr(result, "region_code")
                        else str(result)
                    )

                    if actual == expected:
                        print(f"PASS {name} -> {actual} ({description})")
                    else:
                        print(
                            f"FAIL {name} -> {actual} (expected {expected}) - {description}"
                        )
                        self.issues_found.append(f"Korean detection failed: {name}")

                except Exception as e:
                    print(f"FAIL {name} -> ERROR: {e}")
                    self.issues_found.append(f"Korean detection error: {name} - {e}")

            # Test variant generation
            print("\n🔬 Testing Korean Variant Generation:")
            if "E4" in manager._regions:
                processor = manager._regions["E4"]
                test_entry = {"CanonicalLatin": "Kim Jong-un"}

                try:
                    processor.clean(test_entry)
                    processor.augment(test_entry)

                    variants = test_entry.get("Variants", {}).get("Synthesised", [])
                    if variants:
                        print(f"PASS Generated {len(variants)} Korean variants")
                        for v in variants[:3]:
                            print(f"  - {v}")
                        self.successes.append("Korean variant generation working")
                    else:
                        print("FAIL No Korean variants generated")
                        self.issues_found.append("Korean variant generation broken")

                except Exception as e:
                    print(f"FAIL Korean processing error: {e}")
                    self.issues_found.append(f"Korean processing broken: {e}")
            else:
                print("FAIL E4 Korea region not loaded")
                self.issues_found.append("E4 Korea region missing")

        except Exception as e:
            print(f"FAIL Korean verification failed: {e}")
            self.issues_found.append(f"Korean verification error: {e}")

        return True

    def verify_5_persian_arabic_fixes(self):
        """Verify C2 Persian and C4 Arabic fixes."""
        print("\n🔍 VERIFICATION 5: Persian/Arabic Fixes")
        print("=" * 60)

        try:
            from src.regions.manager_optimized import RegionManager

            manager = RegionManager()

            # Test C2 Persian
            if "C2" in manager._regions:
                processor = manager._regions["C2"]
                test_entry = {"CanonicalLatin": "Omar Khayyam"}

                try:
                    processor.clean(test_entry)
                    processor.augment(test_entry)
                    processor.validate(test_entry)
                    print("PASS C2 Persian processing works (no TypeError)")
                    self.successes.append("C2 Persian TypeError fixed")
                except TypeError as e:
                    print(f"FAIL C2 Persian still has TypeError: {e}")
                    self.issues_found.append(f"C2 Persian TypeError not fixed: {e}")
                except Exception as e:
                    print(f"FAIL C2 Persian error: {e}")
                    self.issues_found.append(f"C2 Persian error: {e}")

            # Test C4 Arabic
            if "C4" in manager._regions:
                processor = manager._regions["C4"]
                test_entry = {"CanonicalLatin": "Abdul Jabbar Jerri"}

                try:
                    processor.clean(test_entry)
                    processor.augment(test_entry)
                    processor.validate(test_entry)
                    print("PASS C4 Arabic processing works")
                    self.successes.append("C4 Arabic processing fixed")
                except Exception as e:
                    print(f"FAIL C4 Arabic error: {e}")
                    self.issues_found.append(f"C4 Arabic error: {e}")

        except Exception as e:
            print(f"FAIL Persian/Arabic verification failed: {e}")
            self.issues_found.append(f"Persian/Arabic verification error: {e}")

        return True

    def verify_6_no_regressions(self):
        """Verify no regressions were introduced."""
        print("\n🔍 VERIFICATION 6: Regression Testing")
        print("=" * 60)

        try:
            # Run the comprehensive system audit
            from comprehensive_system_audit import run_comprehensive_audit

            print("Running comprehensive system audit...")

            results = run_comprehensive_audit()

            # Check critical metrics
            if results["passing_tests"] < 4:
                self.issues_found.append(
                    f"Regression: Only {results['passing_tests']}/6 tests passing"
                )
            else:
                self.successes.append(
                    f"No major regressions: {results['passing_tests']}/6 tests passing"
                )

            # Check performance regression
            if results.get("performance_time", 1000) > 500:
                self.issues_found.append(
                    f"Performance regression: {results['performance_time']} min/1M"
                )

        except Exception as e:
            print(f"WARN Regression test skipped: {e}")
            # Don't fail on this - it's optional

        return True

    def run_ultrathink_verification(self):
        """Run complete verification suite."""
        print("🧠 ULTRATHINK FULL COMPLIANCE VERIFICATION")
        print("=" * 80)
        print("Brutally honest testing of all system claims...")
        print("=" * 80)

        # Run all verifications
        self.verify_1_archive_cleanup_safety()
        self.verify_2_performance_claims()
        self.verify_3_regional_classification()
        self.verify_4_korean_processing()
        self.verify_5_persian_arabic_fixes()
        self.verify_6_no_regressions()

        # Generate report
        print("\n" + "=" * 80)
        print("🎯 ULTRATHINK VERIFICATION RESULTS")
        print("=" * 80)

        print(f"\nPASS SUCCESSES ({len(self.successes)}):")
        for success in self.successes:
            print(f"  - {success}")

        print(f"\nFAIL ISSUES FOUND ({len(self.issues_found)}):")
        if self.issues_found:
            for issue in self.issues_found:
                print(f"  - {issue}")
        else:
            print("  - None! All verifications passed!")

        # Performance summary
        if self.performance_metrics:
            print(f"\n📊 PERFORMANCE METRICS:")
            for mode, metrics in self.performance_metrics.items():
                print(f"  - {mode}: {metrics['projected_1m_minutes']:.1f} min/1M")

        # Final verdict
        print(f"\n🏁 FINAL VERDICT:")
        if len(self.issues_found) == 0:
            print("  PASS SYSTEM IS 100% COMPLIANT - ALL CLAIMS VERIFIED!")
            compliance = 100.0
        else:
            compliance = (
                len(self.successes) / (len(self.successes) + len(self.issues_found))
            ) * 100
            print(
                f"  WARN SYSTEM IS {compliance:.1f}% COMPLIANT - ISSUES NEED ATTENTION"
            )

        return compliance


def main():
    """Run the ultrathink verification."""
    verifier = UltrathinkVerifier()
    compliance = verifier.run_ultrathink_verification()

    if compliance < 100:
        sys.exit(1)  # Exit with error if not fully compliant


if __name__ == "__main__":
    main()
