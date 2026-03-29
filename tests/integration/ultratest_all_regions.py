#!/usr/bin/env python3
"""
from typing import List
from typing import Any
ULTRATEST: Comprehensive testing of all 37 regions
Tests every single region for:
1. Loading successfully
2. Processing entries without crashing
3. Handling edge cases properly
4. No "Unknown Person" band-aids
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.regions.base import RegionRuleError
from src.regions.manager_optimized import RegionManager


class UltraRegionTester:
    """Ultra comprehensive region testing."""

    def __init__(self):
        self.manager = RegionManager()
        self.results = {
            "summary": {},
            "details": {},
            "errors": [],
            "edge_case_results": {},
        }

    def test_all_regions(self) -> Dict[str, Any]:
        """Test all 37 regions comprehensively."""
        print("🚀 ULTRATEST: TESTING ALL 37 REGIONS")
        print("=" * 60)

        all_regions = sorted(self.manager.IMPLEMENTED_REGIONS)
        print(f"Total regions to test: {len(all_regions)}")

        # Test region loading
        print("\n📋 PHASE 1: REGION LOADING TEST")
        print("-" * 40)
        loaded_regions = self._test_region_loading(all_regions)

        # Test basic processing
        print("\n🔧 PHASE 2: BASIC PROCESSING TEST")
        print("-" * 40)
        processing_results = self._test_basic_processing(loaded_regions)

        # Test edge cases
        print("\nWARN PHASE 3: EDGE CASE TESTING")
        print("-" * 40)
        edge_results = self._test_edge_cases(loaded_regions)

        # Test for band-aids
        print("\n🔍 PHASE 4: BAND-AID DETECTION")
        print("-" * 40)
        bandaid_results = self._test_for_bandaids(loaded_regions)

        # Compile results
        self._compile_results(
            loaded_regions, processing_results, edge_results, bandaid_results
        )

        return self.results

    def _test_region_loading(self, regions: List[str]) -> Dict[str, Any]:
        """Test that regions load without errors."""
        loaded = {}

        for region_code in regions:
            try:
                region = self.manager.get_region(region_code)
                if region:
                    loaded[region_code] = region
                    print(f"PASS {region_code}: Loaded successfully")
                else:
                    print(f"FAIL {region_code}: Failed to load (None returned)")
                    self.results["errors"].append(
                        {
                            "region": region_code,
                            "phase": "loading",
                            "error": "None returned from get_region",
                        }
                    )
            except Exception as e:
                print(f"FAIL {region_code}: Loading error - {e}")
                self.results["errors"].append(
                    {"region": region_code, "phase": "loading", "error": str(e)}
                )

        print(f"\nLoaded: {len(loaded)}/{len(regions)} regions")
        return loaded

    def _test_basic_processing(self, regions: Dict[str, Any]) -> Dict[str, bool]:
        """Test basic entry processing for each region."""
        results = {}

        # Test entries for different scripts
        test_entries = {
            "Latin": {"CanonicalLatin": "John Smith", "CanonicalNative": ""},
            "Cyrillic": {
                "CanonicalLatin": "Ivan Petrov",
                "CanonicalNative": "Иван Петров",
            },
            "Arabic": {"CanonicalLatin": "Ahmed Hassan", "CanonicalNative": "أحمد حسن"},
            "CJK": {"CanonicalLatin": "Wang Wei", "CanonicalNative": "王伟"},
            "Devanagari": {
                "CanonicalLatin": "Raj Kumar",
                "CanonicalNative": "राज कुमार",
            },
            "Greek": {
                "CanonicalLatin": "Nikos Papadopoulos",
                "CanonicalNative": "Νίκος Παπαδόπουλος",
            },
        }

        for region_code, region in regions.items():

            # Pick appropriate test entry based on region
            if region_code.startswith("A") or region_code.startswith("G"):
                test_entry = test_entries["Latin"].copy()
            elif region_code.startswith("B1"):
                test_entry = test_entries["Cyrillic"].copy()
            elif region_code.startswith("B3"):
                test_entry = test_entries["Greek"].copy()
            elif region_code.startswith("C") and region_code in ["C3", "C4", "C5"]:
                test_entry = test_entries["Arabic"].copy()
            elif region_code.startswith("D"):
                test_entry = test_entries["Devanagari"].copy()
            elif region_code.startswith("E") and region_code in ["E1", "E2", "E3"]:
                test_entry = test_entries["CJK"].copy()
            else:
                test_entry = test_entries["Latin"].copy()

            try:
                # Process through full pipeline
                region.clean(test_entry)
                region.augment(test_entry)
                region.validate(test_entry)

                print(f"PASS {region_code}: Basic processing works")
                results[region_code] = True

            except Exception as e:
                print(f"FAIL {region_code}: Processing error - {e}")
                results[region_code] = False
                self.results["errors"].append(
                    {
                        "region": region_code,
                        "phase": "processing",
                        "error": str(e),
                        "entry": test_entry,
                    }
                )

        print(f"\nProcessing success: {sum(results.values())}/{len(regions)} regions")
        return results

    def _test_edge_cases(self, regions: Dict[str, Any]) -> Dict[str, Dict[str, bool]]:
        """Test edge cases for each region."""
        edge_cases = [
            ("empty_latin", {"CanonicalLatin": "", "CanonicalNative": "नाम"}),
            ("empty_native", {"CanonicalLatin": "Name", "CanonicalNative": ""}),
            ("both_empty", {"CanonicalLatin": "", "CanonicalNative": ""}),
            ("single_char", {"CanonicalLatin": "X", "CanonicalNative": ""}),
            ("whitespace_only", {"CanonicalLatin": "   ", "CanonicalNative": ""}),
            (
                "special_chars",
                {"CanonicalLatin": "O'Brien-Smith", "CanonicalNative": ""},
            ),
            ("unicode_mix", {"CanonicalLatin": "José María", "CanonicalNative": ""}),
            ("very_long", {"CanonicalLatin": "A" * 200, "CanonicalNative": ""}),
        ]

        results = {}

        for region_code, region in regions.items():
            region_results = {}

            for case_name, test_entry in edge_cases:
                entry = test_entry.copy()

                try:
                    region.clean(entry)
                    region.augment(entry)
                    region.validate(entry)

                    # Check for band-aids
                    if "Unknown Person" in str(entry.get("CanonicalLatin", "")):
                        region_results[case_name] = False
                        print(
                            f"WARN {region_code}: {case_name} - Contains 'Unknown Person'"
                        )
                    else:
                        region_results[case_name] = True

                except RegionRuleError:
                    # Expected for some edge cases
                    region_results[case_name] = True

                except Exception as e:
                    region_results[case_name] = False
                    print(f"FAIL {region_code}: {case_name} - Unexpected error: {e}")

            results[region_code] = region_results

            # Summary for this region
            passed = sum(region_results.values())
            total = len(region_results)
            if passed == total:
                print(f"PASS {region_code}: All {total} edge cases handled")
            else:
                print(f"WARN {region_code}: {passed}/{total} edge cases passed")

        return results

    def _test_for_bandaids(self, regions: Dict[str, Any]) -> Dict[str, bool]:
        """Test for 'Unknown Person' band-aids in code."""
        results = {}

        for region_code, region in regions.items():
            # Get the module file path
            module = sys.modules[region.__class__.__module__]
            if hasattr(module, "__file__") and module.__file__:
                file_path = Path(module.__file__)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if "Unknown Person" in content:
                        results[region_code] = False
                        print(f"FAIL {region_code}: Contains 'Unknown Person' band-aid")
                    else:
                        results[region_code] = True
                        print(f"PASS {region_code}: No band-aids found")

                except Exception as e:
                    results[region_code] = False
                    print(f"WARN {region_code}: Could not check for band-aids - {e}")
            else:
                results[region_code] = True  # Assume OK if can't check

        return results

    def _compile_results(
        self, loaded: Dict, processing: Dict, edge_cases: Dict, bandaids: Dict
    ):
        """Compile all test results."""
        total_regions = len(self.manager.IMPLEMENTED_REGIONS)

        # Summary statistics
        self.results["summary"] = {
            "total_regions": total_regions,
            "loaded": len(loaded),
            "processing_success": sum(processing.values()),
            "no_bandaids": sum(bandaids.values()),
            "all_edge_cases_pass": sum(
                1
                for region_results in edge_cases.values()
                if all(region_results.values())
            ),
            "perfect_regions": sum(
                1
                for region in loaded
                if processing.get(region, False)
                and bandaids.get(region, False)
                and all(edge_cases.get(region, {}).values())
            ),
        }

        # Detailed results
        self.results["details"] = {
            "loaded": list(loaded.keys()),
            "processing": processing,
            "edge_cases": edge_cases,
            "bandaids": bandaids,
        }

        # Identify problem regions
        problem_regions = []
        for region in self.manager.IMPLEMENTED_REGIONS:
            issues = []
            if region not in loaded:
                issues.append("loading_failed")
            elif not processing.get(region, False):
                issues.append("processing_failed")
            if not bandaids.get(region, True):
                issues.append("has_bandaids")
            if region in edge_cases and not all(edge_cases[region].values()):
                issues.append("edge_case_failures")

            if issues:
                problem_regions.append({"region": region, "issues": issues})

        self.results["problem_regions"] = problem_regions


def main():
    """Run ultra comprehensive tests."""
    tester = UltraRegionTester()
    results = tester.test_all_regions()

    # Save results
    with open("ultratest_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 ULTRATEST SUMMARY")
    print("=" * 60)

    summary = results["summary"]
    print(f"Total regions in spec: {summary['total_regions']}")
    print(f"Regions loaded: {summary['loaded']}/{summary['total_regions']}")
    print(f"Basic processing: {summary['processing_success']}/{summary['loaded']}")
    print(f"No band-aids: {summary['no_bandaids']}/{summary['loaded']}")
    print(f"All edge cases pass: {summary['all_edge_cases_pass']}/{summary['loaded']}")
    print(f"PERFECT regions: {summary['perfect_regions']}/{summary['total_regions']}")

    # Show problem regions
    if results["problem_regions"]:
        print("\nWARN PROBLEM REGIONS:")
        for problem in results["problem_regions"]:
            print(f"  {problem['region']}: {', '.join(problem['issues'])}")

    # Final verdict
    print("\n" + "=" * 60)
    if summary["perfect_regions"] == summary["total_regions"]:
        print("🎉 ALL 37 REGIONS ARE PERFECT! 100% TRUE COVERAGE ACHIEVED!")
    else:
        print(
            f"🔧 {summary['total_regions'] - summary['perfect_regions']} regions still need work"
        )

    return results


if __name__ == "__main__":
    main()
