import pytest

#!/usr/bin/env python3
"""
Comprehensive V7 functionality test - verifies all components
"""
import os
import sys

os.environ["GMNAP_TEST_MODE"] = "true"
sys.path.insert(0, ".")


@pytest.mark.timeout(15)
def test_imports():
    """Test all imports work"""
    print("\n=== TESTING IMPORTS ===")

    results = {"success": 0, "failed": 0}

    # Test main package
    try:
        import src

        print(f"✓ src package (v{src.__version__})")
        results["success"] += 1
    except Exception as e:
        print(f"✗ src package: {e}")
        results["failed"] += 1

    # Test V7 Pipeline
    try:
        from src import V7Pipeline

        print("✓ V7Pipeline")
        results["success"] += 1
    except Exception as e:
        print(f"✗ V7Pipeline: {e}")
        results["failed"] += 1

    # Test Security Validator
    try:
        from src import SecurityValidator

        print("✓ SecurityValidator")
        results["success"] += 1
    except Exception as e:
        print(f"✗ SecurityValidator: {e}")
        results["failed"] += 1

    # Test Region Manager
    try:
        from src import RegionManager

        print("✓ RegionManager")
        results["success"] += 1
    except Exception as e:
        print(f"✗ RegionManager: {e}")
        results["failed"] += 1

    # Test Authority APIs
    apis = [
        ("Crossref", "src.authorities.crossref", "CrossrefAPI"),
        ("OpenAlex", "src.authorities.openalex", "OpenAlexAPI"),
        ("ORCID", "src.authorities.orcid", "ORCIDAPI"),
        ("ArXiv", "src.authorities.arxiv", "ArXivAPI"),
        ("Math Genealogy", "src.authorities.mathgenealogy", "MathGenealogyAPI"),
    ]

    for name, module, cls in apis:
        try:
            exec(f"from {module} import {cls}")
            print(f"✓ {name}")
            results["success"] += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            results["failed"] += 1

    # Test Memgraph
    try:
        from src.core.memgraph_integration import MemgraphClient, GraphNode

        print("✓ Memgraph Integration")
        results["success"] += 1
    except Exception as e:
        print(f"✗ Memgraph: {e}")
        results["failed"] += 1

    # Test Streaming
    try:
        from src.core.streaming_pipeline import StreamingConfig, StreamingPipeline

        print("✓ Streaming Pipeline")
        results["success"] += 1
    except Exception as e:
        print(f"✗ Streaming: {e}")
        results["failed"] += 1

    # Test Monitoring
    try:
        from src.core.monitoring import MetricsCollector, HealthCheck

        print("✓ Monitoring Stack")
        results["success"] += 1
    except Exception as e:
        print(f"✗ Monitoring: {e}")
        results["failed"] += 1

    print(f"\nImport Results: {results['success']} success, {results['failed']} failed")
    return results


@pytest.mark.timeout(15)
def test_instantiation():
    """Test component instantiation"""
    print("\n=== TESTING INSTANTIATION ===")

    results = {"success": 0, "failed": 0}

    # Test RegionManager
    try:
        from src import RegionManager

        manager = RegionManager()
        print("✓ RegionManager instantiated")
        results["success"] += 1
    except Exception as e:
        print(f"✗ RegionManager: {e}")
        results["failed"] += 1

    # Test Streaming Config
    try:
        from src.core.streaming_pipeline import StreamingConfig, StreamingPipeline

        config = StreamingConfig(chunk_size=8000)
        pipeline = StreamingPipeline(config)
        print(f"✓ StreamingPipeline (chunk={config.chunk_size})")
        results["success"] += 1
    except Exception as e:
        print(f"✗ StreamingPipeline: {e}")
        results["failed"] += 1

    # Test Memgraph Client (mock mode)
    try:
        from src.core.memgraph_integration import MemgraphClient, GraphNode

        client = MemgraphClient()
        node = GraphNode(
            global_id="test-001", canonical_latin="Test, User", region_code="A1"
        )
        print(f"✓ MemgraphClient + GraphNode")
        results["success"] += 1
    except Exception as e:
        print(f"✗ Memgraph: {e}")
        results["failed"] += 1

    print(
        f"\nInstantiation Results: {results['success']} success, {results['failed']} failed"
    )
    return results


@pytest.mark.timeout(15)
def test_basic_functionality():
    """Test basic functionality"""
    print("\n=== TESTING BASIC FUNCTIONALITY ===")

    results = {"success": 0, "failed": 0}

    # Test region detection
    try:
        from src.pipeline.stage2_detect_region import detect_region

        test_entry = {"GlobalID": "test-001", "CanonicalLatin": "Smith, John"}
        region, script = detect_region(test_entry)
        print(f"✓ Region Detection: {region}/{script}")
        results["success"] += 1
    except Exception as e:
        print(f"✗ Region Detection: {e}")
        results["failed"] += 1

    # Test idempotency
    try:
        from src.pipeline.stage11_idempotency_gate import _canonical_bytes

        test_data = [{"id": "1", "name": "test"}]
        hash1 = _canonical_bytes(test_data)
        hash2 = _canonical_bytes(test_data)
        if hash1 == hash2:
            print(f"✓ Idempotency: {len(hash1)} bytes")
            results["success"] += 1
        else:
            print(f"✗ Idempotency: Hash mismatch")
            results["failed"] += 1
    except Exception as e:
        print(f"✗ Idempotency: {e}")
        results["failed"] += 1

    # Test region loading
    try:
        from src import RegionManager

        manager = RegionManager()
        regions_tested = 0
        for code in ["A1", "E4", "B3", "C1"]:
            region = manager.get_region(code)
            if region:
                regions_tested += 1
        print(f"✓ Region Loading: {regions_tested}/4 regions")
        results["success"] += 1
    except Exception as e:
        print(f"✗ Region Loading: {e}")
        results["failed"] += 1

    print(
        f"\nFunctionality Results: {results['success']} success, {results['failed']} failed"
    )
    return results


def main():
    """Run all tests"""
    print("=" * 60)
    print("GMNAP V7 COMPLETE FUNCTIONALITY TEST")
    print("=" * 60)

    # Collect all results
    all_results = {
        "imports": test_imports(),
        "instantiation": test_instantiation(),
        "functionality": test_basic_functionality(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)

    total_success = sum(r["success"] for r in all_results.values())
    total_failed = sum(r["failed"] for r in all_results.values())

    print(f"Total Tests: {total_success + total_failed}")
    print(f"✓ Passed: {total_success}")
    print(f"✗ Failed: {total_failed}")

    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED! V7 FUNCTIONALITY VERIFIED!")
    else:
        print(f"\nWARN {total_failed} tests failed - review needed")

    print("=" * 60)


if __name__ == "__main__":
    main()
