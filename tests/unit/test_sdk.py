"""Unit tests for src/sdk/ — the Python client library.

End-to-end tests spin up the real FastAPI app via TestClient and
exercise both Client and AsyncClient against it. Hashcash minting
is exercised both alone (verifies the PoW math) and through
request flow (verifies the SDK installs the header).
"""

from __future__ import annotations

import hashlib

import pytest

from src.sdk import (
    AsyncClient,
    Client,
    GmnapAPIError,
    GmnapClientError,
    mint_hashcash,
)

# ─── Hashcash minting (pure function, no server) ──────────────────────


def test_mint_hashcash_produces_valid_stamp_18_bits() -> None:
    # This test verifies CORRECTNESS (a valid 18-bit stamp is produced),
    # not speed — the 8-bit test below covers fast minting. An 18-bit
    # proof-of-work nominally finishes in well under a second, but it has
    # a fat geometric tail, so a tight 10 s budget spuriously timed out
    # ~2 % of the time on slow/contended CI runners. A generous ceiling
    # makes that ~1e-10 while the test still returns the instant a stamp
    # is found.
    stamp = mint_hashcash(bits=18, timeout_s=60.0)
    parts = stamp.split(":")
    assert len(parts) == 7  # 1:bits:date:resource::rand:counter
    assert parts[0] == "1"
    assert parts[1] == "18"
    assert parts[3] == "gmnap-api"
    digest = hashlib.sha256(stamp.encode("utf-8")).hexdigest()
    bits = bin(int(digest, 16))[2:].zfill(256)
    assert bits[:18] == "0" * 18


def test_mint_hashcash_low_bits_is_fast() -> None:
    stamp = mint_hashcash(bits=8, timeout_s=2.0)
    digest = hashlib.sha256(stamp.encode("utf-8")).hexdigest()
    bits = bin(int(digest, 16))[2:].zfill(256)
    assert bits[:8] == "0" * 8


def test_mint_hashcash_returns_unique_stamps() -> None:
    a = mint_hashcash(bits=8, timeout_s=2.0)
    b = mint_hashcash(bits=8, timeout_s=2.0)
    # Random nonce makes collisions effectively impossible
    assert a != b


# ─── Client end-to-end (TestClient against the live FastAPI app) ──────


@pytest.fixture(scope="module")
def base_url() -> str:
    """Spin up the API on a free port for the test module.

    The SDK doesn't know about FastAPI's TestClient — it expects a
    real URL — so we use a thread-local uvicorn for the duration of
    the module. The browser-smoke harness uses the same pattern.
    """
    import os
    import socket
    import threading
    import time

    import uvicorn

    # Disable hashcash for tests (we exercise the minting separately
    # above; the request-flow tests just verify the SDK sets the
    # header even when not strictly needed by the server).
    os.environ["GMNAP_REQUIRE_HASHCASH"] = "0"

    import src.api.server as server_mod

    app = server_mod.create_app()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    srv = uvicorn.Server(config)

    t = threading.Thread(target=srv.run, daemon=True)
    t.start()

    # Wait for the server to bind + accept.
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)
    else:
        raise RuntimeError("uvicorn never came up")

    url = f"http://127.0.0.1:{port}"
    yield url

    srv.should_exit = True
    t.join(timeout=5.0)


def test_client_health(base_url: str) -> None:
    with Client(base_url, hashcash_bits=None) as c:
        h = c.health()
        assert h["status"] == "ok"


def test_client_ready(base_url: str) -> None:
    with Client(base_url, hashcash_bits=None) as c:
        # /readyz checks genealogy_enrichment.json — exists in repo
        r = c.ready()
        assert r["status"] == "ready"


def test_client_query_known_name(base_url: str) -> None:
    with Client(base_url, hashcash_bits=None) as c:
        result = c.query("Hilbert, David")
        assert result["region_code"] == "A2"
        # Genealogy enrichment from curated JSON
        assert result["BirthYear"] == 1862
        assert "Königsberg" in (result.get("Institution") or "")


def test_client_query_empty_name_returns_400(base_url: str) -> None:
    with Client(base_url, hashcash_bits=None) as c:
        with pytest.raises(GmnapClientError) as exc:
            c.query("")
        assert exc.value.status_code == 400


def test_client_query_too_long_returns_400(base_url: str) -> None:
    with Client(base_url, hashcash_bits=None) as c:
        with pytest.raises(GmnapClientError) as exc:
            c.query("a" * 600)
        assert exc.value.status_code == 400


