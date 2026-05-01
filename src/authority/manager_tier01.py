"""Tiered authority enrichment manager.

V7 §4 splits authority sources into four tiers by access cost:

- **Tier 0** (free, no auth): OpenAlex, Crossref, ORCID_ETD,
  Crossref_Thesis. Always-on; safe to call without environment.
- **Tier 1** (free, public APIs): Wikidata_P184, GND, zbMATH_Open,
  HAL, OAI_University. Network-dependent; gated by ``OFFLINE``.
- **Tier 2** (gated by API key or subscription): MathSciNet, Scopus,
  Dimensions. Each adapter detects its own credential and short-
  circuits to ``hit=False, reason="no_api_key"`` when missing.
- **Tier 3** (deferred / ToS-incompatible): ProQuest, GoogleScholar.
  Adapter exists for completeness but always returns
  ``hit=False, reason="<defer_reason>"``.

The ``enrich_by_tiers`` orchestrator runs the requested tiers in
parallel for each entry, merges their results into a flat record,
and adds a ``_sources`` audit trail listing the names that were
queried (regardless of hit).

Caching is on-disk, namespaced per adapter, zlib-compressed JSON
keyed by SHA-256 of the canonical query payload. ``_cache_get`` and
``_cache_set`` are unit-testable through the module-level
``CACHE_DIR`` constant which tests patch via temp dirs.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import pathlib
import zlib
from typing import Any, Awaitable, Callable, Dict, List, Tuple

OFFLINE = os.getenv("OFFLINE", "1") == "1"
CACHE_DIR = pathlib.Path(os.getenv("GMNAP_CACHE_DIR", "./cache/authority")).resolve()


# ---------------------------------------------------------------------------
# Cache primitives
# ---------------------------------------------------------------------------


def _cache_key(namespace: str, payload: Dict[str, Any]) -> pathlib.Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps({"ns": namespace, "p": payload}, sort_keys=True).encode("utf-8")
    h = hashlib.sha256(raw).hexdigest()
    return CACHE_DIR / f"{namespace}_{h}.json.zst"


def _cache_get(path: pathlib.Path) -> Dict | None:
    if path.exists():
        data = zlib.decompress(path.read_bytes())
        return json.loads(data.decode("utf-8"))
    return None


def _cache_set(path: pathlib.Path, obj: Dict) -> None:
    payload = zlib.compress(json.dumps(obj, sort_keys=True).encode("utf-8"), level=9)
    path.write_bytes(payload)


# ---------------------------------------------------------------------------
# Adapter helpers
# ---------------------------------------------------------------------------


def _no_name(adapter_name: str, *, reason: str = "no_name") -> Dict[str, Any]:
    """Standard 'empty input, skipping' response shape."""
    return {adapter_name: {"hit": False, "reason": reason}}


def _offline_skip(adapter_name: str) -> Dict[str, Any]:
    """Standard 'OFFLINE=1, skipping live call' response."""
    return {adapter_name: {"hit": False}}


def _to_natural_order(name: str) -> str:
    """Convert pipeline-canonical ``Family, Given`` to natural
    ``Given Family``.

    Live-eval finding (2026-04-30): OpenAlex's
    ``filter=display_name.search:`` API does not tolerate the
    canonical-comma syntax — querying ``"Tao, Terence"`` returns no
    matches at all, but querying ``"Terence Tao"`` returns the
    correct author with full affiliation data. Same likely for
    Crossref and other natural-order-expecting endpoints. The
    pipeline emits names in ``Family, Given`` form (V7 §1), so the
    tier orchestrator must transform before calling out.

    - ``"Tao, Terence"``  → ``"Terence Tao"``
    - ``"Erdős, Paul"``   → ``"Paul Erdős"``
    - ``"García Márquez, Gabriel"`` → ``"Gabriel García Márquez"``
    - ``"Pythagoras"``     → ``"Pythagoras"``  (mononym, unchanged)
    - ``""``               → ``""``
    """
    if "," not in name:
        return name
    family, _, given = name.partition(",")
    given = given.strip()
    family = family.strip()
    if not given or not family:
        return name
    return f"{given} {family}"


# ---------------------------------------------------------------------------
# Fetcher pool (per-process reuse to amortize aiohttp session setup)
# ---------------------------------------------------------------------------
#
# Each `AuthorityFetcher` subclass under `src/authorities/tier{0,1,2}/`
# lazily opens an `aiohttp.ClientSession` on first request and holds
# rate-limiter state on the instance. Spawning a fresh instance per
# `_fetch_*` call (the previous design) wasted ~1 ms/call on session
# setup *and* reset the rate-limit clock, so a 10k-entry batch that
# wanted to respect a 10 RPS budget would hit the upstream as fast as
# the executor would let it.
#
# Pool the instances per-process. First lookup of a (module_path,
# class_name) pair instantiates and caches; subsequent lookups reuse.
# Tests can drop the pool via `_close_fetcher_pool()` between fixtures
# (and the module's atexit hook closes everything on interpreter
# shutdown).

_FETCHER_POOL: Dict[Tuple[str, str], Any] = {}
_FETCHER_POOL_LOCK = asyncio.Lock()


async def _get_pooled_fetcher(
    fetcher_path: str,
    fetcher_class: str,
    extra_config: Dict[str, Any] | None,
) -> Any:
    """Return the cached fetcher instance, creating it on first hit."""
    key = (fetcher_path, fetcher_class)
    cached = _FETCHER_POOL.get(key)
    if cached is not None:
        return cached
    async with _FETCHER_POOL_LOCK:
        cached = _FETCHER_POOL.get(key)
        if cached is not None:
            return cached
        from importlib import import_module

        module = import_module(fetcher_path)
        cls = getattr(module, fetcher_class)
        instance = cls(extra_config or {})
        _FETCHER_POOL[key] = instance
        return instance


async def _close_fetcher_pool() -> None:
    """Close every pooled fetcher's HTTP session and clear the pool.

    Called by tests between fixtures and as an atexit hook so we don't
    leak aiohttp ``ClientSession`` warnings on interpreter shutdown.
    """
    async with _FETCHER_POOL_LOCK:
        for fetcher in list(_FETCHER_POOL.values()):
            close = getattr(fetcher, "close", None)
            if close is None:
                continue
            try:
                maybe_coro = close()
                if hasattr(maybe_coro, "__await__"):
                    await maybe_coro
            except Exception:
                pass
        _FETCHER_POOL.clear()


def _close_fetcher_pool_sync() -> None:
    """Synchronous wrapper for atexit, which can't await."""
    if not _FETCHER_POOL:
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't block in a running loop; schedule and hope.
            asyncio.ensure_future(_close_fetcher_pool())
        else:
            loop.run_until_complete(_close_fetcher_pool())
    except RuntimeError:
        # No event loop available (interpreter teardown). Best effort:
        # the OS will reclaim sockets when the process exits anyway.
        pass


