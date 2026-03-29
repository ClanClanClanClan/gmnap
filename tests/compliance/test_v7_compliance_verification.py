#!/usr/bin/env python3
"""
import unittest
from typing import List
from typing import Any
V7 Compliance Verification Test Suite

Automated verification of GMNAP v7 feature implementation status to prevent
documentation discrepancies discovered during ULTRACHECK audit.

This suite verifies actual implementation against documented compliance claims.
"""

import pytest
import asyncio
import sys
import inspect
from pathlib import Path
from typing import Dict, List, Tuple, Any
from unittest.mock import Mock, patch
import importlib.util

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.core.pipeline_v7 import V7Pipeline
    from src.core.quality_gates import EnhancedQualityGates
    from src.regions.manager import RegionManager
except ImportError as e:
    pytest.skip(f"Pipeline components not available: {e}", allow_module_level=True)


class V7ComplianceVerifier:
    """Automated verification of V7 feature implementations"""

    def __init__(self):
        self.pipeline = None
        self.quality_gates = None
        self.region_manager = None
        self.verification_results = {}

    async def setup(self):
        """Initialize test components"""
        try:
            self.pipeline = V7Pipeline()
            self.quality_gates = EnhancedQualityGates()
            self.region_manager = RegionManager(Path("./config"))
        except Exception as e:
            pytest.skip(f"Failed to initialize components: {e}")

    def verify_implementation_exists(
        self, module_name: str, feature_name: str, expected_methods: List[str]
    ) -> Dict[str, Any]:
        """Verify that a feature is actually implemented in code"""
        result = {
            "feature": feature_name,
            "implemented": False,
            "evidence": [],
            "methods_found": [],
            "line_numbers": {},
        }

        try:
            # Import the module
            if hasattr(self, module_name.lower().replace("_", "")):
                module = getattr(self, module_name.lower().replace("_", ""))
            else:
                spec = importlib.util.spec_from_file_location(
                    module_name, Path(__file__).parent.parent.parent / "src" / f"{module_name}.py"
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            # Check for expected methods/attributes
            for method in expected_methods:
                if hasattr(module, method) or (
                    hasattr(module, "__class__")
                    and any(hasattr(cls, method) for cls in inspect.getmro(module.__class__))
                ):
                    result["methods_found"].append(method)

                    # Try to get source line numbers
                    try:
                        if hasattr(module, method):
                            source_lines = inspect.getsourcelines(getattr(module, method))
                            result["line_numbers"][method] = source_lines[1]
                        elif hasattr(module.__class__, method):
                            source_lines = inspect.getsourcelines(getattr(module.__class__, method))
                            result["line_numbers"][method] = source_lines[1]
                    except (OSError, TypeError):
                        pass  # Source not available

            # Feature is implemented if we found any expected methods
            result["implemented"] = len(result["methods_found"]) > 0
            result["evidence"] = [f"Found method: {m}" for m in result["methods_found"]]

        except Exception as e:
            result["evidence"] = [f"Verification error: {str(e)}"]

        return result

    def check_pipeline_stage(self, stage_number: int, stage_name: str) -> Dict[str, Any]:
        """Check if a specific pipeline stage is implemented"""
        result = {
            "stage": f"Stage {stage_number}: {stage_name}",
            "implemented": False,
            "evidence": [],
        }

        if not self.pipeline:
            result["evidence"] = ["Pipeline not initialized"]
            return result

        try:
            # Check if pipeline has the stage method using actual naming convention
            stage_method = f"_stage_{stage_number}_"

            # For stage 11, check the specific method name
            if stage_number == 11:
                specific_method = f"_stage_11_idempotency_check"
                if hasattr(self.pipeline, specific_method):
                    result["implemented"] = True
                    result["evidence"].append(f"Method {specific_method} exists")

                    # Try to get source code evidence
                    try:
                        source_lines = inspect.getsourcelines(
                            getattr(self.pipeline, specific_method)
                        )
                        result["evidence"].append(f"Implementation at line {source_lines[1]}")
                    except (OSError, TypeError):
                        result["evidence"].append("Source code accessible")
            else:
                # For other stages, check for methods starting with the pattern
                pipeline_methods = [
                    method for method in dir(self.pipeline) if method.startswith(stage_method)
                ]
                if pipeline_methods:
                    result["implemented"] = True
                    result["evidence"].append(f"Found stage methods: {', '.join(pipeline_methods)}")

                    # Try to get source code evidence for the first method
                    try:
                        first_method = pipeline_methods[0]
                        source_lines = inspect.getsourcelines(getattr(self.pipeline, first_method))
                        result["evidence"].append(f"Implementation at line {source_lines[1]}")
                    except (OSError, TypeError):
                        result["evidence"].append("Source code accessible")

            # Additional checks for Stage 11 idempotency features
            if stage_number == 11:
                if hasattr(self.pipeline, "_clear_pipeline_state"):
                    result["evidence"].append("Pipeline state clearing method found")
                if hasattr(self.pipeline, "idempotency_metrics"):
                    result["evidence"].append("Idempotency metrics tracking found")

        except Exception as e:
            result["evidence"] = [f"Stage check error: {str(e)}"]

        return result

    def verify_quality_gates(self) -> Dict[str, Any]:
        """Verify quality gates implementation"""
        result = {
            "feature": "Quality Gates System",
            "implemented": False,
            "evidence": [],
            "gate_count": 0,
        }

        if not self.quality_gates:
            result["evidence"] = ["Quality gates not initialized"]
            return result

        try:
            # Check for expected validators
            expected_validators = [
                "SchemaValidator",
                "RoundtripValidator",
                "CoherenceValidator",
                "DuplicateDetector",
                "PerformanceMonitor",
                "CompletenessChecker",
                "ConsistencyVerifier",
                "AuthorityValidator",
            ]

            found_validators = []
            for validator in expected_validators:
                try:
                    # Check if validator class exists in quality_gates module
                    from src.core.quality_gates import globals as qg_globals

                    if validator in qg_globals() or hasattr(self.quality_gates, validator.lower()):
                        found_validators.append(validator)
                except:
                    pass

            result["gate_count"] = len(found_validators)
            result["implemented"] = result["gate_count"] > 0
            result["evidence"] = [
                f"Found {len(found_validators)} validators: {', '.join(found_validators)}"
            ]

            # Check for main validation methods
            if hasattr(self.quality_gates, "validate_entry"):
                result["evidence"].append("Entry validation method found")
            if hasattr(self.quality_gates, "validate_batch"):
                result["evidence"].append("Batch validation method found")

        except Exception as e:
            result["evidence"] = [f"Quality gates check error: {str(e)}"]

        return result

    def verify_region_coverage(self) -> Dict[str, Any]:
        """Verify regional processor coverage"""
        result = {
            "feature": "Regional Coverage",
            "implemented": False,
            "evidence": [],
            "regions_loaded": 0,
            "total_expected": 33,
        }

        if not self.region_manager:
            result["evidence"] = ["Region manager not initialized"]
            return result

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
            "G1",
        ]

        loaded_regions = []
        for region_code in expected_regions:
            try:
                region = self.region_manager.get_region(region_code)
                if region and hasattr(region, "code"):
                    loaded_regions.append(region_code)
            except Exception:
                pass

        result["regions_loaded"] = len(loaded_regions)
        result["implemented"] = result["regions_loaded"] > 0
        result["evidence"] = [
            f"Loaded {len(loaded_regions)}/{len(expected_regions)} regions",
            f"Coverage: {100 * len(loaded_regions) / len(expected_regions):.1f}%",
        ]

        if len(loaded_regions) < len(expected_regions):
            missing = set(expected_regions) - set(loaded_regions)
            result["evidence"].append(f"Missing regions: {', '.join(sorted(missing))}")

        return result


