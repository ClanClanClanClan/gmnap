#!/usr/bin/env python3
"""Debug full regional processing."""

import sys
sys.path.insert(0, 'src')

from gmnap.core.pipeline import GMNAPPipeline
from gmnap.v7_compat import v7_manager, load_working_processors

if not v7_manager.list_regions():
    load_working_processors()

pipeline = GMNAPPipeline({'database_path': ':memory:'})

# Test single word format that's failing
test_entry = {"CanonicalLatin": "TestffiName"}

print(f"Testing: {test_entry}")

try:
    # Step 1: Ingest (includes normalization)
    ingested = pipeline._stage_ingest(test_entry.copy())
    print(f"1. After ingest: {ingested}")
    
    # Step 2: Region detection
    region = pipeline._stage_detect_region(ingested)
    print(f"2. Detected region: {region}")
    
    # Step 3: Regional processing (the problematic step)
    print(f"3. Testing regional processing...")
    
    # Try full adapter processing
    a1_adapter = v7_manager.get_adapter('A1')
    processed = a1_adapter.process_entry(ingested)
    print(f"   ✓ Regional processing SUCCESS")
    print(f"   Result: {processed}")
    
except Exception as e:
    print(f"   ✗ Regional processing FAILED: {e}")
    
    # Try individual steps
    try:
        print(f"   Testing individual adapter steps:")
        
        # Clean
        clean_entry = ingested.copy()
        a1_adapter.clean(clean_entry)
        print(f"     After clean: {clean_entry}")
        
        # Augment
        a1_adapter.augment(clean_entry)
        print(f"     After augment: {clean_entry}")
        
        # Validate
        a1_adapter.validate(clean_entry)
        print(f"     Validation: ✓ PASS")
        
    except Exception as step_e:
        print(f"     Step failed: {step_e}")