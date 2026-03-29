#!/usr/bin/env python3
"""
Production Validation Script

End-to-end smoke tests to verify v5 deployment success.

Tests:
1. Model loading and initialization
2. Prediction contract compliance
3. Calibration accuracy
4. Abstention policy
5. Performance (latency)
6. Integration with HybridRegionClassifier
7. Known test cases (golden dataset)
8. Error handling

Usage:
    python3 scripts/ml/validate_production.py [--quick] [--verbose]

Exit codes:
    0: All tests passed
    1: One or more tests failed
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.regions.regional_classifier_v5 import RegionalClassifierV5
from src.regions.hybrid_classifier import HybridRegionClassifier


class ProductionValidator:
    """Production validation test suite"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def log(self, message: str, level: str = "INFO"):
        """Log message"""
        prefix = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ ", "INFO": "ℹ️ "}.get(level, "  ")

        print(f"{prefix} {message}")

    def assert_equal(self, actual, expected, test_name: str):
        """Assert equality"""
        if actual == expected:
            self.passed += 1
            self.log(f"{test_name}: PASS", "PASS")
        else:
            self.failed += 1
            self.log(f"{test_name}: FAIL (expected {expected}, got {actual})", "FAIL")

    def assert_true(self, condition: bool, test_name: str):
        """Assert true"""
        if condition:
            self.passed += 1
            self.log(f"{test_name}: PASS", "PASS")
        else:
            self.failed += 1
            self.log(f"{test_name}: FAIL", "FAIL")

    def assert_in(self, item, container, test_name: str):
        """Assert item in container"""
        if item in container:
            self.passed += 1
            self.log(f"{test_name}: PASS", "PASS")
        else:
            self.failed += 1
            self.log(f"{test_name}: FAIL ({item} not in {container})", "FAIL")

    def warn(self, message: str):
        """Log warning"""
        self.warnings += 1
        self.log(message, "WARN")

    def test_model_loading(self) -> bool:
        """Test 1: Model loading"""
        print("\n" + "=" * 80)
        print("TEST 1: MODEL LOADING")
        print("=" * 80)

        try:
            start = time.time()
            classifier = RegionalClassifierV5()
            load_time = time.time() - start

            self.assert_true(classifier is not None, "Classifier initialized")
            self.assert_true(classifier.model is not None, "Model loaded")

            if load_time > 5.0:
                self.warn(f"Model loading took {load_time:.2f}s (expected <5s)")
            else:
                self.log(f"Model loaded in {load_time:.2f}s", "INFO")

            return True

        except Exception as e:
            self.failed += 1
            self.log(f"Model loading FAILED: {e}", "FAIL")
            return False

    def test_prediction_contract(self, classifier: RegionalClassifierV5) -> bool:
        """Test 2: Prediction contract"""
        print("\n" + "=" * 80)
        print("TEST 2: PREDICTION CONTRACT")
        print("=" * 80)

        try:
            result = classifier.predict("John Smith", k=3)

            # Check required fields
            required_fields = [
                "model_name",
                "model_version",
                "label_policy",
                "region_top1",
                "region_top1_confidence",
                "topk",
                "proba",
                "abstained",
                "calibration",
                "provenance",
            ]

            for field in required_fields:
                self.assert_in(field, result, f"Field '{field}' present")

            # Check values
            self.assert_equal(result["model_name"], "fasttext-v5-etymology", "Model name")
            self.assert_equal(result["label_policy"], "etymology", "Label policy")
            self.assert_equal(
                result["calibration"]["method"], "temperature_scaling", "Calibration method"
            )
            self.assert_equal(result["calibration"]["T"], 2.817, "Temperature value")

            # Check top-k structure
            if not result["abstained"]:
                self.assert_true(isinstance(result["topk"], list), "topk is list")
                self.assert_true(len(result["topk"]) <= 3, "topk has ≤3 items")
                self.assert_true(
                    all("region" in item and "p" in item for item in result["topk"]),
                    "topk items have correct structure",
                )
            else:
                self.log("Prediction abstained, skipping topk check", "INFO")

            return True

        except Exception as e:
            self.failed += 1
            self.log(f"Contract test FAILED: {e}", "FAIL")
            return False

    def test_known_cases(self, classifier: RegionalClassifierV5) -> bool:
        """Test 3: Known test cases"""
        print("\n" + "=" * 80)
        print("TEST 3: KNOWN TEST CASES (Golden Dataset)")
        print("=" * 80)

        test_cases = [
            ("John Smith", "A1"),  # Anglo
            ("José García", "G1"),  # Latin America
            ("François Dubois", "A2"),  # Western Europe
            ("Anna Kowalski", "B2"),  # Slavic
            ("Kim Min-jung", "E4"),  # Korean
            ("Zhang Wei", "E1"),  # Chinese (romanized)
            ("Vladimir Putin", "B1"),  # East Slavic
            ("Luigi Ferrucci", "A2"),  # Italian
        ]

        correct = 0
        for name, expected_region in test_cases:
            result = classifier.predict(name, k=3)

            if result["abstained"]:
                self.warn(f"'{name}' abstained (expected {expected_region})")
                continue

            predicted = result["region_top1"]
            if predicted == expected_region:
                correct += 1
                if self.verbose:
                    self.log(
                        f"'{name}' → {predicted} (confidence: {result['region_top1_confidence']:.3f})",
                        "PASS",
                    )
            else:
                self.failed += 1
                self.log(f"'{name}': expected {expected_region}, got {predicted}", "FAIL")

        accuracy = correct / len(test_cases)
        self.log(f"Golden dataset accuracy: {accuracy:.1%} ({correct}/{len(test_cases)})", "INFO")

        if accuracy >= 0.75:
            self.passed += 1
            return True
        else:
            self.failed += 1
            return False

    def test_abstention_policy(self, classifier: RegionalClassifierV5) -> bool:
        """Test 4: Abstention policy"""
        print("\n" + "=" * 80)
        print("TEST 4: ABSTENTION POLICY")
        print("=" * 80)

        # Test names that should have ambiguous predictions
        ambiguous_names = [
            "Lee",  # Could be Korean (E4), Anglo (A1), Chinese (E1)
            "Kim",  # Korean, but very short
            "Wang",  # Chinese, but short
        ]

        abstained_count = 0
        for name in ambiguous_names:
            result = classifier.predict(name, k=3)

            if result["abstained"]:
                abstained_count += 1
                self.log(
                    f"'{name}' correctly abstained (reason: {result['abstain_reason']})", "PASS"
                )
            else:
                if self.verbose:
                    self.log(
                        f"'{name}' did not abstain (confidence: {result['region_top1_confidence']:.3f})",
                        "INFO",
                    )

        # At least some should abstain
        if abstained_count > 0:
            self.passed += 1
            self.log(
                f"Abstention policy working ({abstained_count}/{len(ambiguous_names)} abstained)",
                "PASS",
            )
            return True
        else:
            self.warn("No abstentions observed (expected at least one)")
            return True  # Not a failure, just a warning

    def test_performance(self, classifier: RegionalClassifierV5) -> bool:
        """Test 5: Performance (latency)"""
        print("\n" + "=" * 80)
        print("TEST 5: PERFORMANCE (LATENCY)")
        print("=" * 80)

        test_name = "John Smith"
        iterations = 100

        # Warmup
        for _ in range(10):
            classifier.predict(test_name, k=3)

        # Measure
        start = time.time()
        for _ in range(iterations):
            classifier.predict(test_name, k=3)
        elapsed = time.time() - start

        avg_latency_ms = (elapsed / iterations) * 1000

        self.log(f"Average latency: {avg_latency_ms:.2f}ms ({iterations} iterations)", "INFO")

        # Target: <3ms
        if avg_latency_ms <= 3.0:
            self.passed += 1
            self.log(f"Latency meets target (≤3ms)", "PASS")
            return True
        elif avg_latency_ms <= 5.0:
            self.warn(f"Latency {avg_latency_ms:.2f}ms above target but acceptable")
            return True
        else:
            self.failed += 1
            self.log(f"Latency {avg_latency_ms:.2f}ms exceeds acceptable range (>5ms)", "FAIL")
            return False

    def test_hybrid_integration(self) -> bool:
        """Test 6: Integration with HybridRegionClassifier"""
        print("\n" + "=" * 80)
        print("TEST 6: HYBRID CLASSIFIER INTEGRATION")
        print("=" * 80)

        try:
            hybrid = HybridRegionClassifier()
            entry = {"CanonicalNative": "John Smith"}
            result = hybrid.detect_region(entry)

            self.assert_true(result is not None, "Hybrid classifier returned result")
            self.assert_true(hasattr(result, "region_code"), "Result has region_code")
            self.assert_true(hasattr(result, "confidence"), "Result has confidence")

            # Check that v5 is being used
            if hasattr(result, "detection_method") and "v5" in result.detection_method.lower():
                self.log("Hybrid classifier using v5 model", "PASS")
                self.passed += 1
            else:
                self.warn("Cannot confirm v5 model usage in hybrid classifier")

            return True

        except Exception as e:
            self.failed += 1
            self.log(f"Hybrid integration FAILED: {e}", "FAIL")
            return False

    def test_error_handling(self, classifier: RegionalClassifierV5) -> bool:
        """Test 7: Error handling"""
        print("\n" + "=" * 80)
        print("TEST 7: ERROR HANDLING")
        print("=" * 80)

        error_cases = [
            "",  # Empty string
            " ",  # Whitespace
            "   ",  # Multiple spaces
            "12345",  # Numbers
            "@#$%",  # Special characters
        ]

        errors_handled = 0
        for test_input in error_cases:
            try:
                result = classifier.predict(test_input, k=3)

                # Should either return prediction or abstain, not crash
                if result is not None:
                    errors_handled += 1
                    if self.verbose:
                        self.log(f"Input '{test_input}' handled gracefully", "PASS")
            except Exception as e:
                self.failed += 1
                self.log(f"Input '{test_input}' caused error: {e}", "FAIL")

        if errors_handled == len(error_cases):
            self.passed += 1
            self.log(f"All {len(error_cases)} error cases handled gracefully", "PASS")
            return True
        else:
            return False

    def run_all_tests(self, quick: bool = False) -> Tuple[int, int, int]:
        """Run all validation tests"""
        print("=" * 80)
        print("PRODUCTION VALIDATION SUITE - v5 DEPLOYMENT")
        print("=" * 80)
        print(f"\nMode: {'QUICK' if quick else 'FULL'}")

        # Test 1: Model loading
        if not self.test_model_loading():
            print("\n❌ CRITICAL: Model loading failed. Aborting remaining tests.")
            return self.passed, self.failed, self.warnings

        classifier = RegionalClassifierV5()

        # Test 2: Prediction contract
        self.test_prediction_contract(classifier)

        # Test 3: Known cases
        self.test_known_cases(classifier)

        if not quick:
            # Test 4: Abstention
            self.test_abstention_policy(classifier)

            # Test 5: Performance
            self.test_performance(classifier)

            # Test 6: Hybrid integration
            self.test_hybrid_integration()

            # Test 7: Error handling
            self.test_error_handling(classifier)

        # Summary
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"\n✅ Passed:   {self.passed}")
        print(f"❌ Failed:   {self.failed}")
        print(f"⚠️  Warnings: {self.warnings}")
        print(f"\nTotal tests: {self.passed + self.failed}")

        if self.failed == 0:
            print("\n" + "=" * 80)
            print("✅ ALL TESTS PASSED - PRODUCTION DEPLOYMENT VALIDATED")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("❌ SOME TESTS FAILED - INVESTIGATE BEFORE PROCEEDING")
            print("=" * 80)

        return self.passed, self.failed, self.warnings


def main():
    parser = argparse.ArgumentParser(description="Validate v5 production deployment")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick validation (skip performance and error tests)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    validator = ProductionValidator(verbose=args.verbose)
    passed, failed, warnings = validator.run_all_tests(quick=args.quick)

    # Exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
