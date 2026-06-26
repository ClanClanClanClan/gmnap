from __future__ import annotations

import os
import ssl
from typing import Any, Dict


class SecureMemgraphConfig:
    def __init__(
        self,
        uri: str | None = None,
        username: str | None = None,
        password: str | None = None,
        ca_file: str | None = None,
    ):
        self.uri = uri or os.getenv("GMNAP_DB_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("GMNAP_DB_USER", "gmnap")
        self.password = password or os.getenv("GMNAP_DB_PASS", "CHANGE_ME")
        self.ca_file = ca_file or os.getenv("GMNAP_DB_CA", "")

    def build_ssl_context(self):
        if not self.ca_file:
            return None
        ctx = ssl.create_default_context(cafile=self.ca_file)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        return ctx


class SecureMemgraphClient:
    """Placeholder secure client. To be wired to Memgraph/Neo4j driver."""

    def __init__(self, cfg: SecureMemgraphConfig | None = None):
        self.cfg = cfg or SecureMemgraphConfig()
        self.ssl_context = self.cfg.build_ssl_context()

    def connect(self) -> Dict[str, Any]:
        # In real impl, create driver with auth and tls config. Here we just return config for tests.
        return {
            "uri": self.cfg.uri,
            "username": self.cfg.username,
            "password_set": bool(self.cfg.password),
            "tls": bool(self.ssl_context is not None),
        }
