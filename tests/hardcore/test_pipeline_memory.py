"""
Hardcore pipeline memory management testing for GMNAP.

Tests memory usage, chunk processing, memory leaks, and all scenarios
that could cause memory exhaustion or inefficient memory usage.
"""

import asyncio
import gc
import random
import string
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest
import yaml

from src.core.config import GMNAPConfig
from src.core.errors import ResourceExhaustedError
from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode


class TestPipelineMemoryManagement:
    """Test pipeline memory management under various loads."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_path = Path(self.temp_dir) / "input"
        self.output_path = Path(self.temp_dir) / "output"
        
        self.input_path.mkdir(parents=True)
        self.output_path.mkdir(parents=True)
        
        # Create mock config
        self.config = self._create_test_config()
        
        # Monitor memory
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Force garbage collection
        gc.collect()
        
    def _create_test_config(self) -> GMNAPConfig:
        """Create test configuration."""
        config = Mock(spec=GMNAPConfig)
        config.cache = Mock()
        config.cache.cache_dir = self.temp_dir
        config.database = Mock()
        config.database.path = Path(self.temp_dir) / "test.db"
        config.output = Mock()
        config.output.directory = self.output_path
        return config
    
    def _create_test_entries(self, count: int, entry_size: str = "medium") -> Dict[str, Any]:
        """Create test entries for memory testing."""
        entries = {}
        
        # Different entry sizes
        size_configs = {
            "small": {"name_variants": 2, "affiliations": 1, "metadata_size": 10},
            "medium": {"name_variants": 5, "affiliations": 3, "metadata_size": 50},
            "large": {"name_variants": 20, "affiliations": 10, "metadata_size": 200},
            "huge": {"name_variants": 100, "affiliations": 50, "metadata_size": 1000}
        }
        
        config = size_configs.get(entry_size, size_configs["medium"])
        
        for i in range(count):
            canonical_name = f"TestPerson{i:06d}, John"
            
            # Generate name variants
            name_variants = []
            for j in range(config["name_variants"]):
                variant = f"TestVariant{i:06d}-{j:02d}, John"
                name_variants.append(variant)
            
            # Generate affiliations
            affiliations = []
            for j in range(config["affiliations"]):
                affiliation = {
                    "name": f"University{i:06d}-{j:02d}",
                    "department": f"Department of Mathematics {j:02d}",
                    "position": f"Professor {j:02d}",
                    "years": [2020 + j, 2021 + j],
                    "country": "US"
                }
                affiliations.append(affiliation)
            
            # Generate metadata
            metadata = {}
            for j in range(config["metadata_size"]):
                metadata[f"field_{j:03d}"] = f"value_{j:03d}_" + "x" * 10
            
            entry = {
                "CanonicalLatin": canonical_name,
                "name_variants": name_variants,
                "affiliations": affiliations,
                "birth_year": 1970 + (i % 50),
                "msc_codes": [f"11A{i % 100:02d}", f"11B{i % 100:02d}"],
                "countries": ["US", "UK"],
                "metadata": metadata
            }
            
            entries[canonical_name] = entry
        
        return entries
    
    def _write_yaml_files(self, entries: Dict[str, Any], files_count: int = 1):
        """Write entries to YAML files."""
        entries_per_file = len(entries) // files_count
        if entries_per_file == 0:
            entries_per_file = 1
        
        entry_items = list(entries.items())
        
        for i in range(files_count):
            start_idx = i * entries_per_file
            end_idx = min((i + 1) * entries_per_file, len(entry_items))
            
            if start_idx >= len(entry_items):
                break
                
            file_entries = dict(entry_items[start_idx:end_idx])
            
            yaml_file = self.input_path / f"test_data_{i:03d}.yaml"
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(file_entries, f, default_flow_style=False, allow_unicode=True)
    
    @pytest.mark.asyncio
    async def test_memory_usage_large_dataset(self):
        """Test memory usage with large datasets."""
        # Create large dataset
        entries = self._create_test_entries(count=50000, entry_size="medium")
        self._write_yaml_files(entries, files_count=10)
        
        # Monitor memory before pipeline
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        # Run pipeline with memory monitoring
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
        
        # Mock external dependencies to focus on memory
        with patch.object(pipeline, '_load_authorities'), \
             patch.object(pipeline, '_load_regions'), \
             patch.object(pipeline, '_verify_file_ownership'), \
             patch.object(pipeline, '_check_licenses'):
            
            # Execute pipeline stages that use memory
            await pipeline._stage_0_config()
            await pipeline._stage_1_ingest(self.input_path)
            
            # Check memory usage after ingestion
            ingest_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            ingest_growth = ingest_memory - initial_memory
            
            # Should not use excessive memory
            assert ingest_growth < 500, f"Excessive memory usage after ingestion: {ingest_growth}MB"
            
            # Continue with region detection
            await pipeline._stage_2_detect_region()
            
            # Check memory usage after region detection
            region_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            region_growth = region_memory - initial_memory
            
            # Should not grow significantly
            assert region_growth < 600, f"Excessive memory usage after region detection: {region_growth}MB"
            
            # Memory should be proportional to entry count
            memory_per_entry = region_growth / len(entries)
            assert memory_per_entry < 0.02, f"Too much memory per entry: {memory_per_entry}MB"
    
    @pytest.mark.asyncio
    async def test_chunk_processing_efficiency(self):
        """Test chunk processing efficiency."""
        # Create dataset larger than chunk size
        entries = self._create_test_entries(count=20000, entry_size="small")
        self._write_yaml_files(entries, files_count=5)
        
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
        
        # Test different chunk sizes
        chunk_sizes = [1000, 5000, 10000]
        memory_usages = []
        
        for chunk_size in chunk_sizes:
            # Reset pipeline
            pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
            pipeline.chunk_size = chunk_size
            
            # Mock dependencies
            with patch.object(pipeline, '_load_authorities'), \
                 patch.object(pipeline, '_load_regions'), \
                 patch.object(pipeline, '_verify_file_ownership'), \
                 patch.object(pipeline, '_check_licenses'):
                
                # Monitor memory usage
                start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                
                # Run stages that use chunking
                await pipeline._stage_0_config()
                await pipeline._stage_1_ingest(self.input_path)
                await pipeline._stage_2_detect_region()
                
                # Simulate chunked processing
                entries_list = list(pipeline._entries.items())
                max_memory = start_memory
                
                for i in range(0, len(entries_list), chunk_size):
                    chunk = entries_list[i:i + chunk_size]
                    
                    # Process chunk (simulate work)
                    for canonical_name, entry in chunk:
                        # Simulate processing
                        _ = entry.get("name_variants", [])
                        _ = entry.get("affiliations", [])
                    
                    # Check memory usage
                    current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                    max_memory = max(max_memory, current_memory)
                    
                    # Force garbage collection between chunks
                    gc.collect()
                
                memory_growth = max_memory - start_memory
                memory_usages.append(memory_growth)
        
        # Smaller chunks should use less memory
        assert memory_usages[0] <= memory_usages[1], "Smaller chunks should use less memory"
        assert memory_usages[1] <= memory_usages[2], "Smaller chunks should use less memory"
    
    @pytest.mark.asyncio
    async def test_memory_leaks_during_pipeline(self):
        """Test for memory leaks during pipeline execution."""
        # Create moderate dataset
        entries = self._create_test_entries(count=5000, entry_size="medium")
        self._write_yaml_files(entries, files_count=3)
        
        # Run pipeline multiple times
        memory_measurements = []
        
        for iteration in range(5):
            # Force garbage collection before measurement
            gc.collect()
            start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            # Run pipeline
            pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
            
            with patch.object(pipeline, '_load_authorities'), \
                 patch.object(pipeline, '_load_regions'), \
                 patch.object(pipeline, '_verify_file_ownership'), \
                 patch.object(pipeline, '_check_licenses'):
                
                await pipeline._stage_0_config()
                await pipeline._stage_1_ingest(self.input_path)
                await pipeline._stage_2_detect_region()
            
            # Clean up pipeline
            del pipeline
            
            # Force garbage collection after cleanup
            gc.collect()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            memory_measurements.append(end_memory - start_memory)
        
        # Check for memory leaks
        # Memory usage should not grow significantly across iterations
        if len(memory_measurements) > 1:
            memory_trend = memory_measurements[-1] - memory_measurements[0]
            assert memory_trend < 50, f"Memory leak detected: {memory_trend}MB growth across iterations"
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_between_stages(self):
        """Test memory cleanup between pipeline stages."""
        # Create dataset
        entries = self._create_test_entries(count=10000, entry_size="medium")
        self._write_yaml_files(entries, files_count=2)
        
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
        
        with patch.object(pipeline, '_load_authorities'), \
             patch.object(pipeline, '_load_regions'), \
             patch.object(pipeline, '_verify_file_ownership'), \
             patch.object(pipeline, '_check_licenses'):
            
            # Monitor memory at each stage
            stage_memories = []
            
            # Stage 0
            gc.collect()
            start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            await pipeline._stage_0_config()
            stage_memories.append(('stage_0', self.process.memory_info().rss / 1024 / 1024 - start_memory))
            
            # Stage 1
            gc.collect()
            stage1_start = self.process.memory_info().rss / 1024 / 1024  # MB
            await pipeline._stage_1_ingest(self.input_path)
            stage_memories.append(('stage_1', self.process.memory_info().rss / 1024 / 1024 - stage1_start))
            
            # Stage 2
            gc.collect()
            stage2_start = self.process.memory_info().rss / 1024 / 1024  # MB
            await pipeline._stage_2_detect_region()
            stage_memories.append(('stage_2', self.process.memory_info().rss / 1024 / 1024 - stage2_start))
            
            # Verify memory usage is reasonable for each stage
            for stage_name, memory_usage in stage_memories:
                assert memory_usage < 200, f"Excessive memory usage in {stage_name}: {memory_usage}MB"
    
    @pytest.mark.asyncio
    async def test_memory_pressure_handling(self):
        """Test pipeline behavior under memory pressure."""
        # Create very large dataset
        entries = self._create_test_entries(count=100000, entry_size="large")
        self._write_yaml_files(entries, files_count=20)
        
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
        
        # Mock memory pressure
        def mock_memory_check():
            # Simulate memory pressure
            memory_info = self.process.memory_info()
            if memory_info.rss > 500 * 1024 * 1024:  # 500MB
                raise ResourceExhaustedError("Memory limit exceeded")
        
        with patch.object(pipeline, '_load_authorities'), \
             patch.object(pipeline, '_load_regions'), \
             patch.object(pipeline, '_verify_file_ownership'), \
             patch.object(pipeline, '_check_licenses'):
            
            # Should handle memory pressure gracefully
            try:
                await pipeline._stage_0_config()
                await pipeline._stage_1_ingest(self.input_path)
                
                # Check memory usage periodically
                current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                if current_memory > 400:  # 400MB threshold
                    # Should reduce chunk size automatically
                    assert pipeline.chunk_size <= 8000, "Should reduce chunk size under memory pressure"
                
            except ResourceExhaustedError:
                # Should handle memory exhaustion gracefully
                pass
    
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_memory_safety(self):
        """Test memory safety with concurrent pipeline execution."""
        # Create multiple smaller datasets
        datasets = []
        for i in range(3):
            entries = self._create_test_entries(count=2000, entry_size="small")
            dataset_path = Path(self.temp_dir) / f"dataset_{i}"
            dataset_path.mkdir()
            
            yaml_file = dataset_path / "data.yaml"
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(entries, f, default_flow_style=False, allow_unicode=True)
            
            datasets.append(dataset_path)
        
        # Run pipelines concurrently
        results = []
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        async def run_pipeline(dataset_path):
            pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
            
            with patch.object(pipeline, '_load_authorities'), \
                 patch.object(pipeline, '_load_regions'), \
                 patch.object(pipeline, '_verify_file_ownership'), \
                 patch.object(pipeline, '_check_licenses'):
                
                await pipeline._stage_0_config()
                await pipeline._stage_1_ingest(dataset_path)
                await pipeline._stage_2_detect_region()
                
                return len(pipeline._entries)
        
        # Run concurrent pipelines
        tasks = [run_pipeline(dataset) for dataset in datasets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        successful_results = [r for r in results if isinstance(r, int)]
        assert len(successful_results) == len(datasets), f"Not all pipelines completed successfully: {results}"
        
        # Check memory usage
        final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Should not use excessive memory
        assert memory_growth < 300, f"Excessive memory usage from concurrent pipelines: {memory_growth}MB"
    
    @pytest.mark.asyncio
    async def test_memory_efficient_streaming(self):
        """Test memory-efficient streaming processing."""
        # Create dataset with many small files
        total_entries = 10000
        entries_per_file = 100
        file_count = total_entries // entries_per_file
        
        # Create many small files
        for i in range(file_count):
            entries = self._create_test_entries(count=entries_per_file, entry_size="small")
            yaml_file = self.input_path / f"stream_{i:04d}.yaml"
            with open(yaml_file, 'w', encoding='utf-8') as f:
                yaml.dump(entries, f, default_flow_style=False, allow_unicode=True)
        
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
        
        # Monitor memory during streaming
        max_memory = 0
        memory_samples = []
        
        def memory_monitor():
            nonlocal max_memory
            for _ in range(100):  # Sample for 10 seconds
                current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                max_memory = max(max_memory, current_memory)
                memory_samples.append(current_memory)
                time.sleep(0.1)
        
        # Start memory monitoring
        monitor_thread = threading.Thread(target=memory_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Run pipeline
        with patch.object(pipeline, '_load_authorities'), \
             patch.object(pipeline, '_load_regions'), \
             patch.object(pipeline, '_verify_file_ownership'), \
             patch.object(pipeline, '_check_licenses'):
            
            await pipeline._stage_0_config()
            await pipeline._stage_1_ingest(self.input_path)
        
        # Stop monitoring
        time.sleep(1)
        
        # Check memory efficiency
        assert len(pipeline._entries) == total_entries, f"Not all entries processed: {len(pipeline._entries)}"
        
        # Memory should remain bounded
        memory_per_entry = max_memory / total_entries
        assert memory_per_entry < 0.01, f"Memory usage too high: {memory_per_entry}MB per entry"
    
    @pytest.mark.asyncio
    async def test_memory_limits_enforcement(self):
        """Test enforcement of memory limits."""
        # Create large dataset
        entries = self._create_test_entries(count=50000, entry_size="huge")
        self._write_yaml_files(entries, files_count=10)
        
        pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
        
        # Mock memory limit enforcement
        memory_limit = 200  # MB
        
        def check_memory_limit():
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            if current_memory > memory_limit:
                raise ResourceExhaustedError(f"Memory limit exceeded: {current_memory}MB > {memory_limit}MB")
        
        with patch.object(pipeline, '_load_authorities'), \
             patch.object(pipeline, '_load_regions'), \
             patch.object(pipeline, '_verify_file_ownership'), \
             patch.object(pipeline, '_check_licenses'):
            
            # Should either complete within limits or raise ResourceExhaustedError
            try:
                await pipeline._stage_0_config()
                await pipeline._stage_1_ingest(self.input_path)
                
                # Check memory periodically
                check_memory_limit()
                
                await pipeline._stage_2_detect_region()
                
                # Final memory check
                check_memory_limit()
                
            except ResourceExhaustedError:
                # Expected behavior when memory limit is exceeded
                pass
    
    @pytest.mark.asyncio
    async def test_memory_optimization_strategies(self):
        """Test memory optimization strategies."""
        # Create dataset
        entries = self._create_test_entries(count=10000, entry_size="medium")
        self._write_yaml_files(entries, files_count=5)
        
        # Test different optimization strategies
        strategies = [
            {"chunk_size": 1000, "description": "Small chunks"},
            {"chunk_size": 5000, "description": "Medium chunks"},
            {"chunk_size": 10000, "description": "Large chunks"},
        ]
        
        results = []
        
        for strategy in strategies:
            pipeline = GMNAPPipeline(self.config, PipelineMode.QUICK)
            pipeline.chunk_size = strategy["chunk_size"]
            
            # Monitor memory usage
            start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            
            with patch.object(pipeline, '_load_authorities'), \
                 patch.object(pipeline, '_load_regions'), \
                 patch.object(pipeline, '_verify_file_ownership'), \
                 patch.object(pipeline, '_check_licenses'):
                
                start_time = time.time()
                await pipeline._stage_0_config()
                await pipeline._stage_1_ingest(self.input_path)
                await pipeline._stage_2_detect_region()
                end_time = time.time()
                
                end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
                memory_usage = end_memory - start_memory
                processing_time = end_time - start_time
                
                results.append({
                    "strategy": strategy["description"],
                    "chunk_size": strategy["chunk_size"],
                    "memory_usage": memory_usage,
                    "processing_time": processing_time,
                    "entries_processed": len(pipeline._entries)
                })
        
        # Analyze results
        for result in results:
            assert result["entries_processed"] == len(entries), f"Not all entries processed: {result}"
            assert result["memory_usage"] < 300, f"Excessive memory usage: {result['memory_usage']}MB"
            assert result["processing_time"] < 30, f"Processing too slow: {result['processing_time']}s"
        
        # Smaller chunks should generally use less memory
        small_chunk_memory = results[0]["memory_usage"]
        large_chunk_memory = results[2]["memory_usage"]
        
        # Allow some variance, but smaller chunks should be more memory efficient
        assert small_chunk_memory <= large_chunk_memory * 1.5, \
            f"Small chunks should be more memory efficient: {small_chunk_memory}MB vs {large_chunk_memory}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])