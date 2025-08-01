#!/usr/bin/env python3
"""
Fix common conversion errors by removing incorrect mappings
"""
import csv
from pathlib import Path

E4_ROOT = Path(__file__).parent.parent

# Incorrect mappings to remove
remove_mappings = [
    ("뱈", "baek"),  # Should be 백
    ("밲", "baek"),  # Should be 백
    ("휸", "hyun"),  # Should be 현
]

def main():
    syllable_map_path = E4_ROOT / "resources" / "rr_syllable_map.csv"
    temp_path = syllable_map_path.with_suffix('.tmp')
    
    removed = 0
    kept = 0
    
    with open(syllable_map_path, encoding="utf8") as f_in:
        with open(temp_path, 'w', encoding="utf8") as f_out:
            writer = csv.writer(f_out)
            
            for row in csv.reader(f_in):
                if len(row) >= 2:
                    hangul, roman = row[0], row[1]
                    if (hangul, roman) in remove_mappings:
                        removed += 1
                        print(f"Removing: {hangul},{roman}")
                    else:
                        writer.writerow(row)
                        kept += 1
                else:
                    writer.writerow(row)
    
    # Replace original file
    temp_path.replace(syllable_map_path)
    
    print(f"✓ Removed {removed} incorrect mappings")
    print(f"✓ Kept {kept} mappings")
    print("✓ Rebuild FSTs with: python scripts/build_fsts_multi.py")

if __name__ == "__main__":
    main()