import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.llm.stage1b_llmextract_etd import extract_from_text


@pytest.mark.timeout(15)
def test_etd_extract_and_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("GMNAP_ETD_CACHE_DIR", str(tmp_path))
    text = """Title: An Approach to Prime Numbers
Author: Jane Doe
Advisors: Prof. X, Prof. Y
Degree Date: 2015-06
Institution: ETH Zurich"""
    out = extract_from_text(text)
    assert out["title"].startswith("An Approach")
    out2 = extract_from_text(text)
    assert out2 == out
