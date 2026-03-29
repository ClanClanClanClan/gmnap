import pytest

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
    from src.authorities.crossref import CrossrefAPI

    print("✓ Crossref: Import successful")
except Exception as e:
    print(f"✗ Crossref: {e}")

# Test OpenAlex
try:
    from src.authorities.openalex import OpenAlexAPI

    print("✓ OpenAlex: Import successful")
except Exception as e:
    print(f"✗ OpenAlex: {e}")

# Test ORCID
try:
    from src.authorities.orcid import ORCIDAPI

    print("✓ ORCID: Import successful")
except Exception as e:
    print(f"✗ ORCID: {e}")

# Test ArXiv
try:
    from src.authorities.arxiv import ArXivAPI

    print("✓ ArXiv: Import successful")
except Exception as e:
    print(f"✗ ArXiv: {e}")

# Test Math Genealogy
try:
    from src.authorities.mathgenealogy import MathGenealogyAPI

    print("✓ Math Genealogy: Import successful")
except Exception as e:
    print(f"✗ Math Genealogy: {e}")

print("\n=== TESTING PIPELINE IMPORTS ===")

# Test Region Detection
try:
    from src.pipeline.stage2_detect_region import detect_region

    print("✓ Region Detection: Import successful")
except Exception as e:
    print(f"✗ Region Detection: {e}")

# Test Idempotency
try:
    from src.pipeline.stage11_idempotency_gate import _canonical_bytes

    print("✓ Idempotency: Import successful")
except Exception as e:
    print(f"✗ Idempotency: {e}")

# Test Short Forms
try:
    from src.pipeline.stage7_tag_short_forms import tag_short_forms

    print("✓ Short Forms: Import successful")
except Exception as e:
    print(f"✗ Short Forms: {e}")

print("\n=== TESTING MEMGRAPH IMPORTS ===")

# Test Memgraph
try:
    from src.core.memgraph_integration import MemgraphClient, GraphNode

    print("✓ Memgraph: Import successful")
except Exception as e:
    print(f"✗ Memgraph: {e}")

print("\n=== TESTING STREAMING IMPORTS ===")

# Test Streaming
try:
    from src.core.streaming_pipeline import StreamingConfig, StreamingPipeline

    print("✓ Streaming: Import successful")
except Exception as e:
    print(f"✗ Streaming: {e}")

print("\n" + "=" * 60)
print("IMPORT TEST COMPLETE")
print("=" * 60)
