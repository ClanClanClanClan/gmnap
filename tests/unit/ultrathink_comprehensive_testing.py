#!/usr/bin/env python3
"""
from typing import List
from typing import Optional
from typing import Any
ULTRATHINK COMPREHENSIVE TESTING FRAMEWORK
Real-world mathematician testing for GMNAP v7 system.

This replaces synthetic testing with real mathematician names to expose
actual linguistic patterns, romanization issues, and performance bottlenecks.
"""

import sys
import time
import json
import logging
import traceback
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple, Optional
import tempfile
import yaml

sys.path.insert(0, str(Path(__file__).parent))

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Individual test result."""

    test_name: str
    mathematician_name: str
    expected_region: str
    actual_region: str
    passed: bool
    variants_generated: int
    processing_time: float
    error_message: Optional[str] = None
    linguistic_features_tested: List[str] = None


class UltrathinkTester:
    """Comprehensive testing framework using real mathematician data."""

    def __init__(self):
        self.results: List[TestResult] = []
        self.dataset: Dict[str, Any] = {}
        self.load_mathematician_dataset()

    def load_mathematician_dataset(self):
        """Load the real mathematician dataset."""
        dataset_path = Path("mathematician_test_dataset.json")
        if not dataset_path.exists():
            raise FileNotFoundError(
                "Mathematician dataset not found. Run the dataset creation task first."
            )

        with open(dataset_path, "r", encoding="utf-8") as f:
            self.dataset = json.load(f)

        print(
            f"📚 Loaded {self.dataset['dataset_metadata']['total_entries']} real mathematicians"
        )
        print(f"🌍 Regions: {len(self.dataset['dataset_metadata']['regions_covered'])}")

    def test_1_real_mathematician_classification(self):
        """Test 1: Real mathematician regional classification accuracy."""
        print("\n🧪 TEST 1: Real Mathematician Classification")
        print("=" * 60)

        try:
            from src.regions.manager_optimized import RegionManager

            manager = RegionManager()
            manager._ensure_regions_loaded()

            total_tests = 0
            correct_classifications = 0
            region_accuracy = {}

            # Test each region with real mathematician names
            for region_name, mathematicians in self.dataset["test_data"].items():
                region_code = self._region_name_to_code(region_name)
                if not region_code:
                    continue

                region_correct = 0
                region_total = 0

                print(f"\n🔬 Testing {region_name} ({region_code}):")

                for mathematician in mathematicians[:10]:  # Test first 10 per region
                    name = mathematician["romanized_primary"]
                    expected_region = region_code

                    try:
                        # Test with primary romanization
                        start_time = time.time()
                        detection_result = manager.detect_region(
                            {"CanonicalLatin": name}
                        )
                        processing_time = time.time() - start_time

                        if hasattr(detection_result, "region_code"):
                            actual_region = detection_result.region_code
                        else:
                            actual_region = str(detection_result)

                        passed = actual_region == expected_region
                        if passed:
                            correct_classifications += 1
                            region_correct += 1

                        # Test alternative romanizations
                        alt_variants = 0
                        for alt_name in mathematician.get(
                            "alternative_romanizations", []
                        ):
                            try:
                                alt_result = manager.detect_region(
                                    {"CanonicalLatin": alt_name}
                                )
                                if hasattr(alt_result, "region_code"):
                                    alt_region = alt_result.region_code
                                else:
                                    alt_region = str(alt_result)
                                if alt_region == expected_region:
                                    alt_variants += 1
                            except:
                                pass

                        result = TestResult(
                            test_name="mathematician_classification",
                            mathematician_name=name,
                            expected_region=expected_region,
                            actual_region=actual_region,
                            passed=passed,
                            variants_generated=alt_variants,
                            processing_time=processing_time,
                            linguistic_features_tested=mathematician.get(
                                "linguistic_features", []
                            ),
                        )
                        self.results.append(result)

                        status = "PASS" if passed else "FAIL"
                        print(
                            f"  {status} {name} -> {actual_region} (expected {expected_region})"
                        )

                        total_tests += 1
                        region_total += 1

                    except Exception as e:
                        error_result = TestResult(
                            test_name="mathematician_classification",
                            mathematician_name=name,
                            expected_region=expected_region,
                            actual_region="ERROR",
                            passed=False,
                            variants_generated=0,
                            processing_time=0.0,
                            error_message=str(e),
                        )
                        self.results.append(error_result)
                        total_tests += 1
                        region_total += 1
                        print(f"  FAIL {name} -> ERROR: {e}")

                region_accuracy[region_name] = (
                    region_correct / region_total if region_total > 0 else 0
                )
                print(
                    f"  📊 {region_name}: {region_correct}/{region_total} ({region_accuracy[region_name]:.1%})"
                )

            overall_accuracy = (
                correct_classifications / total_tests if total_tests > 0 else 0
            )
            print(
                f"\n📊 OVERALL CLASSIFICATION ACCURACY: {correct_classifications}/{total_tests} ({overall_accuracy:.1%})"
            )

            # Detailed accuracy report
            print(f"\n📈 PER-REGION ACCURACY:")
            for region, accuracy in sorted(region_accuracy.items()):
                status = (
                    "PASS"
                    if accuracy >= 0.8
                    else ("WARN" if accuracy >= 0.6 else "FAIL")
                )
                print(f"  {status} {region}: {accuracy:.1%}")

            return overall_accuracy >= 0.75  # 75% threshold for real names

        except Exception as e:
            print(f"FAIL TEST 1 FAILED: {e}")
            traceback.print_exc()
            return False

    def test_2_linguistic_feature_validation(self):
        """Test 2: Validate specific linguistic features work correctly."""
        print("\n🧪 TEST 2: Linguistic Feature Validation")
        print("=" * 60)

        try:
            from src.regions.manager_optimized import RegionManager

            manager = RegionManager()
            manager._ensure_regions_loaded()

            feature_tests = {
                "patronymic": [],
                "romanization_variants": [],
                "diacritics": [],
                "name_order": [],
                "compound_names": [],
            }

            # Collect mathematicians with specific linguistic features
            for region_name, mathematicians in self.dataset["test_data"].items():
                region_code = self._region_name_to_code(region_name)
                if not region_code or region_code not in manager._regions:
                    continue

                processor = manager._regions[region_code]

                for mathematician in mathematicians[:5]:  # Test 5 per region
                    features = mathematician.get("linguistic_features", [])
                    name = mathematician["romanized_primary"]

                    try:
                        # Test processing
                        test_entry = {"CanonicalLatin": name}
                        processor.clean(test_entry)
                        processor.augment(test_entry)

                        # Check for variants generation
                        variants = test_entry.get("Variants", {}).get("Synthesised", [])
                        has_variants = len(variants) > 0

                        # Test specific features
                        if "patronymic" in features or "patronymic_surname" in features:
                            feature_tests["patronymic"].append(
                                (name, has_variants, region_code)
                            )

                        if (
                            "alternative_romanizations" in mathematician
                            and mathematician["alternative_romanizations"]
                        ):
                            feature_tests["romanization_variants"].append(
                                (name, has_variants, region_code)
                            )

                        if any("diacritic" in f or "accent" in f for f in features):
                            feature_tests["diacritics"].append(
                                (name, has_variants, region_code)
                            )

                        if "compound" in str(features):
                            feature_tests["compound_names"].append(
                                (name, has_variants, region_code)
                            )

                    except Exception as e:
                        print(f"  FAIL Error processing {name}: {e}")

            # Analyze feature test results
            feature_success = {}
            for feature, tests in feature_tests.items():
                if tests:
                    successful = sum(1 for _, has_variants, _ in tests if has_variants)
                    feature_success[feature] = successful / len(tests)
                    status = "PASS" if feature_success[feature] >= 0.5 else "FAIL"
                    print(
                        f"  {status} {feature}: {successful}/{len(tests)} ({feature_success[feature]:.1%}) generated variants"
                    )
                else:
                    print(f"  ⚪ {feature}: No test cases found")

            overall_feature_success = (
                sum(feature_success.values()) / len(feature_success)
                if feature_success
                else 0
            )
            print(
                f"\n📊 OVERALL LINGUISTIC FEATURE SUCCESS: {overall_feature_success:.1%}"
            )

            return (
                overall_feature_success >= 0.4
            )  # 40% threshold for linguistic features

        except Exception as e:
            print(f"FAIL TEST 2 FAILED: {e}")
            traceback.print_exc()
            return False

    def test_3_realistic_performance_measurement(self):
        """Test 3: Realistic performance measurement with real mathematician data."""
        print("\n🧪 TEST 3: Realistic Performance Measurement")
        print("=" * 60)

        try:
            from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
            from src.core.config import GMNAPConfig

            # Create realistic test dataset
            test_entries = {}
            mathematician_count = 0

            for region_name, mathematicians in self.dataset["test_data"].items():
                for mathematician in mathematicians[:15]:  # 15 per region = 180 total
                    name = mathematician["romanized_primary"]
                    global_id = f"MATH{mathematician_count:06d}"

                    test_entries[name] = {
                        "GlobalID": global_id,
                        "CanonicalLatin": name,
                        "UpdatedAt": "2025-08-04T00:00:00Z",
                        "ExpectedRegion": self._region_name_to_code(region_name),
                        "LinguisticFeatures": mathematician.get(
                            "linguistic_features", []
                        ),
                        "Period": mathematician.get("period", "Unknown"),
                        "Country": mathematician.get("country", "Unknown"),
                    }
                    mathematician_count += 1

            print(f"📊 Testing with {len(test_entries)} real mathematician names")

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)

                # Write realistic test data
                test_file = tmpdir_path / "mathematicians.yaml"
                with open(test_file, "w", encoding="utf-8") as f:
                    yaml.dump(test_entries, f, allow_unicode=True)

                # Configure pipeline
                config = GMNAPConfig()
                config.cache.cache_dir = str(tmpdir_path / "cache")

                # Test performance with realistic data
                start_time = time.time()
                pipeline = GMNAPPipeline(config, mode=PipelineMode.QUICK)
                result = pipeline.run(tmpdir_path)
                end_time = time.time()

                duration = end_time - start_time
                entries_per_sec = len(test_entries) / duration
                minutes_per_million = (1_000_000 / entries_per_sec) / 60

                print(f"📈 REALISTIC PERFORMANCE RESULTS:")
                print(
                    f"  ⏱️  Duration: {duration:.2f}s for {len(test_entries)} entries"
                )
                print(f"  🚀 Rate: {entries_per_sec:.1f} entries/sec")
                print(f"  📊 Projected 1M rate: {minutes_per_million:.1f} min/1M")
                print(
                    f"  PASS Success rate: {result.successful_entries / result.total_entries:.1%}"
                )

                # Analyze processing quality
                processing_errors = result.total_entries - result.successful_entries
                error_rate = processing_errors / result.total_entries

                print(
                    f"  FAIL Processing errors: {processing_errors} ({error_rate:.1%})"
                )

                if minutes_per_million <= 30:
                    print("  🎯 PERFORMANCE: MEETS TARGET (<=30 min/1M)")
                    performance_grade = "EXCELLENT"
                elif minutes_per_million <= 60:
                    print("  WARN PERFORMANCE: CLOSE TO TARGET (<=60 min/1M)")
                    performance_grade = "GOOD"
                elif minutes_per_million <= 240:
                    print("  WARN PERFORMANCE: ACCEPTABLE FOR PILOTS (<=240 min/1M)")
                    performance_grade = "ACCEPTABLE"
                else:
                    print("  FAIL PERFORMANCE: TOO SLOW FOR PRODUCTION")
                    performance_grade = "POOR"

                # This is the TRUE performance measurement with real data
                print(
                    f"\n🎯 TRUE PERFORMANCE WITH REAL MATHEMATICIAN DATA: {minutes_per_million:.1f} min/1M"
                )
                return minutes_per_million <= 240  # Acceptable threshold for pilots

        except Exception as e:
            print(f"FAIL TEST 3 FAILED: {e}")
            traceback.print_exc()
            return False

    def test_4_edge_cases_and_robustness(self):
        """Test 4: Edge cases and system robustness."""
        print("\n🧪 TEST 4: Edge Cases and Robustness")
        print("=" * 60)

        try:
            from src.regions.manager_optimized import RegionManager

            manager = RegionManager()
            manager._ensure_regions_loaded()

            edge_cases = [
                # Empty and malformed inputs
                ("", "empty_string"),
                ("   ", "whitespace_only"),
                ("A", "single_character"),
                ("a" * 500, "very_long_name"),
                # Special characters and injection attempts
                ("John; DROP TABLE;", "sql_injection"),
                ("<script>alert('xss')</script>", "xss_attempt"),
                ("../../../etc/passwd", "path_traversal"),
                ("Джон Смит", "mixed_cyrillic_latin"),
                # Unicode edge cases
                ("José Ádam Đorđević", "multiple_diacritics"),
                ("김정은金正恩", "mixed_scripts"),
                ("محمد中村田中", "mixed_arabic_japanese"),
                # Formatting variations
                ("smith,john", "lowercase_comma"),
                ("SMITH JOHN", "uppercase"),
                ("Smith,,John", "double_comma"),
                ("Smith\tJohn", "tab_separator"),
                ("Smith\nJohn", "newline_separator"),
            ]

            robust_count = 0
            total_tests = len(edge_cases)

            for test_input, test_type in edge_cases:
                try:
                    result = manager.detect_region({"CanonicalLatin": test_input})
                    # System should handle gracefully without crashing
                    robust_count += 1
                    print(f"  PASS {test_type}: Handled gracefully -> {result}")

                except Exception as e:
                    print(f"  FAIL {test_type}: System crashed -> {e}")

            robustness_rate = robust_count / total_tests
            print(
                f"\n📊 ROBUSTNESS: {robust_count}/{total_tests} ({robustness_rate:.1%}) handled gracefully"
            )

            return robustness_rate >= 0.8  # 80% robustness threshold

        except Exception as e:
            print(f"FAIL TEST 4 FAILED: {e}")
            traceback.print_exc()
            return False

    def test_5_end_to_end_workflow_validation(self):
        """Test 5: End-to-end workflow with real mathematician data."""
        print("\n🧪 TEST 5: End-to-End Workflow Validation")
        print("=" * 60)

        try:
            # Test the complete workflow a user would experience
            sample_mathematicians = [
                ("Isaac Newton", "A1"),
                ("Carl Friedrich Gauss", "A2"),
                ("Andrey Kolmogorov", "B1"),
                ("김정은", "E4"),
                ("محمد الخوارزمي", "C3"),
                ("श्रीनिवास रामानुजन", "D1"),
                ("陈省身", "E1"),
                ("田中紀雄", "E3"),
                ("José Ádem", "G1"),
            ]

            workflow_success = 0
            total_workflows = len(sample_mathematicians)

            for name, expected_region in sample_mathematicians:
                try:
                    print(f"\n🔬 Testing workflow for: {name}")

                    # Step 1: Region Detection
                    from src.regions.manager_optimized import RegionManager

                    manager = RegionManager()
                    manager._ensure_regions_loaded()

                    detection_result = manager.detect_region({"CanonicalLatin": name})
                    if hasattr(detection_result, "region_code"):
                        detected_region = detection_result.region_code
                    else:
                        detected_region = str(detection_result)

                    print(f"  1️⃣ Region Detection: {name} -> {detected_region}")

                    # Step 2: Regional Processing
                    if detected_region in manager._regions:
                        processor = manager._regions[detected_region]
                        test_entry = {"CanonicalLatin": name}

                        processor.clean(test_entry)
                        processor.augment(test_entry)
                        processor.validate(test_entry)
                        order_key = processor.order_key(test_entry)

                        variants = test_entry.get("Variants", {}).get("Synthesised", [])
                        metadata = test_entry.get("RegionMetadata", {})

                        print(
                            f"  2️⃣ Regional Processing: Generated {len(variants)} variants"
                        )
                        print(f"  3️⃣ Metadata: {metadata}")
                        print(f"  4️⃣ Sort Key: {order_key}")

                        # Workflow success criteria
                        workflow_successful = (
                            detected_region is not None
                            and order_key is not None
                            and len(str(order_key).strip()) > 0
                        )

                        if workflow_successful:
                            workflow_success += 1
                            print(f"  PASS End-to-end workflow successful")
                        else:
                            print(f"  FAIL Workflow incomplete")

                    else:
                        print(f"  FAIL No processor found for region {detected_region}")

                except Exception as e:
                    print(f"  FAIL Workflow failed: {e}")

            workflow_rate = workflow_success / total_workflows
            print(
                f"\n📊 END-TO-END SUCCESS: {workflow_success}/{total_workflows} ({workflow_rate:.1%})"
            )

            return workflow_rate >= 0.7  # 70% end-to-end success threshold

        except Exception as e:
            print(f"FAIL TEST 5 FAILED: {e}")
            traceback.print_exc()
            return False

    def _region_name_to_code(self, region_name: str) -> str:
        """Convert region name to code."""
        mapping = {
            "A1_Anglo_Sphere": "A1",
            "A2_Western_Europe": "A2",
            "B1_East_Slavic": "B1",
            "B2_South_Slavic_Central": "B2",
            "C2_Persian_Tajik": "C2",
            "C3_Arabic_Levant_Nile": "C3",
            "C4_Arabic_Gulf": "C4",
            "D1_South_Asia_Hindi_Belt": "D1",
            "E1_Sinophone_Mainland": "E1",
            "E3_Japan": "E3",
            "E4_Korea": "E4",
            "G1_Latin_America": "G1",
        }
        return mapping.get(region_name, "")

    def run_ultrathink_comprehensive_audit(self):
        """Run complete ultrathink testing framework."""
        print("🧠 ULTRATHINK COMPREHENSIVE TESTING FRAMEWORK")
        print("=" * 80)
        print("Testing GMNAP v7 with REAL mathematician data and workflows")
        print("=" * 80)

        test_results = []

        # Run all comprehensive tests
        test_results.append(
            (
                "Real Mathematician Classification",
                self.test_1_real_mathematician_classification(),
            )
        )
        test_results.append(
            (
                "Linguistic Feature Validation",
                self.test_2_linguistic_feature_validation(),
            )
        )
        test_results.append(
            (
                "Realistic Performance Measurement",
                self.test_3_realistic_performance_measurement(),
            )
        )
        test_results.append(
            ("Edge Cases and Robustness", self.test_4_edge_cases_and_robustness())
        )
        test_results.append(
            (
                "End-to-End Workflow Validation",
                self.test_5_end_to_end_workflow_validation(),
            )
        )

        # Generate comprehensive report
        print("\n" + "=" * 80)
        print("🎯 ULTRATHINK COMPREHENSIVE AUDIT RESULTS")
        print("=" * 80)

        passed_tests = sum(1 for _, result in test_results if result)
        total_tests = len(test_results)
        success_rate = passed_tests / total_tests

        for test_name, passed in test_results:
            status = "PASS PASS" if passed else "FAIL FAIL"
            print(f"{status} {test_name}")

        print(
            f"\n📊 OVERALL ULTRATHINK COMPLIANCE: {passed_tests}/{total_tests} ({success_rate:.1%})"
        )

        if success_rate >= 0.8:
            print("🎉 ULTRATHINK ASSESSMENT: SYSTEM READY FOR PRODUCTION")
        elif success_rate >= 0.6:
            print("WARN ULTRATHINK ASSESSMENT: SYSTEM READY FOR PILOT DEPLOYMENT")
        else:
            print("FAIL ULTRATHINK ASSESSMENT: SYSTEM NEEDS MAJOR IMPROVEMENTS")

        return success_rate


def main():
    """Run the ultrathink comprehensive testing framework."""
    tester = UltrathinkTester()
    success_rate = tester.run_ultrathink_comprehensive_audit()

    if success_rate < 0.6:
        sys.exit(1)  # Exit with error if system is not ready


if __name__ == "__main__":
    main()
