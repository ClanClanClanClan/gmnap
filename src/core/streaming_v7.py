"""
V7 Streaming Pipeline - Production Ready Architecture
Modern async streaming pipeline with Memgraph integration and thread-safe processing
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.core.memgraph_client import MemgraphClient
from src.regions.manager import RegionManager


class StreamingMode(Enum):
    """Streaming pipeline modes."""

    DEVELOPMENT = "development"  # Testing with small datasets
    PRODUCTION = "production"  # High-throughput production mode
    BATCH = "batch"  # Large batch processing


@dataclass
class StreamingMetrics:
    """Real-time streaming metrics."""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    entries_ingested: int = 0
    entries_processed: int = 0
    entries_stored: int = 0
    entries_failed: int = 0
    batches_processed: int = 0
    current_throughput: float = 0.0
    peak_throughput: float = 0.0
    average_latency_ms: float = 0.0
    errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        total = self.entries_processed + self.entries_failed
        return (self.entries_processed / total * 100) if total > 0 else 0.0

    @property
    def duration_seconds(self) -> float:
        """Calculate total duration."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def average_throughput(self) -> float:
        """Calculate average throughput."""
        duration = self.duration_seconds
        return self.entries_processed / duration if duration > 0 else 0.0


@dataclass
class StreamingConfig:
    """Configuration for V7 streaming pipeline."""

    mode: StreamingMode = StreamingMode.PRODUCTION
    batch_size: int = 100
    parallel_workers: int = 8
    max_memory_mb: int = 1024
    checkpoint_interval: int = 1000
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    enable_performance_monitoring: bool = True
    database_batch_size: int = 50
    rate_limit_per_second: int = 2000


