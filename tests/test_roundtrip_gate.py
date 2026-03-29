from pathlib import Path
import pytest
import csv, pathlib
from src.linguistics.roundtrip import roundtrip_score


@pytest.mark.timeout(15)
def test_cjk_roundtrip_fixture():
    p = pathlib.Path("extras/fixtures/cjk_pairs.csv")
    ok = []
    with p.open(encoding="utf-8") as fh:
        for i, row in enumerate(csv.DictReader(fh)):
            native = row["native"]
            assert roundtrip_score(native) >= 0.97


@pytest.mark.timeout(15)
def test_sea_roundtrip_fixture():
    p = pathlib.Path("extras/fixtures/sea_pairs.csv")
    with p.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            native = row["native"]
            assert roundtrip_score(native) >= 0.97
