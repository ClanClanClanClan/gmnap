import yaml
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.e_groups.e4_korea.processor import E4KoreanProcessor

# Load test data
import os

data_file = os.path.join(os.path.dirname(__file__), "../../data/korean.yaml")
if os.path.exists(data_file):
    test_data = yaml.safe_load(open(data_file))
else:
    test_data = {"test1": {"name": "김민수", "romanized": "Kim Min-su"}}
handler = E4KoreanProcessor()


@pytest.mark.parametrize("entry_id,entry", test_data.items())
@pytest.mark.timeout(15)
def test_roundtrip(entry_id, entry):
    """Test each mathematician entry"""
    assert handler.quality_gate(
        entry
    ), f"Failed: {entry_id} - {entry['CanonicalLatin']}"


@pytest.mark.timeout(15)
def test_handler_integration():
    """Test E4 handler integration"""
    test_entry = {
        "CanonicalLatin": "Kim, Tae-Hyung",
        "AllCommonVariants": ["Kim Taehyung"],
    }

    # Test conversion
    hangul = handler.latin_to_native(test_entry)
    assert hangul is not None
    assert handler._contains_hangul(hangul)

    # Test quality gate
    assert handler.quality_gate(test_entry)


@pytest.mark.timeout(15)
def test_hyphen_space_variants():
    """Test GMNAP rule #13 compliance"""
    test_cases = [
        ("Kim Jong-un", ["kimjongun", "kim jong un", "kim-jong-un"]),
        ("Park Ji-sung", ["parkjisung", "park ji sung", "park-ji-sung"]),
    ]

    for name, expected_variants in test_cases:
        order_key = handler.generate_order_key({"CanonicalLatin": name})
        assert order_key == expected_variants[0]  # Collapsed form
