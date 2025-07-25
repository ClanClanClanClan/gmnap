#!/usr/bin/env python3
"""
Integrate the completed Korean given name mappings into the V4 comprehensive mappings
"""

import json

def integrate_mappings():
    """Merge given name mappings into V4 comprehensive mappings"""
    print("=== INTEGRATING KOREAN MAPPINGS INTO V4 FST ===\n")
    
    # Load existing V4 mappings (surnames and some given names)
    print("Loading existing V4 comprehensive mappings...")
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive_mappings.json', 'r', encoding='utf-8') as f:
        v4_mappings = json.load(f)
    
    print(f"Existing V4 mappings: {len(v4_mappings)} entries")
    
    # Load completed Korean given name mappings
    print("Loading Korean given name mappings...")
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/korean_given_name_mappings.json', 'r', encoding='utf-8') as f:
        given_name_mappings = json.load(f)
    
    print(f"Korean given name mappings: {len(given_name_mappings)} entries")
    
    # Merge mappings - prioritize given name mappings for conflicts
    merged_count = 0
    updated_count = 0
    skipped_count = 0
    
    for name, hangul in given_name_mappings.items():
        # Skip special blocks
        if hangul.startswith("SKIP_"):
            skipped_count += 1
            continue
            
        # Add or update mapping
        if name in v4_mappings:
            if v4_mappings[name] != hangul:
                print(f"  ⚠️  Updating: {name}: {v4_mappings[name]} -> {hangul}")
                v4_mappings[name] = hangul
                updated_count += 1
        else:
            v4_mappings[name] = hangul
            merged_count += 1
    
    print(f"\n📊 Integration Results:")
    print(f"  ✅ New mappings added: {merged_count}")
    print(f"  🔄 Existing mappings updated: {updated_count}")
    print(f"  ⏭️  Special blocks skipped: {skipped_count}")
    print(f"  📈 Total V4 mappings: {len(v4_mappings)}")
    
    # Save integrated mappings
    print(f"\nSaving integrated V4 mappings...")
    with open('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive_mappings.json', 'w', encoding='utf-8') as f:
        json.dump(v4_mappings, f, indent=2, ensure_ascii=False)
    
    print(f"✅ V4 mappings updated successfully!")
    
    # Create backup of original mapping if it doesn't exist
    import os
    backup_path = '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/data/v4_comprehensive_mappings_backup.json'
    if not os.path.exists(backup_path):
        print(f"Creating backup at {backup_path}")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(v4_mappings, f, indent=2, ensure_ascii=False)
    
    return v4_mappings

if __name__ == "__main__":
    integrate_mappings()