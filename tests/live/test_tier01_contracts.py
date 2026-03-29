import pytest
import os, pytest, requests

LIVE = os.getenv("OFFLINE", "1") == "0" and os.getenv("LIVE_AUTH", "0") == "1"


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="LIVE_AUTH=1 and OFFLINE=0 required")
@pytest.mark.timeout(15)
def test_crossref_thesis_contract():
    r = requests.get(
        "https://api.crossref.org/works",
        params={"filter": "type:dissertation", "query.author": "Gauss", "rows": 1},
        timeout=20,
    )
    r.raise_for_status()
    j = r.json()
    assert "message" in j and (
        "items" in j["message"] or "total-results" in j["message"]
    )


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="LIVE_AUTH=1 and OFFLINE=0 required")
@pytest.mark.timeout(15)
def test_wikidata_p184_contract():
    r = requests.get(
        "https://query.wikidata.org/sparql",
        params={
            "query": "SELECT ?p WHERE { ?p wdt:P106 wd:Q170790 . } LIMIT 1",
            "format": "json",
        },
        timeout=30,
        headers={"User-Agent": "gmnap-v7"},
    )
    r.raise_for_status()
    j = r.json()
    assert "results" in j and "bindings" in j["results"]


@pytest.mark.live
@pytest.mark.skipif(
    not LIVE or os.getenv("OAI_BASE_URL") is None, reason="Need OAI_BASE_URL"
)
@pytest.mark.timeout(15)
def test_oai_identify_contract():
    base = os.getenv("OAI_BASE_URL")
    r = requests.get(base, params={"verb": "Identify"}, timeout=20)
    r.raise_for_status()
    assert "<Identify>" in r.text or "Identify" in r.text


@pytest.mark.live
@pytest.mark.skipif(not LIVE, reason="LIVE_AUTH=1 and OFFLINE=0 required")
@pytest.mark.timeout(15)
def test_hal_contract():
    r = requests.get(
        "https://api.archives-ouvertes.fr/search/",
        params={"q": "thesis", "rows": 1, "fl": "docid"},
        timeout=20,
    )
    r.raise_for_status()
    j = r.json()
    assert isinstance(j, dict) and ("response" in j or "nhits" in j)


@pytest.mark.live
@pytest.mark.skipif(
    not LIVE or os.getenv("GND_SRU_URL") is None, reason="Need GND_SRU_URL"
)
@pytest.mark.timeout(15)
def test_gnd_contract():
    base = os.getenv("GND_SRU_URL")
    r = requests.get(
        base,
        params={
            "version": "1.1",
            "operation": "searchRetrieve",
            "recordSchema": "PicaPlus-xml",
            "query": 'any="Albert Einstein"',
            "maximumRecords": 1,
        },
        timeout=20,
    )
    r.raise_for_status()
    assert "<searchRetrieveResponse" in r.text


@pytest.mark.live
@pytest.mark.skipif(
    not LIVE or os.getenv("ZBMATH_API_URL") is None, reason="Need ZBMATH_API_URL"
)
@pytest.mark.timeout(15)
def test_zbmath_contract():
    base = os.getenv("ZBMATH_API_URL")
    r = requests.get(base, params={"q": "einstein"}, timeout=20)
    r.raise_for_status()
    j = r.json()
    assert isinstance(j, dict)
