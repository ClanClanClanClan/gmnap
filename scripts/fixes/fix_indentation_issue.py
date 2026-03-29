#!/usr/bin/env python3
"""
Quick fix for the indentation issue in the pipeline that's causing the 'scores' variable error.
"""

import re
from pathlib import Path


def fix_pipeline_indentation():
    pipeline_path = Path(
        "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py"
    )

    print("🔧 Fixing pipeline indentation issue...")

    # Read the current pipeline
    with open(pipeline_path, "r") as f:
        content = f.read()

    # Fix the Slavic surnames list indentation
    # The problem is that the list items are indented incorrectly
    slavic_section_bad = r"""        # Czech/Polish surname patterns \(fix for G1→B2 misclassification\)
        slavic_surnames = \[
    ([^]]+)
\]"""

    # Find the current Slavic surnames section
    match = re.search(slavic_section_bad, content, re.DOTALL)

    if match:
        # Extract the list items
        list_content = match.group(1)

        # Re-format with proper indentation
        items = [
            item.strip().strip("'\"")
            for line in list_content.split("\n")
            for item in line.split(",")
            if item.strip().strip("'\"")
        ]

        # Create properly formatted list
        formatted_items = []
        for i, item in enumerate(items):
            if item:  # Skip empty items
                formatted_items.append(f"'{item}'")

        # Format as multi-line list with proper indentation
        lines = ["        slavic_surnames = ["]
        current_line = "            "
        line_length = 0

        for i, item in enumerate(formatted_items):
            if line_length + len(item) + 2 > 100 and current_line != "            ":
                # Start new line
                lines.append(current_line.rstrip(", ") + ",")
                current_line = "            " + item
                line_length = len(item)
            else:
                # Add to current line
                if current_line == "            ":
                    current_line += item
                    line_length = len(item)
                else:
                    current_line += ", " + item
                    line_length += len(item) + 2

            # Add comma for all but last item
            if i < len(formatted_items) - 1:
                if line_length > 100:
                    lines.append(current_line + ",")
                    current_line = "            "
                    line_length = 0

        # Add final line
        if current_line != "            ":
            lines.append(current_line)

        lines.append("        ]")

        # Replace in content
        replacement = (
            "        # Czech/Polish surname patterns (fix for G1→B2 misclassification)\n"
            + "\n".join(lines)
        )
        content = re.sub(slavic_section_bad, replacement, content, flags=re.DOTALL)

        print("   ✅ Fixed Slavic surnames list indentation")

    # Write the fixed pipeline
    with open(pipeline_path, "w") as f:
        f.write(content)

    print("✅ Pipeline indentation fixed!")


if __name__ == "__main__":
    fix_pipeline_indentation()
