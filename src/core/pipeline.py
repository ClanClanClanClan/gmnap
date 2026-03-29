"""
Core pipeline architecture for GMNAP.
Implements the multi-stage processing pipeline with error recovery and monitoring.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar

from src.utils.database import DatabaseManager
from src.validation.schema import SchemaValidator

# Type variables for generic pipeline stages
T = TypeVar("T")
R = TypeVar("R")


class PipelineMode(Enum):
    """Pipeline execution modes."""

    QUICK = "quick"  # Minimal processing for testing
    FULL = "full"  # Standard processing
    EXTREME = "extreme"  # Full validation and verification


class StageStatus(Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class StageResult:
    """Result from a pipeline stage execution."""

    stage_name: str
    status: StageStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    records_processed: int = 0
    records_failed: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    output: Any = None

    @property
    def duration(self) -> float:
        """Calculate stage duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        total = self.records_processed + self.records_failed
        if total == 0:
            return 100.0
        return (self.records_processed / total) * 100


class PipelineStage(ABC, Generic[T, R]):
    """Abstract base class for pipeline stages."""

    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"pipeline.{name}")
        self._result = StageResult(
            stage_name=name, status=StageStatus.PENDING, start_time=datetime.now()
        )

    @abstractmethod
    async def process(self, input_data: T) -> R:
        """Process input data and return output."""
        pass

    @abstractmethod
    async def validate_input(self, input_data: T) -> bool:
        """Validate input data before processing."""
        pass

    async def setup(self) -> None:
        """Setup stage resources."""
        pass

    async def cleanup(self) -> None:
        """Cleanup stage resources."""
        pass

    async def execute(self, input_data: T) -> StageResult:
        """Execute the stage with error handling and monitoring."""
        self._result.status = StageStatus.RUNNING
        self._result.start_time = datetime.now()

        try:
            # Setup
            await self.setup()

            # Validate input
            if not await self.validate_input(input_data):
                raise ValueError(f"Invalid input for stage {self.name}")

            # Process
            self.logger.info(f"Starting {self.name} stage")
            output = await self.process(input_data)

            # Update result
            self._result.status = StageStatus.COMPLETED
            self._result.output = output

        except Exception as e:
            self.logger.error(f"Stage {self.name} failed: {e}")
            self._result.status = StageStatus.FAILED
            self._result.errors.append(
                {"error": str(e), "type": type(e).__name__, "timestamp": datetime.now().isoformat()}
            )
            raise

        finally:
            self._result.end_time = datetime.now()
            await self.cleanup()

        return self._result


@dataclass
class PipelineConfig:
    """Configuration for the pipeline."""

    mode: PipelineMode = PipelineMode.FULL
    max_retries: int = 3
    retry_delay: float = 1.0
    checkpoint_interval: int = 1000
    batch_size: int = 100
    parallel_workers: int = 4
    enable_monitoring: bool = True
    enable_checkpointing: bool = True
    checkpoint_dir: Path = Path("./cache/checkpoints")
    log_dir: Path = Path("./logs")


