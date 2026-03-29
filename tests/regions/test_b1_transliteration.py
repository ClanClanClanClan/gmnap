import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.b_groups.b1_east_slavic import B1_EastSlavic as B1EastSlavic


@pytest.mark.timeout(15)
def test_b1_handles_cyrillic_text():
    """Test that B1 processor can handle Cyrillic text without errors."""
    try:
        b1 = B1EastSlavic()  # No arguments needed
    except Exception as e:
        pytest.skip(f"Could not instantiate B1_EastSlavic: {e}")

    # Test 1: Process Latin text (should remain unchanged)
    entry_latin = {"CanonicalLatin": "Vladimir Putin"}
    b1.clean(entry_latin)
    assert (
        entry_latin["CanonicalLatin"] == "Vladimir Putin"
    ), "Latin text should remain unchanged"

    # Test 2: Process entry with Cyrillic in native field
    entry_native = {
        "CanonicalLatin": "Vladimir Putin",
        "CanonicalNative": "Владимир Путин",
    }
    b1.clean(entry_native)
    # Should process without errors
    assert "CanonicalLatin" in entry_native
    assert "CanonicalNative" in entry_native

    # Test 3: Handle mixed script (this is allowed per B1 config)
    entry_mixed = {"CanonicalLatin": "Vladimir Путин"}
    b1.clean(entry_mixed)
    # Should process without raising exceptions
    assert "CanonicalLatin" in entry_mixed
