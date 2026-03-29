import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.unicode_handler import normalise_entry_strings


@pytest.mark.timeout(15)
def test_zwsp_and_ctrl_removed():
    s = "A\u200B\u200D\uFEFFB\u0001"
    assert normalise_text(s) == "AB"


@pytest.mark.timeout(15)
def test_fold_exceptions():
    assert "strasse" in normalise_text("Straße").lower()
    assert "AE" in normalise_text("Æneas")


@pytest.mark.timeout(15)
def test_entry_recursive():
    e = {"a": "Noe\u200Bther, Emmy", "b": ["Straße", {"c": "\uFEFFX"}]}
    out = normalise_entry_strings(e)
    assert out["a"] == "Noether, Emmy"
    assert out["b"][0] == "Strasse"
    assert out["b"][1]["c"] == "X"
