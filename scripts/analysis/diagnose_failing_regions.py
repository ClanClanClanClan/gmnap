#!/usr/bin/env python3
"""
Diagnostic script for the 4 failing V7 compliance regions.

Diagnoses specific failures in:
- E2: Traditional Chinese (0% compliance - critical issue)
- F1: SSA Francophone (0% compliance - critical issue)
- A3: Nordic Baltic (93.4% compliance - needs minor fixes)
- B3: Greek (93.4% compliance - needs minor fixes)
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import traceback

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.regions.manager import RegionManager


class RegionDiagnostic:
    """Diagnostic tool for failing V7 regions."""

    def __init__(self):
        self.manager = RegionManager(Path("./config"))

        # Test cases from the comprehensive test
        self.security_attacks = [
            {"name": "NULL character", "input": "Test\x00Malicious"},
            {"name": "DELETE character", "input": "Test\x7f"},
            {"name": "Zero-width space", "input": "Test\u200b"},
            {"name": "DoS length attack", "input": "A" * 200},
        ]

        self.edge_cases = [
            {
                "name": "Single char A",
                "test": {"CanonicalLatin": "A", "GlobalID": "edge-1"},
            },
            {
                "name": "Single char X",
                "test": {"CanonicalLatin": "X", "GlobalID": "edge-2"},
            },
            {
                "name": "Empty Latin field",
                "test": {
                    "CanonicalLatin": "",
                    "CanonicalNative": "Test Native",
                    "GlobalID": "edge-3",
                },
            },
            {"name": "Missing canonical", "test": {"GlobalID": "edge-4"}},
            {
                "name": "Complex hyphenated",
                "test": {
                    "CanonicalLatin": "Jean-Claude Van Damme-O'Connor Jr.",
                    "GlobalID": "edge-5",
                },
            },
        ]

    def diagnose_region(self, region_code: str) -> Dict[str, Any]:
        """Diagnose a specific region's failures."""
        print(f"\n🔍 DIAGNOSING REGION {region_code}")
        print("=" * 40)

        try:
            region = self.manager.get_region(region_code)
            if not region:
                return {
                    "status": "CRITICAL",
                    "error": "Region not loaded",
                    "details": "RegionManager.get_region() returned None",
                }
        except Exception as e:
            return {
                "status": "CRITICAL",
                "error": f"Failed to load region: {str(e)}",
                "details": traceback.format_exc(),
            }

        results = {
            "region_code": region_code,
            "security_failures": [],
            "edge_case_failures": [],
            "method_errors": {},
        }

        # Test each V7 method individually
        print("🛠️  Testing V7 methods individually...")
        test_entry = {"CanonicalLatin": "Test Name", "GlobalID": "diagnostic-test"}

        for method_name in ["clean", "augment", "validate", "order_key"]:
            print(f"  Testing {method_name}()...")
            try:
                method = getattr(region, method_name)
                if method_name == "order_key":
                    result = method(test_entry)
                    print(f"    ✅ {method_name}() returned: {repr(result)}")
                else:
                    method(test_entry.copy())
                    print(f"    ✅ {method_name}() completed successfully")
            except Exception as e:
                error_msg = str(e)
                results["method_errors"][method_name] = error_msg
                print(f"    ❌ {method_name}() failed: {error_msg}")

        # Test security compliance
        print("\n🛡️  Testing security attacks...")
        for attack in self.security_attacks:
            attack_entry = {
                "CanonicalLatin": attack["input"],
                "GlobalID": "security-test",
            }

            try:
                # Test all methods
                region.clean(attack_entry)
                region.augment(attack_entry)
                region.validate(attack_entry)
                region.order_key(attack_entry)

                # If we reach here, attack was not blocked
                results["security_failures"].append(
                    {
                        "attack": attack["name"],
                        "input": repr(attack["input"]),
                        "status": "BYPASSED",
                    }
                )
                print(f"  ❌ {attack['name']}: BYPASSED")

            except Exception as e:
                # Attack was blocked (good)
                print(f"  ✅ {attack['name']}: BLOCKED ({str(e)[:50]})")

        # Test edge cases
        print("\n🎯 Testing edge cases...")
        for case in self.edge_cases:
            try:
                entry = case["test"].copy()
                region.clean(entry)
                region.augment(entry)
                region.validate(entry)
                key = region.order_key(entry)

                # Success
                print(f"  ✅ {case['name']}: PASSED")

            except Exception as e:
                # Edge case failed
                error_msg = str(e)
                results["edge_case_failures"].append(
                    {
                        "case": case["name"],
                        "test": case["test"],
                        "error": error_msg,
                        "status": "FAILED",
                    }
                )
                print(f"  ❌ {case['name']}: FAILED - {error_msg}")

        # Summary
        security_blocks = len(self.security_attacks) - len(results["security_failures"])
        security_rate = 100 * security_blocks / len(self.security_attacks)

        edge_passes = len(self.edge_cases) - len(results["edge_case_failures"])
        edge_rate = 100 * edge_passes / len(self.edge_cases)

        print(f"\n📊 DIAGNOSTIC SUMMARY:")
        print(
            f"  Security: {security_blocks}/{len(self.security_attacks)} blocked ({security_rate:.1f}%)"
        )
        print(
            f"  Edge cases: {edge_passes}/{len(self.edge_cases)} passed ({edge_rate:.1f}%)"
        )
        print(f"  Method errors: {len(results['method_errors'])}/4 methods broken")

        results.update(
            {
                "security_rate": security_rate,
                "edge_rate": edge_rate,
                "methods_broken": len(results["method_errors"]),
            }
        )

        return results

    def run_diagnostic(self):
        """Run diagnostic on the 4 failing regions."""
        print("🚨 V7 COMPLIANCE DIAGNOSTIC")
        print("=" * 60)
        print("Diagnosing 4 regions with compliance issues:")
        print("- E2: Traditional Chinese (0% compliance)")
        print("- F1: SSA Francophone (0% compliance)")
        print("- A3: Nordic Baltic (93.4% compliance)")
        print("- B3: Greek (93.4% compliance)")

        failing_regions = ["E2", "F1", "A3", "B3"]
        all_results = {}

        for region_code in failing_regions:
            try:
                result = self.diagnose_region(region_code)
                all_results[region_code] = result
            except Exception as e:
                print(f"\n💥 CRITICAL ERROR diagnosing {region_code}: {str(e)}")
                all_results[region_code] = {"status": "CRITICAL_ERROR", "error": str(e)}

        # Overall analysis
        print("\n" + "=" * 60)
        print("🎯 DIAGNOSTIC RESULTS ANALYSIS")
        print("=" * 60)

        critical_regions = []
        fixable_regions = []

        for region_code, result in all_results.items():
            if (
                result.get("status") == "CRITICAL"
                or result.get("methods_broken", 0) > 0
            ):
                critical_regions.append(region_code)
                print(
                    f"🚨 CRITICAL: {region_code} - {result.get('error', 'Method failures detected')}"
                )
            else:
                fixable_regions.append(region_code)
                print(
                    f"🔧 FIXABLE: {region_code} - Minor security/edge case improvements needed"
                )

        print(f"\n📊 PRIORITY ASSESSMENT:")
        print(
            f"  🚨 Critical (method failures): {len(critical_regions)} regions - {critical_regions}"
        )
        print(
            f"  🔧 Fixable (compliance tuning): {len(fixable_regions)} regions - {fixable_regions}"
        )

        if critical_regions:
            print(f"\n⚡ IMMEDIATE ACTION REQUIRED:")
            print(f"   Fix method failures in {critical_regions} first")
            print(f"   Then address security/edge case compliance in {fixable_regions}")
        else:
            print(f"\n✅ NO CRITICAL FAILURES:")
            print(f"   All regions have working methods")
            print(f"   Focus on improving security/edge case compliance")

        return all_results


def main():
    """Main diagnostic function."""
    diagnostic = RegionDiagnostic()
    results = diagnostic.run_diagnostic()

    # Exit code based on severity
    critical_count = sum(
        1
        for r in results.values()
        if r.get("status") == "CRITICAL" or r.get("methods_broken", 0) > 0
    )
    if critical_count > 0:
        print(f"\n🚨 DIAGNOSTIC COMPLETE: {critical_count} critical issues found")
        sys.exit(1)
    else:
        print(f"\n✅ DIAGNOSTIC COMPLETE: No critical issues, compliance tuning needed")
        sys.exit(0)


if __name__ == "__main__":
    main()
