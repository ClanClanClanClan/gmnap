from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from ..genealogy.authority_enricher import AuthorityEnricher

_enricher: AuthorityEnricher | None = None


def _get_enricher() -> AuthorityEnricher:
    global _enricher
    if _enricher is None:
        _enricher = AuthorityEnricher()
    return _enricher


async def enrich_batch(
    entries: List[Dict[str, Any]], offline: bool = False
) -> List[Dict[str, Any]]:
    """Stage 4: Authority enrichment.
    Adds `Advisors` array to each entry. Safe in OFFLINE mode (deterministic stubs).
    """
    enricher = _get_enricher()
    sem = asyncio.Semaphore(8)

    async def _enrich(e: Dict[str, Any]) -> Dict[str, Any]:
        async with sem:
            return await enricher.enrich_entry(e, offline=offline)

    tasks = [_enrich(e) for e in entries]
    return await asyncio.gather(*tasks)
