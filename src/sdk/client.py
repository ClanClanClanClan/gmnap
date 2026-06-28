"""GMNAP/MathLineage Python client.

Sync + async API over httpx. Auto-mints V7 spec §12 hashcash stamps
for the free tier; auto-retries network errors and 5xx with exponential
backoff. See module docstring in __init__.py for usage examples.
"""

from __future__ import annotations

import asyncio
import hashlib
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import httpx

HASHCASH_BITS_DEFAULT = 18

# Retry policy
_RETRY_BACKOFFS_S = (0.5, 1.0, 2.0)  # 3 attempts after the initial
_RATE_LIMIT_BACKOFF_S = 60.0


# ─── Errors ──────────────────────────────────────────────────────────


class GmnapAPIError(Exception):
    """Base exception for all SDK errors."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GmnapClientError(GmnapAPIError):
    """4xx error — caller's fault. Don't retry."""


class GmnapServerError(GmnapAPIError):
    """5xx error — server's fault. Retried internally by the SDK."""


# ─── Hashcash ─────────────────────────────────────────────────────────


def mint_hashcash(
    resource: str = "gmnap-api",
    bits: int = HASHCASH_BITS_DEFAULT,
    timeout_s: float = 30.0,
) -> str:
    """Compute a hashcash stamp meeting the V7 spec §12 PoW gate.

    Format: ``1:<bits>:<YYMMDD>:<resource>::<rand>:<counter>``

    Returns the first stamp whose SHA-256 hex starts with ``bits``
    leading zero bits. 18 bits ≈ 250 ms on a modern laptop core; the
    timeout caps malicious-CPU-budget abuse.
    """
    today = datetime.now(timezone.utc).strftime("%y%m%d")
    rand = secrets.token_hex(6)
    prefix = f"1:{bits}:{today}:{resource}::{rand}:"

    deadline = time.time() + timeout_s
    counter = 0
    while time.time() < deadline:
        stamp = prefix + str(counter)
        digest = hashlib.sha256(stamp.encode("utf-8")).hexdigest()
        as_bits = bin(int(digest, 16))[2:].zfill(256)
        if as_bits[:bits] == "0" * bits:
            return stamp
        counter += 1
    raise GmnapAPIError(f"Failed to mint {bits}-bit hashcash within {timeout_s}s")


# ─── Shared request helpers ───────────────────────────────────────────


def _build_headers(
    token: Optional[str],
    hashcash_bits: Optional[int],
) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "User-Agent": "gmnap-python-sdk/0.1.0",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    elif hashcash_bits is not None:
        headers["X-Hashcash"] = mint_hashcash(bits=hashcash_bits)
    return headers


def _raise_for_status(response: httpx.Response) -> None:
    """Translate HTTP status → SDK exception class.

    4xx (except 429) → ``GmnapClientError``. 5xx → ``GmnapServerError``
    (the caller retries internally). 2xx returns silently.
    """
    if response.status_code < 400:
        return
    try:
        detail = response.json().get("detail", response.text[:200])
    except Exception:
        detail = response.text[:200]
    cls = GmnapServerError if response.status_code >= 500 else GmnapClientError
    raise cls(f"{response.status_code} {detail}", status_code=response.status_code)


# ─── Sync client ──────────────────────────────────────────────────────


