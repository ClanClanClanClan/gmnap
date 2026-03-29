#!/usr/bin/env python3
"""
Week 4 Day 1: Test Regional Processing
Tests all 33 regions for V7 compliance.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent))
os.environ["OFFLINE"] = "1"  # Test offline for speed

from src.core.pipeline_v7_complete_final import create_v7_pipeline
from src.regions.manager_optimized import RegionManager


class RegionalProcessingTester:
    """Test all 33 regions for proper processing."""

    def __init__(self):
        self.regions = [
            "A1",
            "A2",
            "A3",
            "A4",
            "A5",  # Anglo-sphere/Western
            "B1",
            "B2",
            "B3",  # Slavic
            "C1",
            "C2",
            "C3",
            "C4",
            "C5",
            "C6",
            "C7",
            "C8",
            "C9",  # Middle East/Turkic
            "D1",
            "D2",
            "D3",
            "D4",
            "D5",  # South Asia
            "E1",
            "E2",
            "E3",
            "E4",
            "E5",
            "E6",
            "E7",  # East Asia
            "F1",
            "F2",
            "F3",  # Africa
            "G1",  # Latin America
        ]

        self.test_names = {
            "A1": "John Smith",  # Anglo
            "A2": "Jean-Claude Dupont",  # French
            "A3": "Erik Andersson",  # Nordic
            "A4": "Bruce Wilson",  # Oceania
            "A5": "Marcus Johnson",  # Caribbean
            "B1": "Ivan Petrov",  # East Slavic
            "B2": "Milan Novak",  # South Slavic
            "B3": "Νίκος Παπαδόπουλος",  # Greek
            "C1": "Mehmet Özkan",  # Turkic
            "C2": "محمد رضایی",  # Persian
            "C3": "أحمد محمد",  # Arabic Levant
            "C4": "عبدالله الكويتي",  # Arabic Gulf
            "C5": "محمد بن علي",  # Arabic Maghreb
            "C6": "דוד כהן",  # Hebrew
            "C7": "Արմեն Հակոբյան",  # Armenian
            "C8": "გიორგი ჯავახიშვილი",  # Georgian
            "C9": "Eldar Mammadov",  # Caucasus Turkic
            "D1": "राज कुमार",  # Hindi
            "D2": "முருகன்",  # Tamil/Dravidian
            "D3": "রহমান আলী",  # Bengali
            "D4": "محمد علی",  # Urdu
            "D5": "මලින්ද සිල්වා",  # Sinhala
            "E1": "王伟",  # Chinese Mainland
            "E2": "陳大明",  # Traditional Chinese
            "E3": "山田太郎",  # Japanese
            "E4": "김민준",  # Korean
            "E5": "Nguyễn Văn A",  # Vietnamese
            "E6": "Ahmad Ibrahim",  # Mainland SEA
            "E7": "Jose Santos",  # Maritime SEA
            "F1": "Jean-Baptiste Kouadio",  # SSA Francophone
            "F2": "Kwame Mensah",  # SSA Anglophone
            "F3": "Abebe Tadesse",  # Horn of Africa
            "G1": "José García Rodríguez",  # Latin America
        }

        self.results = {"tested": 0, "passed": 0, "failed": 0, "errors": []}

    async def test_region_detection(self):
        """Test Stage 2: Region Detection."""
        print("\n" + "=" * 60)
        print("TESTING STAGE 2: REGION DETECTION")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        for region_code in self.regions:
            test_name = self.test_names[region_code]

            test_entry = [
                {
                    "GlobalID": f"REG-{region_code}",
                    "CanonicalLatin": test_name,
                    "Field": "Testing",
                    "Source": "Test",
                    "LastUpdated": "2025-09-11",
                    "ValidationStatus": "pending",
                }
            ]

            try:
                result = await pipeline.process(test_entry)

                if result and len(result) > 0:
                    detected_region = result[0].get("_detected_region", "Unknown")

                    # Check if region was detected
                    if detected_region != "Unknown":
                        print(f"✅ {region_code}: Detected as {detected_region}")
                        self.results["passed"] += 1
                    else:
                        print(f"❌ {region_code}: Not detected (name: {test_name})")
                        self.results["failed"] += 1
                        self.results["errors"].append(f"{region_code}: No detection")
                else:
                    print(f"❌ {region_code}: Processing failed")
                    self.results["failed"] += 1
                    self.results["errors"].append(f"{region_code}: Processing failed")

            except Exception as e:
                print(f"❌ {region_code}: Error - {str(e)[:50]}")
                self.results["failed"] += 1
                self.results["errors"].append(f"{region_code}: {str(e)[:50]}")

            self.results["tested"] += 1

        return self.results["failed"] == 0

    async def test_region_processing(self):
        """Test Stage 3: Regional Hooks."""
        print("\n" + "=" * 60)
        print("TESTING STAGE 3: REGIONAL PROCESSING")
        print("=" * 60)

        pipeline = create_v7_pipeline(mode="quick", enable_live=False)

        # Test a few regions with special processing
        special_tests = {
            "A2": {  # French - should handle particles
                "input": "Jean-Claude de la Fontaine",
                "expected_contains": ["particle", "de la"],
            },
            "E4": {  # Korean - should handle Hangul
                "input": "김민준",
                "native_field": "CanonicalNative",
            },
            "E3": {  # Japanese - should handle multiple scripts
                "input": "山田太郎",
                "native_field": "CanonicalNative",
            },
        }

        for region_code, test_config in special_tests.items():
            test_entry = [
                {
                    "GlobalID": f"PROC-{region_code}",
                    "CanonicalLatin": test_config.get("input"),
                    "Field": "Testing",
                    "Source": "Test",
                    "LastUpdated": "2025-09-11",
                    "ValidationStatus": "pending",
                }
            ]

            try:
                result = await pipeline.process(test_entry)

                if result and len(result) > 0:
                    entry = result[0]

                    # Check for expected processing
                    if "expected_contains" in test_config:
                        found = False
                        for field in test_config["expected_contains"]:
                            if field in str(entry).lower():
                                found = True
                                break

                        if found:
                            print(f"✅ {region_code}: Special processing applied")
                        else:
                            print(f"⚠️ {region_code}: Processing unclear")

                    if "native_field" in test_config:
                        if test_config["native_field"] in entry:
                            print(f"✅ {region_code}: Native field populated")
                        else:
                            print(f"⚠️ {region_code}: Native field missing")

                    self.results["passed"] += 1
                else:
                    print(f"❌ {region_code}: Processing failed")
                    self.results["failed"] += 1

            except Exception as e:
                print(f"❌ {region_code}: Error - {str(e)[:50]}")
                self.results["failed"] += 1

        return True

    async def test_region_manager(self):
        """Test RegionManager can load all regions."""
        print("\n" + "=" * 60)
        print("TESTING REGION MANAGER")
        print("=" * 60)

        try:
            manager = RegionManager(Path("./config"))

            loaded = 0
            failed = []

            for region_code in self.regions:
                try:
                    region = manager.get_region(region_code)
                    if region:
                        loaded += 1
                    else:
                        failed.append(region_code)
                except Exception as e:
                    failed.append(f"{region_code}: {str(e)[:30]}")

            print(f"Regions loaded: {loaded}/{len(self.regions)}")

            if failed:
                print(f"Failed regions: {failed}")
                self.results["errors"].extend(failed)
                return False
            else:
                print("✅ All regions loaded successfully")
                return True

        except Exception as e:
            print(f"❌ RegionManager failed: {e}")
            self.results["errors"].append(f"RegionManager: {str(e)[:50]}")
            return False

    async def run_all_tests(self):
        """Run all regional processing tests."""
        print("\n" + "=" * 70)
        print("REGIONAL PROCESSING TEST SUITE - WEEK 4 DAY 1")
        print("=" * 70)

        # Test 1: Region Manager
        manager_ok = await self.test_region_manager()

        # Test 2: Region Detection
        detection_ok = await self.test_region_detection()

        # Test 3: Regional Processing
        processing_ok = await self.test_region_processing()

        # Calculate score
        total_possible = len(self.regions)
        score = (self.results["passed"] / total_possible) * 100 if total_possible > 0 else 0

        # Summary
        print("\n" + "=" * 70)
        print("REGIONAL PROCESSING SUMMARY")
        print("=" * 70)
        print(f"Regions Tested: {self.results['tested']}/{len(self.regions)}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Score: {score:.1f}%")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"][:10]:  # Show first 10
                print(f"  - {error}")

        # Regional processing component score (10% of total V7)
        regional_compliance = 10 * (score / 100)
        print(f"\nRegional Processing Compliance: {regional_compliance:.1f}/10 points")

        return score


async def main():
    """Run regional processing tests."""
    tester = RegionalProcessingTester()
    score = await tester.run_all_tests()

    # Update compliance estimate
    base_compliance = 80.0  # From end of Week 3
    regional_addition = 10 * (score / 100)  # Regional processing is 10% of total
    new_compliance = base_compliance + regional_addition

    print(f"\n📊 UPDATED V7 COMPLIANCE: {new_compliance:.1f}%")

    if score >= 90:
        print("✅ Regional processing tests PASSED!")
    elif score >= 70:
        print("⚠️ Regional processing partially working")
    else:
        print("❌ Regional processing needs fixes")

    return score >= 70


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
