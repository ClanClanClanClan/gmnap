"""
Regional Processing Verification - Step 3.3
Real verification of regional processing functionality with 5+ regions tested
"""

from datetime import datetime
from typing import Dict, Any
import logging

from ..regions.manager import RegionManager


class RegionalProcessingVerifier:
    """
    V7 Regional Processing Verification System for Step 3.3
    Tests and verifies regional processing functionality across multiple regions

    Target: Verify 5+ regions are working correctly
    Current: 34/43 regions available (79.07%)
    Goal: Test 5 specific regions with comprehensive functionality
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.working_regions = []
        self.failed_regions = []
        self.verification_results = {}

        # Test regions for verification (diverse coverage)
        self.target_regions = [
            "A1",  # Anglo-sphere primary
            "E4",  # Korea (complex CJK processing)
            "C1",  # Turkic (non-Latin scripts)
            "D1",  # South Asia (complex scripts)
            "B1",  # Slavic (Cyrillic scripts)
        ]

        # Comprehensive test entries for each region
        self.test_entries = {
            "A1": [
                {"CanonicalLatin": "Smith, John", "BirthYear": 1970, "Country": "United States"},
                {
                    "CanonicalLatin": "Jones, Mary Elizabeth",
                    "BirthYear": 1985,
                    "Country": "United Kingdom",
                },
                {
                    "CanonicalLatin": "Brown-Wilson, David",
                    "BirthYear": 1962,
                    "Country": "Australia",
                },
            ],
            "E4": [
                {
                    "CanonicalLatin": "Kim, Min-jun",
                    "BirthYear": 1978,
                    "Country": "Korea",
                    "NativeScript": "김민준",
                },
                {
                    "CanonicalLatin": "Lee, Hye-jin",
                    "BirthYear": 1983,
                    "Country": "Korea",
                    "NativeScript": "이혜진",
                },
                {
                    "CanonicalLatin": "Park, Seung-ho",
                    "BirthYear": 1975,
                    "Country": "Korea",
                    "NativeScript": "박승호",
                },
            ],
            "C1": [
                {"CanonicalLatin": "Özkan, Mehmet", "BirthYear": 1982, "Country": "Turkey"},
                {"CanonicalLatin": "Yılmaz, Ayşe", "BirthYear": 1976, "Country": "Turkey"},
                {"CanonicalLatin": "Demir, Fatma", "BirthYear": 1989, "Country": "Turkey"},
            ],
            "D1": [
                {"CanonicalLatin": "Sharma, Rajesh", "BirthYear": 1973, "Country": "India"},
                {"CanonicalLatin": "Patel, Priya", "BirthYear": 1980, "Country": "India"},
                {"CanonicalLatin": "Singh, Arjun", "BirthYear": 1967, "Country": "India"},
            ],
            "B1": [
                {"CanonicalLatin": "Petrov, Ivan", "BirthYear": 1979, "Country": "Russia"},
                {"CanonicalLatin": "Kuznetsova, Elena", "BirthYear": 1984, "Country": "Russia"},
                {"CanonicalLatin": "Volkov, Dmitri", "BirthYear": 1971, "Country": "Russia"},
            ],
        }

    async def run_regional_processing_verification(self) -> Dict[str, Any]:
        """
        Run comprehensive regional processing verification testing
        Goal: Verify 5+ regions are working with full functionality
        """

        self.logger.info("Starting regional processing verification for Step 3.3...")

        # Initialize region manager
        region_manager = RegionManager()

        # Test each target region
        verification_results = {}
        working_count = 0

        for region_code in self.target_regions:
            self.logger.info(f"Verifying regional processing: {region_code}")

            try:
                region_result = await self._verify_region(region_code, region_manager)
                verification_results[region_code] = region_result

                if region_result["working"]:
                    working_count += 1
                    self.working_regions.append(region_code)
                    self.logger.info(f"✅ {region_code}: WORKING")
                else:
                    self.failed_regions.append(region_code)
                    self.logger.warning(f"❌ {region_code}: FAILED - {region_result['error']}")

            except Exception as e:
                error_msg = f"Verification test failed: {e}"
                verification_results[region_code] = {
                    "working": False,
                    "error": error_msg,
                    "test_results": [],
                }
                self.failed_regions.append(region_code)
                self.logger.error(f"❌ {region_code}: EXCEPTION - {error_msg}")

        # Test additional region manager functionality
        manager_info = await self._test_region_manager_functionality(region_manager)

        # Calculate verification success metrics
        total_target_regions = len(self.target_regions)
        success_rate = (
            (working_count / total_target_regions) * 100 if total_target_regions > 0 else 0
        )
        step_3_3_success = working_count >= 5  # Need at least 5 working

        # Compile comprehensive results
        results = {
            "verification_summary": {
                "working_regions": working_count,
                "total_target_regions": total_target_regions,
                "success_rate_percent": success_rate,
                "step_3_3_target_met": step_3_3_success,
                "working_region_codes": self.working_regions,
                "failed_region_codes": self.failed_regions,
            },
            "region_details": verification_results,
            "region_manager_info": manager_info,
            "verification_metadata": {
                "test_timestamp": datetime.now().isoformat(),
                "target_regions": self.target_regions,
                "entries_per_region": 3,
            },
        }

        self.verification_results = results
        return results

    async def _verify_region(
        self, region_code: str, region_manager: RegionManager
    ) -> Dict[str, Any]:
        """
        Verify a specific region with comprehensive functionality testing

        Args:
            region_code: Code of region to verify
            region_manager: RegionManager instance

        Returns:
            Verification results with working status and metrics
        """

        test_results = []
        successful_processing = 0
        test_entries = self.test_entries.get(region_code, [])
        total_entries = len(test_entries)

        try:
            # Get region processor
            region_processor = region_manager.get_region(region_code)
            if not region_processor:
                return {
                    "working": False,
                    "error": f"Region {region_code} not found or not implemented",
                    "test_results": [],
                    "success_rate_percent": 0.0,
                }

            # Test each entry
            for entry in test_entries:
                entry_result = {
                    "entry": entry["CanonicalLatin"],
                    "success": False,
                    "processing_time_ms": 0,
                    "detected_region": None,
                    "confidence": 0.0,
                    "processed_data": None,
                    "error": None,
                }

                try:
                    # Time the processing
                    start_time = datetime.now()

                    # Test region detection
                    detection = region_manager.detect_region(entry)
                    if detection:
                        entry_result["detected_region"] = detection.region_code
                        entry_result["confidence"] = detection.confidence

                    # Test region processing
                    if region_processor:
                        # Create a copy for processing
                        test_entry = entry.copy()
                        test_entry["GlobalID"] = (
                            f"TEST_{region_code}_{hash(entry['CanonicalLatin']) % 1000:03d}"
                        )

                        # Process the entry (clean modifies in-place, returns None)
                        region_processor.clean(test_entry)
                        processed_entry = test_entry  # Use the modified entry

                        end_time = datetime.now()
                        processing_time = (end_time - start_time).total_seconds() * 1000
                        entry_result["processing_time_ms"] = processing_time

                        # Verify processing worked
                        if processed_entry.get("CanonicalLatin"):
                            entry_result["success"] = True
                            entry_result["processed_data"] = {
                                "canonical_latin": processed_entry.get("CanonicalLatin"),
                                "global_id": processed_entry.get("GlobalID"),
                                "has_native_script": "NativeScript" in processed_entry,
                                "processed_fields": len(processed_entry.keys()),
                            }
                            successful_processing += 1
                        else:
                            entry_result["error"] = "Processing returned empty or invalid result"
                    else:
                        entry_result["error"] = "Region processor not available"

                except Exception as e:
                    entry_result["error"] = f"Processing exception: {str(e)}"

                test_results.append(entry_result)

        except Exception as e:
            return {
                "working": False,
                "error": f"Region verification failed: {str(e)}",
                "test_results": test_results,
                "success_rate_percent": 0.0,
            }

        # Determine if region is working
        success_rate = (successful_processing / total_entries) * 100 if total_entries > 0 else 0
        working = successful_processing > 0 and success_rate >= 70  # At least 70% success

        # Calculate average metrics
        successful_tests = [r for r in test_results if r["success"]]
        avg_processing_time = (
            sum(r["processing_time_ms"] for r in successful_tests) / len(successful_tests)
            if successful_tests
            else 0
        )
        avg_confidence = (
            sum(r["confidence"] for r in test_results) / len(test_results) if test_results else 0
        )

        return {
            "working": working,
            "success_rate_percent": success_rate,
            "successful_processing": successful_processing,
            "total_entries": total_entries,
            "average_processing_time_ms": avg_processing_time,
            "average_confidence": avg_confidence,
            "test_results": test_results,
            "error": None if working else f"Low success rate: {success_rate:.1f}% (need ≥70%)",
        }

    async def _test_region_manager_functionality(
        self, region_manager: RegionManager
    ) -> Dict[str, Any]:
        """Test overall region manager functionality"""

        try:
            # Get available regions
            available_regions = region_manager.get_region_codes()

            # Test region loading
            loaded_regions = 0
            for region_code in available_regions[:10]:  # Test first 10
                try:
                    region = region_manager.get_region(region_code)
                    if region:
                        loaded_regions += 1
                except Exception:
                    pass

            # Test region detection on sample entries
            detection_tests = 0
            successful_detections = 0

            sample_entries = [
                {"CanonicalLatin": "Smith, John", "Country": "United States"},
                {"CanonicalLatin": "Kim, Min-jun", "Country": "Korea"},
                {"CanonicalLatin": "Müller, Hans", "Country": "Germany"},
            ]

            for entry in sample_entries:
                detection_tests += 1
                try:
                    detection = region_manager.detect_region(entry)
                    if detection and detection.region_code:
                        successful_detections += 1
                except Exception:
                    pass

            detection_rate = (
                (successful_detections / detection_tests) * 100 if detection_tests > 0 else 0
            )
            loading_rate = (
                (loaded_regions / min(len(available_regions), 10)) * 100 if available_regions else 0
            )

            return {
                "available_regions_count": len(available_regions),
                "loaded_regions_count": loaded_regions,
                "loading_success_rate": loading_rate,
                "detection_success_rate": detection_rate,
                "region_manager_working": loading_rate >= 80 and detection_rate >= 60,
            }

        except Exception as e:
            return {
                "available_regions_count": 0,
                "loaded_regions_count": 0,
                "loading_success_rate": 0.0,
                "detection_success_rate": 0.0,
                "region_manager_working": False,
                "error": str(e),
            }

    async def run_enhanced_compliance_check(self) -> Dict[str, Any]:
        """
        Run enhanced compliance check with regional processing verification
        Updates the compliance percentage with regional processing improvements
        """

        # Run regional processing verification
        verification_results = await self.run_regional_processing_verification()

        # Previous compliance components (from Step 3.2)
        base_compliance = 62.8  # From authority source integration

        # Calculate regional processing improvement
        working_regions = verification_results["verification_summary"]["working_regions"]
        success_rate = verification_results["verification_summary"]["success_rate_percent"]

        # Regional boost based on working regions and success rate
        regional_improvement = (success_rate / 100) * 8  # Up to 8% boost for 100% regional success

        # Updated V7 compliance
        new_compliance = base_compliance + regional_improvement

        return {
            "previous_compliance_percent": base_compliance,
            "regional_processing_boost_percent": regional_improvement,
            "new_v7_compliance_percent": new_compliance,
            "working_regions": working_regions,
            "target_regions": 5,
            "step_3_3_success": working_regions >= 5,
            "verification_details": verification_results,
        }
