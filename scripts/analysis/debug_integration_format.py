#!/usr/bin/env python3
"""Debug integration test format issue."""

import sys
sys.path.insert(0, 'src')

from gmnap.core.pipeline import GMNAPPipeline

pipeline = GMNAPPipeline({'database_path': ':memory:'})

# Test the exact format used in integration test
test_case = "TestﬃName"  # This is what integration test uses

print(f"Testing integration format: '{test_case}'")

try:
    entry = {"CanonicalLatin": test_case}
    result = pipeline.process_entry(entry)
    print(f"  ✓ SUCCESS: '{result['CanonicalLatin']}'")
except Exception as e:
    print(f"  ✗ FAILED: {e}")
    
    # Debug individual steps
    try:
        # Step 1: After ingest/normalization
        ingested = pipeline._stage_ingest(entry.copy())
        print(f"    After ingest: '{ingested['CanonicalLatin']}'")
        
        # Step 2: Check region detection
        region = pipeline._stage_detect_region(ingested)
        print(f"    Detected region: {region}")
        
        # Step 3: Try A1 validation directly
        from gmnap.v7_compat import v7_manager, load_working_processors
        if not v7_manager.list_regions():
            load_working_processors()
        
        a1_adapter = v7_manager.get_adapter('A1')
        try:
            a1_adapter.validate(ingested)
            print(f"    A1 validation: ✓ PASS")
        except Exception as a1_e:
            print(f"    A1 validation: ✗ FAIL - {a1_e}")
            
    except Exception as debug_e:
        print(f"    Debug error: {debug_e}")

print(f"\nTesting proper format: 'Testffi, Name'")
try:
    entry2 = {"CanonicalLatin": "Testffi, Name"}
    result2 = pipeline.process_entry(entry2)
    print(f"  ✓ SUCCESS: '{result2['CanonicalLatin']}'")
except Exception as e:
    print(f"  ✗ FAILED: {e}")