#!/usr/bin/env python3
"""
Fix the jung variant mapping by adding proper tag.
"""

import csv
import subprocess

def fix_jung_variant():
    """Add GIVEN_0 tag to 중,jung mapping."""
    filepath = 'resources/variant_map.csv'
    
    mappings = []
    changed = False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[0] == '중' and row[1] == 'jung':
                if len(row) < 3 or not row[2]:
                    # Add GIVEN_0 tag
                    new_row = [row[0], row[1], 'GIVEN_0']
                    mappings.append(new_row)
                    changed = True
                    print(f"Changed: {row} → {new_row}")
                else:
                    mappings.append(row)
            else:
                mappings.append(row)
    
    if changed:
        # Write back
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(mappings)
        
        print("Updated variant_map.csv")
        return True
    
    return False

def test_accuracy():
    """Get current accuracy numbers."""
    # Test mathematician
    result = subprocess.run(["python3", "scripts/validate.py"], 
                          capture_output=True, text=True)
    math_pass = int(result.stdout.split()[0].split('/')[0])
    
    # Test diverse
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

def main():
    print("Fixing jung variant tag")
    print("=" * 50)
    
    # Get baseline
    print("Testing baseline accuracy...")
    math_before, div_before = test_accuracy()
    print(f"  Mathematician: {math_before}/733")
    print(f"  Diverse: {div_before}/200")
    
    # Apply fix
    if fix_jung_variant():
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
    else:
        print("\nNo changes needed.")

if __name__ == "__main__":
    main()