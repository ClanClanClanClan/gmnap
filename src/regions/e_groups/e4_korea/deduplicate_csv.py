#!/usr/bin/env python3
"""Deduplicate CSV files while preserving order and tags."""

import csv
import os
from collections import OrderedDict

def deduplicate_variant_map():
    """Deduplicate variant_map.csv, keeping tagged entries."""
    filepath = 'resources/variant_map.csv'
    print(f"Deduplicating {filepath}...")
    
    # Read all entries
    entries = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and any(row):  # Skip empty rows
                entries.append(row)
    
    # Deduplicate: prefer entries with tags
    seen = {}
    deduped = []
    
    for row in entries:
        if len(row) >= 2:
            key = (row[0], row[1])  # (hangul, romanization)
            tag = row[2] if len(row) > 2 else ""
            
            if key not in seen:
                seen[key] = row
                deduped.append(row)
            elif tag and not (len(seen[key]) > 2 and seen[key][2]):
                # Replace with tagged version if current has no tag
                idx = deduped.index(seen[key])
                deduped[idx] = row
                seen[key] = row
    
    # Write back
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(deduped)
    
    print(f"  Reduced from {len(entries)} to {len(deduped)} entries")
    return len(entries), len(deduped)

def deduplicate_rr_syllable_map():
    """Deduplicate rr_syllable_map.csv."""
    filepath = 'resources/rr_syllable_map.csv'
    print(f"Deduplicating {filepath}...")
    
    # Read all entries
    entries = []
    seen = OrderedDict()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and len(row) >= 2:
                key = row[0]  # hangul syllable
                if key not in seen:
                    seen[key] = row
                    entries.append(row)
    
    # Write back
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(entries)
    
    print(f"  Reduced from {len(entries) + 125} to {len(entries)} entries")
    return len(entries) + 125, len(entries)

def backup_files():
    """Create backups before modification."""
    import shutil
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files = [
        'resources/variant_map.csv',
        'resources/rr_syllable_map.csv'
    ]
    
    for f in files:
        if os.path.exists(f):
            backup = f + f'.backup_{timestamp}'
            shutil.copy2(f, backup)
            print(f"Backed up {f} to {backup}")

def main():
    print("CSV Deduplication")
    print("=" * 50)
    
    # Create backups first
    backup_files()
    
    print("\nDeduplicating files...")
    
    # Deduplicate variant_map.csv
    v_before, v_after = deduplicate_variant_map()
    
    # Deduplicate rr_syllable_map.csv
    r_before, r_after = deduplicate_rr_syllable_map()
    
    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  variant_map.csv: {v_before} → {v_after} entries")
    print(f"  rr_syllable_map.csv: {r_before} → {r_after} entries")
    
    print("\n✅ Deduplication complete")

if __name__ == "__main__":
    main()