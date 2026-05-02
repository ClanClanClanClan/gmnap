"""Live ORCID-ETD regression test (opt-in, OFFLINE=0 only).

Round 14 fixed three cascading bugs in the ORCID-ETD code path
(name → ORCID resolution via OpenAlex; ``AuthorityData`` field
names ``source_id`` / ``confidence_score`` / ``canonical_name``;
``FetchResult`` wrapping in ``ORCIDETDFetcher.fetch``). The fix is
currently only validated by mocked unit tests in
``tests/unit/test_canonical_fetcher_delegation.py`` — and mocks
won't catch real-API shape drift (the bug class round 14
fixed was *exactly* code-vs-API shape mismatch).

This file adds a live test that hits the real ORCID API. It is
gated three ways so it only fires when explicitly requested:

  1. ``@pytest.mark.live`` — pytest's `-m "not live"` skips it
  2. ``OFFLINE=1`` skip — the project default
  3. CI does not include this file in any test job's enumerated list

To run:

    OFFLINE=0 pytest tests/integration/test_orcid_etd_live.py -v

Uses Terence Tao's ORCID (``0000-0002-0140-7641``) as the known-
good reference — registered, public, well-populated. If ORCID
removes his profile or changes its API contract, this test fails
loudly, which is correct: that's the same shape of regression
round 14 caught.
"""

from __future__ import annotations

import asyncio
import os

import pytest

pytestmark = pytest.mark.live


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.mark.skipif(
    os.getenv("OFFLINE", "1") == "1",
    reason="needs OFFLINE=0 (live network access)",
)
def test_orcid_etd_resolves_known_living_mathematician():
    """Tao's ORCID 0000-0002-0140-7641 must resolve via the
    name → OpenAlex → ORCID-ETD chain end-to-end."""
    from src.authority.manager_tier01 import _fetch_orcid_etd

    entry = {"CanonicalLatin": "Tao, Terence"}
    result = _run(_fetch_orcid_etd(entry))
    inner = result.get("ORCID_ETD") or {}

    # Round-14 chain regressions break at exactly these assertions:
    #   - hit=False with reason='no_orcid_for_name' → OpenAlex
    #     stopped resolving the ORCID (either name normalization
    #     regressed or OpenAlex API drifted)
    #   - hit=False with reason starting 'fetch_error:' → ORCIDETDFetcher
    #     raised; field-name mismatch (round-14 bug #2) or
    #     FetchResult-wrapping regression (round-14 bug #3)
    #   - hit=False with reason='status:unknown' → fetch returned a
    #     bare record instead of FetchResult
    assert (
        inner.get("hit") is True
    ), f"ORCID-ETD chain broken; reason={inner.get('reason')!r}"

    # The fetcher returns the canonical name from ORCID's person
    # endpoint. "Terence Tao" is what ORCID has on file.
    assert "Tao" in (
        inner.get("canonical_name") or ""
    ), f"unexpected canonical_name: {inner.get('canonical_name')!r}"

    # source_id should be the ORCID itself (round-14 bug #2 fix —
    # before, this propagated as None because the dataclass field
    # was named `identifier` instead of `source_id`).
    assert (
        inner.get("source_id") == "0000-0002-0140-7641"
    ), f"source_id propagation regressed: {inner.get('source_id')!r}"


@pytest.mark.skipif(
    os.getenv("OFFLINE", "1") == "1",
    reason="needs OFFLINE=0 (live network access)",
)
def test_orcid_etd_returns_no_orcid_for_historical_mathematician():
    """Euler died in 1783; he has no ORCID profile. The chain must
    return ``hit=False, reason='no_orcid_for_name'`` rather than
    crashing or silently returning an unrelated person.

    This validates the explicit no-ORCID branch in
    ``_fetch_orcid_etd``, which was added in round 14 specifically
    so historical mathematicians don't trigger 'Invalid ORCID
    format' log noise.
    """
    from src.authority.manager_tier01 import _fetch_orcid_etd

    entry = {"CanonicalLatin": "Euler, Leonhard"}
    result = _run(_fetch_orcid_etd(entry))
    inner = result.get("ORCID_ETD") or {}
    assert inner.get("hit") is False
    assert (
        inner.get("reason") == "no_orcid_for_name"
    ), f"expected no_orcid_for_name, got reason={inner.get('reason')!r}"
