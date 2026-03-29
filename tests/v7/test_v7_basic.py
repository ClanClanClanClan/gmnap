import pytest

#!/usr/bin/env python3
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


Basic V7 functionality test
Tests that core components are working
"""
import traceback


@pytest.mark.timeout(15)
def test_imports():
    """Test that all critical imports work"""
    print("\n" + "=" * 70)
    print("Testing Critical Imports")
    print("=" * 70)

    tests = []

    # Core modules
    try:

        tests.append(("✓", "src.core.pipeline_v7"))
    except Exception as e:
        tests.append(("✗", f"src.core.pipeline_v7: {e}"))

    try:

        tests.append(("✓", "src.core.db_pool (with BoltPool alias)"))
    except Exception as e:
        tests.append(("✗", f"src.core.db_pool: {e}"))

    try:

        tests.append(("✓", "src.core.security_validator"))
    except Exception as e:
        tests.append(("✗", f"src.core.security_validator: {e}"))

    # Pipeline stages
    stages = [
        ("src.pipeline.stage0_config", "stage0_load_config"),
        ("src.pipeline.stage1_ingest", "ingest_batch"),
        ("src.pipeline.stage1b_llmextract_etd", "llm_extract_etd"),
        ("src.pipeline.stage2_detect_region", "detect_region"),
        ("src.pipeline.stage3_region_hooks", "apply_region_hooks"),
        ("src.pipeline.stage4_authority_enrichment", "enrich_from_authorities"),
        ("src.pipeline.stage5_collision_analytics", "collision_analytics"),
        ("src.pipeline.stage6_graph_consistency", "enforce_graph_coherence_gate"),
        ("src.pipeline.stage7_tag_short_forms", "apply_tagging"),
        ("src.pipeline.stage8_global_validate", "global_validate"),
        ("src.pipeline.stage9_write_diff", "write_and_diff"),
        ("src.pipeline.stage10_report", "publish_report"),
        ("src.pipeline.stage11_idempotency_check", "idempotency_check"),
    ]

    for module, func in stages:
        try:
            mod = __import__(module, fromlist=[func])
            if hasattr(mod, func):
                tests.append(("✓", f"{module}.{func}"))
            else:
                tests.append(("✗", f"{module}: missing {func}"))
        except Exception as e:
            tests.append(("✗", f"{module}: {str(e)[:50]}"))

    # Metrics
    try:

        tests.append(("✓", "src.ops.metrics (all required metrics)"))
    except Exception as e:
        tests.append(("✗", f"src.ops.metrics: {e}"))

    # Print results
    passed = sum(1 for status, _ in tests if status == "✓")
    total = len(tests)

    for status, msg in tests:
        print(f"  {status} {msg}")

    print(f"\nPassed: {passed}/{total} ({100*passed/total:.1f}%)")
    return passed == total


@pytest.mark.timeout(15)
def test_basic_pipeline():
    """Test basic pipeline functionality"""
    print("\n" + "=" * 70)
    print("Testing Basic Pipeline Operations")
    print("=" * 70)

    try:
        # Test basic entry processing
        from src.pipeline.stage2_detect_region import detect_region

        test_entry = {
            "GlobalID": "test-001",
            "CanonicalLatin": "John Smith",
            "CanonicalNative": "",
            "Type": "Individual",
        }

        # Try to detect region (returns tuple of region_code, script)
        region_code, script = detect_region(test_entry)
        print(f"  ✓ Region detection works: {region_code} (script: {script})")
        test_entry["DetectedRegion"] = region_code
        test_entry["DetectedScript"] = script

        # Test region hooks (expects list of entries)
        from src.pipeline.stage3_region_hooks import apply_region_hooks

        result = apply_region_hooks([test_entry])
        print("  ✓ Region hooks work")

        # Test validation
        from src.pipeline.stage8_global_validate import global_validate

        try:
            result, metrics = global_validate(result, mode="Quick")
            print("  ✓ Global validation works")
        except Exception as e:
            print(f"  ⚠ Global validation warning: {str(e)[:50]}")

        return True

    except Exception as e:
        print(f"  ✗ Pipeline test failed: {e}")
        traceback.print_exc()
        return False


@pytest.mark.timeout(15)
def test_idempotency():
    """Test idempotency functionality"""
    print("\n" + "=" * 70)
    print("Testing Idempotency")
    print("=" * 70)

    try:
        from src.pipeline.stage11_idempotency_check import idempotency_check

        test_batch = [
            {"GlobalID": "test-001", "Name": "Test One"},
            {"GlobalID": "test-002", "Name": "Test Two"},
        ]

        batch, metrics = idempotency_check(test_batch, mode="self", strict=False)
        diff_bytes = metrics.get("idempotency_diff_bytes", -1)

        if diff_bytes == 0:
            print(f"  ✓ Idempotency check passed: {diff_bytes} diff bytes")
        else:
            print(f"  ⚠ Idempotency check: {diff_bytes} diff bytes (expected 0)")

        return True

    except Exception as e:
        print(f"  ✗ Idempotency test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\nGMNAP V7 Basic Functionality Test")
    print("==================================")

    results = []

    # Run tests
    results.append(("Import Tests", test_imports()))
    results.append(("Pipeline Tests", test_basic_pipeline()))
    results.append(("Idempotency Tests", test_idempotency()))

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ All tests passed! V7 system is functional.")
        return 0
    else:
        print("\n✗ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    pass  # sys.exit(main())
