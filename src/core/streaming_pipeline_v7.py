#!/usr/bin/env python3
"""
V7-Compliant Streaming Pipeline Implementation
Processes data in 8,000-entry chunks with constant memory usage
"""

import gc
import json
import logging
import psutil
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
import time

from src.regions.manager_optimized import RegionManager
from src.core.security_validator import security_validator
from src.core.globalid import GlobalIDGenerator
from src.validation.schema import SchemaValidator

logger = logging.getLogger(__name__)


@dataclass
class V7StreamConfig:
    """V7-compliant streaming configuration"""

    chunk_size: int = 8000  # From v7 spec
    peak_memory_limit_gb: float = 6.0  # From v7 spec: "6GB RSS"
    output_dir: Path = Path("output/chunks")
    enable_compression: bool = True  # zstd compression from spec


class V7StreamingPipeline:
    """
    V7-compliant streaming pipeline that processes data in fixed-size chunks
    to maintain constant memory usage regardless of dataset size.
    """

    def __init__(self, config: Optional[V7StreamConfig] = None):
        self.config = config or V7StreamConfig()
        self.chunk_counter = 0
        self.total_processed = 0
        self.start_time = time.time()

        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize core components (but not RegionManager yet)
        self.globalid_generator = GlobalIDGenerator()
        self.schema_validator = SchemaValidator()

        logger.info(f"V7 Streaming Pipeline initialized with chunk_size={self.config.chunk_size}")

    def get_memory_usage_gb(self) -> float:
        """Get current memory usage in GB"""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024**3)

    def check_memory_limit(self):
        """Check if we're within V7 memory limits"""
        current_memory = self.get_memory_usage_gb()
        if current_memory > self.config.peak_memory_limit_gb:
            raise MemoryError(
                f"Memory usage {current_memory:.2f}GB exceeds V7 limit of "
                f"{self.config.peak_memory_limit_gb}GB RSS"
            )

    def read_chunks(
        self, input_path: Path, format: str = "jsonl"
    ) -> Iterator[List[Dict[str, Any]]]:
        """
        Read input file in chunks of 8,000 entries.
        Supports JSONL and CSV formats.
        """
        chunk = []

        if format == "jsonl":
            with open(input_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        entry = json.loads(line.strip())
                        chunk.append(entry)

                        if len(chunk) >= self.config.chunk_size:
                            yield chunk
                            chunk = []

                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping invalid JSON at line {line_num}: {e}")
                        continue

                # Yield final partial chunk
                if chunk:
                    yield chunk

        elif format == "csv":
            import csv

            with open(input_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    chunk.append(row)

                    if len(chunk) >= self.config.chunk_size:
                        yield chunk
                        chunk = []

                if chunk:
                    yield chunk
        else:
            raise ValueError(f"Unsupported format: {format}")

    def process_chunk(self, chunk: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a single chunk of entries.
        Creates fresh RegionManager to avoid state accumulation.
        """
        # Fresh RegionManager instance per chunk - no state accumulation!
        manager = RegionManager()
        results = []

        for entry in chunk:
            try:
                # Security validation
                validated_entry = security_validator.validate_entry(entry, internal=True)

                # Region detection
                region_result = manager.detect_region(validated_entry, internal=True)

                # Generate GlobalID if needed
                if "GlobalID" not in validated_entry:
                    validated_entry["GlobalID"] = self.globalid_generator.generate(validated_entry)

                # Combine results
                output_entry = {
                    **validated_entry,
                    "RegionCode": region_result.region_code,
                    "RegionConfidence": region_result.confidence,
                    "DetectionMethod": region_result.detection_method,
                    "ProcessingTimestamp": time.time(),
                }

                # Schema validation
                is_valid, validation_errors = self.schema_validator.validate_entry(output_entry)
                if is_valid:
                    results.append(output_entry)
                else:
                    logger.warning(f"Entry failed validation: {validation_errors}")

            except Exception as e:
                logger.error(f"Error processing entry: {e}")
                continue

        # Explicitly delete manager to ensure cleanup
        del manager

        return results

    def write_chunk_results(self, results: List[Dict[str, Any]], chunk_num: int):
        """Write chunk results to disk immediately"""
        output_file = self.config.output_dir / f"chunk_{chunk_num:06d}.jsonl"

        if self.config.enable_compression:
            import zstandard as zstd

            output_file = output_file.with_suffix(".jsonl.zst")

            with zstd.open(output_file, "wt", encoding="utf-8") as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                for result in results:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")

        logger.info(f"Wrote {len(results)} results to {output_file}")

    def cleanup_memory(self):
        """Force memory cleanup between chunks"""
        # Explicit garbage collection
        gc.collect()
        gc.collect()  # Second pass for circular references

        # Force clearing of any module-level caches
        import sys

        modules_to_clear = [
            "src.regions.manager_optimized",
            "src.core.security_validator",
            "src.core.rate_limiter",
        ]

        for module_name in modules_to_clear:
            if module_name in sys.modules:
                module = sys.modules[module_name]
                # Clear any cache attributes
                for attr in dir(module):
                    if "cache" in attr.lower() and hasattr(module, attr):
                        cache = getattr(module, attr)
                        if hasattr(cache, "clear"):
                            cache.clear()

    def process_dataset(self, input_path: Path, format: str = "jsonl") -> Dict[str, Any]:
        """
        Process entire dataset in V7-compliant streaming fashion.
        Returns processing statistics.
        """
        logger.info(f"Starting V7 streaming processing of {input_path}")
        initial_memory = self.get_memory_usage_gb()

        stats = {
            "total_entries": 0,
            "total_chunks": 0,
            "successful_entries": 0,
            "failed_entries": 0,
            "peak_memory_gb": initial_memory,
            "processing_time_seconds": 0,
        }

        try:
            for chunk in self.read_chunks(input_path, format):
                chunk_start = time.time()

                # Process chunk
                results = self.process_chunk(chunk)

                # Write results immediately
                self.write_chunk_results(results, self.chunk_counter)

                # Update statistics
                stats["total_entries"] += len(chunk)
                stats["successful_entries"] += len(results)
                stats["failed_entries"] += len(chunk) - len(results)
                stats["total_chunks"] += 1

                # Cleanup memory
                self.cleanup_memory()

                # Check memory limit
                current_memory = self.get_memory_usage_gb()
                stats["peak_memory_gb"] = max(stats["peak_memory_gb"], current_memory)
                self.check_memory_limit()

                # Log progress
                chunk_time = time.time() - chunk_start
                entries_per_second = len(chunk) / chunk_time if chunk_time > 0 else 0

                logger.info(
                    f"Chunk {self.chunk_counter}: "
                    f"{len(results)}/{len(chunk)} processed in {chunk_time:.1f}s "
                    f"({entries_per_second:.0f} entries/s), "
                    f"Memory: {current_memory:.2f}GB"
                )

                self.chunk_counter += 1
                self.total_processed += len(chunk)

        except Exception as e:
            logger.error(f"Fatal error during processing: {e}")
            raise

        # Final statistics
        stats["processing_time_seconds"] = time.time() - self.start_time
        stats["average_memory_gb"] = stats["peak_memory_gb"]  # Approximation

        # Write final statistics
        stats_file = self.config.output_dir / "processing_stats.json"
        with open(stats_file, "w") as f:
            json.dump(stats, f, indent=2)

        logger.info(f"Processing complete: {stats}")
        return stats

    def merge_output_chunks(self, output_file: Path):
        """
        Merge all chunk files into a single output file.
        Still processes in streaming fashion to maintain memory limits.
        """
        logger.info(f"Merging chunks to {output_file}")

        chunk_files = sorted(self.config.output_dir.glob("chunk_*.jsonl*"))

        with open(output_file, "w", encoding="utf-8") as out:
            for chunk_file in chunk_files:
                if chunk_file.suffix == ".zst":
                    import zstandard as zstd

                    with zstd.open(chunk_file, "rt", encoding="utf-8") as f:
                        for line in f:
                            out.write(line)
                else:
                    with open(chunk_file, "r", encoding="utf-8") as f:
                        for line in f:
                            out.write(line)

        logger.info(f"Merged {len(chunk_files)} chunks to {output_file}")


def main():
    """Example usage of V7 streaming pipeline"""
    import argparse

    parser = argparse.ArgumentParser(description="V7-compliant GMNAP streaming pipeline")
    parser.add_argument("input", type=Path, help="Input file (JSONL or CSV)")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("output/chunks"), help="Output directory for chunks"
    )
    parser.add_argument(
        "--format", choices=["jsonl", "csv"], default="jsonl", help="Input file format"
    )
    parser.add_argument("--merge", action="store_true", help="Merge chunks into single output file")
    parser.add_argument(
        "--merge-output",
        type=Path,
        default=Path("output/merged.jsonl"),
        help="Output file for merged results",
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create pipeline
    config = V7StreamConfig(output_dir=args.output_dir)
    pipeline = V7StreamingPipeline(config)

    # Process dataset
    stats = pipeline.process_dataset(args.input, format=args.format)

    # Optionally merge output
    if args.merge:
        pipeline.merge_output_chunks(args.merge_output)

    print(f"\n✅ Processing complete!")
    print(f"   Total entries: {stats['total_entries']:,}")
    print(f"   Successful: {stats['successful_entries']:,}")
    print(f"   Failed: {stats['failed_entries']:,}")
    print(f"   Peak memory: {stats['peak_memory_gb']:.2f}GB")
    print(f"   Time: {stats['processing_time_seconds']:.1f}s")
    print(f"   Rate: {stats['total_entries']/stats['processing_time_seconds']:.0f} entries/s")


if __name__ == "__main__":
    main()
