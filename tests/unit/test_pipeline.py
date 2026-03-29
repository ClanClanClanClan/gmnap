"""
Unit tests for pipeline components.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from src.core.pipeline import (
    DataIngestionStage,
    Pipeline,
    PipelineConfig,
    PipelineMode,
    PipelineStage,
    StageResult,
    StageStatus,
    ValidationStage,
)


# Test fixtures
@pytest.fixture
def pipeline_config():
    """Create test pipeline configuration."""
    return PipelineConfig(
        mode=PipelineMode.FULL,
        max_retries=2,
        retry_delay=0.1,
        checkpoint_interval=10,
        batch_size=5,
        enable_monitoring=True,
        enable_checkpointing=False,  # Disable for tests
    )


@pytest.fixture
def pipeline(pipeline_config):
    """Create test pipeline instance."""
    return Pipeline(pipeline_config)


# Test Stage Implementation
class TestStage(PipelineStage[str, str]):
    """Test pipeline stage for unit tests."""

    async def validate_input(self, input_data: str) -> bool:
        return isinstance(input_data, str)

    async def process(self, input_data: str) -> str:
        self._result.records_processed = 1
        return f"processed_{input_data}"


class FailingStage(PipelineStage[str, str]):
    """Test stage that always fails."""

    async def validate_input(self, input_data: str) -> bool:
        return True

    async def process(self, input_data: str) -> str:
        raise ValueError("Test error")


# Pipeline tests
class TestPipeline:
    """Test Pipeline class."""

    def test_pipeline_creation(self, pipeline_config):
        """Test pipeline creation with config."""
        pipeline = Pipeline(pipeline_config)
        assert pipeline.config == pipeline_config
        assert len(pipeline.stages) == 0
        assert pipeline._metrics == {}

    def test_add_stage(self, pipeline):
        """Test adding stages to pipeline."""
        stage1 = TestStage("test1", {})
        stage2 = TestStage("test2", {})

        pipeline.add_stage(stage1)
        pipeline.add_stage(stage2)

        assert len(pipeline.stages) == 2
        assert pipeline.stages[0] == stage1
        assert pipeline.stages[1] == stage2

    @pytest.mark.asyncio
    async def test_pipeline_execution(self, pipeline):
        """Test basic pipeline execution."""
        stage1 = TestStage("stage1", {})
        stage2 = TestStage("stage2", {})

        pipeline.add_stage(stage1)
        pipeline.add_stage(stage2)

        result = await pipeline.execute("input")

        assert result["status"] == "completed"
        assert result["mode"] == "full"
        assert len(result["stages"]) == 2
        assert result["stages"][0]["name"] == "stage1"
        assert result["stages"][0]["status"] == "completed"
        assert result["stages"][1]["name"] == "stage2"
        assert result["stages"][1]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_pipeline_stage_failure(self, pipeline):
        """Test pipeline behavior on stage failure."""
        stage1 = TestStage("stage1", {})
        stage2 = FailingStage("failing", {})
        stage3 = TestStage("stage3", {})

        pipeline.add_stage(stage1)
        pipeline.add_stage(stage2)
        pipeline.add_stage(stage3)

        # In non-extreme mode, pipeline should skip failed stage
        result = await pipeline.execute("input")

        assert result["status"] == "partial"
        assert result["stages"][0]["status"] == "completed"
        assert result["stages"][1]["status"] == "skipped"
        assert result["stages"][2]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_pipeline_extreme_mode_failure(self):
        """Test pipeline fails fast in extreme mode."""
        config = PipelineConfig(mode=PipelineMode.EXTREME, enable_checkpointing=False)
        pipeline = Pipeline(config)

        pipeline.add_stage(TestStage("stage1", {}))
        pipeline.add_stage(FailingStage("failing", {}))

        with pytest.raises(ValueError, match="Test error"):
            await pipeline.execute("input")

    @pytest.mark.asyncio
    async def test_pipeline_metrics_update(self, pipeline):
        """Test pipeline metrics are updated during execution."""
        stage = TestStage("test", {})
        pipeline.add_stage(stage)

        await pipeline.execute("input")

        assert "test" in pipeline._metrics
        assert pipeline._metrics["test"]["records_processed"] == 1
        assert pipeline._metrics["test"]["status"] == "completed"
        assert pipeline._metrics["total_records_processed"] == 1


# Stage tests
class TestPipelineStage:
    """Test PipelineStage base class."""

    def test_stage_creation(self):
        """Test stage creation."""
        stage = TestStage("test_stage", {"key": "value"})

        assert stage.name == "test_stage"
        assert stage.config == {"key": "value"}
        assert stage._result.stage_name == "test_stage"
        assert stage._result.status == StageStatus.PENDING

    @pytest.mark.asyncio
    async def test_stage_execution(self):
        """Test stage execution flow."""
        stage = TestStage("test", {})
        result = await stage.execute("input")

        assert result.status == StageStatus.COMPLETED
        assert result.records_processed == 1
        assert result.output == "processed_input"
        assert result.duration > 0

    @pytest.mark.asyncio
    async def test_stage_validation_failure(self):
        """Test stage validation failure."""
        stage = TestStage("test", {})

        with pytest.raises(ValueError, match="Invalid input"):
            await stage.execute(123)  # Wrong type

    @pytest.mark.asyncio
    async def test_stage_error_handling(self):
        """Test stage error handling."""
        stage = FailingStage("failing", {})

        with pytest.raises(ValueError, match="Test error"):
            await stage.execute("input")

        assert stage._result.status == StageStatus.FAILED
        assert len(stage._result.errors) == 1
        assert stage._result.errors[0]["error"] == "Test error"


# StageResult tests
class TestStageResult:
    """Test StageResult class."""

    def test_stage_result_duration(self):
        """Test duration calculation."""
        start = datetime.now()
        result = StageResult(
            stage_name="test", status=StageStatus.COMPLETED, start_time=start
        )

        # No end time yet
        assert result.duration == 0.0

        # Set end time
        import time

        time.sleep(0.1)
        result.end_time = datetime.now()

        assert result.duration > 0.1

    def test_stage_result_success_rate(self):
        """Test success rate calculation."""
        result = StageResult(
            stage_name="test",
            status=StageStatus.COMPLETED,
            start_time=datetime.now(),
            records_processed=80,
            records_failed=20,
        )

        assert result.success_rate == 80.0

        # Test with no records
        result2 = StageResult(
            stage_name="test", status=StageStatus.COMPLETED, start_time=datetime.now()
        )
        assert result2.success_rate == 100.0


# Concrete stage tests
class TestDataIngestionStage:
    """Test DataIngestionStage."""

    @pytest.mark.asyncio
    async def test_data_ingestion(self):
        """Test data ingestion stage."""
        stage = DataIngestionStage("ingestion", {})
        result = await stage.execute(None)

        assert result.status == StageStatus.COMPLETED
        assert result.records_processed == 10
        assert isinstance(result.output, list)
        assert len(result.output) == 10
        assert all("id" in record for record in result.output)


class TestValidationStage:
    """Test ValidationStage."""

    @pytest.mark.asyncio
    async def test_validation_stage(self):
        """Test validation stage with valid data."""
        stage = ValidationStage("validation", {})

        # Mock valid data
        input_data = [
            {"id": "1", "name": "Test 1", "global_id": "GMNAP-TEST-0001"},
            {"id": "2", "name": "Test 2", "global_id": "GMNAP-TEST-0002"},
        ]

        with patch.object(stage.validator, "validate_entry", return_value=True):
            result = await stage.execute(input_data)

        assert result.status == StageStatus.COMPLETED
        assert result.records_processed == 2
        assert result.records_failed == 0
        assert len(result.output) == 2

    @pytest.mark.asyncio
    async def test_validation_stage_with_failures(self):
        """Test validation stage with some invalid data."""
        stage = ValidationStage("validation", {})

        input_data = [
            {"id": "1", "name": "Valid"},
            {"id": "2", "name": "Invalid"},
            {"id": "3", "name": "Valid"},
        ]

        # Mock validation to fail for "Invalid"
        def mock_validate(record):
            return record["name"] != "Invalid"

        with patch.object(stage.validator, "validate_entry", side_effect=mock_validate):
            result = await stage.execute(input_data)

        assert result.status == StageStatus.COMPLETED
        assert result.records_processed == 2
        assert result.records_failed == 1
        assert len(result.output) == 2


# Pipeline Mode tests
class TestPipelineMode:
    """Test PipelineMode enum."""

    def test_pipeline_modes(self):
        """Test pipeline mode values."""
        assert PipelineMode.QUICK.value == "quick"
        assert PipelineMode.FULL.value == "full"
        assert PipelineMode.EXTREME.value == "extreme"


# Integration test
class TestPipelineIntegration:
    """Integration tests for pipeline components."""

    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self):
        """Test complete pipeline flow with multiple stages."""
        config = PipelineConfig(
            mode=PipelineMode.FULL, enable_checkpointing=False, enable_monitoring=True
        )
        pipeline = Pipeline(config)

        # Add stages
        pipeline.add_stage(DataIngestionStage("ingestion", {}))
        pipeline.add_stage(ValidationStage("validation", {}))

        # Mock validation to pass all
        with patch(
            "src.validation.schema.SchemaValidator.validate_entry", return_value=True
        ):
            result = await pipeline.execute()

        assert result["status"] == "completed"
        assert len(result["stages"]) == 2
        assert (
            result["metrics"]["total_records_processed"] == 20
        )  # 10 from ingestion + 10 from validation
        assert all(s["status"] == "completed" for s in result["stages"])
