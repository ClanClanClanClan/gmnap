"""Unit tests for `_call_canonical_fetcher` and the `_fetch_*` shims.

These pin the contract between the V7 tier-orchestrator
(`src/authority/manager_tier01.py`) and the canonical fetchers
(`src/authorities/tierN/*.py`):

  - With OFFLINE=1: the live path is never invoked; callers see
    `{"<source>": {"hit": False}}`.
  - With OFFLINE=0 + cache miss: the canonical Fetcher's `fetch()`
    is awaited, the FetchResult is translated to the tier01 dict
    shape, and the result is cached for next time.
  - With OFFLINE=0 + cache hit: the cache is returned without
    touching the Fetcher (no network).
  - On any Fetcher exception (network failure, parse error, etc.):
    the call degrades to `{"hit": False, "reason": "fetch_error:…"}`
    rather than propagating — a single source's failure must not
    poison a 1000-entry batch.
  - On Fetcher class missing / un-importable: same defensive
    degradation with `reason: fetcher_unavailable:…`.
"""

from __future__ import annotations

import asyncio
import pathlib
import tempfile
from unittest.mock import patch

import pytest

from src.authorities.base import AuthorityData, FetchResult, FetchStatus


@pytest.fixture
def fresh_module(monkeypatch):
    """Patch `manager_tier01` to use a temp cache dir per test, and
    drain the pooled fetchers between tests.

    Earlier versions of this fixture did ``importlib.reload(m)`` to
    rebuild the module against a fresh env. That left other test
    modules (which did ``from src.authority.manager_tier01 import
    _fetch_X`` at file-load time) holding *stale* function references
    bound to a now-replaced module globals dict — so e.g.
    ``test_authority_manager.py``'s ``with patch("…OFFLINE", True)``
    became a no-op against the post-reload module's already-frozen
    globals.

    Use ``monkeypatch.setattr`` on the module attributes instead. It
    flips the constants for the duration of one test, then reverts
    cleanly so neither the module identity nor any cross-module
    import binding is disturbed.

    Also: the fetcher pool now lives across tests by design, so
    drop it on entry/exit. Otherwise a previous test's mocked
    `OpenAlexFetcher.fetch` (which has been unwound by patch.object)
    would still apply via the cached instance.
    """
    import src.authority.manager_tier01 as m

    # Drain any stale pooled fetchers from a previous test.
    asyncio.run(m._close_fetcher_pool())

    cache_dir = pathlib.Path(tempfile.mkdtemp()).resolve()
    monkeypatch.setattr(m, "CACHE_DIR", cache_dir)
    yield m

    # Drain again on teardown so the next test starts clean.
    asyncio.run(m._close_fetcher_pool())


def _run(coro):
    """Run an async coroutine on a fresh event loop."""
    return asyncio.run(coro)


def _set_offline(monkeypatch, m, value: bool):
    """Helper: patch OFFLINE on the module and let monkeypatch revert."""
    monkeypatch.setattr(m, "OFFLINE", value)


# ── Successful translation path ──────────────────────────────────────


def test_successful_fetch_translates_to_tier01_dict(monkeypatch, fresh_module):
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.openalex import OpenAlexFetcher

    fake = FetchResult(
        status=FetchStatus.SUCCESS,
        data=AuthorityData(
            source="OpenAlex",
            source_id="A12345",
            canonical_name="Test, Person",
            identifiers={"OpenAlexID": "A12345", "ORCID": "0000-0001-2345-6789"},
            affiliations=[{"institution": "MIT"}],
            birth_year=1900,
            death_year=1990,
            countries=["US"],
        ),
    )

    async def fake_fetch(self, query):
        return fake

    with patch.object(OpenAlexFetcher, "fetch", fake_fetch):
        result = _run(fresh_module._fetch_openalex({"CanonicalLatin": "Test, Person"}))

    assert result["OpenAlex"]["hit"] is True
    assert result["OpenAlex"]["source_id"] == "A12345"
    assert result["OpenAlex"]["canonical_name"] == "Test, Person"
    assert result["OpenAlex"]["identifiers"]["ORCID"] == "0000-0001-2345-6789"
    assert result["OpenAlex"]["affiliations"] == [{"institution": "MIT"}]
    assert result["OpenAlex"]["birth_year"] == 1900
    assert result["OpenAlex"]["death_year"] == 1990
    assert result["OpenAlex"]["countries"] == ["US"]


# ── Cache hit short-circuits the live path ────────────────────────


def test_cache_hit_does_not_call_fetcher(monkeypatch, fresh_module):
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.crossref import CrossrefFetcher

    fake = FetchResult(
        status=FetchStatus.SUCCESS,
        data=AuthorityData(source="Crossref", source_id="X1"),
    )

    fetch_call_count = {"n": 0}

    async def counting_fetch(self, query):
        fetch_call_count["n"] += 1
        return fake

    with patch.object(CrossrefFetcher, "fetch", counting_fetch):
        # First call — should hit the wire
        _run(fresh_module._fetch_crossref({"CanonicalLatin": "Cache, Test"}))
        # Second call — should hit the on-disk cache
        result2 = _run(fresh_module._fetch_crossref({"CanonicalLatin": "Cache, Test"}))

    assert fetch_call_count["n"] == 1, "second call must come from cache, not network"
    assert result2["Crossref"]["hit"] is True
    assert result2["Crossref"]["source_id"] == "X1"


