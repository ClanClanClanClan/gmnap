#!/usr/bin/env python3
"""Analyze which mathematician names regressed after adding English syllables."""

import subprocess
import json

def get_failures():
    """Get current failures from mathematician dataset."""
    result = subprocess.run(["python3", "scripts/validate.py"], 
                          capture_output=True, text=True)
    
    failures = []
    lines = result.stdout.split('\n')
    
    # Find the "First 5 misses" line
    for i, line in enumerate(lines):
        if "First 5 misses:" in line:
            # Parse the list of failures
            import ast
            failures_str = line.split("First 5 misses:")[1].strip()
            failures = ast.literal_eval(failures_str)
            break
    
    return failures

def check_problematic_mappings():
    """Check which English mappings might be problematic."""
    # Load the batch additions
    with open('batch_additions_20250729_160111.json', 'r', encoding='utf-8') as f:
        batch = json.load(f)
    
    print("Potentially problematic mappings:")
    print("-" * 50)
    
    # These syllables might conflict with Korean names
    problematic = ['ja', 'jo', 'mi', 'sa', 'pe', 'eu', 'si', 'ca']
    
    for addition in batch['additions']:
        rom = addition['romanization']
        if rom in problematic:
            print(f"  {rom} → {addition['hangul']} (might conflict with Korean names)")

def main():
    print("Analyzing English syllable regression")
    print("=" * 50)
    
    # Get current failures
    failures = get_failures()
    print(f"\nFirst 5 mathematician failures:")
    for name, error_type, detail in failures[:5]:
        print(f"  {name}: {error_type} - {detail}")
    
    print()
    check_problematic_mappings()
    
    print("\nRecommendation: Remove single-syllable English mappings that conflict")
    print("with common Korean syllables (ja, jo, mi, sa, etc.)")

if __name__ == "__main__":
    main()