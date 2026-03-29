#!/usr/bin/env python3
"""
Fix Czech/Slovak accent normalization issue - apply same logic as Hungarian
The problem: Novák, Wójcik have accents that trigger Spanish detection,
but we're not using accent normalization for Slavic surname matching like we do for Hungarian
"""

import re
from pathlib import Path


def fix_czech_slovak_accents():
    pipeline_path = Path(
        "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py"
    )

    print("🔧 Fixing Czech/Slovak accent normalization...")

    # Read current pipeline
    with open(pipeline_path, "r") as f:
        content = f.read()

    # Find the current Slavic surname matching logic
    slavic_match_pattern = r"has_slavic_surname = any\(surname in name_lower for surname in slavic_surnames\)"

    if re.search(slavic_match_pattern, content):
        # Replace with accent-normalized matching (same as Hungarian)
        new_slavic_logic = """# Accent-normalized Slavic surname matching (fix for Czech/Slovak accents → Spanish issue)
        has_slavic_surname = any(surname in name_normalized for surname in slavic_surnames)"""

        content = re.sub(slavic_match_pattern, new_slavic_logic, content)
        print("   ✅ Applied accent normalization to Slavic surname matching")

        # Also boost Slavic scoring to override Spanish accent detection more strongly
        slavic_scoring_pattern = r"if has_slavic_surname:\n            scores\['B2'\] \+= 8  # Strong boost to override Spanish detection\n            scores\['G1'\] = max\(0, scores\['G1'\] - 4\)  # Reduce Spanish score"

        if re.search(slavic_scoring_pattern, content):
            new_slavic_scoring = """if has_slavic_surname:
            scores['B2'] += 10  # Very strong boost to override Spanish accent detection
            scores['G1'] = max(0, scores['G1'] - 6)  # Stronger Spanish score reduction"""

            content = re.sub(slavic_scoring_pattern, new_slavic_scoring, content)
            print(
                "   ✅ Increased Slavic surname boost to override Spanish accent detection"
            )

    # Write fixed pipeline
    with open(pipeline_path, "w") as f:
        f.write(content)

    print("✅ Czech/Slovak accent normalization fixed!")
    print("   Names like Novák, Wójcik should now go to B2 instead of G1")


if __name__ == "__main__":
    fix_czech_slovak_accents()
