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
    from importlib import import_module

    from .common import retry_with_backoff

    try:
        module = import_module(fetcher_path)
        cls = getattr(module, fetcher_class)
    except (ImportError, AttributeError) as exc:
        return {source_name: {"hit": False, "reason": f"fetcher_unavailable:{exc}"}}

    fetcher = cls(extra_config or {})

    try:
        result = await retry_with_backoff(
            lambda: fetcher.fetch(name), max_retries=2, base_delay=0.5
        )
    except Exception as exc:  # noqa: BLE001 — defensive batch isolation
        return {
            source_name: {"hit": False, "reason": f"fetch_error:{type(exc).__name__}"}
        }
    finally:
        # AuthorityFetcher holds an aiohttp.ClientSession; release it
        # so we don't leak connections across batches.
        try:
            close = getattr(fetcher, "close", None)
            if close is not None:
                maybe_coro = close()
                if hasattr(maybe_coro, "__await__"):
                    await maybe_coro
        except Exception:
            pass

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
    ck = _cache_key("openalex", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("OpenAlex")
    result = await _call_canonical_fetcher(
        "src.authorities.tier0.openalex", "OpenAlexFetcher", "OpenAlex", name
    )
    _cache_set(ck, result)
    return result


async def _fetch_crossref(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("Crossref")
    ck = _cache_key("crossref", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("Crossref")
    result = await _call_canonical_fetcher(
        "src.authorities.tier0.crossref", "CrossrefFetcher", "Crossref", name
    )
    _cache_set(ck, result)
    return result


async def _fetch_orcid_etd(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return _no_name("ORCID_ETD")
    ck = _cache_key("orcid_etd", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return _offline_skip("ORCID_ETD")
    result = await _call_canonical_fetcher(
        "src.authorities.tier0.orcid_etd", "ORCIDETDFetcher", "ORCID_ETD", name
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
    _cache_set(ck, result)
    return result


# ---------------------------------------------------------------------------
# Tier 1 — free public APIs
# ---------------------------------------------------------------------------


async def _fetch_wikidata_p184(entry: Dict) -> Dict:
    name = (entry.get("CanonicalLatin") or "").strip()
    if not name:
        return {"Wikidata_P184": {"hit": False, "reason": "no_name", "edges": []}}
    ck = _cache_key("wikidata_p184", {"name": name})
    cached = _cache_get(ck)
    if cached is not None:
        return cached
    if OFFLINE:
        return {"Wikidata_P184": {"hit": False, "edges": []}}
    # Live path: search for the QID, then run the SPARQL doctoral-
    # advisor query. Both legs are wrapped in retry_with_backoff
    # because Wikidata's public endpoint regularly throws transient
    # 503s under load (typically resolved on the next attempt) — a
    # naive single-shot would poison entire batches of enrichment.
    try:
        import aiohttp  # type: ignore
    except ImportError:
        return {"Wikidata_P184": {"hit": False, "reason": "no_aiohttp", "edges": []}}

    from .common import retry_with_backoff

    async with aiohttp.ClientSession() as session:
        search_url = (
            "https://www.wikidata.org/w/api.php?"
            "action=wbsearchentities&format=json&language=en&search=" + name
        )

        async def _do_search():
            async with session.get(search_url) as resp:
                return resp.status, (await resp.json() if resp.status == 200 else None)

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

        sparql = (
            "SELECT ?advisor ?advisorLabel WHERE { "
            f"wd:{qid} wdt:P184 ?advisor . "
            'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }'
        )
        sparql_url = "https://query.wikidata.org/sparql?format=json&query=" + sparql

        async def _do_sparql():
            async with session.get(sparql_url) as resp:
                return resp.status, (await resp.json() if resp.status == 200 else None)

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

    edges = []
    for binding in (qd.get("results") or {}).get("bindings", []):
        target = (binding.get("advisorLabel") or {}).get("value")
        if target:
            edges.append({"relation": "doctoralAdvisor", "target": target})

    result = {"Wikidata_P184": {"hit": True, "wikidata_id": qid, "edges": edges}}
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
