import re
from pathlib import Path

# Pattern to match single @pytest.mark.timeout decorators followed by a blank line
pattern = re.compile(r"(@pytest\.mark\.timeout\(\d+\))\n\n(\s+def )")

# Test files that might have issues
test_files = [
    "tests/unit/test_cache_system.py",
    "tests/unit/test_regions.py",
    "tests/unit/regions/test_region_e4.py",
]

fixed_files = []
for filepath in test_files:
    path = Path(filepath)
    if path.exists():
        content = path.read_text()
        # Replace the pattern - remove the extra blank line
        new_content = pattern.sub(r"\1\n\2", content)
        if content != new_content:
            path.write_text(new_content)
            fixed_files.append(filepath)
            print(f"Fixed: {filepath}")

print(f"\nFixed {len(fixed_files)} files")
