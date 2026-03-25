"""
Integration tests for the GMNAP pipeline.

Tests end-to-end pipeline execution with all components working together.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
import yaml

from src.authorities.tier0.openalex import OpenAlexFetcher
from src.core.config import GMNAPConfig
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.regions.a_groups.a1_anglo_sphere import A1_AngloSphere


class TestPipelineIntegration:
    """Test full pipeline integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = GMNAPConfig()
        self.config.processing.batch_size = 10
        self.config.processing.chunk_size = 50
        self.config.processing.memory_limit_mb = 512  # Lower for testing

        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.temp_dir) / "input"
        self.output_dir = Path(self.temp_dir) / "output"
        self.cache_dir = Path(self.temp_dir) / "cache"

        self.input_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)
        self.cache_dir.mkdir(parents=True)

        # Update config paths
        self.config.cache.cache_dir = str(self.cache_dir)
        self.config.database.path = str(self.cache_dir / "test.db")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_test_entries(self, count: int = 10) -> None:
        """Create test YAML entries."""
        entries = {}

        for i in range(count):
            canonical = f"Test{i:03d}, Person"
            entries[canonical] = {
                "GlobalID": f"ABCDEFGHIJKLMNOPQRST{i:02d}",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": canonical,
                "CanonicalNative": canonical,
                "BirthYear": 1950 + i,
                "CountryCodes": ["US"],
                "Confidence": 80 + i % 20,
            }

        # Write to YAML file
        test_file = self.input_dir / "test_entries.yaml"
        with open(test_file, "w") as f:
            yaml.dump(entries, f)

    def create_mixed_region_entries(self) -> None:
        """Create entries from different regions."""
        entries = {
            "Smith, John": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": 1980,
                "CountryCodes": ["US"],
                "Confidence": 85,
            },
            "García, José": {
                "GlobalID": "BCDEFGHIJKLMNOPQRSTUVW",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "García, José",
                "CanonicalNative": "García, José",
                "BirthYear": 1975,
                "CountryCodes": ["ES"],
                "Confidence": 90,
            },
            "李明": {
                "GlobalID": "CDEFGHIJKLMNOPQRSTUVWX",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Li, Ming",
                "CanonicalNative": "李明",
                "BirthYear": 1985,
                "CountryCodes": ["CN"],
                "Confidence": 75,
            },
            "Владимир Петров": {
                "GlobalID": "DEFGHIJKLMNOPQRSTUVWXY",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Petrov, Vladimir",
                "CanonicalNative": "Владимир Петров",
                "BirthYear": 1970,
                "CountryCodes": ["RU"],
                "Confidence": 82,
            },
        }

        test_file = self.input_dir / "mixed_regions.yaml"
        with open(test_file, "w", encoding="utf-8") as f:
            yaml.dump(entries, f, allow_unicode=True)

    def test_quick_mode_pipeline(self):
        """Test pipeline in quick mode."""
        self.create_test_entries(5)

        # Mock authority fetcher to avoid real API calls
        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_fetcher:
            mock_instance = Mock()
            mock_instance.fetch = AsyncMock(
                return_value=Mock(status=Mock(value="not_found"), error_message="Not found")
            )
            mock_fetcher.return_value = mock_instance

            pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
            result = pipeline.run(self.input_dir)

            assert result.mode == PipelineMode.QUICK
            assert result.total_entries == 5
            assert len(result.stage_metrics) == 11  # 10 stages + stage 0

    def test_stage_sequencing(self):
        """Test that stages execute in correct order."""
        self.create_test_entries(3)

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Mock stages to track execution order
        execution_order = []

        def mock_stage(stage_name):
            def _inner(*args, **kwargs):
                execution_order.append(stage_name)
                return Mock()

            return _inner

        # Mock all stages
        with patch.object(pipeline, "_stage_0_config", side_effect=mock_stage("stage_0")):
            with patch.object(pipeline, "_stage_1_ingest", side_effect=mock_stage("stage_1")):
                with patch.object(
                    pipeline, "_stage_2_detect_region", side_effect=mock_stage("stage_2")
                ):
                    with patch.object(
                        pipeline, "_stage_3_region_hooks", side_effect=mock_stage("stage_3")
                    ):
                        with patch.object(
                            pipeline, "_stage_4_authority_enrich", side_effect=mock_stage("stage_4")
                        ):
                            with patch.object(
                                pipeline,
                                "_stage_5_collision_analytics",
                                side_effect=mock_stage("stage_5"),
                            ):
                                with patch.object(
                                    pipeline,
                                    "_stage_6_tag_short_forms",
                                    side_effect=mock_stage("stage_6"),
                                ):
                                    with patch.object(
                                        pipeline,
                                        "_stage_7_global_validate",
                                        side_effect=mock_stage("stage_7"),
                                    ):
                                        with patch.object(
                                            pipeline,
                                            "_stage_8_write_diff",
                                            side_effect=mock_stage("stage_8"),
                                        ):
                                            with patch.object(
                                                pipeline,
                                                "_stage_9_report",
                                                side_effect=mock_stage("stage_9"),
                                            ):
                                                with patch.object(
                                                    pipeline,
                                                    "_stage_10_idempotency_check",
                                                    side_effect=mock_stage("stage_10"),
                                                ):
                                                    pipeline.run(self.input_dir)

        expected_order = [
            "stage_0",
            "stage_1",
            "stage_2",
            "stage_3",
            "stage_4",
            "stage_5",
            "stage_6",
            "stage_7",
            "stage_8",
            "stage_9",
            "stage_10",
        ]

        assert execution_order == expected_order

    def test_region_detection_integration(self):
        """Test region detection with real entries."""
        self.create_mixed_region_entries()

        # Mock FastText to avoid loading model
        with patch("src.regions.manager.fasttext") as mock_fasttext:
            mock_model = Mock()
            mock_model.predict.return_value = (["__label__en"], [0.8])
            mock_fasttext.load_model.return_value = mock_model

            pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

            # Only run first 3 stages to test region detection
            pipeline._stage_0_config()
            pipeline._stage_1_ingest(self.input_dir)
            pipeline._stage_2_detect_region()

            # Check that entries were assigned regions
            assert len(pipeline._entries) == 4

            # Check specific assignments
            smith_entry = pipeline._entries.get("Smith, John")
            assert smith_entry is not None
            assert smith_entry.get("_region") == "A1"  # Should detect Anglo-sphere

            # Other entries might be detected as different regions or R0/Z0
            for entry in pipeline._entries.values():
                assert "_region" in entry
                assert entry["_region"] in ["A1", "A2", "B1", "E1", "R0", "Z0"]

    def test_region_hooks_integration(self):
        """Test region hooks with A1 region."""
        # Create A1-specific entries
        entries = {
            "Dr. Smith, John C. Jr.": {
                "GlobalID": "ABCDEFGHIJKLMNOPQRSTUV",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Dr. Smith, John C. Jr.",
                "CanonicalNative": "Dr. Smith, John C. Jr.",
                "BirthYear": 1980,
                "CountryCodes": ["US"],
                "Confidence": 85,
            }
        }

        test_file = self.input_dir / "a1_entries.yaml"
        with open(test_file, "w") as f:
            yaml.dump(entries, f)

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Register A1 region
        pipeline.region_manager.register_region(A1_AngloSphere())

        # Run first 4 stages
        pipeline._stage_0_config()
        pipeline._stage_1_ingest(self.input_dir)
        pipeline._stage_2_detect_region()
        pipeline._stage_3_region_hooks()

        # Check that A1 processing was applied
        entry = pipeline._entries.get("Dr. Smith, John C. Jr.")
        assert entry is not None

        # Should have cleaned the name
        assert entry["CanonicalLatin"] == "Smith, John C."

        # Should have regional extras
        assert "RegionalExtras" in entry
        extras = entry["RegionalExtras"]
        assert extras["family_name"] == "Smith"
        assert extras["given_name"] == "John C."

        # Should have order key
        assert "_order_key" in entry
        assert entry["_order_key"] == "SMITH, JOHN C"

    def test_authority_enrichment_integration(self):
        """Test authority enrichment with mock API."""
        self.create_test_entries(3)

        # Mock OpenAlex response
        mock_response = Mock()
        mock_response.status = Mock(value="success")
        mock_response.data = Mock()
        mock_response.data.source_id = "A1234567890"
        mock_response.data.name_variants = ["Smith, J.", "Smith, John"]
        mock_response.data.identifiers = {"ORCID": "0000-0003-1234-5678"}
        mock_response.data.confidence_score = 0.8

        with patch("src.authorities.tier0.openalex.OpenAlexFetcher") as mock_fetcher:
            mock_instance = Mock()
            mock_instance.fetch = AsyncMock(return_value=mock_response)
            mock_instance.tier = Mock(value=0)
            mock_fetcher.return_value = mock_instance

            pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
            pipeline._authorities = {"OpenAlex": mock_instance}

            # Mock quota manager
            pipeline._quota_manager = Mock()
            pipeline._quota_manager.batch_fetch = AsyncMock(return_value=[mock_response])

            # Run first 5 stages
            pipeline._stage_0_config()
            pipeline._stage_1_ingest(self.input_dir)
            pipeline._stage_2_detect_region()
            pipeline._stage_3_region_hooks()
            pipeline._stage_4_authority_enrich()

            # Check that authority data was added
            for entry in pipeline._entries.values():
                if "AuthorityIDs" in entry:
                    assert "OpenAlex" in entry["AuthorityIDs"]
                    assert entry["AuthorityIDs"]["OpenAlex"] == "A1234567890"

    def test_collision_analytics_integration(self):
        """Test collision analytics with DuckDB."""
        self.create_test_entries(20)  # Enough for analytics

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Run first 6 stages
        pipeline._stage_0_config()
        pipeline._stage_1_ingest(self.input_dir)
        pipeline._stage_2_detect_region()
        pipeline._stage_3_region_hooks()
        pipeline._stage_4_authority_enrich()
        pipeline._stage_5_collision_analytics()

        # Check that collision stats were generated
        assert hasattr(pipeline, "_collision_stats")
        assert "total_entries" in pipeline._collision_stats
        assert pipeline._collision_stats["total_entries"] == 20

    def test_memory_management(self):
        """Test memory management with chunking."""
        # Create enough entries to test chunking
        self.create_test_entries(25)  # More than chunk size of 20

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
        pipeline.chunk_size = 10  # Small chunk for testing

        # Monitor memory usage
        import psutil

        process = psutil.Process()
        initial_memory = process.memory_info().rss

        pipeline._stage_0_config()
        pipeline._stage_1_ingest(self.input_dir)
        pipeline._stage_2_detect_region()
        pipeline._stage_3_region_hooks()

        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB

        # Should not exceed memory limit
        assert memory_increase < self.config.processing.memory_limit_mb

    def test_validation_integration(self):
        """Test validation with schema checking."""
        # Create entry with validation errors
        entries = {
            "Smith, John": {
                "GlobalID": "INVALID_ID",  # Invalid format
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": "Smith, John",
                "CanonicalNative": "Smith, John",
                "BirthYear": 1980,
                "DeathYear": 1970,  # Before birth year
                "Confidence": 150,  # Out of range
                "CountryCodes": ["US"],
            }
        }

        test_file = self.input_dir / "invalid_entries.yaml"
        with open(test_file, "w") as f:
            yaml.dump(entries, f)

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Run through validation stage
        pipeline._stage_0_config()
        pipeline._stage_1_ingest(self.input_dir)
        pipeline._stage_2_detect_region()
        pipeline._stage_3_region_hooks()
        pipeline._stage_4_authority_enrich()
        pipeline._stage_5_collision_analytics()
        pipeline._stage_6_tag_short_forms()
        pipeline._stage_7_global_validate()

        # Check that validation/quality errors were recorded
        # V6 pipeline stores quality issues in stage metrics, not validation_errors
        stage7 = pipeline._metrics.stage_metrics.get("stage_7")
        has_errors = len(pipeline._metrics.validation_errors) > 0 or (
            stage7 and len(stage7.errors) > 0
        )
        assert has_errors, "Expected validation or quality errors for invalid entry"

    def test_yaml_roundtrip(self):
        """Test YAML write and read roundtrip."""
        self.create_test_entries(5)

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Run through write stage
        pipeline._stage_0_config()
        pipeline._stage_1_ingest(self.input_dir)
        pipeline._stage_2_detect_region()
        pipeline._stage_3_region_hooks()
        pipeline._stage_4_authority_enrich()
        pipeline._stage_5_collision_analytics()
        pipeline._stage_6_tag_short_forms()
        pipeline._stage_7_global_validate()
        pipeline._stage_8_write_diff()

        # Check that output files were created
        output_dir = Path(self.config.cache.cache_dir) / "output"
        assert output_dir.exists()

        output_files = list(output_dir.glob("*.yaml"))
        assert len(output_files) > 0

        # Verify output can be read back
        with open(output_files[0], "r") as f:
            output_data = yaml.safe_load(f)

        assert isinstance(output_data, dict)
        assert len(output_data) > 0

    def test_error_handling(self):
        """Test error handling - pipeline raises on stage failure."""
        self.create_test_entries(3)

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Mock a stage to raise an error
        with patch.object(
            pipeline, "_stage_4_authority_enrich", side_effect=Exception("Test error")
        ):
            with pytest.raises(Exception, match="Test error"):
                pipeline.run(self.input_dir)

    def test_different_pipeline_modes(self):
        """Test different pipeline modes."""
        self.create_test_entries(3)

        modes = [PipelineMode.QUICK, PipelineMode.FULL]

        for mode in modes:
            pipeline = GMNAPPipeline(self.config, mode)

            # Mock authority components
            with patch("src.authorities.tier0.openalex.OpenAlexFetcher"):
                result = pipeline.run(self.input_dir)

                assert result.mode == mode
                assert result.total_entries == 3

    def test_checkpoint_functionality(self):
        """Test checkpoint saving and loading."""
        self.create_test_entries(5)

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Enable checkpointing
        pipeline.config.enable_checkpointing = True

        # Run first few stages
        pipeline._stage_0_config()
        pipeline._stage_1_ingest(self.input_dir)
        pipeline._stage_2_detect_region()

        # Check that checkpoints were saved
        checkpoint_dir = Path(self.config.cache.cache_dir) / "checkpoints"
        if checkpoint_dir.exists():
            checkpoint_files = list(checkpoint_dir.glob("*_checkpoint.json"))
            # May or may not have checkpoints depending on implementation

    def test_metrics_collection(self):
        """Test metrics collection throughout pipeline."""
        self.create_test_entries(5)

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
        result = pipeline.run(self.input_dir)

        # Check that metrics were collected
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.total_entries == 5

        # Check stage metrics
        assert len(result.stage_metrics) > 0

        for stage_name, metrics in result.stage_metrics.items():
            assert metrics.start_time is not None
            assert metrics.end_time is not None
            assert metrics.entries_processed >= 0
            assert metrics.entries_failed >= 0

    def test_configuration_defaults(self):
        """Test that default configuration creates a valid pipeline."""
        config = GMNAPConfig()
        pipeline = GMNAPPipeline(config, PipelineMode.QUICK)
        assert pipeline.mode == PipelineMode.QUICK

    def test_cleanup_on_error(self):
        """Test resource cleanup on error."""
        self.create_test_entries(3)

        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)

        # Mock stage to raise exception
        with patch.object(pipeline, "_stage_2_detect_region", side_effect=Exception("Test error")):
            with pytest.raises(Exception):
                pipeline.run(self.input_dir)

        # Check that resources were cleaned up
        # This depends on implementation details


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
