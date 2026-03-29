from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import Optional

from neo4j import Driver, GraphDatabase


@dataclass
class MGConfig:
    host: str = os.getenv("MG_HOST", "127.0.0.1")
    port: int = int(os.getenv("MG_PORT", "7687"))
    user: Optional[str] = os.getenv("MG_USER") or None
    password: Optional[str] = os.getenv("MG_PASSWORD") or None
    encrypted: bool = os.getenv("MG_TLS", "0") == "1"
    timeout: float = float(os.getenv("MG_TIMEOUT", "5.0"))


def _can_connect(host: str, port: int, timeout: float) -> bool:
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def build_driver(cfg: MGConfig) -> Driver:
    host = cfg.host
    port = cfg.port
    if host in ("localhost", "::1") and not _can_connect(host, port, cfg.timeout):
        host = "127.0.0.1"
    scheme = "bolt+s" if cfg.encrypted else "bolt"
    uri = f"{scheme}://{host}:{port}"
    auth = (cfg.user, cfg.password) if (cfg.user or cfg.password) else None
    return GraphDatabase.driver(uri, auth=auth, connection_timeout=cfg.timeout)


def sanity_ping(drv: Driver) -> bool:
    with drv.session() as s:
        rec = s.run("RETURN 1 AS ok").single()
        return int(rec["ok"]) == 1
