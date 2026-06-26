from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

import aiohttp
import yaml


@dataclass
class ConnectorRateLimiter:
    rps: float = 2.0
    _last: float = 0.0

    async def wait(self):
        now = time.time()
        min_interval = 1.0 / max(self.rps, 1e-9)
        elapsed = now - self._last
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last = time.time()


class BaseConnector(ABC):
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.rate = RateLimiter(rps=float(cfg.get("rps", 2.0)))

    async def _robots_allowed(self, session: aiohttp.ClientSession, url: str) -> bool:
        # Minimal robots check placeholder. Pipeline should enforce robots/ToS.
        return True

    def _tos_allowed(self) -> bool:
        return not self.cfg.get("legal_blocked", False)

    @abstractmethod
    async def records(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        # Yield raw records from the source
        ...

    @abstractmethod
    def to_thesis(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        # Map raw record to standardized Thesis dict
        ...


def load_sources(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
