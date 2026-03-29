#!/usr/bin/env python3
"""
Fix Chinese-Korean disambiguation issue - Yang, Lei should go to E1 not E4
The problem: 'yang' appears in both Chinese and Korean surname lists
Solution: Add competitive scoring to prioritize Chinese when both match
"""

import re
from pathlib import Path


def fix_chinese_korean_disambiguation():
    pipeline_path = Path(
        "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py"
    )

    print("🔧 Fixing Chinese-Korean surname disambiguation...")

    # Read current pipeline
    with open(pipeline_path, "r") as f:
        content = f.read()

    # Find the location after Chinese surname scoring
    chinese_scoring_pattern = (
        r"if has_chinese_surname:\n            scores\['E1'\] \+= 7  # Very strong indicator"
    )

    if re.search(chinese_scoring_pattern, content):
        # Add Chinese-Korean disambiguation logic after Chinese scoring
        disambiguation_code = """
        
        # Chinese-Korean disambiguation (fix for Yang→Korean issue)
        if has_chinese_surname and has_korean_pattern:
            # When surname matches both Chinese and Korean, use given name to decide
            name_parts = name_lower.replace(',', ' ').split()
            chinese_given_boost = ['lei', 'ming', 'wei', 'jing', 'hong', 'fang', 'gang', 'jun', 'hui']
            korean_given_boost = ['min-ho', 'jong-un', 'ji-su', 'hoon', 'kyun', 'yeol']
            
            has_chinese_given_strong = any(given in name_parts for given in chinese_given_boost)
            has_korean_given_strong = any(given.replace('-', '') in ''.join(name_parts) for given in korean_given_boost)
            
            if has_chinese_given_strong and not has_korean_given_strong:
                scores['E1'] += 3  # Boost Chinese for Chinese given names
                scores['E4'] = max(0, scores['E4'] - 2)  # Reduce Korean score
            elif has_korean_given_strong and not has_chinese_given_strong:  
                scores['E4'] += 3  # Boost Korean for Korean given names
                scores['E1'] = max(0, scores['E1'] - 2)  # Reduce Chinese score"""

        # Insert the disambiguation logic after Chinese surname scoring
        content = re.sub(
            chinese_scoring_pattern, chinese_scoring_pattern + disambiguation_code, content
        )
        print("   ✅ Added Chinese-Korean disambiguation logic")

    # Write fixed pipeline
    with open(pipeline_path, "w") as f:
        f.write(content)

    print("✅ Chinese-Korean disambiguation fixed!")
    print("   Yang, Lei should now go to E1 (Chinese) instead of E4 (Korean)")


if __name__ == "__main__":
    fix_chinese_korean_disambiguation()
