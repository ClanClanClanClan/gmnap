#!/usr/bin/env python3
"""Quick fix for pipeline attribute error"""

import sys
from src.core.pipeline_v7 import V7Pipeline, PipelineMode

# Test that the attribute exists
try:
    pipeline = V7Pipeline(mode=PipelineMode.QUICK)
    print(
        f"✅ _force_immediate_processing exists: {hasattr(pipeline, '_force_immediate_processing')}"
    )
    print(f"   Value: {getattr(pipeline, '_force_immediate_processing', 'NOT FOUND')}")

    # Test with all modes
    for mode in [PipelineMode.QUICK, PipelineMode.FULL, PipelineMode.EXTREME]:
        p = V7Pipeline(mode=mode)
        if not hasattr(p, "_force_immediate_processing"):
            print(f"❌ Missing attribute for mode: {mode}")
        else:
            print(f"✅ Attribute exists for mode: {mode}")

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
