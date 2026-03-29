#!/usr/bin/env python3
"""
V7 GMNAP Production Startup
Launch optimized V7 system with production configuration
"""

import asyncio
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def main():
    """Start V7 production system."""
    print("🚀 V7 GMNAP PRODUCTION SYSTEM")
    print("=" * 40)

    try:
        # Load production configuration
        with open("v7_production.json", "r") as f:
            config = json.load(f)

        print("📋 Production Configuration:")
        print(f"   Batch Size: {config['streaming']['batch_size']}")
        print(f"   Workers: {config['streaming']['parallel_workers']}")
        print(f"   Peak Throughput: {config['performance']['peak_throughput']}")
        print(f"   Optimization Grade: {config['performance']['optimization_grade']}")

        # Initialize streaming pipeline
        from src.core.streaming_v7 import V7StreamingPipeline, StreamingConfig

        stream_config = StreamingConfig(**config["streaming"])

        print("\n🎯 Starting V7 streaming pipeline...")
        async with V7StreamingPipeline(stream_config) as pipeline:
            print("✅ V7 Production System Online")
            print("📡 Ready to process data streams")
            print("\nPress Ctrl+C to stop")

            # Keep running
            while True:
                await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️ V7 production system stopped")
    except Exception as e:
        print(f"❌ V7 startup failed: {e}")
        return False

    return True


if __name__ == "__main__":
    asyncio.run(main())
