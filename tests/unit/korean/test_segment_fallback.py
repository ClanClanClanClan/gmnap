#!/usr/bin/env python3
import os
import sys

import pytest

# Try to import segment, skip if not available
try:
    # Change to Korean module directory
    original_cwd = os.getcwd()
    korean_dir = os.path.join(original_cwd, "src/regions/e_groups/e4_korea")
    os.chdir(korean_dir)
    sys.path.insert(0, "src")
    try:
        from segment import segment

        SEGMENT_AVAILABLE = True
    finally:
        os.chdir(original_cwd)
except ImportError:
    SEGMENT_AVAILABLE = False
    segment = None


# Skip test if segment function is not available
@pytest.mark.skipif(
    not SEGMENT_AVAILABLE,
    reason="segment function not available (pynini dependency missing)",
)
@pytest.mark.timeout(15)
def test_segment_cases():
    """Test segmentation functionality."""
    test_cases = [
        ("songkangho", ["song", "kang", "ho"]),
        ("ahncheolhwan", ["ahn", "cheol", "hwan"]),
        ("kimyoung", ["kim", "young"]),
    ]

    for input_name, expected in test_cases:
        result = segment(input_name)
        assert result == expected, f"Expected {expected}, got {result} for {input_name}"
        print(f"✓ {input_name} -> {result}")


if __name__ == "__main__":
    test_segment_cases()
    print("✓ All segmentation tests passed")
