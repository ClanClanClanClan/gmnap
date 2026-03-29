#!/usr/bin/env python3
"""
from typing import List
from typing import Any
ULTRATEST FINAL: Test ALL 37 regions from V7 spec.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.regions.base import RegionRuleError, REGION_CODES


class UltraFinalRegionTester:
    """Test all 37 regions defined in the V7 spec."""

    # All 37 regions from V7 spec
    ALL_REGIONS = {
        # A-Group (5)
        "A1": "Anglo Sphere",
        "A2": "Western Europe",
        "A3": "Nordic Baltic",
        "A4": "Oceania",
        "A5": "Caribbean",
        # B-Group (3)
        "B1": "East Slavic",
        "B2": "South Slavic Central",
        "B3": "Greek",
        # C-Group (9)
        "C1": "Turkic",
        "C2": "Persian Tajik",
        "C3": "Arabic Levant Nile",
        "C4": "Arabic Gulf",
        "C5": "Arabic Maghreb",
        "C6": "Hebrew Diaspora",
        "C7": "Armenian",
        "C8": "Georgian",
        "C9": "Caucasus Turkic",
        # D-Group (5)
        "D1": "South Asia Hindi Belt",
        "D2": "South Asia Dravidian",
        "D3": "South Asia Bengali",
        "D4": "Pakistan Urdu",
        "D5": "Sinhala",
        # E-Group (7)
        "E1": "Sinophone Mainland",
        "E2": "Traditional Chinese",
        "E3": "Japan",
        "E4": "Korea",
        "E5": "Vietnam",
        "E6": "Mainland SEA",
        "E7": "Maritime SEA",
        # F-Group (4)
        "F1": "SSA Francophone",
        "F2": "SSA Anglophone",
        "F3": "SSA Lusophone",
        "F4": "SSA Arabophone",
        # G-Group (1)
        "G1": "Latin America",
        # Special (3)
        "H1": "Indigenous Americas",
        "R0": "Global Diaspora",
        "Z0": "Unknown Region",
    }

    def __init__(self):
        self.results = {"summary": {}, "details": {}, "errors": [], "coverage": {}}

    def test_all_regions(self) -> Dict[str, Any]:
        """Test all 37 regions comprehensively."""
        print("🚀 ULTRATEST FINAL: TESTING ALL 37 REGIONS")
        print("=" * 60)

        print(f"Total regions in V7 spec: {len(self.ALL_REGIONS)}")

        # Test region loading
        print("\n📋 PHASE 1: REGION LOADING TEST")
        print("-" * 40)
        loaded_regions = self._test_region_loading()

        # Test basic processing
        print("\n🔧 PHASE 2: BASIC PROCESSING TEST")
        print("-" * 40)
        processing_results = self._test_basic_processing(loaded_regions)

        # Test edge cases
        print("\nWARN PHASE 3: EDGE CASE TESTING")
        print("-" * 40)
        edge_results = self._test_edge_cases(loaded_regions)

        # Test V7 compliance
        print("\n📊 PHASE 4: V7 COMPLIANCE CHECK")
        print("-" * 40)
        compliance_results = self._test_v7_compliance(loaded_regions)

        # Compile results
        self._compile_results(loaded_regions, processing_results, edge_results, compliance_results)

        return self.results

    def _test_region_loading(self) -> Dict[str, Any]:
        """Test that regions can be loaded."""
        loaded = {}

        # Try direct imports for each region
        for region_code, region_name in self.ALL_REGIONS.items():
            try:
                region = self._load_region(region_code)
                if region:
                    loaded[region_code] = region
                    print(f"PASS {region_code} ({region_name}): Loaded successfully")
                else:
                    print(f"FAIL {region_code} ({region_name}): Failed to load")
                    self.results["errors"].append(
                        {
                            "region": region_code,
                            "phase": "loading",
                            "error": "Failed to load region",
                        }
                    )
            except Exception as e:
                print(f"FAIL {region_code} ({region_name}): Loading error - {str(e)[:50]}...")
                self.results["errors"].append(
                    {"region": region_code, "phase": "loading", "error": str(e)}
                )

        print(f"\nLoaded: {len(loaded)}/{len(self.ALL_REGIONS)} regions")
        return loaded

    def _load_region(self, region_code: str):
        """Load a specific region."""
        import importlib

        # Define import paths for all regions
        region_imports = {
            # A-Group
            "A1": ("src.regions.a_groups.a1_anglo_sphere", "A1_AngloSphere"),
            "A2": ("src.regions.a_groups.a2_western_europe", "A2_WesternEurope"),
            "A3": ("src.regions.a_groups.a3_nordic_baltic.processor", "A3NordicBalticProcessor"),
            "A4": ("src.regions.a_groups.a4_oceania.processor", "A4OceaniaProcessor"),
            "A5": ("src.regions.a_groups.a5_caribbean.processor", "A5CaribbeanProcessor"),
            # B-Group
            "B1": ("src.regions.b_groups.b1_east_slavic", "B1_EastSlavic"),
            "B2": ("src.regions.b_groups.b2_south_slavic_central", "B2_SouthSlavicCentral"),
            "B3": ("src.regions.b_groups.b3_greek.processor", "B3GreekProcessor"),
            # C-Group
            "C1": ("src.regions.c_groups.c1_turkic.processor", "C1TurkicProcessor"),
            "C2": ("src.regions.c_groups.c2_persian_tajik", "C2_PersianTajik"),
            "C3": ("src.regions.c_groups.c3_arabic_levant_nile", "C3_ArabicLevantNile"),
            "C4": ("src.regions.c_groups.c4_arabic_gulf", "C4_ArabicGulf"),
            "C5": ("src.regions.c_groups.c5_arabic_maghreb", "C5_ArabicMaghreb"),
            "C6": ("src.regions.c_groups.c6_hebrew_diaspora", "C6_HebrewDiaspora"),
            "C7": ("src.regions.c_groups.c7_armenian", "C7_Armenian"),
            "C8": ("src.regions.c_groups.c8_georgian", "C8_Georgian"),
            "C9": ("src.regions.c_groups.c9_caucasus_turkic", "C9_CaucasusTurkic"),
            # D-Group
            "D1": ("src.regions.d_groups.d1_south_asia_hindi_belt", "D1_SouthAsiaHindiBelt"),
            "D2": ("src.regions.d_groups.d2_south_asia_dravidian", "D2_SouthAsiaDravidian"),
            "D3": ("src.regions.d_groups.d3_south_asia_bengali", "D3_SouthAsiaBengali"),
            "D4": ("src.regions.d_groups.d4_pakistan_urdu", "D4_PakistanUrdu"),
            "D5": ("src.regions.d_groups.d5_sinhala", "D5_Sinhala"),
            # E-Group
            "E1": ("src.regions.e_groups.e1_sinophone_mainland", "E1_SinophoneMainland"),
            "E2": ("src.regions.e_groups.e2_traditional_chinese", "E2_TraditionalChinese"),
            "E3": ("src.regions.e_groups.e3_japan", "E3_Japan"),
            "E4": ("src.regions.e_groups.e4_korea.processor_lightweight", "E4KoreanProcessor"),
            "E5": ("src.regions.e_groups.e5_vietnam", "E5_Vietnam"),
            "E6": ("src.regions.e_groups.e6_mainland_sea", "E6_MainlandSEA"),
            "E7": ("src.regions.e_groups.e7_maritime_sea", "E7_MaritimeSEA"),
            # F-Group
            "F1": ("src.regions.f_groups.f1_ssa_francophone", "F1_SSAFrancophone"),
            "F2": ("src.regions.f_groups.f2_ssa_anglophone", "F2_SSAAnglophone"),
            "F3": ("src.regions.f_groups.f3_ssa_lusophone", "F3_SSALusophone"),
            "F4": ("src.regions.f_groups.f4_ssa_arabophone", "F4_SSAArabophone"),
            # G-Group
            "G1": ("src.regions.g_groups.g1_latin_america", "G1_LatinAmerica"),
            # Special
            "H1": ("src.regions.special.h1_indigenous_americas", "H1_IndigenousAmericas"),
            "R0": ("src.regions.special.r0_global_diaspora", "R0_GlobalDiaspora"),
            "Z0": ("src.regions.special.z0_unknown_region", "Z0_UnknownRegion"),
        }

        if region_code not in region_imports:
            return None

        module_path, class_name = region_imports[region_code]

        try:
            module = importlib.import_module(module_path)
            region_class = getattr(module, class_name)
            return region_class()
        except Exception as e:
            raise Exception(f"Failed to load {region_code}: {e}")

    def _test_basic_processing(self, regions: Dict[str, Any]) -> Dict[str, bool]:
        """Test basic entry processing for each region."""
        results = {}

        # Test entries for different scripts
        test_entries = {
            "Latin": {"CanonicalLatin": "Smith, John", "CanonicalNative": ""},
            "Cyrillic": {"CanonicalLatin": "Petrov, Ivan", "CanonicalNative": "Петров, Иван"},
            "Arabic": {"CanonicalLatin": "Hassan, Ahmed", "CanonicalNative": "حسن، أحمد"},
            "CJK": {"CanonicalLatin": "Wang, Wei", "CanonicalNative": "王伟"},
            "Devanagari": {"CanonicalLatin": "Kumar, Raj", "CanonicalNative": "कुमार, राज"},
            "Greek": {
                "CanonicalLatin": "Papadopoulos, Nikos",
                "CanonicalNative": "Παπαδόπουλος, Νίκος",
            },
        }

        for region_code, region in regions.items():
            # Pick appropriate test entry
            if region_code in [
                "A1",
                "A2",
                "A3",
                "A4",
                "A5",
                "G1",
                "F1",
                "F2",
                "F3",
                "F4",
                "H1",
                "R0",
            ]:
                test_entry = test_entries["Latin"].copy()
            elif region_code in ["B1", "B2", "C9"]:
                test_entry = test_entries["Cyrillic"].copy()
            elif region_code == "B3":
                test_entry = test_entries["Greek"].copy()
            elif region_code in ["C2", "C3", "C4", "C5"]:
                test_entry = test_entries["Arabic"].copy()
            elif region_code in ["D1", "D2", "D3", "D4", "D5"]:
                test_entry = test_entries["Devanagari"].copy()
            elif region_code in ["E1", "E2", "E3"]:
                test_entry = test_entries["CJK"].copy()
            else:
                test_entry = test_entries["Latin"].copy()

            try:
                # Process through pipeline
                region.clean(test_entry)
                region.augment(test_entry)
                region.validate(test_entry)

                print(f"PASS {region_code}: Basic processing works")
                results[region_code] = True

            except Exception as e:
                print(f"FAIL {region_code}: Processing error - {str(e)[:50]}...")
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
            ("empty_both", {"CanonicalLatin": "", "CanonicalNative": ""}),
            ("single_char", {"CanonicalLatin": "X", "CanonicalNative": ""}),
            ("special_chars", {"CanonicalLatin": "O'Brien-Smith, Jr.", "CanonicalNative": ""}),
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
                    region_results[case_name] = True

                except RegionRuleError:
                    # Expected for some edge cases
                    region_results[case_name] = True

                except Exception as e:
                    region_results[case_name] = False
                    print(f"FAIL {region_code}: {case_name} - Unexpected error: {e}")

            results[region_code] = region_results

            # Summary
            passed = sum(region_results.values())
            total = len(region_results)
            if passed == total:
                print(f"PASS {region_code}: All {total} edge cases handled")
            else:
                print(f"WARN {region_code}: {passed}/{total} edge cases passed")

        return results

    def _test_v7_compliance(self, regions: Dict[str, Any]) -> Dict[str, Dict[str, bool]]:
        """Test V7 spec compliance for each region."""
        results = {}

        for region_code, region in regions.items():
            compliance = {
                "has_clean": hasattr(region, "clean"),
                "has_augment": hasattr(region, "augment"),
                "has_validate": hasattr(region, "validate"),
                "has_order_key": hasattr(region, "order_key"),
                "correct_code": hasattr(region, "code") and region.code == region_code,
            }

            results[region_code] = compliance

            if all(compliance.values()):
                print(f"PASS {region_code}: V7 compliant")
            else:
                missing = [k for k, v in compliance.items() if not v]
                print(f"WARN {region_code}: Missing {missing}")

        return results

    def _compile_results(self, loaded: Dict, processing: Dict, edge_cases: Dict, compliance: Dict):
        """Compile all test results."""
        total_regions = len(self.ALL_REGIONS)

        # Coverage analysis
        loaded_codes = set(loaded.keys())
        all_codes = set(self.ALL_REGIONS.keys())

        # Group analysis
        groups = {
            "A": ["A1", "A2", "A3", "A4", "A5"],
            "B": ["B1", "B2", "B3"],
            "C": ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"],
            "D": ["D1", "D2", "D3", "D4", "D5"],
            "E": ["E1", "E2", "E3", "E4", "E5", "E6", "E7"],
            "F": ["F1", "F2", "F3", "F4"],
            "G": ["G1"],
            "Special": ["H1", "R0", "Z0"],
        }

        group_coverage = {}
        for group_name, group_codes in groups.items():
            loaded_in_group = len([c for c in group_codes if c in loaded_codes])
            total_in_group = len(group_codes)
            group_coverage[group_name] = {
                "loaded": loaded_in_group,
                "total": total_in_group,
                "percentage": (loaded_in_group / total_in_group * 100) if total_in_group > 0 else 0,
            }

        # Summary statistics
        self.results["summary"] = {
            "total_regions": total_regions,
            "loaded": len(loaded),
            "processing_success": sum(processing.values()) if processing else 0,
            "all_edge_cases_pass": (
                sum(1 for region_results in edge_cases.values() if all(region_results.values()))
                if edge_cases
                else 0
            ),
            "v7_compliant": (
                sum(
                    1
                    for region_compliance in compliance.values()
                    if all(region_compliance.values())
                )
                if compliance
                else 0
            ),
            "perfect_regions": sum(
                1
                for region in loaded
                if processing.get(region, False)
                and all(edge_cases.get(region, {}).values())
                and all(compliance.get(region, {}).values())
            ),
        }

        self.results["coverage"] = {
            "by_group": group_coverage,
            "missing_regions": sorted(all_codes - loaded_codes),
        }

        # Detailed results
        self.results["details"] = {
            "loaded": sorted(list(loaded.keys())),
            "processing": processing,
            "edge_cases": edge_cases,
            "compliance": compliance,
        }


def main():
    """Run comprehensive test of all 37 regions."""
    tester = UltraFinalRegionTester()
    results = tester.test_all_regions()

    # Save results
    with open("ultratest_final_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print summary
    print("\n" + "=" * 60)
    print("📊 ULTRATEST FINAL SUMMARY")
    print("=" * 60)

    summary = results["summary"]
    print(f"Total regions in V7 spec: {summary['total_regions']}")
    print(
        f"Regions loaded: {summary['loaded']}/{summary['total_regions']} ({summary['loaded']/summary['total_regions']*100:.1f}%)"
    )
    print(f"Basic processing: {summary['processing_success']}/{summary['loaded']}")
    print(f"Edge cases pass: {summary['all_edge_cases_pass']}/{summary['loaded']}")
    print(f"V7 compliant: {summary['v7_compliant']}/{summary['loaded']}")
    print(f"PERFECT regions: {summary['perfect_regions']}/{summary['total_regions']}")

    # Group coverage
    print("\n📈 COVERAGE BY GROUP:")
    for group, stats in results["coverage"]["by_group"].items():
        print(f"  {group}: {stats['loaded']}/{stats['total']} ({stats['percentage']:.1f}%)")

    # Missing regions
    if results["coverage"]["missing_regions"]:
        print(f"\nWARN MISSING REGIONS ({len(results['coverage']['missing_regions'])}):")
        print(f"  {', '.join(results['coverage']['missing_regions'])}")

    # Final verdict
    print("\n" + "=" * 60)
    coverage_percent = summary["loaded"] / summary["total_regions"] * 100
    if coverage_percent == 100:
        print("🎉 ALL 37 REGIONS LOADED! 100% COVERAGE ACHIEVED!")
    elif coverage_percent >= 90:
        print(f"🚀 EXCELLENT! {coverage_percent:.1f}% coverage achieved!")
    elif coverage_percent >= 70:
        print(f"👍 GOOD! {coverage_percent:.1f}% coverage achieved!")
    else:
        print(
            f"🔧 {summary['total_regions'] - summary['loaded']} regions still need work ({coverage_percent:.1f}% coverage)"
        )

    return results


if __name__ == "__main__":
    main()
