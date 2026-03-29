from src.ops.unicode_norm import normalise_text, normalise_entry_strings


def test_zwsp_and_ctrl_removed():
    s = "A\u200b\u200d\ufeffB\u0001"
    assert normalise_text(s) == "AB"


def test_fold_exceptions():
    assert "strasse" in normalise_text("Straße").lower()
    assert "AE" in normalise_text("Æneas")


def test_entry_recursive():
    e = {"a": "Noe\u200bther, Emmy", "b": ["Straße", {"c": "\ufeffX"}]}
    out = normalise_entry_strings(e)
    assert out["a"] == "Noether, Emmy"
    assert out["b"][0] == "Strasse"
    assert out["b"][1]["c"] == "X"
