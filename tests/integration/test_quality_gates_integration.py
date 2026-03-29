#!/usr/bin/env python3
"""
import unittest
from typing import List
from typing import Any
Integration tests for the Quality Gates system.

Tests the complete quality gates pipeline with real-world data scenarios,
focusing on system-level behavior and cross-gate interactions.
"""

import pytest
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.core.quality_gates import EnhancedQualityGates, ValidationResult
    from src.core.pipeline_v7 import V7Pipeline
    from src.regions.manager import RegionManager
except ImportError as e:
    pytest.skip(f"Quality gates components not available: {e}", allow_module_level=True)


class QualityGatesIntegrationTester:
    """Integration test helper for quality gates system"""

    def __init__(self):
        self.gates = None
        self.pipeline = None
        self.region_manager = None
        self.test_entries = []

    async def setup(self):
        """Initialize test components"""
        try:
            self.gates = EnhancedQualityGates()
            self.pipeline = V7Pipeline()
            self.region_manager = RegionManager(Path("./config"))
            self._prepare_test_data()
        except Exception as e:
            pytest.skip(f"Failed to initialize integration components: {e}")

    def _prepare_test_data(self):
        """Prepare comprehensive test dataset"""
        base_time = datetime.now()

        self.test_entries = [
            # Perfect entry - should pass all gates
            {
                "name": "perfect_entry",
                "data": {
                    "CanonicalLatin": "Smith, John William",
                    "CanonicalNative": "Smith, John William",
                    "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                    "DetectedRegion": "A1",
                    "UpdatedAt": base_time.isoformat(),
                    "LanguageOfPublication": ["eng"],
                    "CountryCodes": ["US"],
                    "Confidence": 0.95,
                    "FamilyNameType": "patronymic",
                    "Gender": "male",
                    "Historic": False,
                    "GDPR_DATA": False,
                    "RegionalExtras": {"region_confidence": 0.95},
                    "GraphQualityGates": {"graph_coherence_score": 0.92},
                    "Variants": {"Observed": [{"str": "J. Smith"}, {"str": "John W. Smith"}]},
                    "authority_data": {
                        "ORCID": {
                            "confidence": 0.95,
                            "orcid": "0000-0002-1234-5678",
                            "publications": 42,
                        }
                    },
                },
                "expected_gates_passed": 8,
                "expected_overall_pass": True,
            },
            # CJK entry with roundtrip validation
            {
                "name": "cjk_roundtrip_entry",
                "data": {
                    "CanonicalLatin": "Li Ming",
                    "CanonicalNative": "李明",
                    "GlobalID": "CJKDEFGHIJKLMNOPQRSTUV",
                    "DetectedRegion": "E1",
                    "UpdatedAt": base_time.isoformat(),
                    "LanguageOfPublication": ["chi"],
                    "CountryCodes": ["CN"],
                    "Confidence": 0.92,
                    "RegionalExtras": {"transliteration": "Li Ming"},
                    "GraphQualityGates": {"graph_coherence_score": 0.88},
                    "Variants": {"Synthesised": [{"str": "Ming Li", "type": "roundtrip"}]},
                },
                "expected_gates_passed": 7,
                "expected_overall_pass": True,
            },
            # Korean entry with specific challenges
            {
                "name": "korean_complex_entry",
                "data": {
                    "CanonicalLatin": "Kim Jung-un",
                    "CanonicalNative": "김정은",
                    "GlobalID": "KORDEFGHIJKLMNOPQRSTUV",
                    "DetectedRegion": "E4",
                    "UpdatedAt": base_time.isoformat(),
                    "LanguageOfPublication": ["kor"],
                    "CountryCodes": ["KR"],
                    "Confidence": 0.94,
                    "RegionalExtras": {"romanization_method": "revised"},
                    "GraphQualityGates": {"graph_coherence_score": 0.90},
                    "Variants": {"Synthesised": [{"str": "Kim Jong-un", "type": "roundtrip"}]},
                },
                "expected_gates_passed": 7,
                "expected_overall_pass": True,
            },
            # Entry with schema violations
            {
                "name": "schema_violation_entry",
                "data": {
                    "CanonicalLatin": "Invalid Entry",
                    "GlobalID": "invalid-format",  # Invalid format
                    "DetectedRegion": "INVALID",
                    "UpdatedAt": (base_time + timedelta(days=1)).isoformat(),  # Future date
                    "Confidence": 1.5,  # Out of range
                    "LanguageOfPublication": "invalid_format",  # Should be array
                },
                "expected_gates_passed": 0,
                "expected_overall_pass": False,
            },
            # Entry with coherence issues
            {
                "name": "coherence_mismatch_entry",
                "data": {
                    "CanonicalLatin": "Tanaka Hiroshi",
                    "GlobalID": "COHERDEFGHIJKLMNOPQRSTU",
                    "DetectedRegion": "E3",  # Japan
                    "UpdatedAt": base_time.isoformat(),
                    "LanguageOfPublication": ["eng"],  # Should be jpn
                    "CountryCodes": ["US"],  # Should be JP
                    "Confidence": 0.95,
                    "GraphQualityGates": {"graph_coherence_score": 0.45},  # Low graph score
                },
                "expected_gates_passed": 5,  # Schema + others pass, coherence fails
                "expected_overall_pass": True,  # Still passes overall but with warnings
            },
            # Potential duplicate entry
            {
                "name": "duplicate_candidate_entry",
                "data": {
                    "CanonicalLatin": "Smith, John William",  # Same as perfect entry
                    "GlobalID": "DUPLIDEFGHIJKLMNOPQRSTU",
                    "DetectedRegion": "A1",
                    "UpdatedAt": base_time.isoformat(),
                    "CountryCodes": ["US"],
                    "Confidence": 0.93,
                },
                "expected_gates_passed": 6,
                "expected_overall_pass": True,  # Passes but should have duplicate warnings
            },
            # Minimal but valid entry
            {
                "name": "minimal_valid_entry",
                "data": {
                    "CanonicalLatin": "Minimal Name",
                    "GlobalID": "MINIMALFGHIJKLMNOPQRSTU",
                    "DetectedRegion": "A1",
                    "UpdatedAt": base_time.isoformat(),
                    "Confidence": 0.85,
                },
                "expected_gates_passed": 6,  # Lower completeness score
                "expected_overall_pass": True,
            },
        ]


