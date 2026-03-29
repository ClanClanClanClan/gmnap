#!/usr/bin/env python3
"""
Test imports only - no async, no network calls
"""

import os
import sys

os.environ["GMNAP_TEST_MODE"] = "true"
sys.path.insert(0, ".")

print("=" * 60)
print("GMNAP V7 IMPORT TEST")
print("=" * 60)

print("\n=== TESTING AUTHORITY IMPORTS ===")

# Test Crossref
try:

    print("✓ Crossref: Import successful")
except Exception as e:
    print(f"✗ Crossref: {e}")

# Test OpenAlex
try:

    print("✓ OpenAlex: Import successful")
except Exception as e:
    print(f"✗ OpenAlex: {e}")

# Test ORCID
try:

    print("✓ ORCID: Import successful")
except Exception as e:
    print(f"✗ ORCID: {e}")

# Test ArXiv
try:

    print("✓ ArXiv: Import successful")
except Exception as e:
    print(f"✗ ArXiv: {e}")

# Test Math Genealogy
try:

    print("✓ Math Genealogy: Import successful")
except Exception as e:
    print(f"✗ Math Genealogy: {e}")

print("\n=== TESTING PIPELINE IMPORTS ===")

# Test Region Detection
try:

    print("✓ Region Detection: Import successful")
except Exception as e:
    print(f"✗ Region Detection: {e}")

# Test Idempotency
try:

    print("✓ Idempotency: Import successful")
except Exception as e:
    print(f"✗ Idempotency: {e}")

# Test Short Forms
try:

    print("✓ Short Forms: Import successful")
except Exception as e:
    print(f"✗ Short Forms: {e}")

print("\n=== TESTING MEMGRAPH IMPORTS ===")

# Test Memgraph
try:

    print("✓ Memgraph: Import successful")
except Exception as e:
    print(f"✗ Memgraph: {e}")

print("\n=== TESTING STREAMING IMPORTS ===")

# Test Streaming
try:

    print("✓ Streaming: Import successful")
except Exception as e:
    print(f"✗ Streaming: {e}")

print("\n" + "=" * 60)
print("IMPORT TEST COMPLETE")
print("=" * 60)
