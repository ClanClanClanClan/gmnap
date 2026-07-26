"""R66 pins — every canonical fetcher must honour the FetchResult contract.

WHY THIS EXISTS. Three fetchers (GND, OAI_University, Crossref_Thesis) were
documented "✅ WORKING" while being structurally incapable of returning data.
The pre-existing guard, tests/unit/test_canonical_fetcher_delegation.py,
monkeypatches each fetcher's ``fetch()`` to RETURN a FetchResult — so it
exercises the orchestrator's translation layer and can never observe that the
fetcher itself is broken. That is exactly how three dead sources passed CI.

These tests call the REAL ``fetch()`` with the network stubbed, so a fetcher
that fails before the socket (missing template config, wrong return type)
fails here. This is the same bug class as R40.1 — it has now recurred twice,
which is why the guard is contract-level rather than per-source.
"""

import asyncio
from typing import Any

import pytest

from src.authorities.base import FetchResult, FetchStatus


class _FakeResponse:
    def __init__(self, payload: Any, status: int = 200):
        self._payload = payload
        self.status = status

    async def json(self):
        return self._payload

    async def text(self):
        return ""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    """Returns a canned payload for any GET — no network."""

    def __init__(self, payload: Any, status: int = 200):
        self._payload = payload
        self._status = status

    def get(self, *a, **kw):
        return _FakeResponse(self._payload, self._status)

    async def close(self):
        return None


GND_HILBERT = {
    "totalItems": 1,
    "member": [
        {
            "gndIdentifier": "11855090X",
            "preferredName": "Hilbert, David",
            "dateOfBirth": ["1862-01-23"],
            "dateOfDeath": ["1943-02-14"],
            "placeOfBirth": [{"label": "Wehlau"}],
            "placeOfDeath": [{"label": "Göttingen"}],
            "academicDegree": ["Prof. Dr."],
            "variantName": ["Hilbert, D.", "Gil'bert, David"],
            "sameAs": [{"collection": {"abbr": "VIAF"}, "id": "http://viaf.org/1"}],
        }
    ],
}


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ── the contract ────────────────────────────────────────────────────────


def test_gnd_returns_a_real_fetchresult_with_parsed_fields():
    """GND used to return PARSE_ERROR 'Unsupported authority' before opening a
    socket, because it delegated to a template registry that lacks it."""
    from src.authorities.tier1.gnd import GNDFetcher

    f = GNDFetcher({})
    f.get_session = lambda: _as_coro(_FakeSession(GND_HILBERT))  # type: ignore
    res = _run(f.fetch("Hilbert, David"))

    assert isinstance(res, FetchResult), "must return a FetchResult, not a bare record"
    assert res.status == FetchStatus.SUCCESS
    assert res.data is not None
    assert res.data.birth_year == 1862  # the field that makes GND worth having
    assert res.data.death_year == 1943
    assert res.data.identifiers.get("GND") == "11855090X"
    assert "Hilbert, D." in res.data.name_variants
    assert res.data.metadata.get("place_of_birth") == ["Wehlau"]


def test_gnd_handles_partial_dates_without_raising():
    """GND emits '1862', '1862-01' and ranges — a bare int(v[:4]) breaks."""
    from src.authorities.tier1.gnd import GNDFetcher

    payload = {
        "totalItems": 1,
        "member": [
            {"gndIdentifier": "X", "preferredName": "N", "dateOfBirth": ["1862"]}
        ],
    }
    f = GNDFetcher({})
    f.get_session = lambda: _as_coro(_FakeSession(payload))  # type: ignore
    res = _run(f.fetch("N"))
    assert res.status == FetchStatus.SUCCESS and res.data.birth_year == 1862


def test_gnd_empty_result_is_not_found_not_an_exception():
    from src.authorities.tier1.gnd import GNDFetcher

    f = GNDFetcher({})
    f.get_session = lambda: _as_coro(_FakeSession({"totalItems": 0, "member": []}))  # type: ignore
    assert _run(f.fetch("Nobody")).status == FetchStatus.NOT_FOUND


def test_oai_university_is_honestly_dead_not_accidentally_dead():
    """No endpoint registry exists, so it cannot return data. It must say so
    explicitly rather than burning retry cycles on a template dispatch error."""
    from src.authorities.tier1.oai_university import OAIUniversityFetcher

    res = _run(OAIUniversityFetcher({}).fetch("Hilbert, David"))
    assert isinstance(res, FetchResult)
    assert res.status == FetchStatus.NOT_FOUND
    assert "not implemented" in (res.error_message or "").lower()


@pytest.mark.parametrize(
    "module_path,cls_name",
    [
        ("src.authorities.tier1.gnd", "GNDFetcher"),
        ("src.authorities.tier1.oai_university", "OAIUniversityFetcher"),
        ("src.authorities.tier1.hal", "HALFetcher"),
    ],
)
def test_fetcher_never_returns_a_bare_record(module_path, cls_name):
    """THE CONTRACT: fetch() returns a FetchResult. The orchestrator reads
    ``getattr(result, "status", None)``, so a bare record silently degrades to
    status:unknown => hit:False forever — which is precisely how
    Crossref_Thesis stayed dead after its data-parsing was already correct."""
    import importlib

    mod = importlib.import_module(module_path)
    f = getattr(mod, cls_name)({})
    f.get_session = lambda: _as_coro(_FakeSession({"totalItems": 0, "member": []}))  # type: ignore
    res = _run(f.fetch("Someone, Test"))
    assert isinstance(res, FetchResult), f"{cls_name}.fetch() must return FetchResult"
    assert hasattr(res.status, "value"), "status must be a FetchStatus enum"


async def _as_coro(value):
    return value
