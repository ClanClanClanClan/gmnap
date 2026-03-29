from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class DBConfig:
    uri: str
    user: str | None
    password: str | None
    tls: bool
    tls_cert: str | None
    verify: bool


def build_db_config(prefix: str = "MG") -> DBConfig:
    """
    Build a Memgraph/Neo4j Bolt config from environment (no connection opened).
    Env (prefix MG_ by default):
      MG_URI (bolt://host:7687 or bolt+s://... for TLS)
      MG_USER, MG_PASSWORD
      MG_TLS ("0"/"1"), MG_TLS_CERT (path), MG_TLS_VERIFY ("0"/"1")
    """
    uri = os.getenv(f"{prefix}_URI", "bolt://localhost:7687")
    tls_env = os.getenv(f"{prefix}_TLS", "").strip()
    tls = tls_env == "1" or uri.startswith(("bolt+s://", "neo4j+s://"))
    user = os.getenv(f"{prefix}_USER")
    password = os.getenv(f"{prefix}_PASSWORD")
    cert = os.getenv(f"{prefix}_TLS_CERT")
    verify = os.getenv(f"{prefix}_TLS_VERIFY", "1") != "0"
    # Normalise TLS schemes
    if tls and uri.startswith("bolt://"):
        uri = uri.replace("bolt://", "bolt+s://", 1)
    return DBConfig(
        uri=uri, user=user, password=password, tls=tls, tls_cert=cert, verify=verify
    )