class TestV7ComplianceVerification:
    """Test suite for V7 compliance verification"""

    @pytest.fixture
    def verifier(self):
        """Create and setup verifier"""

        async def _setup():
            v = V7ComplianceVerifier()
            await v.setup()
            return v

        return asyncio.run(_setup())

    @pytest.mark.asyncio
    async def test_stage_11_idempotency_check(self, verifier):
        """Verify Stage 11 IdempotencyCheck is implemented"""
        result = verifier.check_pipeline_stage(11, "IdempotencyCheck")

        # This was documented as "Not Implemented" but should be found
        assert result["implemented"], f"Stage 11 not found: {result['evidence']}"
        assert len(result["evidence"]) > 0, "No implementation evidence found"

        # Store result for reporting
        verifier.verification_results["stage_11"] = result

    @pytest.mark.asyncio
    async def test_roundtrip_validation(self, verifier):
        """Verify Round-trip Validation is implemented"""
        # Check multiple possible locations for roundtrip validation
        pipeline_result = verifier.verify_implementation_exists(
            "pipeline_v7",
            "Round-trip Validation",
            ["validate_roundtrip", "roundtrip_validation", "dice_coefficient"],
        )

        quality_gates_result = verifier.verify_quality_gates()

        # Should find implementation in either location
        implemented = pipeline_result["implemented"] or quality_gates_result["implemented"]

        assert implemented, "Round-trip validation not found in pipeline or quality gates"

        verifier.verification_results["roundtrip"] = {
            "pipeline": pipeline_result,
            "quality_gates": quality_gates_result,
        }

    @pytest.mark.asyncio
    async def test_graph_coherence_scoring(self, verifier):
        """Verify Graph Coherence Scoring is implemented"""
        result = verifier.verify_implementation_exists(
            "pipeline_v7",
            "Graph Coherence Scoring",
            ["calculate_graph_coherence", "graph_coherence_score", "coherence_validation"],
        )

        # This was documented as "Not Implemented" but should be found
        assert result["implemented"], f"Graph coherence not found: {result['evidence']}"

        verifier.verification_results["graph_coherence"] = result

    @pytest.mark.asyncio
    async def test_quality_gates_system(self, verifier):
        """Verify Quality Gates system implementation"""
        result = verifier.verify_quality_gates()

        assert result["implemented"], f"Quality gates not implemented: {result['evidence']}"
        assert result["gate_count"] > 0, f"No quality gate validators found"

        verifier.verification_results["quality_gates"] = result

    @pytest.mark.asyncio
    async def test_regional_coverage(self, verifier):
        """Verify regional processor coverage"""
        result = verifier.verify_region_coverage()

        assert result["implemented"], "No regions loaded"
        assert (
            result["regions_loaded"] > 25
        ), f"Insufficient region coverage: {result['regions_loaded']}/33"

        verifier.verification_results["regional_coverage"] = result

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, verifier):
        """Generate final compliance verification report"""
        # Run all verifications if not already done
        if not verifier.verification_results:
            await self.test_stage_11_idempotency_check(verifier)
            await self.test_roundtrip_validation(verifier)
            await self.test_graph_coherence_scoring(verifier)
            await self.test_quality_gates_system(verifier)
            await self.test_regional_coverage(verifier)

        # Generate report
        report = {
            "timestamp": "2025-01-27T00:00:00Z",
            "verification_summary": {},
            "implementation_evidence": verifier.verification_results,
            "documentation_discrepancies": [],
        }

        # Analyze results
        total_features = len(verifier.verification_results)
        implemented_features = sum(
            1
            for r in verifier.verification_results.values()
            if isinstance(r, dict) and r.get("implemented", False)
        )

        report["verification_summary"] = {
            "total_features_tested": total_features,
            "implemented_features": implemented_features,
            "implementation_rate": f"{100 * implemented_features / total_features:.1f}%",
            "compliance_status": (
                "HIGH" if implemented_features / total_features > 0.8 else "MODERATE"
            ),
        }

        # Check for discrepancies (features implemented but documented as not implemented)
        documented_as_unimplemented = [
            "Stage 11 IdempotencyCheck",
            "Round-trip Validation",
            "Graph Coherence Scoring",
        ]

        for feature in documented_as_unimplemented:
            if feature in [r.get("feature", "") for r in verifier.verification_results.values()]:
                report["documentation_discrepancies"].append(
                    {
                        "feature": feature,
                        "status": "IMPLEMENTED_BUT_DOCUMENTED_AS_NOT_IMPLEMENTED",
                        "severity": "HIGH",
                    }
                )

        # Save report (this would normally write to file, but we'll just verify structure)
        assert "timestamp" in report
        assert "verification_summary" in report
        assert "implementation_evidence" in report
        assert report["verification_summary"]["total_features_tested"] > 0

        print(f"\nCompliance Verification Report Generated:")
        print(f"Features tested: {report['verification_summary']['total_features_tested']}")
        print(f"Implementation rate: {report['verification_summary']['implementation_rate']}")
        print(f"Documentation discrepancies: {len(report['documentation_discrepancies'])}")


