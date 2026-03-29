#!/usr/bin/env python3
"""
ULTRAUDIT: Final comprehensive readiness verification
Test EVERYTHING after thread safety fixes to ensure nothing is broken
"""

import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


class FinalReadinessAuditor:
    """Comprehensive final readiness audit."""

    def __init__(self):
        self.issues = []
        self.warnings = []
        self.tests_run = 0
        self.tests_passed = 0

    def log_issue(self, severity: str, issue: str):
        """Log an issue found during audit."""
        if severity == "CRITICAL":
            self.issues.append(f"❌ CRITICAL: {issue}")
        elif severity == "WARNING":
            self.warnings.append(f"⚠️ WARNING: {issue}")
        print(f"{'❌' if severity == 'CRITICAL' else '⚠️'} {severity}: {issue}")

    def run_test(self, test_name: str, test_func):
        """Run a test and track results."""
        print(f"\n🧪 TESTING: {test_name}")
        self.tests_run += 1

        try:
            success = test_func()
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED: {test_name}")
                return True
            else:
                self.log_issue("CRITICAL", f"Test failed: {test_name}")
                return False
        except Exception as e:
            self.log_issue("CRITICAL", f"Test crashed: {test_name} - {e}")
            traceback.print_exc()
            return False

    def test_basic_manager_functionality(self) -> bool:
        """Test that RegionManager still works after modifications."""
        try:
            from regions.manager import RegionManager

            manager = RegionManager(Path("./config"))

            # Test getting regions
            region_a1 = manager.get_region("A1")
            if not region_a1:
                self.log_issue("CRITICAL", "Cannot get A1 region")
                return False

            region_a2 = manager.get_region("A2")
            if not region_a2:
                self.log_issue("CRITICAL", "Cannot get A2 region")
                return False

            # Test thread-safe parameter works
            region_thread_safe = manager.get_region("A1", thread_safe=True)
            region_legacy = manager.get_region("A1", thread_safe=False)

            if not region_thread_safe or not region_legacy:
                self.log_issue("CRITICAL", "thread_safe parameter not working")
                return False

            # Fresh instances should be different
            if region_thread_safe is region_legacy:
                self.log_issue(
                    "WARNING", "thread_safe=True not creating fresh instances"
                )

            return True

        except Exception as e:
            self.log_issue("CRITICAL", f"Manager functionality broken: {e}")
            return False

    def test_all_regions_load(self) -> bool:
        """Test that all 37 regions still load correctly."""
        try:
            from regions.manager import RegionManager

            manager = RegionManager(Path("./config"))
            expected_regions = [
                "A1",
                "A2",
                "A3",
                "A4",
                "A5",
                "B1",
                "B2",
                "B3",
                "C1",
                "C2",
                "C3",
                "C4",
                "C5",
                "C6",
                "C7",
                "C8",
                "C9",
                "D1",
                "D2",
                "D3",
                "D4",
                "D5",
                "E1",
                "E2",
                "E3",
                "E4",
                "E5",
                "E6",
                "E7",
                "F1",
                "F2",
                "F3",
                "F4",
                "G1",
                "H1",
                "R0",
                "Z0",
            ]

            failed_regions = []
            for region_code in expected_regions:
                region = manager.get_region(region_code)
                if not region:
                    failed_regions.append(region_code)

            if failed_regions:
                self.log_issue("CRITICAL", f"Failed to load regions: {failed_regions}")
                return False

            print(f"✅ All {len(expected_regions)} regions load successfully")
            return True

        except Exception as e:
            self.log_issue("CRITICAL", f"Region loading test failed: {e}")
            return False

    def test_end_to_end_processing(self) -> bool:
        """Test complete end-to-end processing pipeline."""
        try:
            from regions.manager import RegionManager
            from core.security_validator import SecurityValidator

            manager = RegionManager(Path("./config"))
            validator = SecurityValidator()

            # Test complex mathematician entry
            test_entry = {
                "GlobalID": "final-audit-test-001",
                "CanonicalLatin": "Jean-François Monté",
                "CanonicalNative": "Jean-François Monté",
                "Field": "Differential Geometry",
            }

            # Step 1: Security validation
            success, clean_name = validator.validate_string(
                test_entry["CanonicalLatin"], "test"
            )
            if not success:
                self.log_issue("CRITICAL", "Security validation failed")
                return False

            # Step 2: Region processing
            region = manager.get_region("A2")  # Western Europe
            if not region:
                self.log_issue("CRITICAL", "Cannot get A2 region for processing")
                return False

            # Step 3: Full pipeline
            original_entry = test_entry.copy()
            region.clean(test_entry)
            region.augment(test_entry)
            region.validate(test_entry)

            # Verify processing occurred
            if test_entry == original_entry:
                self.log_issue("WARNING", "Entry not modified by processing")

            # Check for expected fields
            if "Variants" not in test_entry:
                self.log_issue("WARNING", "No variants generated")

            print(f"✅ End-to-end processing successful")
            print(f"   Input: {original_entry['CanonicalLatin']}")
            print(f"   Output has variants: {'Variants' in test_entry}")

            return True

        except Exception as e:
            self.log_issue("CRITICAL", f"End-to-end processing failed: {e}")
            return False

    def test_edge_cases_still_work(self) -> bool:
        """Test that V7 edge cases still work after changes."""
        try:
            from regions.manager import RegionManager

            manager = RegionManager(Path("./config"))
            region = manager.get_region("A1")

            if not region:
                self.log_issue("CRITICAL", "Cannot get A1 region for edge case testing")
                return False

            edge_cases = [
                {"GlobalID": "edge-1", "CanonicalLatin": "Test\tName"},  # Tab
                {"GlobalID": "edge-2", "CanonicalLatin": "Test\nName"},  # Newline
                {"GlobalID": "edge-3", "CanonicalLatin": "X"},  # Single char
                {"GlobalID": "edge-4", "CanonicalNative": "Native Only"},  # Native only
                {"GlobalID": "edge-5"},  # No names
            ]

            failed_cases = []
            for i, test_case in enumerate(edge_cases):
                try:
                    test_copy = test_case.copy()
                    region.clean(test_copy)
                    region.augment(test_copy)
                    region.validate(test_copy)
                except Exception as e:
                    failed_cases.append(f"Case {i+1}: {e}")

            if failed_cases:
                self.log_issue("CRITICAL", f"Edge cases failed: {failed_cases}")
                return False

            print(f"✅ All {len(edge_cases)} edge cases handled successfully")
            return True

        except Exception as e:
            self.log_issue("CRITICAL", f"Edge case testing failed: {e}")
            return False

    def test_performance_after_changes(self) -> bool:
        """Test that performance is still acceptable."""
        try:
            from regions.manager import RegionManager

            manager = RegionManager(Path("./config"))

            # Baseline: 100 entries single threaded
            test_entries = [
                {"GlobalID": f"perf-{i}", "CanonicalLatin": f"Performance Test {i}"}
                for i in range(100)
            ]

            start_time = time.time()
            for entry in test_entries:
                region = manager.get_region("A1")
                region.clean(entry.copy())
                region.augment(entry.copy())
            end_time = time.time()

            duration = end_time - start_time
            throughput = len(test_entries) / duration

            print(f"   Single-threaded performance: {throughput:.1f} entries/second")

            # Should be at least 50 entries/second for reasonable performance
            if throughput < 50:
                self.log_issue(
                    "WARNING",
                    f"Performance may be degraded: {throughput:.1f} entries/s",
                )
                return False

            return True

        except Exception as e:
            self.log_issue("CRITICAL", f"Performance test failed: {e}")
            return False

    def test_thread_safety_maintained(self) -> bool:
        """Verify thread safety is maintained."""
        try:
            import concurrent.futures
            from regions.manager import RegionManager

            manager = RegionManager(Path("./config"))

            def worker(worker_id):
                errors = []
                for i in range(10):
                    try:
                        region = manager.get_region("A1", thread_safe=True)
                        entry = {
                            "GlobalID": f"thread-{worker_id}-{i}",
                            "CanonicalLatin": f"Thread Test {worker_id} {i}",
                        }
                        region.clean(entry)
                        region.augment(entry)
                    except Exception as e:
                        if "dictionary changed size during iteration" in str(e):
                            errors.append(f"RACE CONDITION: {e}")
                        else:
                            errors.append(f"ERROR: {e}")
                return errors

            # Run concurrent workers
            all_errors = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(worker, i) for i in range(10)]
                for future in concurrent.futures.as_completed(futures):
                    errors = future.result()
                    all_errors.extend(errors)

            if all_errors:
                self.log_issue(
                    "CRITICAL", f"Thread safety broken: {len(all_errors)} errors"
                )
                for error in all_errors[:3]:
                    print(f"   {error}")
                return False

            print("✅ Thread safety maintained")
            return True

        except Exception as e:
            self.log_issue("CRITICAL", f"Thread safety test failed: {e}")
            return False

    def test_infrastructure_integration(self) -> bool:
        """Test that infrastructure components still integrate."""
        try:
            # Test imports
            from regions.manager import RegionManager
            from core.security_validator import SecurityValidator
            from core.pipeline import Pipeline, PipelineConfig
            from core.memgraph_client import MemgraphClient

            # Test basic initialization
            manager = RegionManager(Path("./config"))
            validator = SecurityValidator()
            config = PipelineConfig()
            pipeline = Pipeline(config)
            client = MemgraphClient()

            print("✅ All infrastructure components import and initialize")
            return True

        except ImportError as e:
            self.log_issue("CRITICAL", f"Infrastructure import failed: {e}")
            return False
        except Exception as e:
            self.log_issue("CRITICAL", f"Infrastructure initialization failed: {e}")
            return False

    def run_comprehensive_audit(self) -> bool:
        """Run the complete final audit."""
        print("🔥 ULTRAUDIT: FINAL COMPREHENSIVE READINESS VERIFICATION")
        print("=" * 80)

        tests = [
            ("Basic Manager Functionality", self.test_basic_manager_functionality),
            ("All Regions Load", self.test_all_regions_load),
            ("End-to-End Processing", self.test_end_to_end_processing),
            ("Edge Cases Still Work", self.test_edge_cases_still_work),
            ("Performance After Changes", self.test_performance_after_changes),
            ("Thread Safety Maintained", self.test_thread_safety_maintained),
            ("Infrastructure Integration", self.test_infrastructure_integration),
        ]

        for test_name, test_func in tests:
            self.run_test(test_name, test_func)

        return self.generate_final_report()

    def generate_final_report(self) -> bool:
        """Generate final readiness report."""
        print("\n" + "=" * 80)
        print("🎯 ULTRAUDIT FINAL READINESS REPORT")
        print("=" * 80)

        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {100 * self.tests_passed / self.tests_run:.1f}%")

        if self.issues:
            print(f"\n❌ CRITICAL ISSUES FOUND ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  {issue}")

        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")

        # Final assessment
        critical_issues = len(self.issues)
        major_warnings = len(
            [w for w in self.warnings if "Performance" in w or "thread_safe" in w]
        )

        print(f"\n🎯 FINAL READINESS ASSESSMENT:")

        if critical_issues == 0 and major_warnings == 0:
            print("🚀 STATUS: FULLY READY FOR V7 TACTICAL ROADMAP")
            print("✅ All core functionality working")
            print("✅ Thread safety implemented and verified")
            print("✅ Performance maintained")
            print("✅ Infrastructure components operational")
            print("✅ Edge cases handled correctly")
            print("\n🎯 RECOMMENDATION: PROCEED WITH CONFIDENCE")
            return True

        elif critical_issues == 0 and major_warnings <= 2:
            print("✅ STATUS: READY FOR V7 TACTICAL ROADMAP")
            print("⚠️ Minor issues present but not blocking")
            print("✅ Core functionality solid")
            print("\n🎯 RECOMMENDATION: PROCEED WITH MONITORING")
            return True

        elif critical_issues <= 1:
            print("⚠️ STATUS: MOSTLY READY")
            print("❌ Some issues need resolution")
            print("\n🎯 RECOMMENDATION: RESOLVE CRITICAL ISSUES FIRST")
            return False

        else:
            print("❌ STATUS: NOT READY")
            print("🚨 Multiple critical issues prevent deployment")
            print("\n🎯 RECOMMENDATION: MAJOR FIXES REQUIRED")
            return False


def main():
    """Run final comprehensive readiness audit."""
    auditor = FinalReadinessAuditor()
    ready = auditor.run_comprehensive_audit()
    return ready


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
