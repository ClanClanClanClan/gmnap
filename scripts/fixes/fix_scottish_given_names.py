#!/usr/bin/env python3
"""
Fix Scottish given name prioritization - "Lee, MacPherson" should go to A1 not E4
When Korean surname matches but Scottish given name is present, prioritize Scottish
"""

import re
from pathlib import Path

def fix_scottish_given_names():
    pipeline_path = Path("/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py")
    
    print("🔧 Adding Scottish given name prioritization...")
    
    # Read current pipeline
    with open(pipeline_path, 'r') as f:
        content = f.read()
    
    # Find the Anglo given names section
    anglo_given_pattern = r"# Explicit Anglo given names  \n        anglo_given = \['john'.*?\]\n        has_anglo_given = any\(given in name_lower for given in anglo_given\)"
    
    if re.search(anglo_given_pattern, content, re.DOTALL):
        # Add Scottish given name detection
        scottish_given_code = """# Explicit Anglo given names  
        anglo_given = ['john', 'william', 'james', 'charles', 'george', 'frank', 'joseph', 'thomas', 'henry', 'robert',
                      'edward', 'mary', 'patricia', 'jennifer', 'linda', 'elizabeth', 'barbara', 'susan', 'jessica',
                      'isaac', 'alan', 'godfrey', 'arthur', 'augustus', 'colin', 'ian', 'matthew', 'michael', 'david',
                      'richard', 'daniel', 'paul', 'mark', 'christopher', 'rowan', 'francis', 'grant']
        has_anglo_given = any(given in name_lower for given in anglo_given)
        
        # Scottish given names (fix for MacPherson → E4 instead of A1)
        scottish_given = ['macpherson', 'macdonald', 'macleod', 'campbell', 'fraser', 'mackenzie', 'stewart', 'murray',
                         'davidson', 'robertson', 'morrison', 'sinclair', 'gordon', 'hamilton', 'douglas', 'bruce']
        has_scottish_given = any(given in name_lower for given in scottish_given)"""
        
        content = re.sub(anglo_given_pattern, scottish_given_code, content, flags=re.DOTALL)
        print("   ✅ Added Scottish given name detection")
        
        # Find the Anglo scoring section and add Scottish logic
        anglo_scoring_pattern = r"if has_anglo_surname:\n            scores\['A1'\] \+= 6  # Boost to compete better with other regions\n        if has_anglo_given:\n            scores\['A1'\] \+= 3"
        
        if re.search(anglo_scoring_pattern, content):
            new_scoring = """if has_anglo_surname:
            scores['A1'] += 6  # Boost to compete better with other regions
        if has_anglo_given:
            scores['A1'] += 3
        if has_scottish_given:
            scores['A1'] += 8  # Strong boost for Scottish given names
            # Override Korean detection if Scottish given name present
            if has_korean_pattern:
                scores['E4'] = max(0, scores['E4'] - 5)  # Reduce Korean score"""
            
            content = re.sub(anglo_scoring_pattern, new_scoring, content)
            print("   ✅ Added Scottish given name scoring with Korean override")
    
    # Write fixed pipeline
    with open(pipeline_path, 'w') as f:
        f.write(content)
    
    print("✅ Scottish given name prioritization added!")
    print("   Names like 'Lee, MacPherson' should now go to A1 instead of E4")

if __name__ == "__main__":
    fix_scottish_given_names()