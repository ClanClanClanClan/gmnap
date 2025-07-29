#!/usr/bin/env python3
"""
Comprehensive Regional Processor Testing Suite

Tests all aspects of regional processors to ensure they're fully functional
before proceeding with v7 implementation.
"""

import sys
import traceback
import time
import json
from typing import Any, Dict, List, Tuple

# Add src to path
sys.path.insert(0, 'src')

def test_imports():
    """Test that all regional processors can be imported."""
    print("=== PHASE 1: IMPORT TESTING ===")
    
    regions_to_test = [
        ('gmnap.regions.base', 'RegionSpec', 'RegionRuleError'),
        ('gmnap.regions.a_groups.a1_anglo_sphere', 'A1_AngloSphere'),
        ('gmnap.regions.a_groups.a2_western_europe', 'A2_WesternEurope'),
        ('gmnap.regions.b_groups.b1_east_slavic', 'B1_EastSlavic'),
        ('gmnap.regions.b_groups.b2_south_slavic_central', 'B2_SouthSlavicCentral'),
        ('gmnap.regions.c_groups.c2_persian_tajik', 'C2_PersianTajik'),
        ('gmnap.regions.c_groups.c3_arabic_levant_nile', 'C3_ArabicLevantNile'),
        ('gmnap.regions.c_groups.c4_arabic_gulf', 'C4_ArabicGulf'),
        ('gmnap.regions.d_groups.d1_south_asia_hindi_belt', 'D1_SouthAsiaHindiBelt'),
        ('gmnap.regions.e_groups.e1_sinophone_mainland', 'E1_SinophoneMainland'),
        ('gmnap.regions.e_groups.e3_japan', 'E3_Japan'),
        ('gmnap.regions.g_groups.g1_latin_america', 'G1_LatinAmerica'),
    ]
    
    imported_classes = {}
    
    for module_name, *class_names in regions_to_test:
        try:
            module = __import__(module_name, fromlist=class_names)
            for class_name in class_names:
                cls = getattr(module, class_name)
                imported_classes[class_name] = cls
                print(f"✓ {class_name} imported successfully")
        except Exception as e:
            class_list = ', '.join(class_names) if class_names else 'unknown'
            print(f"✗ Failed to import {class_list} from {module_name}: {e}")
            return None
    
    print(f"✓ All {len(imported_classes)} classes imported successfully\n")
    return imported_classes

def test_instantiation(imported_classes):
    """Test that all regional processors can be instantiated."""
    print("=== PHASE 2: INSTANTIATION TESTING ===")
    
    instances = {}
    region_classes = {k: v for k, v in imported_classes.items() 
                     if k not in ['RegionSpec', 'RegionRuleError']}
    
    for class_name, cls in region_classes.items():
        try:
            instance = cls()
            instances[class_name] = instance
            print(f"✓ {class_name} instantiated: code='{instance.code}'")
        except Exception as e:
            print(f"✗ Failed to instantiate {class_name}: {e}")
            traceback.print_exc()
            return None
    
    print(f"✓ All {len(instances)} regional processors instantiated\n")
    return instances

def test_method_existence(instances):
    """Test that all required methods exist."""
    print("=== PHASE 3: METHOD EXISTENCE TESTING ===")
    
    required_methods = ['clean', 'augment', 'validate', 'order_key']
    
    for class_name, instance in instances.items():
        print(f"\nTesting {class_name}:")
        for method_name in required_methods:
            if hasattr(instance, method_name):
                method = getattr(instance, method_name)
                if callable(method):
                    print(f"  ✓ {method_name}() exists and is callable")
                else:
                    print(f"  ✗ {method_name} exists but is not callable")
                    return False
            else:
                print(f"  ✗ {method_name}() missing")
                return False
    
    print("✓ All required methods exist on all processors\n")
    return True

