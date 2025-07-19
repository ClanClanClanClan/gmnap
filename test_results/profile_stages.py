#!/usr/bin/env python3
"""Profile pipeline stages to identify bottlenecks"""
import sys
import tempfile
import yaml
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.pipeline_v6 import GMNAPPipeline, PipelineMode
from src.core.config import GMNAPConfig

def profile_pipeline_stages():
    """Profile each pipeline stage to identify bottlenecks"""
    print("=== PIPELINE STAGE PROFILING ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_dir = temp_path / "input"
        input_dir.mkdir()
        
        # Create test data with multiple entries
        test_data = {}
        names = [
            ("Smith, John Michael", "A1"),
            ("Иванов, Иван Петрович", "B1"),
            ("王小明", "E1"),
            ("محمد عبد الله", "C3"),
            ("田中太郎", "E3"),
            ("García López, José María", "G1"),
            ("राम प्रकाश शर्मा", "D1"),
            ("Johnson, Robert", "A1"),
            ("Williams, David", "A1"),
            ("Brown, Michael", "A1"),
        ]
        
        for i, (name, region) in enumerate(names):
            test_data[name] = {
                "GlobalID": f"TEST{i:03d}",
                "UpdatedAt": "2025-01-01T00:00:00Z",
                "CanonicalLatin": name,
                "CanonicalNative": name,
                "BirthYear": 1980 + i,
                "CountryCodes": ["US" if region == "A1" else "XX"],
                "Confidence": 85
            }
        
        with open(input_dir / "test.yaml", 'w') as f:
            yaml.dump(test_data, f)
        
        # Setup config
        config = GMNAPConfig()
        config.cache.cache_dir = str(temp_path / "cache")
        config.database.db_path = str(temp_path / "test.db")
        config.database.path = str(temp_path / "test.db")
        
        # Create source manifest
        manifest_dir = temp_path / "cache" / "config"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "source_manifest.json"
        
        manifest_data = {
            "OpenAlex": {"enabled": True, "tier": 0, "daily_quota": 864000},
            "Crossref": {"enabled": True, "tier": 0, "daily_quota": 4300000},
            "ORCID": {"enabled": True, "tier": 0, "daily_quota": 500},
            "zbMATH": {"enabled": True, "tier": 0, "daily_quota": 200}
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest_data, f)
        
        # Run pipeline
        print(f"\nProcessing {len(test_data)} entries...")
        pipeline = GMNAPPipeline(config, PipelineMode.QUICK)
        result = pipeline.run(input_dir)
        
        # Analyze stage timings
        print("\n📊 STAGE PERFORMANCE ANALYSIS")
        print("=" * 70)
        print(f"{'Stage':<30} {'Duration (s)':<15} {'Entries':<10} {'ms/entry':<10}")
        print("-" * 70)
        
        total_duration = 0
        for stage_name, metrics in result.stage_metrics.items():
            if metrics.start_time and metrics.end_time:
                duration = (metrics.end_time - metrics.start_time).total_seconds()
                total_duration += duration
                entries = metrics.entries_processed or 1
                ms_per_entry = (duration * 1000) / entries
                
                # Highlight slow stages
                flag = "🔥" if duration > 0.5 else "✅"
                print(f"{flag} {stage_name:<27} {duration:>10.3f}s    {entries:>6}    {ms_per_entry:>8.1f}")
        
        print("-" * 70)
        print(f"{'TOTAL':<30} {total_duration:>10.3f}s")
        
        # Identify bottlenecks
        print("\n🎯 BOTTLENECK ANALYSIS")
        print("=" * 70)
        
        bottlenecks = []
        for stage_name, metrics in result.stage_metrics.items():
            if metrics.start_time and metrics.end_time:
                duration = (metrics.end_time - metrics.start_time).total_seconds()
                percentage = (duration / total_duration) * 100
                if percentage > 10:
                    bottlenecks.append((stage_name, duration, percentage))
        
        bottlenecks.sort(key=lambda x: x[1], reverse=True)
        
        for stage, duration, percentage in bottlenecks:
            print(f"  {stage}: {duration:.3f}s ({percentage:.1f}% of total)")
        
        print("\n💡 RECOMMENDATIONS:")
        if bottlenecks:
            top_bottleneck = bottlenecks[0][0]
            if "authority" in top_bottleneck:
                print("  - Authority enrichment is the main bottleneck")
                print("  - Consider implementing caching for authority responses")
                print("  - Reduce API calls by batching queries")
            elif "collision" in top_bottleneck:
                print("  - Collision analytics is slow")
                print("  - Consider using database indexes for surname lookups")
            elif "validate" in top_bottleneck:
                print("  - Validation is taking too long")
                print("  - Consider parallelizing validation checks")
        
        return result

if __name__ == "__main__":
    profile_pipeline_stages()