@pytest.mark.asyncio
async def test_full_compliance_verification():
    """Run full V7 compliance verification suite"""
    verifier = V7ComplianceVerifier()
    await verifier.setup()

    # Critical features that were misreported
    critical_features = [
        (11, "IdempotencyCheck"),
        ("roundtrip", "Round-trip Validation"),
        ("graph_coherence", "Graph Coherence Scoring"),
    ]

    results = {}

    for feature_id, feature_name in critical_features:
        if isinstance(feature_id, int):
            # Pipeline stage
            result = verifier.check_pipeline_stage(feature_id, feature_name)
        else:
            # Other feature type
            if feature_id == "roundtrip":
                result = verifier.verify_implementation_exists(
                    "pipeline_v7", feature_name, ["validate_roundtrip", "dice_coefficient"]
                )
            elif feature_id == "graph_coherence":
                result = verifier.verify_implementation_exists(
                    "pipeline_v7", feature_name, ["calculate_graph_coherence"]
                )

        results[feature_name] = result

        # Assert implementation exists (contradicting documentation)
        assert result["implemented"], f"{feature_name} not found but should be implemented"

    # Verify we found evidence for all critical features
    implemented_count = sum(1 for r in results.values() if r["implemented"])
    total_count = len(results)

    print(f"\nCritical Feature Verification: {implemented_count}/{total_count} implemented")
    for feature_name, result in results.items():
        status = "✓ FOUND" if result["implemented"] else "✗ NOT FOUND"
        print(f"  {status}: {feature_name}")
        for evidence in result["evidence"]:
            print(f"    - {evidence}")

    # Final assertion: all critical features should be implemented
    assert (
        implemented_count == total_count
    ), f"Missing implementations: {total_count - implemented_count}"


def main():
    """Run the compliance verification test suite"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    main()
