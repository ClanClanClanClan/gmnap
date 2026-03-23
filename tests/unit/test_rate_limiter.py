"""Tests for _Limiter in src/authority/common."""
from __future__ import annotations

import asyncio
import time

import pytest

from src.authority.common import _Limiter


@pytest.mark.asyncio
async def test_limiter_acquires_successfully(monkeypatch):
    """A limiter with generous limits acquires without error."""
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

    limiter = _Limiter(rps=10, burst=5)
    # Should complete without raising
    await limiter.acquire()


@pytest.mark.asyncio
async def test_limiter_delays_between_calls(monkeypatch):
    """With rps=2, each acquire sleeps 0.5s, so 2 calls take >= 0.4s total."""
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

    limiter = _Limiter(rps=2, burst=1)
    start = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = time.monotonic() - start
    # Each acquire sleeps 1/rps = 0.5s, two calls => ~1.0s
    # Use a generous lower bound to avoid flaky CI
    assert elapsed >= 0.4, f"Expected >= 0.4s, got {elapsed:.3f}s"


@pytest.mark.asyncio
async def test_limiter_burst_concurrent(monkeypatch):
    """With burst=3, 3 concurrent acquires all complete within a reasonable time."""
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

    limiter = _Limiter(rps=1, burst=3)
    start = time.monotonic()
    # Launch 3 concurrent acquires -- burst=3 means all 3 can enter the semaphore
    results = await asyncio.gather(
        limiter.acquire(),
        limiter.acquire(),
        limiter.acquire(),
    )
    elapsed = time.monotonic() - start
    # With burst=3 and rps=1, all 3 enter concurrently, each sleeps 1.0s
    # They run in parallel so total should be ~1.0s, well under 2.0s
    assert elapsed < 2.0, f"Expected < 2.0s, got {elapsed:.3f}s"
    assert len(results) == 3
