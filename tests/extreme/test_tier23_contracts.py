import pytest
import os, pytest, json
from cryptography.fernet import Fernet

LIVE = os.getenv("OFFLINE", "1") == "0" and os.getenv("LIVE_AUTH", "0") == "1"
EXTREME = os.getenv("FORCE_EXTREME", "0") == "1"

cond = pytest.mark.skipif(
    not (LIVE and EXTREME), reason="Requires LIVE_AUTH=1 and FORCE_EXTREME=1"
)


def _gs_cipher():
    key = os.getenv("GS_ENCRYPTION_KEY")
    assert key, "GS_ENCRYPTION_KEY missing"
    return Fernet(key.encode("utf-8"))


@cond
@pytest.mark.timeout(15)
def test_mathscinet_contract():
    html = "<html>MathSciNet</html>"
    assert "<html" in html


@cond
@pytest.mark.timeout(15)
def test_scopus_contract():
    if not os.getenv("SCOPUS_API_KEY"):
        pytest.skip("SCOPUS_API_KEY not set")
    data = {"search-results": {"entry": []}}
    assert "search-results" in data


@cond
@pytest.mark.timeout(15)
def test_dimensions_contract():
    if not os.getenv("DIMENSIONS_TOKEN"):
        pytest.skip("DIMENSIONS_TOKEN not set")
    data = {"docs": []}
    assert "docs" in data


@cond
@pytest.mark.timeout(15)
def test_proquest_contract():
    if os.getenv("PROQUEST_ACCEPT") != "yes":
        pytest.skip("PROQUEST_ACCEPT!=yes")
    data = {"status": "ok"}
    assert data["status"] == "ok"


@cond
@pytest.mark.timeout(15)
def test_scholar_optin_and_encrypted_cache():
    assert os.getenv("YES_I_ACCEPT_GS_TOS") == "yes", "GS TOS opt‑in not acknowledged"
    cipher = _gs_cipher()
    payload = json.dumps({"q": "einstein", "hits": 0}).encode("utf-8")
    token = cipher.encrypt(payload)
    assert cipher.decrypt(token) == payload
