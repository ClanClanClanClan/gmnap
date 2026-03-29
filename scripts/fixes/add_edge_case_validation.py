#!/usr/bin/env python3
"""
Add edge case validation to reject malformed names that should fail
Fix ~10 tests: titles (Dr. Smith), symbols (Smith@gmail), numbers (Smith2), etc.
"""

import re
from pathlib import Path


def add_edge_case_validation():
    pipeline_path = Path(
        "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/Maths/gmnap/src/gmnap/core/pipeline.py"
    )

    print("🔧 Adding edge case validation for malformed names...")

    # Read current pipeline
    with open(pipeline_path, "r") as f:
        content = f.read()

    # Find the beginning of the _detect_region_by_name_pattern function
    function_start_pattern = r"def _detect_region_by_name_pattern\(self, name: str\) -> str:\n        \"\"\"Detect region based on Latin name patterns\.\"\"\"\n        if not name:\n            return 'R0'\n            \n        name_lower = name\.lower\(\)"

    if re.search(function_start_pattern, content, re.DOTALL):
        # Add validation logic right after the initial checks
        validation_code = """def _detect_region_by_name_pattern(self, name: str) -> str:
        \"\"\"Detect region based on Latin name patterns.\"\"\"
        if not name:
            return 'R0'
            
        name_lower = name.lower()
        
        # Edge case validation - reject malformed names that should fail
        # Titles (Dr., Prof., etc.)
        title_prefixes = ['dr.', 'prof.', 'mr.', 'mrs.', 'ms.', 'sir ', 'lord ', 'lady ']
        if any(name_lower.startswith(title) for title in title_prefixes):
            raise ValueError(f"Names with titles not allowed: {name}")
        
        # Numbers in names
        if any(char.isdigit() for char in name):
            raise ValueError(f"Numbers not allowed in names: {name}")
        
        # Special symbols
        forbidden_symbols = ['@', '#', '$', '%', '&', '*', '+', '=', '|', '\\\\', '/', '?', '<', '>']
        if any(symbol in name for symbol in forbidden_symbols):
            raise ValueError(f"Special symbols not allowed in names: {name}")
        
        # Excessive length (over 100 characters total)
        if len(name) > 100:
            raise ValueError(f"Name too long ({len(name)} characters): {name}")
        
        # Missing surname or given name
        if name.count(',') == 1:
            parts = name.split(',')
            surname = parts[0].strip()
            given = parts[1].strip()
            if not surname or not given:
                raise ValueError(f"Missing surname or given name: {name}")
        elif ',' not in name:
            # No comma format - require at least 2 words
            words = name.split()
            if len(words) < 2:
                raise ValueError(f"Name must contain both surname and given name: {name}")"""

        content = re.sub(function_start_pattern, validation_code, content, flags=re.DOTALL)
        print("   ✅ Added comprehensive edge case validation")

    # Write fixed pipeline
    with open(pipeline_path, "w") as f:
        f.write(content)

    print("✅ Edge case validation added!")
    print("   Names with titles, numbers, symbols should now be properly rejected")


if __name__ == "__main__":
    add_edge_case_validation()
