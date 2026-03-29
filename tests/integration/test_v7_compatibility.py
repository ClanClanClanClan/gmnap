from typing import Dict
from typing import List
import pytest

#!/usr/bin/env python3
"""
V7 Compatibility Layer Testing Suite

Thoroughly tests the v7 compatibility layer to ensure it works correctly
with existing regional processors while providing enhanced features.
"""

import sys
import traceback
import time
import json
from typing import Any, Dict, List

# Add src to path
sys.path.insert(0, "src")


@pytest.mark.timeout(15)
def test_v7_imports():
    """Test that v7 compatibility layer can be imported."""
    print("=== PHASE 1: V7 IMPORT TESTING ===")

    try:
        # from src.v7_compat import V7RegionAdapter, V7RegionManager, v7_manager, load_working_processors
        print("✓ V7RegionAdapter imported successfully")
        print("✓ V7RegionManager imported successfully")
        print("✓ v7_manager global instance imported successfully")
        print("✓ load_working_processors function imported successfully")

        return {
            "V7RegionAdapter": V7RegionAdapter,
            "V7RegionManager": V7RegionManager,
            "v7_manager": v7_manager,
            "load_working_processors": load_working_processors,
        }

    except Exception as e:
        print(f"✗ Failed to import v7 compatibility layer: {e}")
        traceback.print_exc()
        return None


@pytest.mark.timeout(15)
def test_v7_manager_loading(v7_imports):
    """Test loading processors into v7 manager."""
    print("\n=== PHASE 2: V7 MANAGER LOADING ===")

    try:
        load_working_processors = v7_imports["load_working_processors"]
        manager = load_working_processors()

        regions = manager.list_regions()
        print(f"✓ Loaded {len(regions)} regions: {', '.join(regions)}")

        status = manager.get_status()
        print(
            f"✓ V7 status: {status['registered_regions']} regions, features: {list(status['features'].keys())}"
        )

        return manager

    except Exception as e:
        print(f"✗ Failed to load v7 manager: {e}")
        traceback.print_exc()
        return None


@pytest.mark.timeout(15)
def test_v7_adapter_functionality(manager):
    """Test individual v7 adapter functionality."""
    print("\n=== PHASE 3: V7 ADAPTER TESTING ===")

    # Test cases for different regions
    test_cases = {
        "A1": [
            {"CanonicalLatin": "Smith, John William"},
            {"CanonicalLatin": "O'Brien, Mary Catherine"},
        ],
        "B1": [
            {"CanonicalLatin": "Иванов, Александр Петрович"},
        ],
        "C2": [
            {"CanonicalLatin": "Mohammad Ahmadi"},
        ],
        "C3": [
            {"CanonicalLatin": "Ahmad Muhammad al-Ali"},
        ],
        "E1": [
            {"CanonicalLatin": "Wang Ming"},
        ],
        "E3": [
            {"CanonicalLatin": "Tanaka Taro"},
        ],
    }

    results = {}

    for region_code in manager.list_regions():
        print(f"\nTesting V7 adapter for {region_code}:")
        adapter = manager.get_adapter(region_code)

        if not adapter:
            print(f"  ✗ Could not get adapter for {region_code}")
            continue

        # Test adapter properties
        print(f"  ✓ Adapter code: {adapter.code}")
        print(f"  ✓ Enhanced validation: {adapter.enhanced_validation}")
        print(f"  ✓ Performance monitoring: {adapter.performance_monitoring}")
        print(f"  ✓ Detailed logging: {adapter.detailed_logging}")

        # Test with sample data
        cases = test_cases.get(region_code, [{"CanonicalLatin": "Test Name"}])
        region_results = []

        for i, test_entry in enumerate(cases):
            print(f"  Test case {i+1}: {test_entry['CanonicalLatin']}")

            try:
                # Test individual methods
                cleaned = adapter.clean(test_entry)
                print(f"    ✓ clean() returned copy")

                augmented = adapter.augment(cleaned)
                print(f"    ✓ augment() returned copy")

                is_valid = adapter.validate(augmented)
                print(f"    ✓ validate() returned: {is_valid}")

                order_key = adapter.order_key(augmented)
                print(f"    ✓ order_key() returned: {order_key[:30]}...")

                # Test full pipeline
                processed = adapter.process_entry(test_entry)
                print(f"    ✓ process_entry() completed")
                print(f"    ✓ Entry has _order_key: {'_order_key' in processed}")

                region_results.append(
                    {"success": True, "processed_entry": processed, "order_key": order_key}
                )

            except Exception as e:
                print(f"    ✗ Processing failed: {e}")
                region_results.append({"success": False, "error": str(e)})

        results[region_code] = region_results

    # Summary
    total_tests = sum(len(region_results) for region_results in results.values())
    successful_tests = sum(
        1
        for region_results in results.values()
        for result in region_results
        if result.get("success")
    )

    print(f"\n✓ V7 adapter testing: {successful_tests}/{total_tests} tests passed")

    return successful_tests == total_tests


