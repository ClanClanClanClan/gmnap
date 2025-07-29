#!/usr/bin/env python3
"""Debug the remaining database store issue."""

from src.gmnap.core.pipeline import GMNAPPipeline
import tempfile
import os
import time

# Create a test pipeline
pipeline = GMNAPPipeline()

# Try to store the same entry that's failing in the test
test_entry = {
    "GlobalID": "test_recovery_entry",
    "CanonicalLatin": "Test Recovery", 
    "CanonicalNative": "Test Recovery",
    "RegionCode": "A1"
}

print("Testing database store operation...")
try:
    result = pipeline.database.store_entry(test_entry)
    print(f"Store result: {result}")
    if result:
        print("✓ Store succeeded")
    else:
        print("✗ Store returned False")
        
    # Try to retrieve it
    retrieved = pipeline.database.get_entry("test_recovery_entry")
    print(f"Retrieved: {retrieved is not None}")
    
    # Check database stats
    stats = pipeline.database.get_stats()
    print(f"Database stats: {stats}")
    
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()