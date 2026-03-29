import csv

import pytest

from src.linguistics.roundtrip import roundtrip_score


def _pairs(path):
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            yield row["native"], row["latin"]


@pytest.mark.parametrize("native,latin", list(_pairs("extras/fixtures/cjk_pairs.csv")))
@pytest.mark.timeout(15)
def test_cjk_roundtrip_extreme(native, latin):
    assert roundtrip_score(native) >= 0.97


@pytest.mark.parametrize("native,latin", list(_pairs("extras/fixtures/sea_pairs.csv")))
@pytest.mark.timeout(15)
def test_sea_roundtrip_extreme(native, latin):
    assert roundtrip_score(native) >= 0.97
