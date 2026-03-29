import re
from pathlib import Path

# Pattern to match duplicate @pytest.mark.timeout decorators
pattern = re.compile(r"(\s*)@pytest\.mark\.timeout\((\d+)\)\n\1@pytest\.mark\.timeout\(\d+\)\n")

# Get all python test files
test_files = list(Path("tests").rglob("test_*.py"))

fixed_files = []
for filepath in test_files:
    if filepath.exists():
        content = filepath.read_text()
        # Replace with single decorator
        new_content = pattern.sub(r"\1@pytest.mark.timeout(\2)\n", content)
        if content != new_content:
            filepath.write_text(new_content)
            fixed_files.append(str(filepath))
            print(f"Fixed: {filepath}")

print(f"\nFixed {len(fixed_files)} files")
