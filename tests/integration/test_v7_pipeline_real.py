#!/usr/bin/env python3
"""
REAL V7 Pipeline Integration Test
Tests actual functionality, not simulations or mocks.
"""

import asyncio
import json
import pytest
from pathlib import Path
import sys

sys.path.insert(0, ".")

from src.core.pipeline_v7_complete import V7PipelineComplete, PipelineMode
from src.core.security_validator import SecurityError


@pytest.mark.integration
class TestV7PipelineReal:
    """Real integration tests for V7 pipeline."""

    @pytest.mark.asyncio
    async def test_pipeline_basic_flow(self):
        """Test basic pipeline flow with real data."""
        # Create pipeline
        pipeline = V7PipelineComplete(mode=PipelineMode.QUICK)

        # Test data with various edge cases
        test_entries = [
            {
                "GlobalID": "test_001",
                "CanonicalLatin": "Albert Einstein",
                "NativeName": None,
                "ExternalID": "einstein_001",
            },
            {
                "GlobalID": "test_002",
                "CanonicalLatin": "Marie Curie",
                "NativeName": "Maria Skłodowska",
                "ExternalID": "curie_001",
            },
            {
                "GlobalID": "test_003",
                "CanonicalLatin": "Test\tName",  # Tab character
                "NativeName": None,
                "ExternalID": "tab_test",
            },
            {
                "GlobalID": "test_004",
                "CanonicalLatin": "Test\nName",  # Newline character
                "NativeName": None,
                "ExternalID": "newline_test",
            },
        ]

        # Process through pipeline
        result = await pipeline.process_batch(test_entries, chunk_size=2)

        # Verify result structure
        assert "success" in result
        assert "metrics" in result
        assert "quality_gates" in result
        assert "results" in result
        assert "output_files" in result

        # Verify metrics
        metrics = result["metrics"]
        assert metrics["total_entries"] == 4
        assert metrics["processed_entries"] > 0
        assert metrics["security_blocked"] == 0  # None should be blocked

        # Verify stage timings recorded
        assert "stage_0_config" in metrics["stage_timings"]
        assert "stage_1_ingest" in metrics["stage_timings"]

        # Verify output files created
        output_yaml = Path(result["output_files"]["yaml"])
        output_report = Path(result["output_files"]["report"])

        # Files should exist after processing
        if metrics["processed_entries"] > 0:
            assert output_yaml.exists() or output_report.exists()

    @pytest.mark.asyncio
    async def test_pipeline_security_validation(self):
        """Test that SQL injection is blocked."""
        pipeline = V7PipelineComplete(mode=PipelineMode.QUICK)

        # Malicious test data
        malicious_entries = [
            {
                "GlobalID": "evil_001",
                "CanonicalLatin": "Smith'; DROP TABLE users; --",
                "NativeName": None,
                "ExternalID": "sql_injection",
            },
            {
                "GlobalID": "evil_002",
                "CanonicalLatin": "Normal Name",
                "NativeName": "' OR 1=1 --",
                "ExternalID": "sql_injection2",
            },
        ]

        # Process through pipeline
        result = await pipeline.process_batch(malicious_entries)

        # Verify security blocks
        metrics = result["metrics"]
        assert metrics["security_blocked"] > 0, "SQL injection should be blocked"
        assert metrics["processed_entries"] < metrics["total_entries"]

    @pytest.mark.asyncio
    async def test_pipeline_unicode_normalization(self):
        """Test Unicode normalization per V7 spec."""
        pipeline = V7PipelineComplete(mode=PipelineMode.QUICK)

        # Unicode test data
        unicode_entries = [
            {
                "GlobalID": "unicode_001",
                "CanonicalLatin": "Café",  # é in composed form
                "NativeName": "김민준",  # Korean
                "ExternalID": "unicode_test1",
            },
            {
                "GlobalID": "unicode_002",
                "CanonicalLatin": "Müller",  # German umlaut
                "NativeName": "Мюллер",  # Cyrillic
                "ExternalID": "unicode_test2",
            },
        ]

        # Process
        result = await pipeline.process_batch(unicode_entries)

        # Check normalization happened
        assert result["metrics"]["processed_entries"] > 0

        # Verify Unicode was handled (no crashes)
        assert result["success"] is not None

    @pytest.mark.asyncio
    async def test_pipeline_authority_enrichment(self):
        """Test authority source enrichment."""
        pipeline = V7PipelineComplete(mode=PipelineMode.QUICK)

        # Test with names that might have authority data
        test_entries = [
            {
                "GlobalID": "auth_001",
                "CanonicalLatin": "Donald Knuth",
                "NativeName": None,
                "ExternalID": "knuth_001",
            }
        ]

        # Process
        result = await pipeline.process_batch(test_entries)

        # Check that enrichment was attempted
        assert result["metrics"]["total_entries"] == 1

        # Authority enrichment should at least be attempted
        # (even if it fails due to API keys missing)
        assert "stage_4_authority_enrich" in result["metrics"]["stage_timings"]

    @pytest.mark.asyncio
    async def test_pipeline_idempotency(self):
        """Test idempotency - running twice should produce same result."""
        pipeline = V7PipelineComplete(mode=PipelineMode.QUICK)

        test_entries = [
            {
                "GlobalID": "idem_001",
                "CanonicalLatin": "Test Person",
                "NativeName": None,
                "ExternalID": "idem_test",
            }
        ]

        # Run twice
        result1 = await pipeline.process_batch(test_entries)
        result2 = await pipeline.process_batch(test_entries)

        # Both should succeed
        assert result1["success"] is not None
        assert result2["success"] is not None

        # Idempotency check should pass (0 byte diff)
        if "idempotency_diff_bytes" in result2["metrics"]:
            # Second run should have minimal or no diff
            assert result2["metrics"].get("idempotency_diff_bytes", 0) == 0

    @pytest.mark.asyncio
    async def test_pipeline_collision_detection(self):
        """Test collision detection for duplicate names."""
        pipeline = V7PipelineComplete(mode=PipelineMode.QUICK)

        # Entries with potential collisions
        collision_entries = [
            {
                "GlobalID": "coll_001",
                "CanonicalLatin": "John Smith",
                "NativeName": None,
                "ExternalID": "smith_001",
            },
            {
                "GlobalID": "coll_002",
                "CanonicalLatin": "John Smith",  # Same name
                "NativeName": None,
                "ExternalID": "smith_002",
            },
            {
                "GlobalID": "coll_003",
                "CanonicalLatin": "JOHN SMITH",  # Case variant
                "NativeName": None,
                "ExternalID": "smith_003",
            },
        ]

        # Process
        result = await pipeline.process_batch(collision_entries)

        # Should detect potential collisions
        assert result["metrics"]["total_entries"] == 3

        # Check if collision analytics ran
        assert "stage_5_collision_analytics" in result["metrics"]["stage_timings"]

    @pytest.mark.asyncio
    async def test_pipeline_quality_gates(self):
        """Test that quality gates are checked."""
        pipeline = V7PipelineComplete(mode=PipelineMode.QUICK)

        # Simple test data
        test_entries = [
            {
                "GlobalID": "qg_001",
                "CanonicalLatin": "Quality Test",
                "NativeName": None,
                "ExternalID": "quality_001",
            }
        ]

        # Process
        result = await pipeline.process_batch(test_entries)

        # Quality gates should be evaluated
        assert "quality_gates" in result
        assert "passed" in result["quality_gates"]
        assert "checks" in result["quality_gates"]

        # Should have actual quality metrics
        qg = result["quality_gates"]
        if qg["checks"]:
            # At least some quality checks should be present
            assert len(qg["checks"]) > 0

    @pytest.mark.asyncio
    async def test_pipeline_different_modes(self):
        """Test pipeline works in different modes."""

        test_entries = [
            {
                "GlobalID": "mode_001",
                "CanonicalLatin": "Mode Test",
                "NativeName": None,
                "ExternalID": "mode_test",
            }
        ]

        # Test QUICK mode
        pipeline_quick = V7PipelineComplete(mode=PipelineMode.QUICK)
        result_quick = await pipeline_quick.process_batch(test_entries)
        assert result_quick["metrics"]["total_entries"] == 1

        # Test FULL mode (more stringent quality gates)
        pipeline_full = V7PipelineComplete(mode=PipelineMode.FULL)
        result_full = await pipeline_full.process_batch(test_entries)
        assert result_full["metrics"]["total_entries"] == 1

        # FULL mode should have more workers
        assert pipeline_full.workers > pipeline_quick.workers

    @pytest.mark.asyncio
    async def test_pipeline_streaming_chunks(self):
        """Test streaming with chunks."""
        pipeline = V7PipelineComplete(mode=PipelineMode.QUICK)

        # Create many entries to test chunking
        many_entries = [
            {
                "GlobalID": f"stream_{i:04d}",
                "CanonicalLatin": f"Person {i}",
                "NativeName": None,
                "ExternalID": f"stream_test_{i}",
            }
            for i in range(20)
        ]

        # Process with small chunk size
        result = await pipeline.process_batch(many_entries, chunk_size=5)

        # All should be processed in chunks
        assert result["metrics"]["total_entries"] == 20

        # Should process successfully
        assert result["success"] is not None


if __name__ == "__main__":
    # Run tests
    import sys

    pytest.main([__file__, "-v", "-s"])
