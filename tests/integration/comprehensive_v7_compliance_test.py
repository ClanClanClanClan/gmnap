#!/usr/bin/env python3
"""
from typing import List
from typing import Any
Comprehensive V7 Compliance Testing Framework

Tests all 33 regions for:
- 99%+ security compliance (attack blocking)
- 95%+ edge case handling
- End-to-end processing functionality

Targets: A1-A5, B1-B3, C1-C9, D1-D5, E1-E7, F1-F3, G1
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import traceback

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.regions.manager import RegionManager


class V7ComplianceTest:
    """Comprehensive V7 compliance test framework."""

    def __init__(self):
        self.manager = RegionManager(Path("./config"))

        # V7 security attack vectors (should be blocked)
        self.security_attacks = [
            # Control character attacks
            {"name": "NULL character", "input": "Test\x00Malicious"},
            {"name": "Bell character", "input": "Test\x07Alert"},
            {"name": "Backspace attack", "input": "Test\x08"},
            {"name": "Tab injection", "input": "Test\x09\x09"},
            {"name": "Newline injection", "input": "Test\x0A\x0D"},
            {"name": "Vertical tab", "input": "Test\x0B"},
            {"name": "Form feed", "input": "Test\x0C"},
            {"name": "Escape sequence", "input": "Test\x1B[31m"},
            {"name": "Unit separator", "input": "Test\x1F"},
            {"name": "DELETE character", "input": "Test\x7F"},
            # Zero-width character attacks
            {"name": "Zero-width space", "input": "Test\u200B"},
            {"name": "Zero-width non-joiner", "input": "Test\u200C"},
            {"name": "Zero-width joiner", "input": "Test\u200D"},
            {"name": "Byte order mark", "input": "Test\uFEFF"},
            # DoS attacks
            {"name": "DoS length attack", "input": "A" * 200},
            # Combined attacks
            {"name": "Multi-vector attack", "input": "Test\x00\u200B\x1F" + "X" * 180},
        ]

        # V7 edge cases (should be handled gracefully)
        self.edge_cases = [
            # Single character names (should pass with warnings)
            {"name": "Single char A", "test": {"CanonicalLatin": "A", "GlobalID": "edge-1"}},
            {"name": "Single char X", "test": {"CanonicalLatin": "X", "GlobalID": "edge-2"}},
            {"name": "Single char Z", "test": {"CanonicalLatin": "Z", "GlobalID": "edge-3"}},
            # Mononyms (should pass)
            {"name": "Mononym Cher", "test": {"CanonicalLatin": "Cher", "GlobalID": "edge-4"}},
            {
                "name": "Mononym Madonna",
                "test": {"CanonicalLatin": "Madonna", "GlobalID": "edge-5"},
            },
            {
                "name": "Mononym Aristotle",
                "test": {"CanonicalLatin": "Aristotle", "GlobalID": "edge-6"},
            },
            # Complex legitimate names (should pass)
            {
                "name": "Complex hyphenated",
                "test": {
                    "CanonicalLatin": "Jean-Claude Van Damme-O'Connor Jr.",
                    "GlobalID": "edge-7",
                },
            },
            {
                "name": "International accents",
                "test": {"CanonicalLatin": "José María de la Cruz-Sánchez", "GlobalID": "edge-8"},
            },
            {
                "name": "French particles",
                "test": {"CanonicalLatin": "François-André de Saint-Exupéry", "GlobalID": "edge-9"},
            },
            # Empty field handling (should not crash)
            {
                "name": "Empty Latin field",
                "test": {
                    "CanonicalLatin": "",
                    "CanonicalNative": "Test Native",
                    "GlobalID": "edge-10",
                },
            },
            {"name": "Missing canonical", "test": {"GlobalID": "edge-11"}},
            # Roman numerals and suffixes
            {
                "name": "Roman numerals",
                "test": {"CanonicalLatin": "John Smith III", "GlobalID": "edge-12"},
            },
            {
                "name": "Academic suffixes",
                "test": {"CanonicalLatin": "Dr. Smith, John Jr.", "GlobalID": "edge-13"},
            },
            # Mixed scripts (for applicable regions)
            {
                "name": "Mixed scripts",
                "test": {
                    "CanonicalLatin": "Smith John",
                    "CanonicalNative": "スミス",
                    "GlobalID": "edge-14",
                },
            },
        ]

        # All regions to test
        self.all_regions = [
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
            "G1",
        ]

    def test_security_compliance(self, region_code: str) -> Dict[str, Any]:
        """Test a region's security compliance against attack vectors."""
        region = self.manager.get_region(region_code)
        if not region:
            return {"status": "FAILED", "error": "Region not loaded", "blocked": 0, "total": 0}

        blocked_attacks = 0
        failed_blocks = []

        for attack in self.security_attacks:
            attack_entry = {
                "CanonicalLatin": attack["input"],
                "GlobalID": f"security-test-{region_code}",
            }

            try:
                # Test all V7 methods - any should block the attack
                region.clean(attack_entry)
                region.augment(attack_entry)
                region.validate(attack_entry)
                region.order_key(attack_entry)

                # If we reach here, the attack was not blocked
                failed_blocks.append(attack["name"])

            except Exception as e:
                # Attack was blocked (expected behavior)
                blocked_attacks += 1

        total_attacks = len(self.security_attacks)
        block_rate = 100 * blocked_attacks / total_attacks

        return {
            "status": (
                "PASSED" if block_rate >= 99.0 else "PARTIAL" if block_rate >= 90.0 else "FAILED"
            ),
            "blocked": blocked_attacks,
            "total": total_attacks,
            "block_rate": block_rate,
            "failed_blocks": failed_blocks,
        }

    def test_edge_case_handling(self, region_code: str) -> Dict[str, Any]:
        """Test a region's edge case handling."""
        region = self.manager.get_region(region_code)
        if not region:
            return {"status": "FAILED", "error": "Region not loaded", "passed": 0, "total": 0}

        passed_cases = 0
        failed_cases = []

        for case in self.edge_cases:
            try:
                # Test all V7 methods - should handle gracefully
                entry = case["test"].copy()
                region.clean(entry)
                region.augment(entry)
                region.validate(entry)
                key = region.order_key(entry)

                # Success if we reach here without exceptions
                passed_cases += 1

            except Exception as e:
                # Edge case was not handled gracefully
                failed_cases.append(f"{case['name']}: {str(e)[:60]}")

        total_cases = len(self.edge_cases)
        pass_rate = 100 * passed_cases / total_cases

        return {
            "status": (
                "PASSED" if pass_rate >= 95.0 else "PARTIAL" if pass_rate >= 80.0 else "FAILED"
            ),
            "passed": passed_cases,
            "total": total_cases,
            "pass_rate": pass_rate,
            "failed_cases": failed_cases,
        }

    def test_region_v7_compliance(self, region_code: str) -> Dict[str, Any]:
        """Test comprehensive V7 compliance for a single region."""
        print(f"  🔍 Testing {region_code}...")

        start_time = time.time()

        # Test security compliance
        security_result = self.test_security_compliance(region_code)

        # Test edge case handling
        edge_result = self.test_edge_case_handling(region_code)

        # Calculate overall compliance score
        security_weight = 0.6  # Security is weighted higher
        edge_weight = 0.4

        if security_result["status"] != "FAILED" and edge_result["status"] != "FAILED":
            overall_score = (
                security_result["block_rate"] * security_weight
                + edge_result["pass_rate"] * edge_weight
            )
        else:
            overall_score = 0.0

        # Determine overall status
        if overall_score >= 97.0:
            overall_status = "EXCELLENT"
        elif overall_score >= 95.0:
            overall_status = "PASSED"
        elif overall_score >= 85.0:
            overall_status = "PARTIAL"
        else:
            overall_status = "FAILED"

        elapsed = time.time() - start_time

        return {
            "region": region_code,
            "overall_status": overall_status,
            "overall_score": overall_score,
            "security": security_result,
            "edge_cases": edge_result,
            "test_time": elapsed,
        }

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run comprehensive V7 compliance test on all regions."""
        print("🚀 COMPREHENSIVE V7 COMPLIANCE TEST")
        print("=" * 60)
        print(f"Testing {len(self.all_regions)} regions for V7 compliance:")
        print(
            f"  - Security: {len(self.security_attacks)} attack vectors (99%+ block rate required)"
        )
        print(f"  - Edge cases: {len(self.edge_cases)} test cases (95%+ pass rate required)")
        print()

        results = {}
        total_start_time = time.time()

        for region_code in self.all_regions:
            try:
                result = self.test_region_v7_compliance(region_code)
                results[region_code] = result

                # Print result summary
                security = result["security"]
                edge = result["edge_cases"]
                print(
                    f"    📊 {region_code}: {result['overall_status']} "
                    f"({result['overall_score']:.1f}%) - "
                    f"Security: {security['block_rate']:.1f}%, "
                    f"Edge: {edge['pass_rate']:.1f}%"
                )

            except Exception as e:
                print(f"    💥 {region_code}: ERROR - {str(e)[:60]}")
                results[region_code] = {
                    "region": region_code,
                    "overall_status": "ERROR",
                    "overall_score": 0.0,
                    "error": str(e),
                }

        total_elapsed = time.time() - total_start_time

        # Calculate overall statistics
        stats = self._calculate_overall_stats(results)

        print()
        print("=" * 60)
        print("📊 V7 COMPLIANCE TEST RESULTS:")
        print(f"   🏆 Excellent (97%+): {stats['excellent']}/{stats['total']} regions")
        print(f"   PASS Passed (95%+): {stats['passed']}/{stats['total']} regions")
        print(f"   WARN  Partial (85%+): {stats['partial']}/{stats['total']} regions")
        print(f"   FAIL Failed (<85%): {stats['failed']}/{stats['total']} regions")
        print(f"   💥 Errors: {stats['errors']}/{stats['total']} regions")
        print()
        print(f"📈 Overall V7 Compliance: {stats['overall_compliance']:.1f}%")
        print(f"🛡️  Average Security: {stats['avg_security']:.1f}% (Target: 99%+)")
        print(f"🎯 Average Edge Cases: {stats['avg_edge_cases']:.1f}% (Target: 95%+)")
        print(f"⏱️  Total Test Time: {total_elapsed:.2f}s")

        # Final verdict
        if stats["overall_compliance"] >= 97.0:
            print(f"\n🎉 EXCELLENT V7 COMPLIANCE ACHIEVED!")
            print(f"   System exceeds all V7 requirements")
        elif stats["overall_compliance"] >= 95.0:
            print(f"\nPASS V7 COMPLIANCE ACHIEVED!")
            print(f"   System meets all V7 requirements")
        elif stats["overall_compliance"] >= 85.0:
            print(f"\nWARN  PARTIAL V7 COMPLIANCE")
            print(f"   Some regions need improvement")
        else:
            print(f"\nFAIL V7 COMPLIANCE NOT ACHIEVED")
            print(f"   Significant improvements needed")

        print("=" * 60)

        return {"results": results, "statistics": stats, "test_time": total_elapsed}

    def _calculate_overall_stats(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall statistics from test results."""
        total = len(results)
        excellent = sum(1 for r in results.values() if r.get("overall_status") == "EXCELLENT")
        passed = sum(1 for r in results.values() if r.get("overall_status") == "PASSED")
        partial = sum(1 for r in results.values() if r.get("overall_status") == "PARTIAL")
        failed = sum(1 for r in results.values() if r.get("overall_status") == "FAILED")
        errors = sum(1 for r in results.values() if r.get("overall_status") == "ERROR")

        # Calculate averages (excluding errors)
        valid_results = [r for r in results.values() if "security" in r and "edge_cases" in r]

        if valid_results:
            avg_security = sum(r["security"]["block_rate"] for r in valid_results) / len(
                valid_results
            )
            avg_edge_cases = sum(r["edge_cases"]["pass_rate"] for r in valid_results) / len(
                valid_results
            )
            overall_compliance = sum(r["overall_score"] for r in valid_results) / len(valid_results)
        else:
            avg_security = 0.0
            avg_edge_cases = 0.0
            overall_compliance = 0.0

        return {
            "total": total,
            "excellent": excellent,
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "errors": errors,
            "avg_security": avg_security,
            "avg_edge_cases": avg_edge_cases,
            "overall_compliance": overall_compliance,
        }


def main():
    """Main function to run V7 compliance test."""
    test_framework = V7ComplianceTest()
    results = test_framework.run_comprehensive_test()

    # Return exit code based on compliance
    overall_compliance = results["statistics"]["overall_compliance"]
    if overall_compliance >= 95.0:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Needs improvement


if __name__ == "__main__":
    main()
