import csv
import pathlib

import pytest

BASE = pathlib.Path("datasets/regional_test_suites")
codes = [p.name for p in BASE.iterdir() if p.is_dir()]


@pytest.mark.parametrize("rc", codes)
@pytest.mark.timeout(15)
def test_pairs_csv_shape(rc):
    p = BASE / rc / "pairs_sample.csv"
    assert p.exists()
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    assert rows and "native" in rows[0] and "latin" in rows[0]
