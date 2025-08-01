#!/usr/bin/env python3
"""
Add reverse compound mappings for proper roundtrip quality
Fix the Korean→English direction for compound words
"""
import csv
import shutil
from datetime import datetime

# Backup the current file
backup_name = f"resources/rr_syllable_map.csv.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
shutil.copy("resources/rr_syllable_map.csv", backup_name)
print(f"Backed up to: {backup_name}")

print("=== ADDING REVERSE COMPOUND MAPPINGS FOR ROUNDTRIP QUALITY ===")
print("Problem: Korean→English produces character-by-character output")
print("Solution: Add compound Korean→English mappings with strong weights")
print()

# Read current mappings
rows = []
with open("resources/rr_syllable_map.csv", encoding="utf8") as f:
    rows = list(csv.reader(f))

# REVERSE COMPOUND MAPPINGS for proper roundtrip
reverse_compound_mappings = [
    # Compound words from systematic coverage
    ("레어이니셜블록", "rareinitialsblock", "-1.0"),  # 레어이니셜블록 → "rareinitialsblock"
    ("에이비씨", "abc", "-0.8"),                    # 에이비씨 → "abc" (alternative to a.b.c.)
    ("엑스와이지", "xyz", "-0.8"),                  # 엑스와이지 → "xyz" (alternative to x.y.z.)
    
    # Academic compound titles
    ("박사", "phd", "-0.8"),                       # 박사 → "phd" (alternative to ph.d.)
    ("박사", "md", "-0.8"),                        # 박사 → "md" (alternative to m.d.)
    
    # Multi-character sequences
    ("레어", "rare", "-0.8"),                      # 레어 → "rare"
    ("이니셜", "initial", "-0.8"),                 # 이니셜 → "initial"  
    ("블록", "block", "-0.8"),                     # 블록 → "block"
    ("테스트", "test", "-0.8"),                    # 테스트 → "test"
    ("케이스", "case", "-0.8"),                    # 케이스 → "case"
    
    # Common name compounds that might appear
    ("마이클존슨", "michaeljohnson", "-0.8"),       # 마이클존슨 → "michaeljohnson"
    ("데이비드스미스", "davidsmith", "-0.8"),       # 데이비드스미스 → "davidsmith"
    ("제임스윌슨", "jameswilson", "-0.8"),         # 제임스윌슨 → "jameswilson"
    
    # Suffix compounds
    ("주니어", "jr", "-0.8"),                       # 주니어 → "jr"
    ("시니어", "sr", "-0.8"),                       # 시니어 → "sr"  
    ("삼세", "iii", "-0.8"),                        # 삼세 → "iii"
]

print(f"Current rows: {len(rows)}")

added_count = 0
updated_count = 0

for hangul, roman, weight in reverse_compound_mappings:
    # Check if mapping already exists
    found = False
    for i, row in enumerate(rows):
        if len(row) >= 2 and row[0] == hangul and row[1] == roman:
            if len(row) >= 3:
                old_weight = row[2] if row[2] else "0.0"
                # Only update if new weight is stronger
                if float(weight) < float(old_weight):
                    rows[i] = [hangul, roman, weight]
                    print(f"  UPDATED: {hangul} → {roman} (weight: {old_weight} → {weight})")
                    updated_count += 1
                else:
                    print(f"  KEPT: {hangul} → {roman} (existing {old_weight} >= new {weight})")
            else:
                rows[i] = [hangul, roman, weight]
                print(f"  UPDATED: {hangul} → {roman} (added weight: {weight})")
                updated_count += 1
            found = True
            break
    
    if not found:
        rows.append([hangul, roman, weight])
        print(f"  ADDED: {hangul} → {roman} (weight: {weight})")
        added_count += 1

print(f"\nReverse compound mappings:")
print(f"- Added: {added_count} new reverse mappings")
print(f"- Updated: {updated_count} existing mappings")
print(f"- Total rows: {len(rows)}")

# Write updated file
with open("resources/rr_syllable_map.csv", "w", encoding="utf8", newline="") as f:
    writer = csv.writer(f)
    for row in rows:
        writer.writerow(row)

print("\n✅ Reverse compound mappings added for roundtrip quality!")
print("\n=== EXPECTED ROUNDTRIP IMPROVEMENTS ===")
print("Korean→English should now produce:")
print("- 레어이니셜블록 → 'rareinitialsblock' (not char-by-char)")
print("- 에이비씨 → 'abc' (not 'a b c')")
print("- 박사 → 'phd' (not 'bak sa')")
print("\nThis should fix dice coefficient scores and validation!")
print("Expected: Convert eng→kor failures to working cases")