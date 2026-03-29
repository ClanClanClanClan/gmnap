import re
from pathlib import Path

# Pattern to match duplicate @pytest.mark.timeout decorators
pattern = re.compile(r"(@pytest\.mark\.timeout\(\d+\))\n\1\n")

# Get all test files with the issue
test_files = [
    "tests/unit/test_globalid.py",
    "tests/unit/test_regions.py",
    "tests/unit/test_cache_system.py",
    "tests/unit/test_config.py",
    "tests/unit/test_a4_oceania.py",
    "tests/unit/test_debug_indian.py",
    "tests/unit/test_cjk_roundtrip.py",
    "tests/unit/test_debug_detection.py",
    "tests/unit/test_simple_detection.py",
    "tests/unit/test_hell_level.py",
    "tests/unit/test_global_id.py",
    "tests/unit/test_debug_output.py",
    "tests/unit/test_schema.py",
    "tests/unit/test_schema_validation.py",
    "tests/unit/test_debug_optimized_issue.py",
    "tests/unit/test_thread_safety_issues.py",
    "tests/unit/test_debug_spanish.py",
    "tests/unit/test_a3_nordic_baltic.py",
    "tests/unit/test_surname_detection.py",
    "tests/unit/test_direct_classification.py",
    "tests/unit/test_unicode_handler.py",
    "tests/unit/test_thread_safe_demo.py",
    "tests/unit/test_region_a1.py",
    "tests/unit/test_manager_caching.py",
]

fixed_files = []
for filepath in test_files:
    path = Path(filepath)
    if path.exists():
        content = path.read_text()
        new_content = pattern.sub(r"\1\n", content)
        if content != new_content:
            path.write_text(new_content)
            fixed_files.append(filepath)
            print(f"Fixed: {filepath}")

print(f"\nFixed {len(fixed_files)} files")
