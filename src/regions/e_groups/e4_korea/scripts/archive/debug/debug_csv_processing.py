#!/usr/bin/env python3
"""
Debug what mappings are being processed for 'chung' in given position
"""
import csv

chung_mappings = []

# Read the CSV
for row in csv.reader(open("resources/rr_syllable_map.csv", encoding="utf8")):
    if len(row) >= 2 and not row[0].startswith('#'):
        hangul, roman = row[0], row[1]
        weight = row[2] if len(row) > 2 else "0.0"
        context = row[3] if len(row) > 3 else ""
        pos = row[4] if len(row) > 4 else ""
        
        # Look for 'chung' mappings
        if roman.lower() == "chung":
            try:
                w = float(weight)
            except:
                w = 0.0
            
            chung_mappings.append({
                'hangul': hangul,
                'weight': w,
                'pos': pos,
                'context': context,
                'full_row': row
            })

print("=== ALL 'chung' MAPPINGS IN CSV ===")
for m in sorted(chung_mappings, key=lambda x: (x['pos'], x['weight'])):
    pos_str = f"[{m['pos']}]" if m['pos'] else "[general]"
    print(f"{m['hangul']} <- chung {pos_str} weight={m['weight']:.1f}")

print("\n=== GIVEN POSITION MAPPINGS ===")
given_mappings = [m for m in chung_mappings if m['pos'] in ['GN', 'G', '']]
for m in sorted(given_mappings, key=lambda x: x['weight']):
    pos_str = f"[{m['pos']}]" if m['pos'] else "[general]"
    print(f"{m['hangul']} <- chung {pos_str} weight={m['weight']:.1f}")
    if m['pos'] == '':
        print(f"  (gets +1.0 boost in given FST -> {m['weight'] + 1.0:.1f})")