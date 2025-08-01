#!/usr/bin/env python3
"""
Remove duplicate entries from CSV while preserving optimal weights.
Production-safe duplicate cleanup with backup and validation.
"""

import csv
import shutil
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def analyze_duplicates(csv_path="resources/rr_syllable_map.csv"):
    """Analyze duplicate entries and determine best ones to keep"""
    
    print("🔍 Analyzing duplicate entries...")
    
    entries = defaultdict(list)  # (hangul, roman) -> list of full rows
    
    with open(csv_path, 'r', encoding='utf8') as f:
        reader = csv.reader(f)
        for line_num, row in enumerate(reader, 1):
            if not row or row[0].startswith('#'):
                continue
            if len(row) < 2:
                continue
                
            hangul, roman = row[0], row[1]
            key = (hangul, roman)
            entries[key].append((line_num, row))
    
    # Find duplicates
    duplicates = {k: v for k, v in entries.items() if len(v) > 1}
    
    print(f"  📊 Total unique pairs: {len(entries)}")
    print(f"  🔄 Duplicate pairs found: {len(duplicates)}")
    
    if not duplicates:
        print("  ✅ No duplicates found")
        return []
    
    # Analyze each duplicate group
    cleanup_plan = []
    
    for (hangul, roman), rows in duplicates.items():
        print(f"\n  📝 Duplicate: {hangul},{roman} ({len(rows)} entries)")
        
        # Sort by preference: position-specific > general, then by weight
        def preference_score(row_data):
            line_num, row = row_data
            weight = float(row[2]) if len(row) > 2 and row[2] else 0.0
            pos = row[4] if len(row) > 4 else ""
            
            # Prefer position-specific entries
            pos_score = 2 if pos in ['S', 'G'] else 1
            
            # Prefer reasonable weights (not too extreme)
            weight_score = 1 / (1 + abs(weight))  # Prefer weights closer to 0
            
            return (pos_score, weight_score, -line_num)  # Earlier lines as tiebreaker
        
        sorted_rows = sorted(rows, key=preference_score, reverse=True)
        
        # Keep the best entry, mark others for removal
        keep_entry = sorted_rows[0]
        remove_entries = sorted_rows[1:]
        
        print(f"    ✅ Keep: Line {keep_entry[0]} - {keep_entry[1]}")
        for remove_entry in remove_entries:
            print(f"    ❌ Remove: Line {remove_entry[0]} - {remove_entry[1]}")
            cleanup_plan.append(remove_entry[0])
    
    return sorted(cleanup_plan, reverse=True)  # Remove from end to preserve line numbers

def remove_duplicates_safely(csv_path="resources/rr_syllable_map.csv"):
    """Remove duplicates with full production safety"""
    
    print("🧹 Starting production-safe duplicate removal...")
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"{csv_path}.backup_dedup_{timestamp}")
    shutil.copy2(csv_path, backup_path)
    print(f"  💾 Backup created: {backup_path}")
    
    # Analyze duplicates
    lines_to_remove = analyze_duplicates(csv_path)
    
    if not lines_to_remove:
        print("  ✅ No duplicates to remove")
        backup_path.unlink()  # Remove unnecessary backup
        return True
    
    print(f"\n  🎯 Removing {len(lines_to_remove)} duplicate lines...")
    
    # Read all lines
    with open(csv_path, 'r', encoding='utf8') as f:
        all_lines = f.readlines()
    
    # Remove duplicates (in reverse order to preserve line numbers)
    removed_count = 0
    for line_num in lines_to_remove:
        if 1 <= line_num <= len(all_lines):
            print(f"    🗑️  Removing line {line_num}: {all_lines[line_num-1].strip()}")
            all_lines.pop(line_num - 1 - removed_count)  # Adjust for already removed lines
            removed_count += 1
    
    # Write cleaned file
    with open(csv_path, 'w', encoding='utf8') as f:
        f.writelines(all_lines)
    
    print(f"  ✅ Removed {removed_count} duplicate entries")
    
    # Verify cleanup
    remaining_duplicates = analyze_duplicates(csv_path)
    if remaining_duplicates:
        print(f"  ⚠️  Still {len(remaining_duplicates)} duplicates found - may need manual review")
        return False
    else:
        print("  ✅ All duplicates successfully removed")
        return True

def validate_csv_integrity(csv_path="resources/rr_syllable_map.csv"):
    """Validate CSV integrity after cleanup"""
    
    print("🔍 Validating CSV integrity...")
    
    try:
        with open(csv_path, 'r', encoding='utf8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        print(f"  📊 Total rows: {len(rows)}")
        
        # Count valid entries
        valid_entries = 0
        for row in rows:
            if row and not row[0].startswith('#') and len(row) >= 2:
                valid_entries += 1
        
        print(f"  ✅ Valid entries: {valid_entries}")
        
        # Check for basic issues
        issues = []
        for i, row in enumerate(rows, 1):
            if not row:
                continue
            if row[0].startswith('#'):
                continue
            if len(row) < 2:
                issues.append(f"Line {i}: Insufficient fields")
            elif len(row) >= 3:
                try:
                    float(row[2])
                except ValueError:
                    issues.append(f"Line {i}: Invalid weight '{row[2]}'")
        
        if issues:
            print("  ⚠️  Issues found:")
            for issue in issues[:5]:
                print(f"    • {issue}")
            if len(issues) > 5:
                print(f"    • ... and {len(issues)-5} more")
        else:
            print("  ✅ No integrity issues found")
        
        return len(issues) == 0
        
    except Exception as e:
        print(f"  ❌ Validation failed: {e}")
        return False

def main():
    """Production-safe duplicate removal with validation"""
    
    print("🧹 Production Duplicate Removal System")
    print("=" * 45)
    
    csv_path = "resources/rr_syllable_map.csv"
    
    if not Path(csv_path).exists():
        print(f"❌ CSV file not found: {csv_path}")
        return 1
    
    # Initial state
    print("📊 Initial state:")
    analyze_duplicates(csv_path)
    
    # Remove duplicates in multiple passes (handles nested duplicates)
    max_passes = 5
    pass_num = 1
    
    while pass_num <= max_passes:
        print(f"\n🔄 Pass {pass_num}: Checking for duplicates...")
        
        # Check if there are still duplicates
        lines_to_remove = analyze_duplicates(csv_path)
        if not lines_to_remove:
            print("  ✅ No more duplicates found")
            break
        
        # Remove duplicates for this pass
        if not remove_duplicates_safely(csv_path):
            print(f"  ❌ Pass {pass_num} failed")
            return 1
        
        pass_num += 1
    
    if pass_num > max_passes:
        print(f"\n⚠️  Stopped after {max_passes} passes - may have complex duplicates")
    
    # Final verification
    remaining = analyze_duplicates(csv_path)
    if remaining:
        print(f"\n⚠️  {len(remaining)} duplicates remain - manual review needed")
    else:
        print("\n✅ All duplicates successfully removed")
    
    # Validate integrity
    if validate_csv_integrity(csv_path):
        print("\n✅ CSV integrity verified")
        print("🎯 Duplicate cleanup complete - system ready for production")
        return 0
    else:
        print("\n❌ CSV integrity issues detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())