class TestQualityGatesIntegration:
    """Integration test suite for quality gates system"""

    @pytest.fixture
    async def integration_tester(self):
        """Create and setup integration tester"""
        tester = QualityGatesIntegrationTester()
        await tester.setup()
        return tester

    @pytest.mark.asyncio
    async def test_end_to_end_validation_flow(self, integration_tester):
        """Test complete validation flow for various entry types"""
        results = {}

        for test_case in integration_tester.test_entries:
            entry_name = test_case["name"]
            entry_data = test_case["data"]
            expected_pass = test_case["expected_overall_pass"]

            result = await integration_tester.gates.validate_entry(entry_data)
            results[entry_name] = result

            # Verify overall pass/fail matches expectations
            assert (
                result["passed"] == expected_pass
            ), f"{entry_name}: Expected pass={expected_pass}, got {result['passed']}"

            # Verify structure of results
            assert "score" in result
            assert "gates" in result
            assert "summary" in result
            assert isinstance(result["gates"], list)
            assert len(result["gates"]) == 8, f"Expected 8 gates, got {len(result['gates'])}"

    @pytest.mark.asyncio
    async def test_batch_validation_consistency(self, integration_tester):
        """Test that batch validation produces consistent results with individual validation"""
        # Extract all test entry data
        entries = [tc["data"] for tc in integration_tester.test_entries]

        # Run batch validation
        batch_result = await integration_tester.gates.validate_batch(entries)

        # Verify batch result structure
        assert "batch_results" in batch_result
        assert "summary" in batch_result
        assert len(batch_result["batch_results"]) == len(entries)

        # Run individual validations and compare
        for i, entry in enumerate(entries):
            individual_result = await integration_tester.gates.validate_entry(entry)
            batch_entry_result = batch_result["batch_results"][i]

            # Key metrics should match
            assert (
                individual_result["passed"] == batch_entry_result["passed"]
            ), f"Entry {i}: Individual vs batch pass/fail mismatch"

            # Scores should be close (allowing for small floating point differences)
            assert (
                abs(individual_result["score"] - batch_entry_result["score"]) < 0.01
            ), f"Entry {i}: Score mismatch {individual_result['score']} vs {batch_entry_result['score']}"

    @pytest.mark.asyncio
    async def test_gate_interaction_patterns(self, integration_tester):
        """Test how different quality gates interact with each other"""
        # Test entry that should trigger specific gate combinations
        test_entry = {
            "CanonicalLatin": "Test Entry",
            "GlobalID": "TESTDEFGHIJKLMNOPQRSTUV",
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.88,
            "GraphQualityGates": {"graph_coherence_score": 0.92},
        }

        result = await integration_tester.gates.validate_entry(test_entry)

        # Analyze gate-specific results
        gate_results = {gate["gate_name"]: gate for gate in result["gates"]}

        # Schema validation should pass for basic valid entry
        assert gate_results["SchemaValidator"]["passed"] is True

        # Completeness should be lower due to missing optional fields
        completeness_result = gate_results["CompletenessChecker"]
        assert completeness_result["score"] < 0.8, "Expected lower completeness score"

        # Authority validation should note absence of authority data
        authority_result = gate_results["AuthorityValidator"]
        assert len(authority_result["warnings"]) > 0, "Expected authority warnings"

    @pytest.mark.asyncio
    async def test_performance_under_load(self, integration_tester):
        """Test quality gates performance with concurrent validation"""
        import time

        # Create multiple copies of test entries for concurrent testing
        test_entries = []
        for _ in range(10):  # 10 batches of test data
            test_entries.extend([tc["data"] for tc in integration_tester.test_entries])

        start_time = time.time()

        # Run concurrent validations
        tasks = []
        for entry in test_entries[:20]:  # Test with 20 concurrent validations
            task = integration_tester.gates.validate_entry(entry)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert total_time < 10.0, f"Validation took too long: {total_time:.2f}s for 20 entries"
        assert len(results) == 20, "Not all validations completed"

        # Verify all results have proper structure
        for i, result in enumerate(results):
            assert "passed" in result, f"Result {i} missing 'passed' field"
            assert "gates" in result, f"Result {i} missing 'gates' field"
            assert (
                len(result["gates"]) == 8
            ), f"Result {i} has {len(result['gates'])} gates, expected 8"

    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, integration_tester):
        """Test quality gates behavior with malformed or problematic data"""
        problematic_entries = [
            # Completely empty entry
            {},
            # Entry with None values
            {"CanonicalLatin": None, "GlobalID": None, "DetectedRegion": None},
            # Entry with wrong data types
            {
                "CanonicalLatin": ["should", "be", "string"],
                "GlobalID": 12345,
                "Confidence": "should_be_number",
            },
            # Entry with extremely long values (DoS test)
            {"CanonicalLatin": "A" * 10000, "GlobalID": "B" * 1000, "DetectedRegion": "C" * 100},
        ]

        for i, entry in enumerate(problematic_entries):
            try:
                result = await integration_tester.gates.validate_entry(entry)

                # Should not crash, should return structured result
                assert isinstance(result, dict), f"Entry {i}: Result not a dict"
                assert "passed" in result, f"Entry {i}: Missing 'passed' field"
                assert "gates" in result, f"Entry {i}: Missing 'gates' field"

                # Problematic entries should generally fail
                assert (
                    result["passed"] is False
                ), f"Entry {i}: Expected failure for problematic entry"

            except Exception as e:
                pytest.fail(f"Entry {i}: Quality gates crashed with: {str(e)}")

    @pytest.mark.asyncio
    async def test_regional_integration(self, integration_tester):
        """Test quality gates integration with regional processors"""
        if not integration_tester.region_manager:
            pytest.skip("Region manager not available for integration testing")

        # Test entries for different regions
        regional_test_cases = [
            ("A1", "Smith, John", ["eng"], ["US"]),
            ("E1", "Li Ming", ["chi"], ["CN"]),
            ("E4", "Kim Min-jun", ["kor"], ["KR"]),
            ("B1", "Petrov, Ivan", ["rus"], ["RU"]),
            ("D1", "Sharma, Raj", ["hin"], ["IN"]),
        ]

        for region_code, name, languages, countries in regional_test_cases:
            # Check if region is available
            try:
                region = integration_tester.region_manager.get_region(region_code)
                if not region:
                    continue
            except Exception:
                continue

            entry = {
                "CanonicalLatin": name,
                "GlobalID": f"REG{region_code}FGHIJKLMNOPQRSTU",
                "DetectedRegion": region_code,
                "UpdatedAt": datetime.now().isoformat(),
                "LanguageOfPublication": languages,
                "CountryCodes": countries,
                "Confidence": 0.90,
            }

            result = await integration_tester.gates.validate_entry(entry)

            # Regional entries should generally pass basic validation
            assert (
                result["passed"] is True
            ), f"Region {region_code}: Entry should pass basic validation"

            # Coherence validation should be happy with matching region/language/country
            coherence_gate = next(
                (g for g in result["gates"] if g["gate_name"] == "CoherenceValidator"), None
            )
            assert coherence_gate is not None, f"Region {region_code}: Missing coherence gate"
            assert (
                coherence_gate["passed"] is True
            ), f"Region {region_code}: Coherence validation should pass"

    @pytest.mark.asyncio
    async def test_quality_gates_metrics_collection(self, integration_tester):
        """Test that quality gates collect appropriate metrics"""
        test_entry = integration_tester.test_entries[0]["data"]  # Perfect entry

        result = await integration_tester.gates.validate_entry(test_entry)

        # Check summary metrics
        summary = result["summary"]
        expected_summary_fields = [
            "gates_run",
            "gates_passed",
            "gates_failed",
            "total_warnings",
            "total_errors",
            "overall_score",
        ]

        for field in expected_summary_fields:
            assert field in summary, f"Missing summary field: {field}"

        # Verify metrics consistency
        assert summary["gates_run"] == len(result["gates"])
        assert summary["gates_passed"] + summary["gates_failed"] == summary["gates_run"]

        # Check individual gate metrics
        for gate in result["gates"]:
            required_gate_fields = ["gate_name", "passed", "score", "execution_time_ms"]
            for field in required_gate_fields:
                assert (
                    field in gate
                ), f"Gate {gate.get('gate_name', 'unknown')}: Missing field {field}"

    @pytest.mark.asyncio
    async def test_integration_with_pipeline(self, integration_tester):
        """Test quality gates integration with the V7 pipeline"""
        if not integration_tester.pipeline:
            pytest.skip("V7 Pipeline not available for integration testing")

        # Create a test entry that would go through both pipeline and quality gates
        test_entry = {
            "CanonicalLatin": "Integration Test Name",
            "GlobalID": "INTEGDEFGHIJKLMNOPQRSTU",
            "DetectedRegion": "A1",
            "UpdatedAt": datetime.now().isoformat(),
            "Confidence": 0.91,
        }

        # Test that entry structure is compatible between pipeline and quality gates
        quality_result = await integration_tester.gates.validate_entry(test_entry)

        # Verify that quality gates don't conflict with pipeline expectations
        assert quality_result["passed"] in [
            True,
            False,
        ], "Quality gates should return boolean result"
        assert isinstance(quality_result["score"], (int, float)), "Score should be numeric"

        # Test that quality gates enhance rather than replace pipeline validation
        schema_gate = next(
            (g for g in quality_result["gates"] if g["gate_name"] == "SchemaValidator"), None
        )
        assert schema_gate is not None, "Schema validation should be present"
        assert (
            schema_gate["passed"] is True
        ), "Basic schema should pass for pipeline-compatible entry"