class Pipeline:
    """Main pipeline orchestrator."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.stages: List[PipelineStage] = []
        self.logger = logging.getLogger("pipeline")
        self._setup_logging()
        self._checkpoints: Dict[str, Any] = {}
        self._metrics: Dict[str, Any] = {}
        self._start_time: Optional[datetime] = None
        self._db_manager: Optional[DatabaseManager] = None

    def _setup_logging(self):
        """Configure pipeline logging."""
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        # File handler for pipeline logs
        log_file = self.config.log_dir / f"pipeline_{datetime.now():%Y%m%d_%H%M%S}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)

        # Formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)

    def add_stage(self, stage: PipelineStage) -> None:
        """Add a stage to the pipeline."""
        self.stages.append(stage)
        self.logger.info(f"Added stage: {stage.name}")

    async def _save_checkpoint(self, stage_name: str, data: Any) -> None:
        """Save checkpoint data."""
        if not self.config.enable_checkpointing:
            return

        self.config.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_file = self.config.checkpoint_dir / f"{stage_name}_checkpoint.json"

        checkpoint_data = {
            "stage": stage_name,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "metrics": self._metrics,
        }

        with open(checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f, indent=2, default=str)

        self.logger.info(f"Saved checkpoint for stage {stage_name}")

    async def _load_checkpoint(self, stage_name: str) -> Optional[Any]:
        """Load checkpoint data if available."""
        if not self.config.enable_checkpointing:
            return None

        checkpoint_file = self.config.checkpoint_dir / f"{stage_name}_checkpoint.json"

        if checkpoint_file.exists():
            with open(checkpoint_file, "r") as f:
                checkpoint_data = json.load(f)

            self.logger.info(f"Loaded checkpoint for stage {stage_name}")
            return checkpoint_data.get("data")

        return None

    async def _execute_stage_with_retry(self, stage: PipelineStage, input_data: Any) -> StageResult:
        """Execute a stage with retry logic."""
        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                result = await stage.execute(input_data)
                return result

            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Stage {stage.name} failed (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )

                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    stage._result.status = StageStatus.RETRYING

        # All retries failed
        if last_error:
            raise last_error

        return stage._result

    @asynccontextmanager
    async def _database_session(self):
        """Provide database session for pipeline."""
        self._db_manager = DatabaseManager()
        try:
            yield self._db_manager
        finally:
            if self._db_manager:
                self._db_manager.close()
                self._db_manager = None

    async def execute(self, initial_input: Any = None) -> Dict[str, Any]:
        """Execute the full pipeline."""
        self._start_time = datetime.now()
        self.logger.info(f"Starting pipeline execution in {self.config.mode.value} mode")

        results = []
        current_input = initial_input

        async with self._database_session():
            for i, stage in enumerate(self.stages):
                self.logger.info(f"Executing stage {i+1}/{len(self.stages)}: {stage.name}")

                # Check for checkpoint
                checkpoint_data = await self._load_checkpoint(stage.name)
                if checkpoint_data is not None:
                    self.logger.info(f"Resuming from checkpoint for stage {stage.name}")
                    current_input = checkpoint_data
                    continue

                # Execute stage
                try:
                    result = await self._execute_stage_with_retry(stage, current_input)
                    results.append(result)

                    # Save checkpoint
                    await self._save_checkpoint(stage.name, result.output)

                    # Use output as input for next stage
                    current_input = result.output

                    # Update metrics
                    self._update_metrics(result)

                except Exception as e:
                    self.logger.error(f"Pipeline failed at stage {stage.name}: {e}")

                    # Determine if we should continue
                    if self.config.mode == PipelineMode.EXTREME:
                        raise  # Fail fast in extreme mode

                    # Skip failed stage and all remaining stages in other modes
                    stage._result.status = StageStatus.SKIPPED
                    results.append(stage._result)

                    # Mark all remaining stages as skipped
                    for remaining_stage in self.stages[i + 1 :]:
                        remaining_result = StageResult(
                            stage_name=remaining_stage.name,
                            status=StageStatus.SKIPPED,
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            output=None,
                            errors=[{"message": "Skipped due to earlier stage failure"}],
                        )
                        results.append(remaining_result)
                    break

        # Generate final report
        end_time = datetime.now()
        duration = (end_time - self._start_time).total_seconds()

        return {
            "status": (
                "completed"
                if all(r.status == StageStatus.COMPLETED for r in results)
                else "partial"
            ),
            "mode": self.config.mode.value,
            "start_time": self._start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "stages": [self._stage_result_to_dict(r) for r in results],
            "metrics": self._metrics,
        }

    def _update_metrics(self, result: StageResult) -> None:
        """Update pipeline metrics."""
        if not self.config.enable_monitoring:
            return

        stage_metrics = {
            "duration": result.duration,
            "records_processed": result.records_processed,
            "records_failed": result.records_failed,
            "success_rate": result.success_rate,
            "status": result.status.value,
        }

        self._metrics[result.stage_name] = stage_metrics

        # Update global metrics
        self._metrics["total_records_processed"] = (
            self._metrics.get("total_records_processed", 0) + result.records_processed
        )
        self._metrics["total_records_failed"] = (
            self._metrics.get("total_records_failed", 0) + result.records_failed
        )

    def _stage_result_to_dict(self, result: StageResult) -> Dict[str, Any]:
        """Convert stage result to dictionary."""
        return {
            "name": result.stage_name,
            "status": result.status.value,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration": result.duration,
            "records_processed": result.records_processed,
            "records_failed": result.records_failed,
            "success_rate": result.success_rate,
            "errors": result.errors,
            "metrics": result.metrics,
        }


# Example concrete stages for initial testing
class DataIngestionStage(PipelineStage[None, List[Dict[str, Any]]]):
    """Stage for ingesting data from various sources."""

    async def validate_input(self, input_data: None) -> bool:
        return True  # No input validation needed for first stage

    async def process(self, input_data: None) -> List[Dict[str, Any]]:
        """Ingest data from configured sources."""
        # Placeholder implementation
        self.logger.info("Ingesting data from sources...")

        # Simulate data ingestion
        data = []
        for i in range(10):  # Small test dataset
            data.append(
                {"id": f"test_{i}", "name": f"Test Mathematician {i}", "region": "north_america"}
            )

        self._result.records_processed = len(data)
        return data


class ValidationStage(PipelineStage[List[Dict[str, Any]], List[Dict[str, Any]]]):
    """Stage for validating records against schema."""

    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.validator = SchemaValidator()

    async def validate_input(self, input_data: List[Dict[str, Any]]) -> bool:
        return isinstance(input_data, list)

    async def process(self, input_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate each record against schema."""
        valid_records = []

        for record in input_data:
            try:
                # validate_entry returns a tuple (is_valid, errors)
                is_valid, errors = self.validator.validate_entry(record)
                if is_valid:
                    valid_records.append(record)
                    self._result.records_processed += 1
                else:
                    self._result.records_failed += 1
            except Exception as e:
                self.logger.warning(f"Validation failed for record {record.get('id')}: {e}")
                self._result.records_failed += 1

        return valid_records


class GMNAPPipeline:
    """Stub for GMNAPPipeline"""

    def __init__(self, *args, **kwargs):
        pass
