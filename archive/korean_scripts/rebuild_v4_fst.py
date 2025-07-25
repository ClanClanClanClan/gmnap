#!/usr/bin/env python3
"""
Rebuild V4 FST from the updated comprehensive mappings
"""

import json
import pynini as pn
import os

def rebuild_v4_fst():
    """Rebuild V4 FST with updated comprehensive mappings"""
    print("=== REBUILDING V4 FST FROM UPDATED MAPPINGS ===\n")
    
    # Load updated V4 comprehensive mappings
    print("Loading updated V4 comprehensive mappings...")
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive_mappings.json', 'r', encoding='utf-8') as f:
        v4_mappings = json.load(f)
    
    print(f"Loaded {len(v4_mappings)} mappings")
    
    # Ensure data directory exists
    os.makedirs('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data', exist_ok=True)
    
    # Build FST from mappings
    print("Building V4 FST...")
    
    # Filter out any empty or invalid mappings
    valid_mappings = []
    for roman, hangul in v4_mappings.items():
        if roman and hangul and not hangul.startswith("SKIP_"):
            valid_mappings.append((roman, hangul))
    
    print(f"Using {len(valid_mappings)} valid mappings")
    
    # Create the FST
    if valid_mappings:
        v4_fst = pn.string_map(valid_mappings, 
                               input_token_type="utf8", 
                               output_token_type="utf8")
        
        # Apply penalty weight λ=3.0 as specified in blueprint
        lambda_weight = 3.0
        weighted_fst = pn.reweight(v4_fst, [lambda_weight])
        
        # Optimize the FST
        optimized_fst = weighted_fst.optimize()
        
        # Save the FST
        fst_path = '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive.fst'
        optimized_fst.write(fst_path)
        
        print(f"✅ Saved V4 FST to {fst_path}")
        print(f"   FST has {optimized_fst.num_states()} states")
        print(f"   Applied penalty weight λ={lambda_weight}")
        
        # Test a few mappings to verify FST works
        print(f"\n🧪 Testing FST...")
        test_cases = ['kim', 'baekjin', 'jungchul', 'sunghoon']
        
        for test_input in test_cases:
            if test_input in v4_mappings:
                expected = v4_mappings[test_input]
                
                # Create input FST
                input_fst = pn.accep(test_input, token_type="utf8")
                
                # Compose with V4 FST
                result_fst = pn.compose(input_fst, optimized_fst)
                
                if result_fst.num_states() > 0:
                    # Extract result
                    shortest = pn.shortestpath(result_fst)
                    paths_iter = shortest.paths(input_token_type="utf8", output_token_type="utf8")
                    
                    if not paths_iter.done():
                        actual = paths_iter.ostring()
                        status = "✅" if actual == expected else "❌"
                        print(f"  {status} '{test_input}' -> '{actual}' (expected: '{expected}')")
                    else:
                        print(f"  ❌ '{test_input}' -> NO OUTPUT (expected: '{expected}')")
                else:
                    print(f"  ❌ '{test_input}' -> NO MATCH (expected: '{expected}')")
            else:
                print(f"  ⚠️  '{test_input}' -> NOT IN MAPPINGS")
        
        return optimized_fst
    else:
        print("❌ No valid mappings found!")
        return None

if __name__ == "__main__":
    rebuild_v4_fst()