# ── OFFLINE=1 short-circuits everything ───────────────────────────


def test_offline_skips_fetcher_entirely(monkeypatch, fresh_module):
    _set_offline(monkeypatch, fresh_module, True)
    from src.authorities.tier0.orcid_etd import ORCIDETDFetcher

    async def boom(self, query):
        raise AssertionError("OFFLINE=1 must not call fetch()")

    with patch.object(ORCIDETDFetcher, "fetch", boom):
        result = _run(fresh_module._fetch_orcid_etd({"CanonicalLatin": "Off, Line"}))

    assert result["ORCID_ETD"]["hit"] is False
    # OFFLINE skip uses the bare-`hit: False` shape, no `reason` key.
    assert "reason" not in result["ORCID_ETD"]


# ── Error paths: caller must NEVER raise ──────────────────────────


def test_fetcher_exception_is_contained(monkeypatch, fresh_module):
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.openalex import OpenAlexFetcher

    async def explode(self, query):
        raise RuntimeError("simulated meltdown")

    with patch.object(OpenAlexFetcher, "fetch", explode):
        # Must not raise — would poison batch processing.
        result = _run(fresh_module._fetch_openalex({"CanonicalLatin": "Boom, Boom"}))

    assert result["OpenAlex"]["hit"] is False
    assert "fetch_error:RuntimeError" in result["OpenAlex"]["reason"]


def test_non_success_status_returns_hit_false(monkeypatch, fresh_module):
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.zbmath import ZbMATHFetcher

    fake_miss = FetchResult(status=FetchStatus.NOT_FOUND, data=None)

    async def miss_fetch(self, query):
        return fake_miss

    with patch.object(ZbMATHFetcher, "fetch", miss_fetch):
        result = _run(fresh_module._fetch_zbmath({"CanonicalLatin": "Mythical, X"}))

    assert result["zbMATH_Open"]["hit"] is False
    assert "status:not_found" in result["zbMATH_Open"]["reason"]


def test_missing_fetcher_class_degrades_gracefully(fresh_module):
    """If the canonical Fetcher import fails for any reason (file
    deleted, class renamed, optional dep missing), the caller still
    gets a well-shaped negative result."""
    result = _run(
        fresh_module._call_canonical_fetcher(
            "src.authorities.does_not_exist_anywhere",
            "NonExistentFetcher",
            "PhantomSource",
            "any name",
        )
    )
    assert result["PhantomSource"]["hit"] is False
    assert "fetcher_unavailable" in result["PhantomSource"]["reason"]


# ── Empty-name guard runs before everything else ──────────────────


def test_empty_name_short_circuits(fresh_module):
    """Spec: a missing/blank CanonicalLatin returns the no-name
    sentinel without touching the cache, OFFLINE check, or fetcher."""
    for fn_name in (
        "_fetch_openalex",
        "_fetch_crossref",
        "_fetch_orcid_etd",
        "_fetch_crossref_thesis",
        "_fetch_zbmath",
        "_fetch_gnd",
        "_fetch_hal",
        "_fetch_oai_university",
    ):
        fn = getattr(fresh_module, fn_name)
        result = _run(fn({"CanonicalLatin": "  "}))
        # Shape: { "<Source>": { "hit": False, "reason": "no_name", ... } }
        # (or the back-compat {hit, match, works} shape for Crossref_Thesis)
        single = next(iter(result.values()))
        assert single["hit"] is False, f"{fn_name} should refuse empty name"


# ── Tier-1 sources go through the same machinery ─────────────────


def test_tier1_gnd_translates_correctly(monkeypatch, fresh_module):
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier1.gnd import GNDFetcher

    fake = FetchResult(
        status=FetchStatus.SUCCESS,
        data=AuthorityData(
            source="GND",
            source_id="123456789",
            canonical_name="Hilbert, David",
            identifiers={"GND": "123456789"},
        ),
    )

    async def fake_fetch(self, query):
        return fake

    with patch.object(GNDFetcher, "fetch", fake_fetch):
        result = _run(fresh_module._fetch_gnd({"CanonicalLatin": "Hilbert, David"}))

    assert result["GND"]["hit"] is True
    assert result["GND"]["source_id"] == "123456789"
    assert result["GND"]["identifiers"]["GND"] == "123456789"


# ── Crossref_Thesis legacy shape ────────────────────────────────


