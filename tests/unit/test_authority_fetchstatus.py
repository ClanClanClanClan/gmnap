"""Authority fetchers must reference real FetchStatus members and build
valid FetchResults (R39).

The live tier-1 HAL fetcher used FetchStatus.ERROR (no such member) and
passed source=/query=/error= kwargs that FetchResult doesn't accept — so
at OFFLINE=0 every HAL fetch raised AttributeError (in the except block
itself) or TypeError. This guards against that whole class.
"""

import pathlib
import re

import pytest

from src.authorities.base import FetchResult, FetchStatus


def test_all_fetchstatus_references_are_valid_members():
    """Every FetchStatus.X referenced under src/authorities/ must exist —
    a missing one makes a fetcher's error handler itself raise
    AttributeError on every failure."""
    valid = set(FetchStatus.__members__)
    bad = []
    for p in pathlib.Path("src/authorities").rglob("*.py"):
        for m in set(re.findall(r"FetchStatus\.([A-Z_]+)", p.read_text())):
            if m not in valid:
                bad.append(f"{p}:{m}")
    assert not bad, f"non-existent FetchStatus members referenced: {sorted(bad)}"


def test_fetchstatus_has_generic_error_member():
    assert hasattr(FetchStatus, "ERROR")


@pytest.mark.asyncio
async def test_hal_fetch_error_path_returns_result():
    """HAL's except block must return a FetchResult, not raise."""
    from src.authorities.tier1.hal import HALFetcher

    f = HALFetcher()

    async def _boom(*a, **k):
        raise RuntimeError("network down")

    f._search_author = _boom
    res = await f.fetch("Euler, Leonhard")
    assert res.status == FetchStatus.ERROR
    assert "network down" in (res.error_message or "")
    assert isinstance(res, FetchResult)


@pytest.mark.asyncio
async def test_hal_fetch_not_found_path_returns_result():
    from src.authorities.tier1.hal import HALFetcher

    f = HALFetcher()

    async def _empty(*a, **k):
        return []

    f._search_author = _empty
    res = await f.fetch("Nobody Here")
    assert res.status == FetchStatus.NOT_FOUND