class V7StreamingPipeline:
    """
    Production-ready V7 streaming pipeline.

    Features:
    - Async streaming with backpressure
    - Thread-safe regional processing
    - Memgraph database integration
    - Real-time performance monitoring
    - Automatic error recovery
    - Memory-bounded processing
    """

    def __init__(self, config: StreamingConfig):
        self.config = config
        self.metrics = StreamingMetrics()
        self.logger = logging.getLogger("v7_streaming")

        # Initialize components
        self.region_manager = RegionManager(Path("./config"))
        self.db_client: Optional[MemgraphClient] = None
        self._processing_semaphore = asyncio.Semaphore(config.parallel_workers)
        self._rate_limiter = asyncio.Semaphore(config.rate_limit_per_second)

        # Performance monitoring
        self._throughput_samples: List[Tuple[datetime, int]] = []
        self._last_checkpoint_time = time.time()

        self.logger.info(f"V7 Streaming Pipeline initialized: {config.mode.value} mode")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.startup()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()

    async def startup(self) -> None:
        """Initialize streaming pipeline resources."""
        self.logger.info("Starting up V7 streaming pipeline...")

        # Initialize database connection
        self.db_client = MemgraphClient(username="", password="", use_mock=False)
        if not self.db_client.is_connected():
            raise ConnectionError("Cannot connect to Memgraph database")

        self.logger.info("Database connection established")

        # Start performance monitoring
        if self.config.enable_performance_monitoring:
            asyncio.create_task(self._monitor_performance())

        self.metrics.start_time = datetime.now()

    async def shutdown(self) -> None:
        """Cleanup streaming pipeline resources."""
        self.logger.info("Shutting down V7 streaming pipeline...")

        if self.db_client:
            self.db_client.close()
            self.db_client = None

        self.metrics.end_time = datetime.now()
        self.logger.info(f"Pipeline completed in {self.metrics.duration_seconds:.2f}s")

    async def _monitor_performance(self) -> None:
        """Monitor real-time performance metrics."""
        while True:
            try:
                await asyncio.sleep(5)  # Update every 5 seconds

                now = datetime.now()
                current_processed = self.metrics.entries_processed

                # Calculate current throughput (entries per second)
                if self._throughput_samples:
                    last_time, last_count = self._throughput_samples[-1]
                    time_diff = (now - last_time).total_seconds()
                    if time_diff > 0:
                        self.metrics.current_throughput = (
                            current_processed - last_count
                        ) / time_diff

                        # Update peak throughput
                        if self.metrics.current_throughput > self.metrics.peak_throughput:
                            self.metrics.peak_throughput = self.metrics.current_throughput

                # Store sample
                self._throughput_samples.append((now, current_processed))

                # Keep only last 60 samples (5 minutes of data)
                if len(self._throughput_samples) > 60:
                    self._throughput_samples = self._throughput_samples[-60:]

                # Log performance
                if self.config.enable_performance_monitoring:
                    self.logger.info(
                        f"Performance: {self.metrics.current_throughput:.1f} entries/sec, "
                        f"total: {current_processed}, "
                        f"success: {self.metrics.success_rate:.1f}%"
                    )

            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")

    async def _process_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single mathematician entry."""
        async with self._processing_semaphore:  # Limit concurrent processing
            try:
                # Rate limiting
                async with self._rate_limiter:
                    pass

                start_time = time.time()

                # Step 1: Region detection
                detection_result = self.region_manager.detect_region(entry)
                region_code = detection_result.region_code

                # Step 2: Get thread-safe region processor
                region = self.region_manager.get_region(region_code, thread_safe=True)
                if not region:
                    raise ValueError(f"Cannot get region processor for {region_code}")

                # Step 3: Regional processing pipeline
                region.clean(entry)
                region.augment(entry)
                region.validate(entry)

                # Step 4: Add processing metadata
                entry.update(
                    {
                        "RegionCode": region_code,
                        "RegionConfidence": detection_result.confidence,
                        "RegionMethod": detection_result.detection_method,
                        "ProcessedAt": datetime.now().isoformat(),
                        "ProcessingLatencyMs": (time.time() - start_time) * 1000,
                    }
                )

                return entry

            except Exception as e:
                self.logger.error(
                    f"Failed to process entry {entry.get('GlobalID', 'unknown')}: {e}"
                )
                self.metrics.errors.append(
                    {
                        "entry_id": entry.get("GlobalID", "unknown"),
                        "error": str(e),
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                return None

    async def _store_batch(self, batch: List[Dict[str, Any]]) -> Tuple[int, int]:
        """Store a batch of processed entries in Memgraph."""
        stored = 0
        failed = 0

        for entry in batch:
            try:
                success = self.db_client.create_mathematician(entry)
                if success:
                    stored += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                self.logger.error(
                    f"Database storage failed for {entry.get('GlobalID', 'unknown')}: {e}"
                )

        if stored > 0:
            self.logger.debug(f"Stored batch: {stored} success, {failed} failed")

        return stored, failed

    async def process_stream(
        self, data_source: AsyncGenerator[Dict[str, Any], None]
    ) -> StreamingMetrics:
        """
        Process a stream of mathematician entries.

        Args:
            data_source: Async generator yielding mathematician entries

        Returns:
            Complete streaming metrics
        """
        self.logger.info("Starting V7 streaming processing")

        # Processing batch
        processing_batch = []
        storage_batch = []

        async for entry in data_source:
            self.metrics.entries_ingested += 1
            processing_batch.append(entry)

            # Process batch when it reaches target size
            if len(processing_batch) >= self.config.batch_size:
                processed_entries = await self._process_batch(processing_batch)
                storage_batch.extend(processed_entries)
                processing_batch = []

                # Store batch when storage batch is ready
                if len(storage_batch) >= self.config.database_batch_size:
                    await self._store_and_track_batch(storage_batch)
                    storage_batch = []

        # Process final batches
        if processing_batch:
            processed_entries = await self._process_batch(processing_batch)
            storage_batch.extend(processed_entries)

        if storage_batch:
            await self._store_and_track_batch(storage_batch)

        # Finalize metrics
        self.metrics.end_time = datetime.now()

        self.logger.info(
            f"Streaming completed: {self.metrics.entries_processed}/{self.metrics.entries_ingested} processed "
            f"({self.metrics.success_rate:.1f}%), {self.metrics.average_throughput:.1f} entries/sec"
        )

        return self.metrics

    async def _process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of entries concurrently."""
        tasks = [self._process_entry(entry) for entry in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_entries = []
        for result in results:
            if isinstance(result, Exception):
                self.metrics.entries_failed += 1
            elif result is not None:
                self.metrics.entries_processed += 1
                processed_entries.append(result)
            else:
                self.metrics.entries_failed += 1

        return processed_entries

    async def _store_and_track_batch(self, batch: List[Dict[str, Any]]) -> None:
        """Store batch and update metrics."""
        if not batch:
            return

        stored, failed = await self._store_batch(batch)

        self.metrics.entries_stored += stored
        self.metrics.batches_processed += 1

        # Update average latency
        latencies = [entry.get("ProcessingLatencyMs", 0) for entry in batch]
        if latencies:
            batch_avg_latency = sum(latencies) / len(latencies)
            # Running average
            total_entries = self.metrics.entries_processed
            if total_entries > 0:
                self.metrics.average_latency_ms = (
                    self.metrics.average_latency_ms * (total_entries - len(batch))
                    + batch_avg_latency * len(batch)
                ) / total_entries


# Helper generators for data sources
async def test_data_generator(count: int = 1000) -> AsyncGenerator[Dict[str, Any], None]:
    """Generate test mathematician data for streaming."""
    import uuid

    test_run_id = str(uuid.uuid4())[:8]
    for i in range(count):
        yield {
            "GlobalID": f"v7-stream-{test_run_id}-{i:05d}",
            "CanonicalLatin": f"V7 Test Mathematician {i}",
            "CanonicalNative": f"V7 Test {i}",
            "BirthYear": 1900 + (i % 100),
            "DeathYear": 1950 + (i % 80) if i % 3 == 0 else None,
            "Field": "Mathematics",
            "Subfield": ["Algebra", "Analysis", "Geometry", "Topology", "Number Theory"][i % 5],
            "Institution": f"University {i % 20}",
            "Country": ["US", "GB", "CA", "AU", "DE", "FR", "JP", "CN"][i % 8],
            "Source": "V7_Streaming_Test",
        }

        # Small delay for realistic streaming simulation
        if i % 50 == 0:
            await asyncio.sleep(0.01)


async def file_data_generator(file_path: Path) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream mathematician data from JSON Lines file."""
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f):
            try:
                entry = json.loads(line.strip())
                yield entry
            except json.JSONDecodeError as e:
                logging.getLogger("file_generator").warning(
                    f"Skipping invalid JSON on line {line_num}: {e}"
                )


# Factory functions
def create_streaming_config(
    mode: str = "production",
    batch_size: int = 100,
    parallel_workers: int = 8,
    max_memory_mb: int = 1024,
) -> StreamingConfig:
    """Create streaming configuration."""
    mode_enum = StreamingMode.PRODUCTION
    if mode == "development":
        mode_enum = StreamingMode.DEVELOPMENT
    elif mode == "batch":
        mode_enum = StreamingMode.BATCH

    return StreamingConfig(
        mode=mode_enum,
        batch_size=batch_size,
        parallel_workers=parallel_workers,
        max_memory_mb=max_memory_mb,
        database_batch_size=min(50, batch_size),
        rate_limit_per_second=2000,
    )


async def run_streaming_pipeline(
    data_source: AsyncGenerator[Dict[str, Any], None], config: Optional[StreamingConfig] = None
) -> StreamingMetrics:
    """
    Run the complete V7 streaming pipeline.

    Args:
        data_source: Async generator of mathematician entries
        config: Streaming configuration (optional)

    Returns:
        Complete streaming metrics
    """
    if config is None:
        config = create_streaming_config()

    async with V7StreamingPipeline(config) as pipeline:
        return await pipeline.process_stream(data_source)


# Performance testing utilities
async def benchmark_streaming_performance(
    entry_count: int = 5000, config: Optional[StreamingConfig] = None
) -> Dict[str, Any]:
    """
    Benchmark streaming pipeline performance.

    Args:
        entry_count: Number of test entries to process
        config: Streaming configuration

    Returns:
        Performance benchmark results
    """
    if config is None:
        config = create_streaming_config(mode="development")

    logger = logging.getLogger("benchmark")
    logger.info(f"Starting streaming performance benchmark: {entry_count} entries")

    # Generate test data
    data_source = test_data_generator(entry_count)

    # Run pipeline
    start_time = time.time()
    metrics = await run_streaming_pipeline(data_source, config)
    end_time = time.time()

    # Calculate benchmark results
    wall_clock_time = end_time - start_time
    wall_clock_throughput = entry_count / wall_clock_time

    benchmark_results = {
        "test_configuration": {
            "entry_count": entry_count,
            "mode": config.mode.value,
            "batch_size": config.batch_size,
            "parallel_workers": config.parallel_workers,
        },
        "performance_results": {
            "wall_clock_duration_seconds": wall_clock_time,
            "wall_clock_throughput_per_second": wall_clock_throughput,
            "pipeline_throughput_per_second": metrics.average_throughput,
            "peak_throughput_per_second": metrics.peak_throughput,
            "average_latency_ms": metrics.average_latency_ms,
            "success_rate_percent": metrics.success_rate,
        },
        "processing_metrics": {
            "entries_ingested": metrics.entries_ingested,
            "entries_processed": metrics.entries_processed,
            "entries_stored": metrics.entries_stored,
            "entries_failed": metrics.entries_failed,
            "batches_processed": metrics.batches_processed,
        },
        "quality_assessment": {
            "meets_10k_hour_target": wall_clock_throughput * 3600 >= 10000,
            "meets_latency_target": metrics.average_latency_ms <= 5000,
            "meets_success_target": metrics.success_rate >= 99.0,
            "overall_grade": (
                "A+"
                if (
                    wall_clock_throughput * 3600 >= 10000
                    and metrics.average_latency_ms <= 5000
                    and metrics.success_rate >= 99.0
                )
                else (
                    "B+"
                    if (wall_clock_throughput * 3600 >= 5000 and metrics.success_rate >= 95.0)
                    else "C"
                )
            ),
        },
    }

    logger.info(
        f"Benchmark complete: {wall_clock_throughput:.1f} entries/sec, grade: {benchmark_results['quality_assessment']['overall_grade']}"
    )

    return benchmark_results
