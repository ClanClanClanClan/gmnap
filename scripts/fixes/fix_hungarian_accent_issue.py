#!/usr/bin/env python3
"""
Fix Hungarian accent disambiguation issue - Rényi should go to A2 not G1
The problem: Hungarian surnames list has 'renyi' but name is 'rényi' 
Solution: Add accent-normalized matching for Hungarian surnames
"""

import re
import unicodedata
from pathlib import Path

def normalize_for_matching(text):
    """Remove accents for surname matching"""
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) 
                   if unicodedata.category(c) != 'Mn')

def fix_hungarian_accent_disambiguation():
    pipeline_path = Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py")
    
    print("🔧 Fixing Hungarian accent disambiguation (Rényi → A2 not G1)...")
    
    # Read current pipeline
    with open(pipeline_path, 'r') as f:
        content = f.read()
    
    # Find the Hungarian surname matching logic
    hungarian_match_pattern = r"has_hungarian_surname = any\(surname in name_lower for surname in hungarian_surnames\)"
    
    if re.search(hungarian_match_pattern, content):
        # Replace with accent-normalized matching
        new_hungarian_logic = """# Accent-normalized Hungarian surname matching (fix for Rényi issue)
        name_normalized = ''.join(c for c in unicodedata.normalize('NFD', name_lower) if unicodedata.category(c) != 'Mn')
        has_hungarian_surname = any(surname in name_normalized for surname in hungarian_surnames)"""
        
        content = re.sub(hungarian_match_pattern, new_hungarian_logic, content)
        print("   ✅ Updated Hungarian surname matching to use accent normalization")
        
        # Add unicodedata import at the top if not present
        if "import unicodedata" not in content:
            import_pattern = r"(import re\n)"
            content = re.sub(import_pattern, r"import re\nimport unicodedata\n", content, count=1)
            print("   ✅ Added unicodedata import")
    
    # Write fixed pipeline
    with open(pipeline_path, 'w') as f:
        f.write(content)
    
    print("✅ Hungarian accent disambiguation fixed!")
    print("   Rényi should now match 'renyi' in Hungarian surnames list")

if __name__ == "__main__":
    fix_hungarian_accent_disambiguation()