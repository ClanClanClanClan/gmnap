import os, asyncio, json, tempfile
import pytest

from src.pipeline.stage4_authority_enrich import enrich_batch
from src.pipeline.stage5_edge_extract import extract_edges_from_entries


@pytest.mark.asyncio
async def test_e2e_offline_enrich_and_extract():
    os.environ["OFFLINE"] = "1"  # ensure stub mode
    entries = [
        {"GlobalID": "ID1", "CanonicalLatin": "Tao, T.", "BirthYear": 1975},
        {"GlobalID": "ID2", "CanonicalLatin": "Hilbert, David", "BirthYear": 1862},
    ]
    enriched = await enrich_batch(entries, offline=True)
    assert len(enriched) == 2
    assert all("Advisors" in e for e in enriched)

    edges = extract_edges_from_entries(enriched)
    assert isinstance(edges, list)
    # In stub mode, some names may have zero advisors—just assert shape
    for e in edges:
        assert "source_id" in e and "relation_type" in e and "confidence" in e
