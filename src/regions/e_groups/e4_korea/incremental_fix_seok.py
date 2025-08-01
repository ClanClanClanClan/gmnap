#!/usr/bin/env python3
"""
Incremental fix for 석 → 섞 error pattern.
This affects 7 failures in diverse dataset.
"""

import csv
import subprocess
import sys

def test_accuracy():
    """Get current accuracy numbers."""
    # Test mathematician
    result = subprocess.run(["python3", "scripts/validate.py"], 
                          capture_output=True, text=True)
    math_pass = int(result.stdout.split()[0].split('/')[0])
    
    # Test diverse (extract from percentage)
    result = subprocess.run(["python3", "scripts/test_diverse_dataset.py"], 
                          capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if "Diverse Dataset:" in line and "%" in line:
            percent = float(line.split()[-2].rstrip('%'))
            div_pass = int(percent * 200 / 100)
            break
    else:
        div_pass = 0
    
    return math_pass, div_pass

def add_seok_mapping():
    """Add seok → 석 mapping to variant_map.csv."""
    print("Adding seok → 석 mapping...")
    
    # Read current mappings
    mappings = []
    with open('resources/variant_map.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            mappings.append(row)
    
    # Check if already exists
    for row in mappings:
        if len(row) >= 2 and row[0] == '석' and row[1] == 'seok':
            print("  Mapping already exists!")
            return False
    
    # Add new mapping
    mappings.append(['석', 'seok', 'GIVEN_0'])
    
    # Write back sorted
    mappings.sort(key=lambda x: (x[0], x[1]))
    with open('resources/variant_map.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(mappings)
    
    print("  Added 석,seok,GIVEN_0")
    return True

def main():
    print("Incremental Fix: 석 → 섞 error pattern")
    print("=" * 50)
    
    # Get baseline
    print("Testing baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")
    
    # Apply fix
    if not add_seok_mapping():
        print("\nNo changes needed.")
        return
    
    # Rebuild FSTs
    print("\nRebuilding FSTs...")
    subprocess.run(["python3", "scripts/build_fsts_multi.py"], 
                   capture_output=True, text=True)
    
    # Test new accuracy
    print("\nTesting new accuracy...")
    math_after, div_after = test_accuracy()
    print(f"  Mathematician: {math_after}/733")
    print(f"  Diverse: {div_after}/200")
    
    # Report results
    print("\n" + "=" * 50)
    print("Results:")
    print(f"  Mathematician: {math_before} → {math_after} ({math_after - math_before:+d})")
    print(f"  Diverse: {div_before} → {div_after} ({div_after - div_before:+d})")
    
    if math_after >= math_before and div_after >= div_before:
        print("\n✅ Fix successful! No regression.")
    else:
        print("\n❌ Fix caused regression!")
        sys.exit(1)

if __name__ == "__main__":
    main()