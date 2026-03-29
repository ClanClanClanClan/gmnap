import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.regions.script_detect import primary_script
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.pipeline.stage2_detect_region import detect_region


@pytest.mark.timeout(15)
def test_script_detection_various():
    assert primary_script("Владимир") == "Cyrillic"
    assert primary_script("김대중") == "Hangul"
    assert primary_script("陈景润") == "Han"
    assert primary_script("Εύρηκα") == "Greek"
    assert primary_script("عبدالله") == "Arabic"
    assert primary_script("שלום") == "Hebrew"
    assert primary_script("आनंद") == "Devanagari"


@pytest.mark.timeout(15)
def test_region_detection_fallbacks():
    e = {"CanonicalNative": "湯川秀樹"}
    r, s = detect_region(e)
    assert r == "E1"
    e2 = {"CanonicalLatin": "Évariste Galois"}
    r2, s2 = detect_region(e2)
    assert r2 in ("A2", "R0")