def test_client_process_batch(base_url: str) -> None:
    with Client(base_url, hashcash_bits=None) as c:
        result = c.process(
            [
                {"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]},
                {"CanonicalLatin": "Ramanujan, Srinivasa", "CountryCodes": ["IN"]},
            ],
            mode="quick",
        )
        assert "entries" in result
        assert len(result["entries"]) == 2


def test_client_lineage_by_name(base_url: str) -> None:
    """Lineage walks the advisor chain for a known mathematician."""
    with Client(base_url, hashcash_bits=None) as c:
        # name: prefix lets us look up by canonical instead of GlobalID
        result = c.lineage("name:Hilbert, David", depth=2)
        assert "edges" in result or "error" in result


def test_client_lineage_dot_returns_graphviz_text(base_url: str) -> None:
    """fmt='dot' returns the Graphviz source as a *string*.

    Regression: the SDK used to call ``r.json()`` unconditionally, so
    a ``dot`` response (``text/vnd.graphviz``) raised JSONDecodeError.
    The raw path now returns the body verbatim.
    """
    with Client(base_url, hashcash_bits=None) as c:
        try:
            out = c.lineage("name:Hilbert, David", depth=2, fmt="dot")
        except GmnapClientError as exc:
            # 404 when no edges resolve in this environment — the
            # raw-text invariant only applies to a 200. The point is
            # that we did NOT get a JSONDecodeError.
            assert exc.status_code == 404
            return
        assert isinstance(out, str)
        assert "digraph" in out


def test_client_lineage_svg_rejected_client_side() -> None:
    """fmt='svg' is rejected before any network call.

    The server does not render SVG; advertising it was a lie. The SDK
    now fails fast with a clear client error instead of silently
    returning JSON (the server's old fall-through behaviour).
    """
    c = Client("http://example.invalid", hashcash_bits=None)
    try:
        with pytest.raises(GmnapClientError) as exc:
            c.lineage("name:Hilbert, David", fmt="svg")
        assert "svg" in str(exc.value).lower()
    finally:
        c.close()


def test_client_process_pagination(base_url: str) -> None:
    """process() now exposes limit/offset and pages correctly.

    Regression: the SDK never sent limit/offset, so the server's
    default limit=100 silently truncated any batch's returned page and
    callers had no way to see entries 101+.
    """
    entries = [
        {"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]},
        {"CanonicalLatin": "Gauss, Carl", "CountryCodes": ["DE"]},
        {"CanonicalLatin": "Riemann, Bernhard", "CountryCodes": ["DE"]},
    ]
    with Client(base_url, hashcash_bits=None) as c:
        page0 = c.process(entries, limit=2, offset=0)
        assert page0["processed"] == 3
        assert len(page0["entries"]) == 2
        assert page0["has_more"] is True
        assert page0["offset"] == 0 and page0["limit"] == 2

        page1 = c.process(entries, limit=2, offset=2)
        assert len(page1["entries"]) == 1
        assert page1["has_more"] is False


# ─── Async client end-to-end ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_async_client_health(base_url: str) -> None:
    async with AsyncClient(base_url, hashcash_bits=None) as c:
        h = await c.health()
        assert h["status"] == "ok"


@pytest.mark.asyncio
async def test_async_client_query(base_url: str) -> None:
    async with AsyncClient(base_url, hashcash_bits=None) as c:
        result = await c.query("Hilbert, David")
        assert result["region_code"] == "A2"


@pytest.mark.asyncio
async def test_async_client_process_batch(base_url: str) -> None:
    async with AsyncClient(base_url, hashcash_bits=None) as c:
        result = await c.process(
            [{"CanonicalLatin": "Euler, Leonhard", "CountryCodes": ["CH"]}]
        )
        assert "entries" in result


@pytest.mark.asyncio
async def test_async_client_lineage_svg_rejected() -> None:
    """Async client mirrors the sync svg-rejection guard."""
    c = AsyncClient("http://example.invalid", hashcash_bits=None)
    try:
        with pytest.raises(GmnapClientError):
            await c.lineage("name:Hilbert, David", fmt="svg")
    finally:
        await c.close()


# ─── Error handling ───────────────────────────────────────────────────


def test_unreachable_host_raises_after_retries() -> None:
    """A genuinely-unreachable server should raise after exhausting retries."""
    # Reserved-for-documentation port (RFC 6890) — connection refused fast.
    c = Client(
        "http://127.0.0.1:1",
        hashcash_bits=None,
        timeout=1.0,
    )
    with pytest.raises(GmnapAPIError):
        c.query("Hilbert, David")
    c.close()


def test_client_token_skips_hashcash() -> None:
    """Token path disables hashcash even if bits is set."""
    c = Client("http://example.invalid", token="some-token", hashcash_bits=18)
    # Verified by attribute; we don't actually hit the network here.
    assert c.token == "some-token"
    assert c.hashcash_bits is None
    c.close()
