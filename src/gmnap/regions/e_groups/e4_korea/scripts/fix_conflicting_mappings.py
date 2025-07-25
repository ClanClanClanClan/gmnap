#!/usr/bin/env python3
"""
Remove conflicting incorrect mappings as per plan step 2
"""
import csv
from pathlib import Path

E4_ROOT = Path(__file__).parent.parent

# Incorrect mappings to remove (these conflict with correct names)
incorrect_mappings = [
    ("붐", "bum"),   # Should be 범,bum  
    ("숭", "sung"),  # Should be 성,sung
    ("중", "jung"),  # Should be 정,jung
    ("창", "chang"), # Should be 장,chang
    ("초", "cho"),   # Should be 조,cho
    ("숩", "sup"),   # Should be 섭,sup
    ("춘", "chun"),  # Should be 전,chun
    ("출", "chul"),  # Should be 철,chul
    ("큐", "kyu"),   # Should be 규,kyu
    ("숲", "sup"),   # Should be 섭,sup
    ("큥", "kyung"), # Should be 경,kyung
    ("킴", "kim"),   # Should be 김,kim
    ("흉", "hyung"), # Should be 형,hyung
    ("봌", "bok"),   # Should be 복,bok
    ("흌", "hyuk"),  # Should be 혁,hyuk
    ("휵", "hyuk"),  # Should be 혁,hyuk
    ("휶", "hyuk"),  # Should be 혁,hyuk
    ("선", "sun"),   # Should be 선,seon (sun = 순)
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
                    if (hangul, roman) in incorrect_mappings:
                        removed += 1
                        print(f"Removing incorrect: {hangul},{roman}")
                    else:
                        writer.writerow(row)
                        kept += 1
                else:
                    writer.writerow(row)
    
    # Replace original file
    temp_path.replace(syllable_map_path)
    
    print(f"✓ Removed {removed} incorrect mappings")
    print(f"✓ Kept {kept} mappings")

if __name__ == "__main__":
    main()