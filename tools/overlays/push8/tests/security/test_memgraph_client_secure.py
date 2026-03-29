import os
from src.core.memgraph_client_secure import SecureMemgraphClient, SecureMemgraphConfig


def test_secure_client_defaults(tmp_path, monkeypatch):
    ca = tmp_path / "ca.pem"
    ca.write_text(
        "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n", encoding="utf-8"
    )
    monkeypatch.setenv("GMNAP_DB_URI", "bolt+s://memgraph.example:7687")
    monkeypatch.setenv("GMNAP_DB_USER", "ethz")
    monkeypatch.setenv("GMNAP_DB_PASS", "secret")
    monkeypatch.setenv("GMNAP_DB_CA", str(ca))
    client = SecureMemgraphClient()
    conf = client.connect()
    assert conf["uri"].startswith("bolt")
    assert conf["password_set"]
    assert conf["tls"]
