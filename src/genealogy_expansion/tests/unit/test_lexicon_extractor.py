from pipeline.extract import extract_from_text_blob, init


def test_basic_fr_window():
    init("config")
    text = "Sous la direction de Prof. Jean Martin, la thèse traite..."
    hits = extract_from_text_blob(text, "fr")
    assert any("Jean Martin" in h["name"] for h in hits)
