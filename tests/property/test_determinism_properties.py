import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.authorities.policy import ConflictPolicy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.authorities.merge_authority_data import merge_authority_fragments


@pytest.mark.timeout(15)
def test_merge_authority_is_deterministic():
    fragments = [
        {"_source": {"service": "OpenAlex"}, "BirthYear": 1900, "Institution": ["X"]},
        {
            "_source": {"service": "CrossrefThesis"},
            "BirthYear": 1901,
            "Institution": ["X", "Y"],
        },
        {"_source": {"service": "ORCID_ETD"}, "BirthYear": 1899, "Institution": ["Y"]},
    ]
    p = ConflictPolicy.load()
    out1 = merge_authority_fragments(fragments, p)
    out2 = merge_authority_fragments(list(reversed(fragments)), p)
    assert out1 == out2
    assert out1["BirthYear"] in (1899, 1900, 1901)
    assert set(out1["Institution"]) == {"X", "Y"}
