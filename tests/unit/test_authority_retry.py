"""Tests for retry_with_backoff in src/authority/common."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from unittest.mock import AsyncMock, patch

from src.authority.common import retry_with_backoff


@pytest.mark.asyncio
async def test_retry_on_timeout(monkeypatch):
    """Callable that raises TimeoutException twice then succeeds returns the result."""
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise httpx.TimeoutException("timeout")
        return {"ok": True}

    result = await retry_with_backoff(flaky, max_retries=2, base_delay=0.01)
    assert result == {"ok": True}
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_on_connect_error(monkeypatch):
    """Callable that raises ConnectError once then succeeds."""
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

    call_count = 0

    async def flaky():
        nonlocal call_count
        call_count += 1
        if call_count <= 1:
            raise httpx.ConnectError("connection refused")
        return "connected"

    result = await retry_with_backoff(flaky, max_retries=2, base_delay=0.01)
    assert result == "connected"
    assert call_count == 2


@pytest.mark.asyncio
async def test_no_retry_on_value_error(monkeypatch):
    """Non-transient errors raise immediately without retry."""
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

    call_count = 0

    async def bad():
        nonlocal call_count
        call_count += 1
        raise ValueError("bad input")

    with pytest.raises(ValueError, match="bad input"):
        await retry_with_backoff(bad, max_retries=3, base_delay=0.01)

    assert call_count == 1, "Should not have retried on ValueError"


@pytest.mark.asyncio
async def test_max_retries_exceeded(monkeypatch):
    """Always-failing callable raises after max_retries+1 attempts."""
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

    call_count = 0

    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise httpx.TimeoutException("timeout")

    with pytest.raises(httpx.TimeoutException):
        await retry_with_backoff(always_fails, max_retries=2, base_delay=0.01)

    assert call_count == 3  # initial + 2 retries


@pytest.mark.asyncio
async def test_exponential_backoff_timing(monkeypatch):
    """Verify that sleep delays double: base_delay, then base_delay*2."""
    monkeypatch.setenv("OFFLINE", "1")
    monkeypatch.setenv("GMNAP_NO_NETWORK", "1")

    call_count = 0
    sleep_calls: list[float] = []

    async def fails_twice():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise httpx.TimeoutException("timeout")
        return "done"

    original_sleep = asyncio.sleep

    async def mock_sleep(delay):
        sleep_calls.append(delay)
        # Don't actually sleep to keep tests fast
        return

    with patch("src.authority.common.asyncio.sleep", side_effect=mock_sleep):
        result = await retry_with_backoff(fails_twice, max_retries=2, base_delay=1.0)

    assert result == "done"
    assert len(sleep_calls) == 2
    # base_delay * (2 ** attempt): attempt 0 => 1.0, attempt 1 => 2.0
    assert sleep_calls[0] == pytest.approx(1.0)
    assert sleep_calls[1] == pytest.approx(2.0)