def test_crossref_thesis_success_includes_match_and_works(monkeypatch, fresh_module):
    """Success path must populate `match` and `works` for back-compat
    with downstream consumers and `test_authority_manager.TestCrossrefThesis`."""
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.crossref_thesis import CrossrefThesisFetcher

    async def hit_fetch(self, query):
        return FetchResult(
            status=FetchStatus.SUCCESS,
            data=AuthorityData(
                source="Crossref_Thesis",
                source_id="doi:10.0/thesis",
                canonical_name="Hilbert, David",
            ),
        )

    with patch.object(CrossrefThesisFetcher, "fetch", hit_fetch):
        result = _run(
            fresh_module._fetch_crossref_thesis({"CanonicalLatin": "Hilbert, David"})
        )

    inner = result["Crossref_Thesis"]
    assert inner["hit"] is True
    assert inner["match"] is True, "match must be True when hit is True"
    assert inner["works"] >= 1, "works must be ≥ 1 when hit is True"


def test_crossref_thesis_miss_keeps_legacy_shape(monkeypatch, fresh_module):
    """Miss path must still expose `match`/`works` keys."""
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.crossref_thesis import CrossrefThesisFetcher

    async def miss_fetch(self, query):
        return FetchResult(status=FetchStatus.NOT_FOUND, data=None)

    with patch.object(CrossrefThesisFetcher, "fetch", miss_fetch):
        result = _run(
            fresh_module._fetch_crossref_thesis({"CanonicalLatin": "Mythical, X"})
        )

    inner = result["Crossref_Thesis"]
    assert inner["hit"] is False
    assert inner["match"] is False
    assert inner["works"] == 0


# ── Pool semantics: instance reuse across calls ──────────────────


def test_fetcher_pool_reuses_instance_across_calls(monkeypatch, fresh_module):
    """A 100-entry batch must instantiate each Fetcher class exactly
    once. Without pooling, every entry pays a fresh aiohttp.ClientSession
    setup cost AND resets the per-instance rate-limit clock — so an
    upstream that asks for 10 RPS gets hit at full executor speed."""
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.openalex import OpenAlexFetcher

    init_count = {"n": 0}
    real_init = OpenAlexFetcher.__init__

    def counting_init(self, config):
        init_count["n"] += 1
        real_init(self, config)

    async def quick_fetch(self, query):
        return FetchResult(
            status=FetchStatus.SUCCESS,
            data=AuthorityData(source="OpenAlex", source_id=f"id-{query}"),
        )

    with patch.object(OpenAlexFetcher, "__init__", counting_init):
        with patch.object(OpenAlexFetcher, "fetch", quick_fetch):
            for i in range(20):
                _run(fresh_module._fetch_openalex({"CanonicalLatin": f"Person {i}"}))

    # 20 distinct queries → 20 cache misses → 20 fetcher calls. But
    # only ONE Fetcher instance should have been built.
    assert init_count["n"] == 1, (
        f"Expected exactly one Fetcher instantiation across 20 calls "
        f"(pooled), got {init_count['n']}"
    )


def test_fetcher_pool_close_clears_instances(monkeypatch, fresh_module):
    """After _close_fetcher_pool the next call must instantiate fresh."""
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.openalex import OpenAlexFetcher

    init_count = {"n": 0}
    real_init = OpenAlexFetcher.__init__

    def counting_init(self, config):
        init_count["n"] += 1
        real_init(self, config)

    async def quick_fetch(self, query):
        return FetchResult(
            status=FetchStatus.SUCCESS,
            data=AuthorityData(source="OpenAlex", source_id="x"),
        )

    with patch.object(OpenAlexFetcher, "__init__", counting_init):
        with patch.object(OpenAlexFetcher, "fetch", quick_fetch):
            _run(fresh_module._fetch_openalex({"CanonicalLatin": "Once, A"}))
            assert init_count["n"] == 1
            _run(fresh_module._close_fetcher_pool())
            # Different name to bypass the on-disk cache.
            _run(fresh_module._fetch_openalex({"CanonicalLatin": "Once, B"}))
            assert init_count["n"] == 2, "pool drained → next call must rebuild"


# ── End-to-end: a 4-entry batch with mixed outcomes ────────────────


def test_batch_with_mixed_outcomes_no_propagated_exceptions(monkeypatch, fresh_module):
    """Belt-and-braces: if one source explodes mid-batch, the others
    must still produce results."""
    _set_offline(monkeypatch, fresh_module, False)
    from src.authorities.tier0.crossref import CrossrefFetcher
    from src.authorities.tier0.openalex import OpenAlexFetcher

    async def crossref_fail(self, query):
        raise OSError("connection reset by peer")

    async def openalex_ok(self, query):
        return FetchResult(
            status=FetchStatus.SUCCESS,
            data=AuthorityData(source="OpenAlex", source_id="A1"),
        )

    with patch.object(CrossrefFetcher, "fetch", crossref_fail), patch.object(
        OpenAlexFetcher, "fetch", openalex_ok
    ):
        rc = _run(fresh_module._fetch_crossref({"CanonicalLatin": "X"}))
        ro = _run(fresh_module._fetch_openalex({"CanonicalLatin": "X"}))

    assert rc["Crossref"]["hit"] is False
    assert "fetch_error" in rc["Crossref"]["reason"]
    assert ro["OpenAlex"]["hit"] is True