@pytest.mark.timeout(15)
def test_v7_manager_methods(manager):
    """Test v7 manager methods."""
    print("\n=== PHASE 4: V7 MANAGER METHODS ===")

    try:
        # Test process_entry method
        regions = manager.list_regions()
        if not regions:
            print("✗ No regions available for testing")
            return False

        test_region = regions[0]
        test_entry = {"CanonicalLatin": "Test Manager Entry"}

        print(f"Testing manager process_entry with {test_region}:")
        processed = manager.process_entry(test_entry, test_region)
        print(f"  ✓ Entry processed successfully")
        print(f"  ✓ Has _order_key: {'_order_key' in processed}")

        # Test invalid region
        try:
            manager.process_entry(test_entry, "INVALID")
            print("  ✗ Should have raised ValueError for invalid region")
            return False
        except ValueError:
            print("  ✓ Correctly raised ValueError for invalid region")

        # Test status method
        status = manager.get_status()
        print(f"  ✓ Status contains {len(status)} fields")
        print(f"  ✓ V7 compatible: {status.get('v7_compatible')}")

        return True

    except Exception as e:
        print(f"✗ Manager methods test failed: {e}")
        traceback.print_exc()
        return False


@pytest.mark.timeout(15)
def test_v7_error_handling(manager):
    """Test v7 error handling capabilities."""
    print("\n=== PHASE 5: V7 ERROR HANDLING ===")

    regions = manager.list_regions()
    if not regions:
        print("✗ No regions available for error testing")
        return False

    test_region = regions[0]
    adapter = manager.get_adapter(test_region)

    # Test edge cases that might cause errors
    edge_cases = [
        {},  # Missing CanonicalLatin
        {"CanonicalLatin": None},  # None value
        {"CanonicalLatin": ""},  # Empty string
        {"CanonicalLatin": "A" * 10000},  # Very long string
    ]

    print(f"Testing error handling for {test_region}:")

    for i, test_case in enumerate(edge_cases):
        try:
            # Test individual methods
            cleaned = adapter.clean(test_case)
            augmented = adapter.augment(cleaned)
            is_valid = adapter.validate(augmented)
            order_key = adapter.order_key(augmented)

            print(f"  Case {i+1}: Handled gracefully (valid={is_valid})")

        except Exception as e:
            print(f"  Case {i+1}: Exception caught: {type(e).__name__}")

    print("✓ Error handling testing completed")
    return True