def test_basic_functionality(instances):
    """Test basic functionality with sample data."""
    print("=== PHASE 4: BASIC FUNCTIONALITY TESTING ===")
    
    # Test cases for different regions (using ROMANIZED names in CanonicalLatin)
    test_cases = {
        'A1_AngloSphere': [
            {"CanonicalLatin": "Smith, John William"},
            {"CanonicalLatin": "O'Brien, Mary Catherine"},
            {"CanonicalLatin": "Dr. Johnson, Robert Jr."},
        ],
        'A2_WesternEurope': [
            {"CanonicalLatin": "García Márquez, Gabriel José"},
            {"CanonicalLatin": "von Neumann, János"},
            {"CanonicalLatin": "Müller, François"},
        ],
        'B1_EastSlavic': [
            {"CanonicalLatin": "Иванов, Александр Петрович"},
            {"CanonicalLatin": "Петрова, Елена Михайловна"},
        ],
        'B2_SouthSlavicCentral': [
            {"CanonicalLatin": "Kowalski, Jan"},
            {"CanonicalLatin": "Nováková, Marie"},
            {"CanonicalLatin": "Иванов, Петър"},
        ],
        'C2_PersianTajik': [
            {"CanonicalLatin": "Mohammad Ahmadi"},
            {"CanonicalLatin": "Fatemeh Karimi"},
        ],
        'C3_ArabicLevantNile': [
            {"CanonicalLatin": "Ahmad Muhammad al-Ali"},
            {"CanonicalLatin": "Mariam al-Khoury"},
        ],
        'C4_ArabicGulf': [
            {"CanonicalLatin": "Muhammad bin Salman Al-Saud"},
            {"CanonicalLatin": "Fatima bint Rashid Al-Maktoum"},
            {"CanonicalLatin": "Khalid Al-Sabah"},
        ],
        'D1_SouthAsiaHindiBelt': [
            {"CanonicalLatin": "Rajesh Kumar Sharma"},
            {"CanonicalLatin": "Priya Singh"},
            {"CanonicalLatin": "Amit Prasad Gupta"},
        ],
        'E1_SinophoneMainland': [
            {"CanonicalLatin": "Wang Ming"},
            {"CanonicalLatin": "Li Hua"},
        ],
        'E3_Japan': [
            {"CanonicalLatin": "Tanaka Taro"},
            {"CanonicalLatin": "Sato Hanako"},
        ],
        'G1_LatinAmerica': [
            {"CanonicalLatin": "García López, Juan Carlos"},
            {"CanonicalLatin": "da Silva Santos, Maria"},
            {"CanonicalLatin": "Rodríguez Pérez, José Luis"},
        ],
    }
    
    results = {}
    
    for class_name, instance in instances.items():
        print(f"\nTesting {class_name}:")
        results[class_name] = {}
        
        # Get test cases for this region
        cases = test_cases.get(class_name, [{"CanonicalLatin": "Test, Name"}])
        
        for i, test_entry in enumerate(cases):
            print(f"  Test case {i+1}: {test_entry['CanonicalLatin']}")
            entry = test_entry.copy()  # Don't modify original
            
            try:
                # Test clean method
                instance.clean(entry)
                print(f"    ✓ clean() succeeded")
                
                # Test augment method  
                instance.augment(entry)
                print(f"    ✓ augment() succeeded")
                
                # Test validate method
                instance.validate(entry)
                print(f"    ✓ validate() succeeded")
                
                # Test order_key method
                order_key = instance.order_key(entry)
                print(f"    ✓ order_key() succeeded: '{order_key}'")
                
                results[class_name][f'case_{i+1}'] = {
                    'success': True,
                    'final_entry': entry,
                    'order_key': order_key
                }
                
            except Exception as e:
                print(f"    ✗ Processing failed: {e}")
                results[class_name][f'case_{i+1}'] = {
                    'success': False,
                    'error': str(e)
                }
                # Continue testing other cases
    
    # Summary
    total_cases = sum(len(cases) for cases in results.values())
    successful_cases = sum(
        1 for region_results in results.values() 
        for case_result in region_results.values() 
        if case_result.get('success')
    )
    
    print(f"\n✓ Basic functionality: {successful_cases}/{total_cases} test cases passed")
    
    if successful_cases != total_cases:
        print("⚠️  Some test cases failed - see details above")
        return False
        
    return True

