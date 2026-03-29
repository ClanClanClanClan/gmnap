import pytest
from src.regions.b_groups.b1_east_slavic import translit


@pytest.mark.timeout(15)
def test_basic_translit():
    assert translit("Владимир Путин")[:8].lower().startswith("vladimir")