# Wire the pool to atexit — last-resort cleanup if a long-running
# process didn't explicitly close on shutdown.
import atexit  # noqa: E402 (intentional after the pool defs)

atexit.register(_close_fetcher_pool_sync)


async def _call_canonical_fetcher(
    fetcher_path: str,
    fetcher_class: str,
    source_name: str,
    name: str,
    *,
    extra_config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Delegate to the canonical Fetcher class in src/authorities/.

    The real HTTP code lives there (under tier0/, tier1/, tier2/ as
    `AuthorityFetcher` subclasses); the `_fetch_*` functions in this
    module are the V7 tier orchestrator's adapter shims. Until this
    helper landed, the shims silently returned ``{hit: False}`` even
    when ``OFFLINE=0``, so the live HTTP path was unreachable from
    `pipeline_v7.py`'s enrichment stage.

    Fetchers are pooled per (module_path, class_name) for the lifetime
    of the process (see ``_FETCHER_POOL``); the underlying
    aiohttp.ClientSession is reused across calls so a 10k-entry batch
    only pays one session-setup cost.

    Args
    ----
    fetcher_path
        Dotted import path of the module, e.g.
        ``"src.authorities.tier0.openalex"``.
    fetcher_class
        Class name inside that module, e.g. ``"OpenAlexFetcher"``.
    source_name
        The key used in the orchestrator's response dict
        (``"OpenAlex"``, ``"GND"``, …).
    name
        The mathematician name to query.
    extra_config
        Per-source config (e.g. an API key). Falls back to ``{}``.

    Returns
    -------
    Dict shaped ``{source_name: {hit, …}}``. On any importable but
    runtime-failing path (network down, parse error, missing optional
    dependency) we degrade to ``{hit: False, reason: …}`` rather than
    raising, so a single source's failure doesn't poison the batch.
    """
    from .common import retry_with_backoff

    try:
        fetcher = await _get_pooled_fetcher(fetcher_path, fetcher_class, extra_config)
    except (ImportError, AttributeError) as exc:
        return {source_name: {"hit": False, "reason": f"fetcher_unavailable:{exc}"}}

    try:
        result = await retry_with_backoff(
            lambda: fetcher.fetch(name), max_retries=2, base_delay=0.5
        )
    except Exception as exc:  # noqa: BLE001 — defensive batch isolation
        return {
            source_name: {"hit": False, "reason": f"fetch_error:{type(exc).__name__}"}
        }

    # FetchResult is the canonical shape: status enum + optional data.
    status = getattr(result, "status", None)
    status_value = getattr(status, "value", str(status)) if status else "unknown"
    if status_value != "success" or result.data is None:
        return {source_name: {"hit": False, "reason": f"status:{status_value}"}}

    data = result.data
    return {
        source_name: {
            "hit": True,
            "source_id": getattr(data, "source_id", None),
            "canonical_name": getattr(data, "canonical_name", None),
            "affiliations": getattr(data, "affiliations", []),
            "identifiers": getattr(data, "identifiers", {}),
            "birth_year": getattr(data, "birth_year", None),
            "death_year": getattr(data, "death_year", None),
            "countries": getattr(data, "countries", []),
        }
    }


# ---------------------------------------------------------------------------
# Tier 0 — free, no auth
# ---------------------------------------------------------------------------


async def _fetch_openalex(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("OpenAlex")
    # Normalize to natural order — OpenAlex's display_name.search
    # filter rejects the canonical comma syntax (live eval verified).
    query = _to_natural_order(name)
    ck = _cache_key("openalex", {"name": query})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("OpenAlex")
    result = await _call_canonical_fetcher(
        "src.authorities.tier0.openalex", "OpenAlexFetcher", "OpenAlex", query
    )
    _cache_set(ck, result)
    return result


async def _fetch_crossref(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("Crossref")
    # Same natural-order normalization as OpenAlex — Crossref's
    # author search uses author-name fields parsed from natural form.
    query = _to_natural_order(name)
    ck = _cache_key("crossref", {"name": query})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("Crossref")
    result = await _call_canonical_fetcher(
        "src.authorities.tier0.crossref", "CrossrefFetcher", "Crossref", query
    )
    _cache_set(ck, result)
    return result


async def _fetch_orcid_etd(entry: Dict) -> Dict:
    """ORCID_ETD requires an ORCID identifier (\\d{4}-\\d{4}-\\d{4}-…),
    not a name. We get one by piggy-backing on OpenAlex, which exposes
    the author's ORCID on its `orcid` field (when known). The 2026-04-30
    live eval caught this — the fetcher was being called with the raw
    CanonicalLatin and rejecting every input as malformed, so the code
    path returned 0 % hit rate on the curated 30. Now:

      1. Look up the name in OpenAlex (cached if a parallel
         ``_fetch_openalex`` already ran in this batch).
      2. If OpenAlex carries an ORCID for that author, call ORCID_ETD
         with the identifier.
      3. Otherwise return ``hit=False`` with reason ``no_orcid_for_name``
         — distinct from the old ``Invalid ORCID format`` log noise.

    Doubling the OpenAlex call on cold cache is acceptable because the
    cache is keyed by name and ``_call_canonical_fetcher`` short-
    circuits on the second hit. Live API quota cost: at most one extra
    OpenAlex query per author, only on the first run.
    """
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("ORCID_ETD")
    if OFFLINE:
        return _offline_skip("ORCID_ETD")

    # Step 1: name → ORCID via OpenAlex.
    openalex_result = await _fetch_openalex(entry)
    orcid = ((openalex_result.get("OpenAlex") or {}).get("identifiers") or {}).get(
        "ORCID"
    )
    if not orcid:
        return {
            "ORCID_ETD": {
                "hit": False,
                "reason": "no_orcid_for_name",
            }
        }

    # Step 2: ORCID → ETD.
    ck = _cache_key("orcid_etd", {"orcid": orcid})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    result = await _call_canonical_fetcher(
        "src.authorities.tier0.orcid_etd", "ORCIDETDFetcher", "ORCID_ETD", orcid
    )
    _cache_set(ck, result)
    return result


async def _fetch_crossref_thesis(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return {"Crossref_Thesis": {"hit": False, "match": False, "works": 0}}
    ck = _cache_key("crossref_thesis", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return {"Crossref_Thesis": {"hit": False, "match": False, "works": 0}}
    result = await _call_canonical_fetcher(
        "src.authorities.tier0.crossref_thesis",
        "CrossrefThesisFetcher",
        "Crossref_Thesis",
        name,
    )
    # Post-process to keep the legacy { hit, match, works } keys that
    # downstream consumers (and the back-compat tests in
    # test_authority_manager) rely on. `match` is true iff we got any
    # successful canonical-name match; `works` is the count of
    # dissertation entries surfaced from the upstream metadata, falling
    # back to 1-if-hit-else-0 when the canonical fetcher doesn't expose
    # a count.
    inner = result.get("Crossref_Thesis", {})
    inner.setdefault("match", bool(inner.get("hit")))
    if "works" not in inner:
        inner["works"] = 1 if inner.get("hit") else 0
    _cache_set(ck, result)
    return result


# ---------------------------------------------------------------------------
# Tier 1 — free public APIs
# ---------------------------------------------------------------------------


async def _fetch_wikidata_p184(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return {"Wikidata_P184": {"hit": False, "reason": "no_name", "edges": []}}
    # Wikidata accepts both forms but a natural-order query
    # ("Terence Tao") matches more reliably than the canonical
    # comma form. Normalize for parity with OpenAlex.
    query = _to_natural_order(name)
    ck = _cache_key("wikidata_p184", {"name": query})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return {"Wikidata_P184": {"hit": False, "edges": []}}
    # Live path: search for the QID, then run the SPARQL combined
    # doctoral-advisor + birth-year query. Both legs are wrapped in
    # retry_with_backoff because Wikidata's public endpoint regularly
    # throws transient 503s under load (typically resolved on the
    # next attempt) — a naive single-shot would poison entire
    # batches of enrichment.
    try:
        import aiohttp  # type: ignore
    except ImportError:
        return {"Wikidata_P184": {"hit": False, "reason": "no_aiohttp", "edges": []}}

    from urllib.parse import quote

    from .common import retry_with_backoff

    # Wikidata's API requires a User-Agent per their access policy;
    # without one the search endpoint returns text/plain (causing
    # aiohttp.json() to raise ContentTypeError). The 2026-04-30 live
    # eval caught this — every Wikidata call was failing silently.
    headers = {"User-Agent": "GMNAP/7.0 (mathematician name authority)"}

    async with aiohttp.ClientSession(headers=headers) as session:
        search_url = (
            "https://www.wikidata.org/w/api.php?"
            "action=wbsearchentities&format=json&language=en&search=" + quote(query)
        )

        async def _do_search():
            async with session.get(search_url) as resp:
                # content_type=None disables aiohttp's default
                # application/json check — Wikidata sometimes returns
                # text/plain on edge cases and the SPARQL endpoint
                # returns application/sparql-results+json which
                # aiohttp doesn't recognize as JSON.
                return resp.status, (
                    await resp.json(content_type=None) if resp.status == 200 else None
                )

        status, sd = await retry_with_backoff(_do_search, max_retries=2, base_delay=0.5)
        if status != 200 or sd is None:
            return {
                "Wikidata_P184": {
                    "hit": False,
                    "reason": "search_http_error",
                    "edges": [],
                }
            }
        hits = sd.get("search") or []
        if not hits:
            result = {"Wikidata_P184": {"hit": False, "edges": []}}
            _cache_set(ck, result)
            return result
        qid = hits[0]["id"]

        # SPARQL pulls both P184 (doctoral advisor — multiple OK) and
        # P569 (date of birth — single value, year extracted with
        # YEAR()). P184 is OPTIONAL so historical mathematicians
        # without recorded advisors still return a row carrying birth
        # year. P569 is OPTIONAL for the same symmetry — modern
        # researchers may have an advisor but no public DOB.
        # NB: the closing brace for the second OPTIONAL is in an
        # f-string segment so the `}}` escape collapses to a single
        # `}`. Earlier draft had `}} ` in a plain-string segment which
        # left two literal closing braces in the SPARQL → 400 from
        # the SPARQL endpoint. Same trap caught us in round 16.
        sparql = (
            "SELECT ?advisor ?advisorLabel ?birthYear WHERE { "
            f"OPTIONAL {{ wd:{qid} wdt:P184 ?advisor . }} "
            f"OPTIONAL {{ wd:{qid} wdt:P569 ?birthDate . "
            f"             BIND(YEAR(?birthDate) AS ?birthYear) }} "
            'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }'
        )
        sparql_url = "https://query.wikidata.org/sparql?format=json&query=" + quote(
            sparql
        )

        async def _do_sparql():
            async with session.get(sparql_url) as resp:
                # content_type=None — see _do_search for context.
                return resp.status, (
                    await resp.json(content_type=None) if resp.status == 200 else None
                )

        status, qd = await retry_with_backoff(_do_sparql, max_retries=2, base_delay=0.5)
        if status != 200 or qd is None:
            return {
                "Wikidata_P184": {
                    "hit": False,
                    "reason": "sparql_http_error",
                    "wikidata_id": qid,
                    "edges": [],
                }
            }

    edges: List[Dict[str, str]] = []
    birth_year: int | None = None
    for binding in (qd.get("results") or {}).get("bindings", []):
        target = (binding.get("advisorLabel") or {}).get("value")
        if target:
            edge = {"relation": "doctoralAdvisor", "target": target}
            if edge not in edges:  # SPARQL cross-product can dup rows
                edges.append(edge)
        # birth_year is the same on every row (P569 single-valued);
        # take the first non-None we see.
        if birth_year is None:
            by_raw = (binding.get("birthYear") or {}).get("value")
            if by_raw:
                try:
                    birth_year = int(by_raw)
                except ValueError:
                    pass

    payload: Dict[str, Any] = {"hit": True, "wikidata_id": qid, "edges": edges}
    if birth_year is not None:
        payload["birth_year"] = birth_year
    result = {"Wikidata_P184": payload}
    _cache_set(ck, result)
    return result


async def _fetch_gnd(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("GND")
    ck = _cache_key("gnd", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("GND")
    result = await _call_canonical_fetcher(
        "src.authorities.tier1.gnd", "GNDFetcher", "GND", name
    )
    _cache_set(ck, result)
    return result


async def _fetch_zbmath(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("zbMATH_Open")
    ck = _cache_key("zbmath", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("zbMATH_Open")
    result = await _call_canonical_fetcher(
        "src.authorities.tier0.zbmath", "ZbMATHFetcher", "zbMATH_Open", name
    )
    _cache_set(ck, result)
    return result


async def _fetch_hal(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("HAL")
    ck = _cache_key("hal", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("HAL")
    result = await _call_canonical_fetcher(
        "src.authorities.tier1.hal", "HALFetcher", "HAL", name
    )
    _cache_set(ck, result)
    return result


async def _fetch_oai_university(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("OAI_University")
    ck = _cache_key("oai_university", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("OAI_University")
    result = await _call_canonical_fetcher(
        "src.authorities.tier1.oai_university",
        "OAIUniversityFetcher",
        "OAI_University",
        name,
    )
    _cache_set(ck, result)
    return result


# ---------------------------------------------------------------------------
# Tier 2 — gated by API key or institutional subscription
# ---------------------------------------------------------------------------


async def _fetch_mathscinet(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("MathSciNet")
    ck = _cache_key("mathscinet", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("MathSciNet")
    return _offline_skip("MathSciNet")


async def _fetch_scopus(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("Scopus")
    if not os.getenv("SCOPUS_API_KEY"):
        return {"Scopus": {"hit": False, "reason": "no_api_key"}}
    return _offline_skip("Scopus")


async def _fetch_dimensions(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("Dimensions")
    if not os.getenv("DIMENSIONS_API_KEY"):
        return {"Dimensions": {"hit": False, "reason": "no_api_key"}}
    if OFFLINE:
        return _offline_skip("Dimensions")
    return _offline_skip("Dimensions")


# ---------------------------------------------------------------------------
# Tier 3 — deferred / ToS-incompatible
# ---------------------------------------------------------------------------


async def _fetch_proquest(entry: Dict) -> Dict:
    return {"ProQuest": {"hit": False, "reason": "requires_institutional_access"}}


async def _fetch_google_scholar(entry: Dict) -> Dict:
    return {"GoogleScholar": {"hit": False, "reason": "tos_optin_required"}}


# ---------------------------------------------------------------------------
# Tier registry — the single source of truth for who lives where
# ---------------------------------------------------------------------------

Handler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]

TIER_HANDLERS: Dict[int, List[Tuple[str, Handler]]] = {
    0: [
        ("OpenAlex", _fetch_openalex),
        ("Crossref", _fetch_crossref),
        ("ORCID_ETD", _fetch_orcid_etd),
        ("Crossref_Thesis", _fetch_crossref_thesis),
    ],
    1: [
        ("Wikidata_P184", _fetch_wikidata_p184),
        ("GND", _fetch_gnd),
        ("zbMATH_Open", _fetch_zbmath),
        ("HAL", _fetch_hal),
        ("OAI_University", _fetch_oai_university),
    ],
    2: [
        ("MathSciNet", _fetch_mathscinet),
        ("Scopus", _fetch_scopus),
        ("Dimensions", _fetch_dimensions),
    ],
    3: [
        ("ProQuest", _fetch_proquest),
        ("GoogleScholar", _fetch_google_scholar),
    ],
}


def _get_handlers_for_tiers(tiers: List[int]) -> List[Tuple[str, Handler]]:
    """Flatten ``TIER_HANDLERS`` for the requested tier list, in
    declaration order. Unknown tiers are silently dropped so a caller
    asking for ``[0, 99]`` gets only Tier-0 handlers — same shape but
    no exception.
    """
    out: List[Tuple[str, Handler]] = []
    for t in tiers:
        out.extend(TIER_HANDLERS.get(t, []))
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def enrich_by_tiers(
    entries: List[Dict[str, Any]],
    tiers: List[int] | None = None,
) -> List[Dict[str, Any]]:
    """Run the requested authority tiers against each entry in
    parallel and merge results.

    For every entry, we:
      1. Look up the handler list for ``tiers`` (default ``[0]``).
      2. Run all handlers concurrently with ``asyncio.gather``.
      3. Merge each handler's response into a copy of the entry.
      4. Append every adapter name to the entry's ``_sources`` list
         (regardless of hit) so consumers can audit what was queried.
      5. Specifically merge ``Wikidata_P184`` advisor edges into the
         ``Advisors`` list — preserving any caller-supplied advisors.

    Returns a new list of entries (does not mutate the inputs).
    """
    if tiers is None:
        tiers = [0]
    handlers = _get_handlers_for_tiers(tiers)
    out: List[Dict[str, Any]] = []
    for e in entries:
        merged = dict(e)
        if not handlers:
            merged.setdefault("_sources", [])
            out.append(merged)
            continue
        tasks = [h(e) for _, h in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        sources = list(merged.get("_sources") or [])
        for (name, _), r in zip(handlers, results):
            if isinstance(r, Exception):
                continue
            if name not in sources:
                sources.append(name)
            # Merge Wikidata advisor edges
            if name == "Wikidata_P184" and isinstance(r, dict):
                wd = r.get("Wikidata_P184") or {}
                edges = wd.get("edges") or []
                if edges:
                    advisors = list(merged.get("Advisors") or [])
                    for edge in edges:
                        target = edge.get("target") if isinstance(edge, dict) else None
                        if target and target not in advisors:
                            advisors.append(target)
                    merged["Advisors"] = advisors
        merged["_sources"] = sources
        out.append(merged)
    return out


# ---------------------------------------------------------------------------
# Back-compat exports — used by older pipelines (pipeline_v6, streaming_v7)
# ---------------------------------------------------------------------------


# Public-name aliases for the underscore-prefixed fetchers, kept so
# legacy callers compiled against the old names still resolve. New
# code should import the underscore form (the test suite does).
fetch_crossref_thesis = _fetch_crossref_thesis
fetch_wikidata_p184 = _fetch_wikidata_p184
fetch_oai_university = _fetch_oai_university
fetch_hal = _fetch_hal
fetch_gnd = _fetch_gnd
fetch_zbmath = _fetch_zbmath


AUTH_HANDLERS: List[Tuple[str, Handler]] = TIER_HANDLERS[0] + TIER_HANDLERS[1]


async def enrich_all(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Back-compat: run tiers 0 + 1 over all entries."""
    return await enrich_by_tiers(entries, tiers=[0, 1])