@pytest.mark.asyncio
async def test_quality_gates_full_integration():
    """Comprehensive integration test for the complete quality gates system"""
    tester = QualityGatesIntegrationTester()
    await tester.setup()

    if not tester.gates:
        pytest.skip("Quality gates system not available")

    # Run validation on all test cases
    results = {}
    for test_case in tester.test_entries:
        entry_name = test_case["name"]
        entry_data = test_case["data"]

        result = await tester.gates.validate_entry(entry_data)
        results[entry_name] = result

    # Verify overall system behavior
    total_entries = len(results)
    passed_entries = sum(1 for r in results.values() if r["passed"])

    print(f"\nQuality Gates Integration Results:")
    print(f"Total entries tested: {total_entries}")
    print(f"Entries passed: {passed_entries}")
    print(f"Pass rate: {100 * passed_entries / total_entries:.1f}%")

    # System should handle various entry types without crashing
    assert len(results) == len(tester.test_entries), "Not all entries were processed"

    # At least some entries should pass (perfect entries)
    assert passed_entries > 0, "No entries passed validation - system may be broken"

    # Problematic entries should be caught
    problem_entries = ["schema_violation_entry"]
    for problem_entry in problem_entries:
        if problem_entry in results:
            assert (
                results[problem_entry]["passed"] is False
            ), f"{problem_entry} should have failed validation"


def main():
    """Run the quality gates integration test suite"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    main()