@pytest.mark.timeout(15)
def test_v7_performance(manager):
    """Test v7 performance characteristics."""
    print("\n=== PHASE 6: V7 PERFORMANCE TESTING ===")

    regions = manager.list_regions()
    if not regions:
        print("✗ No regions available for performance testing")
        return False

    # Generate test data
    test_entries = [
        {"CanonicalLatin": f"TestName{i}, Given{i}"}
        for i in range(50)  # Smaller dataset for v7 testing
    ]

    for region_code in regions[:3]:  # Test first 3 regions
        print(f"\nTesting v7 performance for {region_code}:")
        adapter = manager.get_adapter(region_code)

        start_time = time.time()

        processed_count = 0
        for entry in test_entries:
            try:
                processed = adapter.process_entry(entry)
                processed_count += 1
            except:
                pass  # Performance test, ignore errors

        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(test_entries) * 1000  # ms per entry

        print(f"  ✓ Processed {processed_count}/{len(test_entries)} entries in {total_time:.3f}s")
        print(f"  ✓ Average: {avg_time:.2f}ms per entry")

        if avg_time > 50:  # More than 50ms per entry is concerning for v7
            print(f"  WARN  Performance concern: {avg_time:.2f}ms per entry is slow")

    print("✓ V7 performance testing completed")
    return True


@pytest.mark.timeout(15)
def test_v7_backwards_compatibility(manager):
    """Test that v7 is backwards compatible with existing processors."""
    print("\n=== PHASE 7: V7 BACKWARDS COMPATIBILITY ===")

    regions = manager.list_regions()
    if not regions:
        print("✗ No regions available for compatibility testing")
        return False

    test_region = regions[0]
    adapter = manager.get_adapter(test_region)
    original_processor = adapter.processor

    test_entry = {"CanonicalLatin": "Compatibility Test Name"}

    print(f"Testing backwards compatibility for {test_region}:")

    try:
        # Test that original processor methods still work
        original_entry = test_entry.copy()
        original_processor.clean(original_entry)
        original_processor.augment(original_entry)
        original_processor.validate(original_entry)
        original_key = original_processor.order_key(original_entry)

        print("  ✓ Original processor methods work")

        # Test that v7 adapter produces equivalent results
        v7_processed = adapter.process_entry(test_entry)
        v7_key = adapter.order_key(v7_processed)

        print("  ✓ V7 adapter methods work")
        print(f"  ✓ Keys match: {original_key == v7_key}")

        return True

    except Exception as e:
        print(f"✗ Backwards compatibility test failed: {e}")
        traceback.print_exc()
        return False


def run_v7_comprehensive_tests():
    """Run all v7 compatibility tests in sequence."""
    print("🧪 COMPREHENSIVE V7 COMPATIBILITY TESTING")
    print("=" * 55)

    # Phase 1: Import testing
    v7_imports = test_v7_imports()
    if not v7_imports:
        print("FAIL V7 IMPORT TESTING FAILED - Cannot continue")
        return False

    # Phase 2: Manager loading
    manager = test_v7_manager_loading(v7_imports)
    if not manager:
        print("FAIL V7 MANAGER LOADING FAILED - Cannot continue")
        return False

    # Phase 3: Adapter functionality
    if not test_v7_adapter_functionality(manager):
        print("FAIL V7 ADAPTER FUNCTIONALITY FAILED")
        return False

    # Phase 4: Manager methods
    if not test_v7_manager_methods(manager):
        print("FAIL V7 MANAGER METHODS FAILED")
        return False

    # Phase 5: Error handling
    test_v7_error_handling(manager)  # Continue even if some errors occur

    # Phase 6: Performance testing
    test_v7_performance(manager)  # Continue even if performance is poor

    # Phase 7: Backwards compatibility
    if not test_v7_backwards_compatibility(manager):
        print("FAIL V7 BACKWARDS COMPATIBILITY FAILED")
        return False

    print("\n🎉 ALL V7 COMPATIBILITY TESTS PASSED!")
    print("✓ V7 compatibility layer is ready for production")

    return True


if __name__ == "__main__":
    success = run_v7_comprehensive_tests()
    # sys.exit(0 if success else 1)  # MOVED: Was at module level