def test_edge_cases(instances):
    """Test edge cases and error handling."""
    print("=== PHASE 5: EDGE CASE TESTING ===")
    
    edge_cases = [
        {"CanonicalLatin": ""},  # Empty string
        {"CanonicalLatin": " "},  # Whitespace only
        {"CanonicalLatin": "A" * 1000},  # Very long name
        {"CanonicalLatin": "Test\x00Name"},  # Null byte
        {"CanonicalLatin": "Test, Name 🚀"},  # Emoji
        {"CanonicalLatin": "Test, Name\n\r\t"},  # Control characters
        {},  # Missing CanonicalLatin
        {"CanonicalLatin": None},  # None value
    ]
    
    for class_name, instance in instances.items():
        print(f"\nTesting edge cases for {class_name}:")
        
        for i, test_entry in enumerate(edge_cases):
            entry = test_entry.copy() if test_entry else {}
            entry_desc = str(test_entry).replace('\x00', '\\x00')[:50]
            
            try:
                # Test each method and see what happens
                instance.clean(entry)
                instance.augment(entry)
                instance.validate(entry)
                order_key = instance.order_key(entry)
                print(f"  ✓ Edge case {i+1} handled: {entry_desc}")
                
            except Exception as e:
                # This might be expected behavior for some edge cases
                print(f"  ⚠️  Edge case {i+1} raised exception: {entry_desc} -> {type(e).__name__}: {e}")
    
    print("✓ Edge case testing completed\n")
    return True

def test_performance(instances):
    """Test basic performance characteristics."""
    print("=== PHASE 6: PERFORMANCE TESTING ===")
    
    # Generate test data
    test_entries = [
        {"CanonicalLatin": f"TestName{i}, Given{i}"} 
        for i in range(100)
    ]
    
    for class_name, instance in instances.items():
        print(f"\nTesting performance for {class_name}:")
        
        start_time = time.time()
        
        for entry in test_entries:
            test_entry = entry.copy()
            try:
                instance.clean(test_entry)
                instance.augment(test_entry)
                instance.validate(test_entry)
                instance.order_key(test_entry)
            except:
                pass  # Performance test, ignore errors
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / len(test_entries) * 1000  # ms per entry
        
        print(f"  ✓ Processed {len(test_entries)} entries in {total_time:.3f}s")
        print(f"  ✓ Average: {avg_time:.2f}ms per entry")
        
        if avg_time > 10:  # More than 10ms per entry is concerning
            print(f"  ⚠️  Performance concern: {avg_time:.2f}ms per entry is quite slow")
    
    print("✓ Performance testing completed\n")
    return True

def run_comprehensive_tests():
    """Run all tests in sequence."""
    print("🧪 COMPREHENSIVE REGIONAL PROCESSOR TESTING")
    print("=" * 50)
    
    # Phase 1: Import testing
    imported_classes = test_imports()
    if not imported_classes:
        print("❌ IMPORT TESTING FAILED - Cannot continue")
        return False
    
    # Phase 2: Instantiation testing  
    instances = test_instantiation(imported_classes)
    if not instances:
        print("❌ INSTANTIATION TESTING FAILED - Cannot continue")
        return False
    
    # Phase 3: Method existence testing
    if not test_method_existence(instances):
        print("❌ METHOD EXISTENCE TESTING FAILED - Cannot continue")
        return False
    
    # Phase 4: Basic functionality testing
    if not test_basic_functionality(instances):
        print("❌ BASIC FUNCTIONALITY TESTING FAILED - Cannot continue")
        return False
    
    # Phase 5: Edge case testing
    test_edge_cases(instances)  # Continue even if edge cases fail
    
    # Phase 6: Performance testing
    test_performance(instances)  # Continue even if performance is poor
    
    print("🎉 ALL CRITICAL TESTS PASSED!")
    print("✓ Regional processors are ready for v7 implementation")
    
    return True

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)