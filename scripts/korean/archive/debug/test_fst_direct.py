#!/usr/bin/env python3
"""
Test FST directly to debug mapping issues
"""
import pynini as pn
import os

# Load the FSTs
ROM2_GIVEN = pn.Fst.read("models/rom2han_given.fst")

# Test specific inputs
test_cases = ["chung", "CHUNG", "Chung"]

print("=== TESTING FST DIRECTLY ===")
for test in test_cases:
    try:
        # Try exact composition
        result_fst = pn.accep(test) @ ROM2_GIVEN
        
        # Get the best path
        shortest = pn.shortestpath(result_fst)
        output = shortest.string()
        
        print(f"\n'{test}' -> '{output}'")
            
    except Exception as e:
        print(f"\n'{test}' error: {e}")