#!/usr/bin/env python3
"""
Fix the Korean boost placement issue - it needs to be after scores is initialized
"""

import re
from pathlib import Path


def fix_korean_boost_placement():
    pipeline_path = Path(
        "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py"
    )

    print("🔧 Fixing Korean boost placement...")

    # Read the current pipeline
    with open(pipeline_path, "r") as f:
        content = f.read()

    # Find and remove the Korean boost section that's in the wrong place
    korean_boost_wrong = r"""        
        # Boost Korean detection \(fix for A1 misclassification\)
        if has_korean_pattern:
            scores\['E4'\] \+= 8  # Strong boost for Korean patterns
            # Reduce A1 score if Korean pattern detected
            scores\['A1'\] = max\(0, scores\['A1'\] - 3\)
        """

    # Remove the misplaced Korean boost
    content = re.sub(korean_boost_wrong, "", content, flags=re.DOTALL)

    # Find where the Korean pattern detection happens (after scores is initialized)
    # Look for "has_korean_pattern = any" which should be after scores initialization
    korean_pattern_match = re.search(
        r"(has_korean_pattern = any\(name_lower\.startswith\(surname \+ \',\'\) or name_lower\.startswith\(surname \+ \' \'\) for surname in korean_surnames\))",
        content,
    )

    if korean_pattern_match:
        # Add the Korean boost right after the pattern detection
        korean_boost_correct = """
        
        # Boost Korean detection (fix for A1 misclassification)
        if has_korean_pattern:
            scores['E4'] += 8  # Strong boost for Korean patterns
            # Reduce A1 score if Korean pattern detected
            scores['A1'] = max(0, scores['A1'] - 3)"""

        # Insert the Korean boost after the pattern detection
        insertion_point = korean_pattern_match.end()
        content = (
            content[:insertion_point] + korean_boost_correct + content[insertion_point:]
        )

        print(
            "   ✅ Moved Korean boost to correct location (after scores initialization)"
        )

    # Write the fixed pipeline
    with open(pipeline_path, "w") as f:
        f.write(content)

    print("✅ Korean boost placement fixed!")


if __name__ == "__main__":
    fix_korean_boost_placement()
