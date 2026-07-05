"""Spec §9 per-source daily quotas actually bind (R49 §3.8).

QuotaManager was fully implemented in src/authorities/base.py but never
wired — live calls only recorded cost, so metered sources (zbMATH 200/day)
had no ceiling. _call_canonical_fetcher now acquires quota per call
(kill-switch GMNAP_DISABLE_QUOTA=1), seeded from the spec's daily_quota
values with the U+00A0 service-name normalisation ("zbMATH\xa0Open" vs the
orchestrator's "zbMATH_Open").
"""

import asyncio

import pytest

from src.authorities.base import QuotaManager


@pytest.mark.timeout(30)
def test_spec_quota_binds_and_blocks(tmp_path):
    async def main():
        # QuotaManager creates an asyncio.Lock — construct inside a loop
        # (py3.9: Lock() outside a running loop is order-dependent flaky)
        qm = QuotaManager({"zbMATH_Open": {"daily_quota": 5}}, cache_dir=tmp_path)
        granted = sum([1 for _ in range(8) if await qm.acquire_quota("zbMATH_Open")])
        blocked = not await qm.acquire_quota("zbMATH_Open")
        return granted, blocked

    granted, blocked = asyncio.run(main())
    assert granted == 5
    assert blocked


@pytest.mark.timeout(30)
def test_manifest_built_from_spec_normalises_nbsp(monkeypatch):
    import src.authorities.manager_tier01 as m

    monkeypatch.setattr(m, "_QUOTA_MANAGER", None)

    async def main():
        # QuotaManager creates an asyncio.Lock — construct inside a loop
        qm = m._quota_manager()
        # the spec value (200/day) must bind under the orchestrator's name,
        # despite the spec spelling the service with a non-breaking space
        return qm._get_quota("zbMATH_Open")

    assert asyncio.run(main()) == 200
    monkeypatch.setattr(m, "_QUOTA_MANAGER", None)
