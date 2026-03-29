import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.b_groups.b1_romanize import romanize_cyrillic, canonical_family_given


@pytest.mark.timeout(15)
def test_simple_romanize():
    assert romanize_cyrillic("Владимир")[:3].lower() in ("vla",)


@pytest.mark.timeout(15)
def test_canonical_swaps_two_tokens():
    out = canonical_family_given("Владимир Путин")
    assert out.startswith("Putin, ")
