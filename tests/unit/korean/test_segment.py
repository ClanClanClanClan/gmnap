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


# No skip - test will handle missing pynini internally
@pytest.mark.timeout(15)
def test_cases():
    if not SEGMENT_AVAILABLE or segment is None:
        pytest.skip("segment function not available (pynini dependency missing)")

    assert segment("songkangho") == ["song", "kang", "ho"]
    assert segment("ahncheolhwan") == ["ahn", "cheol", "hwan"]
    assert segment("kimyoung") == ["kim", "young"]