class Client:
    """Synchronous client for the GMNAP HTTP API."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        hashcash_bits: Optional[int] = HASHCASH_BITS_DEFAULT,
        timeout: float = 30.0,
    ) -> None:
        """``base_url`` example: ``http://localhost:8080``. Trailing
        slash is normalized away.

        Pass ``token=`` for the paid-tier Bearer-token path (bypasses
        hashcash). Pass ``hashcash_bits=None`` to skip stamp minting
        entirely (use against local-dev servers running with
        ``GMNAP_REQUIRE_HASHCASH=0`` or ``--no-hashcash``).
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.hashcash_bits = hashcash_bits if not token else None
        self._http = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        raw: bool = False,
    ) -> Any:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt, backoff in enumerate((0.0,) + _RETRY_BACKOFFS_S):
            if backoff:
                time.sleep(backoff)
            # Fresh hashcash per attempt — server prevents replay.
            headers = _build_headers(self.token, self.hashcash_bits)
            try:
                r = self._http.request(
                    method, url, params=params, json=json, headers=headers
                )
            except httpx.RequestError as exc:
                last_exc = exc
                continue
            if r.status_code == 429:
                # Rate limited — back off once at the rate-limit budget
                # then retry. If we're already on the last retry, bail.
                if attempt == len(_RETRY_BACKOFFS_S):
                    _raise_for_status(r)
                time.sleep(_RATE_LIMIT_BACKOFF_S)
                continue
            if 500 <= r.status_code < 600:
                last_exc = GmnapServerError(
                    f"{r.status_code} {r.text[:200]}", r.status_code
                )
                continue
            _raise_for_status(r)
            # ``raw`` returns the body text verbatim — used for non-JSON
            # responses (e.g. Graphviz ``dot`` source), where ``r.json()``
            # would raise JSONDecodeError on the ``text/vnd.graphviz`` body.
            return r.text if raw else r.json()
        # Exhausted retries
        if isinstance(last_exc, GmnapAPIError):
            raise last_exc
        raise GmnapAPIError(f"Request failed after retries: {last_exc}")

    # ── Public API ────────────────────────────────────────────────

    def query(self, name: str, mode: str = "quick") -> Dict[str, Any]:
        """Look up a single mathematician by canonical name.

        Returns a dict including ``region_code``, ``confidence``,
        ``detection_method``, ``BirthYear``, ``DeathYear``,
        ``Institution``, ``Country``, ``Advisors`` (when curated
        genealogy data exists for the entry).
        """
        return self._request(
            "GET", "/api/v1/query", params={"name": name, "mode": mode}
        )

    def lineage(
        self,
        global_id: str,
        depth: int = 3,
        direction: str = "ancestors",
        fmt: str = "json",
    ) -> Union[Dict[str, Any], str]:
        """Academic genealogy edges from a GlobalID or ``name:<canonical>``.

        ``direction`` is ``"ancestors"`` (default) for the advisor
        chain or ``"descendants"`` for the student chain.

        ``fmt`` is ``"json"`` (default) → returns a ``dict``, or
        ``"dot"`` → returns the Graphviz source as a ``str``. (SVG is
        not currently served; render the ``dot`` output yourself with
        ``dot -Tsvg``.)
        """
        if fmt not in ("json", "dot"):
            raise GmnapClientError(
                f"fmt must be 'json' or 'dot', got {fmt!r} "
                "(SVG is not served by the API)"
            )
        return self._request(
            "GET",
            f"/api/v1/lineage/{global_id}",
            params={"depth": depth, "direction": direction, "format": fmt},
            raw=(fmt != "json"),
        )

    def process(
        self,
        entries: List[Dict[str, Any]],
        mode: str = "quick",
        schema_strict: int = 0,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Batch-process a list of entries through the V7 pipeline.

        Each entry needs at minimum a ``CanonicalLatin`` (or
        equivalent name field).

        The server **paginates** the response: only ``entries[offset:
        offset+limit]`` come back per call (``limit`` defaults to 100,
        max 10 000). Page through a large batch by advancing ``offset``
        until ``has_more`` is ``False``. Returns ``{"processed": N,
        "entries": [...page...], "offset": O, "limit": L, "has_more":
        bool, "quality_gates": {...}, "metrics": {...}}``.
        """
        return self._request(
            "POST",
            "/api/v1/process",
            json={
                "entries": entries,
                "mode": mode,
                "schema_strict": schema_strict,
                "limit": limit,
                "offset": offset,
            },
        )

    def suggest(
        self,
        original_name: str,
        correction_type: str,
        suggested_value: str,
        source_url: str = "",
        submitter_note: str = "",
    ) -> Dict[str, Any]:
        """File a correction suggestion against a known entry.

        ``correction_type`` ∈ {"advisor", "institution", "year",
        "name", "country", "other"}. Returns ``{"status": "received",
        "id": "<filename>"}`` on success — the suggestion is queued to
        disk for human review under the returned id.
        """
        return self._request(
            "POST",
            "/api/v1/suggest",
            json={
                "original_name": original_name,
                "correction_type": correction_type,
                "suggested_value": suggested_value,
                "source_url": source_url,
                "submitter_note": submitter_note,
            },
        )

    def health(self) -> Dict[str, Any]:
        """Liveness probe — fast, no hashcash needed (no /api/ prefix)."""
        r = self._http.get(f"{self.base_url}/healthz")
        _raise_for_status(r)
        return r.json()

    def ready(self) -> Dict[str, Any]:
        """Readiness probe — checks genealogy data + Memgraph if configured."""
        r = self._http.get(f"{self.base_url}/readyz")
        _raise_for_status(r)
        return r.json()


# ─── Async client ─────────────────────────────────────────────────────


class AsyncClient:
    """Async client for the GMNAP HTTP API. Same surface as ``Client``."""

    def __init__(
        self,
        base_url: str,
        token: Optional[str] = None,
        hashcash_bits: Optional[int] = HASHCASH_BITS_DEFAULT,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.hashcash_bits = hashcash_bits if not token else None
        self._http = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        raw: bool = False,
    ) -> Any:
        url = f"{self.base_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt, backoff in enumerate((0.0,) + _RETRY_BACKOFFS_S):
            if backoff:
                await asyncio.sleep(backoff)
            headers = _build_headers(self.token, self.hashcash_bits)
            try:
                r = await self._http.request(
                    method, url, params=params, json=json, headers=headers
                )
            except httpx.RequestError as exc:
                last_exc = exc
                continue
            if r.status_code == 429:
                if attempt == len(_RETRY_BACKOFFS_S):
                    _raise_for_status(r)
                await asyncio.sleep(_RATE_LIMIT_BACKOFF_S)
                continue
            if 500 <= r.status_code < 600:
                last_exc = GmnapServerError(
                    f"{r.status_code} {r.text[:200]}", r.status_code
                )
                continue
            _raise_for_status(r)
            # ``raw`` returns body text verbatim (e.g. Graphviz ``dot``).
            return r.text if raw else r.json()
        if isinstance(last_exc, GmnapAPIError):
            raise last_exc
        raise GmnapAPIError(f"Request failed after retries: {last_exc}")

    async def query(self, name: str, mode: str = "quick") -> Dict[str, Any]:
        return await self._request(
            "GET", "/api/v1/query", params={"name": name, "mode": mode}
        )

    async def lineage(
        self,
        global_id: str,
        depth: int = 3,
        direction: str = "ancestors",
        fmt: str = "json",
    ) -> Union[Dict[str, Any], str]:
        if fmt not in ("json", "dot"):
            raise GmnapClientError(
                f"fmt must be 'json' or 'dot', got {fmt!r} "
                "(SVG is not served by the API)"
            )
        return await self._request(
            "GET",
            f"/api/v1/lineage/{global_id}",
            params={"depth": depth, "direction": direction, "format": fmt},
            raw=(fmt != "json"),
        )

    async def process(
        self,
        entries: List[Dict[str, Any]],
        mode: str = "quick",
        schema_strict: int = 0,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/process",
            json={
                "entries": entries,
                "mode": mode,
                "schema_strict": schema_strict,
                "limit": limit,
                "offset": offset,
            },
        )

    async def suggest(
        self,
        original_name: str,
        correction_type: str,
        suggested_value: str,
        source_url: str = "",
        submitter_note: str = "",
    ) -> Dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/suggest",
            json={
                "original_name": original_name,
                "correction_type": correction_type,
                "suggested_value": suggested_value,
                "source_url": source_url,
                "submitter_note": submitter_note,
            },
        )

    async def health(self) -> Dict[str, Any]:
        r = await self._http.get(f"{self.base_url}/healthz")
        _raise_for_status(r)
        return r.json()

    async def ready(self) -> Dict[str, Any]:
        r = await self._http.get(f"{self.base_url}/readyz")
        _raise_for_status(r)
        return r.json()


__all__: List[Union[str]] = [
    "AsyncClient",
    "Client",
    "GmnapAPIError",
    "GmnapClientError",
    "GmnapServerError",
    "mint_hashcash",
]
