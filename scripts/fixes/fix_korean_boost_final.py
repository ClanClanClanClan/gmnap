#!/usr/bin/env python3
"""
Final fix for the Korean boost placement - move it to after scores initialization
"""

import re
from pathlib import Path


def fix_korean_boost_final():
    pipeline_path = Path(
        "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py"
    )

    print("🔧 Final fix for Korean boost placement...")

    # Read the current pipeline
    with open(pipeline_path, "r") as f:
        content = f.read()

    # Remove the Korean boost that's still in the wrong place
    korean_boost_pattern = r"""        
        # Boost Korean detection \(fix for A1 misclassification\)
        if has_korean_pattern:
            scores\['E4'\] \+= 8  # Strong boost for Korean patterns
            # Reduce A1 score if Korean pattern detected
            scores\['A1'\] = max\(0, scores\['A1'\] - 3\)"""

    content = re.sub(korean_boost_pattern, "", content, flags=re.DOTALL)

    # Find the end of the scores dictionary initialization
    scores_end_pattern = r"(        scores = \{[^}]+        \})"
    scores_match = re.search(scores_end_pattern, content, re.DOTALL)

    if scores_match:
        # Add the Korean boost right after the scores initialization
        korean_boost_correct = """
        
        # Apply Korean pattern boost (fix for A1 misclassification)
        if has_korean_pattern:
            scores['E4'] += 8  # Strong boost for Korean patterns
            scores['A1'] = max(0, scores['A1'] - 3)  # Reduce A1 score"""

        # Insert after the scores dictionary
        insertion_point = scores_match.end()
        content = content[:insertion_point] + korean_boost_correct + content[insertion_point:]

        print("   ✅ Moved Korean boost to after scores initialization")

    # Write the fixed pipeline
    with open(pipeline_path, "w") as f:
        f.write(content)

    print("✅ Korean boost placement finally fixed!")


if __name__ == "__main__":
    fix_korean_boost_final()
