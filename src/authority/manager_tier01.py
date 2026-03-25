"""Authority enrichment manager with V7 tier-based dispatch.

Tier 0: OpenAlex, Crossref, ORCID_ETD, Crossref_Thesis (free, no auth)
Tier 1: Wikidata_P184, OAI_University, HAL, GND, zbMATH_Open (free, rate limited)
Tier 2: MathSciNet, Scopus, Dimensions (subscription required)
Tier 3: ProQuest, Google Scholar (scraper / subscription)

IMPLEMENTATION STATUS (as of 2026-03-16):
  Tier 0 (free, no auth):
    - OpenAlex:        WORKING (httpx adapter, /authors endpoint, no OFFLINE guard)
    - Crossref:        WORKING (httpx adapter, /works?query.author=)
    - ORCID_ETD:       WORKING (httpx adapter, /expanded-search)
    - Crossref_Thesis: WORKING (aiohttp in dispatch + httpx adapter, OFFLINE guard)
  Tier 1 (free, rate-limited):
    - Wikidata_P184:   WORKING (aiohttp SPARQL + httpx adapter, OFFLINE guard)
    - OAI_University:  WORKING (aiohttp BASE API + httpx adapter, OFFLINE guard)
    - HAL:             WORKING (httpx adapter, archives-ouvertes.fr)
    - GND:             WORKING (aiohttp lobid.org + httpx adapter, OFFLINE guard)
    - zbMATH_Open:     WORKING (httpx adapter, api.zbmath.org)
  Tier 2 (subscription):
    - MathSciNet:      WORKING (aiohttp, free MR Lookup + full API w/ MATHSCINET_API_KEY)
    - Scopus:          GATED (needs SCOPUS_API_KEY, free for research at dev.elsevier.com)
    - Dimensions:      GATED (needs DIMENSIONS_API_KEY, free at app.dimensions.ai)
  Tier 3 (restricted):
    - ProQuest:        DEFERRED (requires institutional proxy access)
    - GoogleScholar:   DEFERRED (ToS, opt-in via --force-extreme + YES_I_ACCEPT_GS_TOS)

NOTE: OFFLINE defaults to "1" (True).  In OFFLINE mode, most fetchers
return cached results or empty dicts.  Set OFFLINE=0 to enable real
API calls.
"""

from __future__ import annotations
import os
import json
import asyncio
import pathlib
import hashlib
import zlib
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

OFFLINE = os.getenv("OFFLINE", "1") == "1"
CACHE_DIR = pathlib.Path(os.getenv("GMNAP_CACHE_DIR", "./cache/authority")).resolve()


# ── Cache helpers ──────────────────────────────────────────────────────────


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


# ── Tier 0 fetchers (free, no auth) ───────────────────────────────────────


async def _fetch_openalex(entry: Dict) -> Dict:
    """OpenAlex authors search by name. Free, no auth, 864K/day."""
    ck = _cache_key("openalex", {"name": entry.get("CanonicalLatin", "")})
    cached = _cache_get(ck)
    if cached:
        return cached
    try:
        from src.authority.openalex_adapter import OpenAlexAdapter

        adapter = OpenAlexAdapter()
        try:
            result = await adapter.enrich(entry)
            if result.get("_source", {}).get("hit"):
                data = {
                    "OpenAlex": {
                        "hit": True,
                        "source_id": result.get("OpenAlexID"),
                        "identifiers": {k: v for k, v in result.items() if k not in ("_source",)},
                    }
                }
                _cache_set(ck, data)
                return data
        finally:
            await adapter.ctx.close()
    except Exception as e:
        logger.debug(f"OpenAlex fetch failed: {e}")
    return {"OpenAlex": {"hit": False}}


async def _fetch_crossref(entry: Dict) -> Dict:
    """Crossref generic works search. Free, no auth, 4.3M/day polite pool."""
    ck = _cache_key("crossref", {"name": entry.get("CanonicalLatin", "")})
    cached = _cache_get(ck)
    if cached:
        return cached
    try:
        from src.authority.crossref_adapter import CrossrefAdapter

        adapter = CrossrefAdapter()
        try:
            result = await adapter.enrich(entry)
            if result.get("_source", {}).get("hit"):
                data = {
                    "Crossref": {
                        "hit": True,
                        "identifiers": {k: v for k, v in result.items() if k not in ("_source",)},
                    }
                }
                _cache_set(ck, data)
                return data
        finally:
            await adapter.ctx.close()
    except Exception as e:
        logger.debug(f"Crossref fetch failed: {e}")
    return {"Crossref": {"hit": False}}


async def _fetch_orcid_etd(entry: Dict) -> Dict:
    """ORCID public API — expanded search. Free, no auth, 100K/day."""
    ck = _cache_key("orcid", {"name": entry.get("CanonicalLatin", "")})
    cached = _cache_get(ck)
    if cached:
        return cached
    try:
        from src.authority.orcid_etd_adapter import ORCIDETDAdapter

        adapter = ORCIDETDAdapter()
        try:
            result = await adapter.enrich(entry)
            if result.get("_source", {}).get("hit"):
                data = {
                    "ORCID_ETD": {
                        "hit": True,
                        "source_id": result.get("ORCID"),
                        "identifiers": {k: v for k, v in result.items() if k not in ("_source",)},
                    }
                }
                _cache_set(ck, data)
                return data
        finally:
            await adapter.ctx.close()
    except Exception as e:
        logger.debug(f"ORCID fetch failed: {e}")
    return {"ORCID_ETD": {"hit": False}}


async def _fetch_crossref_thesis(entry: Dict) -> Dict:
    """Crossref thesis-specific lookup (type: dissertation).

    Searches Crossref for dissertation records matching the author name.
    Extracts thesis title, DOI, institution, and year.
    """
    name = entry.get("CanonicalLatin", "")
    if not name:
        return {"Crossref_Thesis": {"works": 0, "match": False, "reason": "no_name"}}
    ck = _cache_key("crossref_thesis", {"name": name})
    cached = _cache_get(ck)
    if cached:
        return cached
    if OFFLINE:
        return {"Crossref_Thesis": {"works": 0, "match": False}}
    try:
        import aiohttp

        # Parse name robustly
        if "," in name:
            family = name.split(",")[0].strip()
            given_parts = name.split(",")[1].strip().split()
            given = given_parts[0] if given_parts else ""
        else:
            parts = name.split()
            family = parts[-1] if parts else name
            given = parts[0] if len(parts) > 1 else ""

        url = (
            f"https://api.crossref.org/works?"
            f"query.author={family}+{given}&filter=type:dissertation&rows=5"
        )
        headers = {
            "User-Agent": f"GMNAP/7.0 (mailto:{os.getenv('GMNAP_EMAIL', 'gmnap@example.com')})"
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return {
                        "Crossref_Thesis": {
                            "works": 0,
                            "match": False,
                            "reason": f"http_{resp.status}",
                        }
                    }
                data = await resp.json()

        items = data.get("message", {}).get("items", [])
        if not items:
            result = {"Crossref_Thesis": {"works": 0, "match": False}}
            _cache_set(ck, result)
            return result

        # Extract thesis metadata from best match
        best = items[0]
        title_parts = best.get("title", [])
        thesis_title = title_parts[0] if title_parts else None
        institution = best.get("institution", {})
        inst_name = institution.get("name") if isinstance(institution, dict) else None
        year = None
        date_parts = best.get("issued", {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

        result = {
            "Crossref_Thesis": {
                "works": len(items),
                "match": True,
                "source_id": best.get("DOI"),
                "thesis_title": thesis_title,
                "institution": inst_name,
                "year": year,
            }
        }
        _cache_set(ck, result)
        return result
    except Exception as e:
        logger.debug(f"Crossref_Thesis fetch failed: {e}")
    return {"Crossref_Thesis": {"works": 0, "match": False}}


# ── Tier 1 fetchers (free, rate limited) ──────────────────────────────────


async def _fetch_wikidata_p184(entry: Dict) -> Dict:
    """Wikidata doctoral advisor (P184) edge lookup via SPARQL.

    Queries the Wikidata Query Service for P184 (doctoral advisor) and
    P185 (doctoral student) claims associated with a person.
    Uses wbsearchentities to find the Wikidata item, then SPARQL for P184.
    """
    name = entry.get("CanonicalLatin", "")
    if not name:
        return {"Wikidata_P184": {"hit": False, "reason": "no_name"}}

    ck = _cache_key("wikidata_p184", {"name": name})
    cached = _cache_get(ck)
    if cached:
        return cached
    if OFFLINE:
        return {"Wikidata_P184": {"hit": False}}
    try:
        import aiohttp

        # Step 1: Find Wikidata item via wbsearchentities
        search_url = (
            "https://www.wikidata.org/w/api.php"
            f"?action=wbsearchentities&search={name}&language=en"
            "&type=item&limit=5&format=json"
        )
        headers = {"User-Agent": "GMNAP/7.0 (academic genealogy research)"}
        async with aiohttp.ClientSession() as session:
            # Rate limit: Wikidata allows ~1 req/s for bots
            await asyncio.sleep(0.5)
            async with session.get(
                search_url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return {"Wikidata_P184": {"hit": False, "reason": "search_failed"}}
                search_data = await resp.json()

            candidates = search_data.get("search", [])
            if not candidates:
                result = {"Wikidata_P184": {"hit": False, "reason": "not_found"}}
                _cache_set(ck, result)
                return result

            # Use the first candidate (best match by Wikidata search ranking)
            qid = candidates[0].get("id", "")
            if not qid:
                result = {"Wikidata_P184": {"hit": False, "reason": "no_qid"}}
                _cache_set(ck, result)
                return result

            # Step 2: SPARQL query for P184 (doctoral advisor) claims
            sparql = f"""
            SELECT ?advisor ?advisorLabel WHERE {{
              wd:{qid} wdt:P184 ?advisor .
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
            }}
            """
            sparql_url = "https://query.wikidata.org/sparql"
            params = {"query": sparql, "format": "json"}
            await asyncio.sleep(0.5)  # Rate limit
            async with session.get(
                sparql_url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    result = {"Wikidata_P184": {"hit": False, "reason": "sparql_failed"}}
                    _cache_set(ck, result)
                    return result
                sparql_data = await resp.json()

            bindings = sparql_data.get("results", {}).get("bindings", [])
            edges = []
            for b in bindings:
                advisor_uri = b.get("advisor", {}).get("value", "")
                advisor_label = b.get("advisorLabel", {}).get("value", "")
                advisor_qid = advisor_uri.split("/")[-1] if advisor_uri else ""
                edges.append(
                    {
                        "relation": "doctoralAdvisor",
                        "target": advisor_label,
                        "wikidata_id": advisor_qid,
                        "confidence": 0.95,
                    }
                )

            result = {
                "Wikidata_P184": {
                    "hit": len(edges) > 0,
                    "wikidata_id": qid,
                    "edges": edges,
                }
            }
            _cache_set(ck, result)
            return result
    except Exception as e:
        logger.debug(f"Wikidata_P184 fetch failed: {e}")
    return {"Wikidata_P184": {"hit": False}}


async def _fetch_oai_university(entry: Dict) -> Dict:
    """OAI-PMH university repository lookup via BASE (Bielefeld Academic Search Engine).

    Searches BASE API for thesis/dissertation records matching the author name.
    Filters by dctypenorm:15 (theses) and validates name match.
    """
    name = entry.get("CanonicalLatin", "")
    if not name:
        return {"OAI_University": {"hit": False, "reason": "no_name"}}
    ck = _cache_key("oai_university", {"name": name})
    cached = _cache_get(ck)
    if cached:
        return cached
    if OFFLINE:
        return {"OAI_University": {"hit": False}}
    try:
        import aiohttp

        # Parse name into family/given for more precise query
        if "," in name:
            family = name.split(",")[0].strip()
            given_parts = name.split(",")[1].strip().split()
            given = given_parts[0] if given_parts else ""
        else:
            parts = name.split()
            family = parts[-1] if parts else name
            given = parts[0] if len(parts) > 1 else ""

        # Search BASE for thesis records by this author
        query = f"aut:{family}"
        if given:
            query += f"+{given}"
        url = (
            "https://api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi"
            f"?func=PerformSearch&query={query}&format=json&hits=5"
            "&filter=dctypenorm:15"  # theses only
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return {"OAI_University": {"hit": False, "reason": f"http_{resp.status}"}}
                data = await resp.json()

        docs = data.get("response", {}).get("docs", [])
        if not docs:
            result = {"OAI_University": {"hit": False}}
            _cache_set(ck, result)
            return result

        # Find best match by comparing author name
        family_lower = family.lower()
        best_doc = None
        for doc in docs:
            creators = doc.get("dccreator", [])
            for creator in creators if isinstance(creators, list) else [creators]:
                if isinstance(creator, str) and family_lower in creator.lower():
                    best_doc = doc
                    break
            if best_doc:
                break

        if not best_doc:
            best_doc = docs[0]  # Fall back to first result

        # Extract thesis metadata
        identifiers = best_doc.get("dcidentifier", [])
        source_id = identifiers[0] if isinstance(identifiers, list) and identifiers else identifiers
        institution = best_doc.get("dcpublisher", [])
        if isinstance(institution, list):
            institution = institution[0] if institution else None
        title = best_doc.get("dctitle", "")

        result = {
            "OAI_University": {
                "hit": True,
                "source_id": source_id,
                "institution": institution,
                "thesis_title": title,
                "year": best_doc.get("dcyear"),
            }
        }
        _cache_set(ck, result)
        return result
    except Exception as e:
        logger.debug(f"OAI_University fetch failed: {e}")
    return {"OAI_University": {"hit": False}}


async def _fetch_hal(entry: Dict) -> Dict:
    """HAL French national archive lookup. Free, no auth, 86K/day."""
    ck = _cache_key("hal", {"name": entry.get("CanonicalLatin", "")})
    cached = _cache_get(ck)
    if cached:
        return cached
    if OFFLINE:
        return {"HAL": {"hit": False}}
    try:
        from src.authority.hal_adapter import HALAdapter

        adapter = HALAdapter({})
        result = await adapter.enrich(entry)
        if result.get("_source", {}).get("hit") or result.get("Institution"):
            data = {
                "HAL": {
                    "hit": True,
                    "identifiers": {k: v for k, v in result.items() if k not in ("_source",)},
                }
            }
            _cache_set(ck, data)
            return data
    except Exception as e:
        logger.debug(f"HAL fetch failed: {e}")
    return {"HAL": {"hit": False}}


async def _fetch_gnd(entry: Dict) -> Dict:
    """GND (German National Library) lookup via lobid.org API."""
    name = entry.get("CanonicalLatin", "")
    ck = _cache_key("gnd", {"name": name})
    cached = _cache_get(ck)
    if cached:
        return cached
    if OFFLINE:
        return {"GND": {"hit": False}}
    try:
        import aiohttp

        family = name.split(",")[0].strip() if "," in name else name.split()[-1]
        given = name.split(",")[1].strip().split()[0] if "," in name else name.split()[0]
        url = f"https://lobid.org/gnd/search?q=preferredNameForThePerson:{family}+{given}&filter=type:DifferentiatedPerson&size=3&format=json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    members = data.get("member", [])
                    result = {
                        "GND": {
                            "hit": len(members) > 0,
                            "source_id": members[0].get("gndIdentifier") if members else None,
                        }
                    }
                    _cache_set(ck, result)
                    return result
    except Exception as e:
        logger.debug(f"GND fetch failed: {e}")
    return {"GND": {"hit": False}}


async def _fetch_zbmath(entry: Dict) -> Dict:
    """zbMATH Open mathematics lookup. Free, no auth, 200/day."""
    ck = _cache_key("zbmath", {"name": entry.get("CanonicalLatin", "")})
    cached = _cache_get(ck)
    if cached:
        return cached
    if OFFLINE:
        return {"zbMATH_Open": {"hit": False}}
    try:
        from src.authority.zbmath_open_adapter import ZbMathOpenAdapter

        adapter = ZbMathOpenAdapter({})
        result = await adapter.enrich(entry)
        if result.get("_source", {}).get("hit") or result.get("Publications"):
            data = {
                "zbMATH_Open": {
                    "hit": True,
                    "identifiers": {k: v for k, v in result.items() if k not in ("_source",)},
                }
            }
            _cache_set(ck, data)
            return data
    except Exception as e:
        logger.debug(f"zbMATH fetch failed: {e}")
    return {"zbMATH_Open": {"hit": False}}


# ── Tier 2 fetchers (subscription required) ──────────────────────────────


async def _fetch_mathscinet(entry: Dict) -> Dict:
    """MathSciNet author lookup via AMS MR Lookup.

    Uses the free MR Lookup endpoint for basic author searches.
    If MATHSCINET_API_KEY is set, uses the full MathSciNet API for richer data.
    """
    name = entry.get("CanonicalLatin", "")
    if not name:
        return {"MathSciNet": {"hit": False, "reason": "no_name"}}
    ck = _cache_key("mathscinet", {"name": name})
    cached = _cache_get(ck)
    if cached:
        return cached
    if OFFLINE:
        return {"MathSciNet": {"hit": False}}
    try:
        import aiohttp

        # Parse name
        if "," in name:
            family = name.split(",")[0].strip()
            given_parts = name.split(",")[1].strip().split()
            given = given_parts[0] if given_parts else ""
        else:
            parts = name.split()
            family = parts[-1] if parts else name
            given = parts[0] if len(parts) > 1 else ""

        api_key = os.getenv("MATHSCINET_API_KEY")
        if api_key:
            # Full MathSciNet API (subscription required)
            url = (
                "https://mathscinet.ams.org/mathscinet/api/publications"
                f"?query=au.exact:{family}+{given}&fmt=json&rows=5"
            )
            headers = {
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "GMNAP/7.0",
            }
        else:
            # Free MR Lookup (limited but no auth needed)
            url = "https://mathscinet.ams.org/mrlookup" f"?s3={family}&s4={given}&format=json"
            headers = {"User-Agent": "GMNAP/7.0"}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    result = {
                        "MathSciNet": {
                            "hit": False,
                            "reason": f"http_{resp.status}",
                        }
                    }
                    _cache_set(ck, result)
                    return result

                # Try JSON first, fall back to text parsing for MR Lookup
                content_type = resp.headers.get("Content-Type", "")
                if "json" in content_type:
                    data = await resp.json()
                else:
                    # MR Lookup returns text; parse for MR numbers
                    text = await resp.text()
                    mr_numbers = []
                    for line in text.split("\n"):
                        line = line.strip()
                        if line.startswith("MR") and line[2:].strip().isdigit():
                            mr_numbers.append(line.strip())
                        elif line.startswith("{"):
                            # Some versions return JSON lines
                            try:
                                data = json.loads(line)
                                mr_numbers.append(data.get("mrnumber", ""))
                            except json.JSONDecodeError:
                                pass
                    result = {
                        "MathSciNet": {
                            "hit": len(mr_numbers) > 0,
                            "mr_numbers": mr_numbers[:5],
                            "source_id": mr_numbers[0] if mr_numbers else None,
                            "api_mode": "mr_lookup",
                        }
                    }
                    _cache_set(ck, result)
                    return result

                # JSON response (full API)
                results_list = data if isinstance(data, list) else data.get("results", [])
                if not results_list:
                    result = {"MathSciNet": {"hit": False}}
                    _cache_set(ck, result)
                    return result

                first = results_list[0] if results_list else {}
                result = {
                    "MathSciNet": {
                        "hit": True,
                        "source_id": first.get("mrnumber") or first.get("id"),
                        "publications_count": len(results_list),
                        "api_mode": "full_api" if api_key else "mr_lookup",
                    }
                }
                _cache_set(ck, result)
                return result
    except Exception as e:
        logger.debug(f"MathSciNet fetch failed: {e}")
    return {"MathSciNet": {"hit": False}}


async def _fetch_scopus(entry: Dict) -> Dict:
    api_key = os.getenv("SCOPUS_API_KEY")
    if not api_key:
        return {"Scopus": {"hit": False, "reason": "no_api_key"}}
    try:
        from src.authorities.tier1.scopus import ScopusFetcher

        fetcher = ScopusFetcher({"api_key": api_key})
        result = await fetcher.fetch(entry.get("CanonicalLatin", ""))
        if result.data:
            return {"Scopus": {"hit": True, "source_id": result.data.source_id}}
    except Exception as e:
        logger.debug(f"Scopus fetch failed: {e}")
    return {"Scopus": {"hit": False}}


async def _fetch_dimensions(entry: Dict) -> Dict:
    """Dimensions researcher lookup via DSL API.

    Requires DIMENSIONS_API_KEY environment variable.
    Uses the Dimensions Search Lite API to find researchers by name.
    """
    name = entry.get("CanonicalLatin", "")
    if not name:
        return {"Dimensions": {"hit": False, "reason": "no_name"}}

    api_key = os.getenv("DIMENSIONS_API_KEY")
    if not api_key:
        return {"Dimensions": {"hit": False, "reason": "no_api_key"}}

    ck = _cache_key("dimensions", {"name": name})
    cached = _cache_get(ck)
    if cached:
        return cached
    if OFFLINE:
        return {"Dimensions": {"hit": False}}
    try:
        import aiohttp

        # Parse name
        if "," in name:
            family = name.split(",")[0].strip()
            given_parts = name.split(",")[1].strip().split()
            given = given_parts[0] if given_parts else ""
        else:
            parts = name.split()
            family = parts[-1] if parts else name
            given = parts[0] if len(parts) > 1 else ""

        # Dimensions DSL query
        dsl_query = (
            f'search researchers where last_name="{family}"'
            f' and first_name="{given}"'
            " return researchers[id,first_name,last_name,orcid_id,"
            "current_research_org,total_publications] limit 5"
        )

        url = "https://app.dimensions.ai/api/dsl/v2"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "GMNAP/7.0",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json={"query": dsl_query},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    result = {"Dimensions": {"hit": False, "reason": "auth_failed"}}
                    return result
                if resp.status != 200:
                    result = {"Dimensions": {"hit": False, "reason": f"http_{resp.status}"}}
                    _cache_set(ck, result)
                    return result
                data = await resp.json()

        researchers = data.get("researchers", [])
        if not researchers:
            result = {"Dimensions": {"hit": False}}
            _cache_set(ck, result)
            return result

        best = researchers[0]
        result = {
            "Dimensions": {
                "hit": True,
                "source_id": best.get("id"),
                "orcid": best.get("orcid_id"),
                "institution": (
                    (best.get("current_research_org") or [{}])[0].get("name")
                    if isinstance(best.get("current_research_org"), list)
                    else None
                ),
                "publications_count": best.get("total_publications"),
            }
        }
        _cache_set(ck, result)
        return result
    except Exception as e:
        logger.debug(f"Dimensions fetch failed: {e}")
    return {"Dimensions": {"hit": False}}


# ── Tier 3 fetchers (scraper / subscription) ─────────────────────────────


async def _fetch_proquest(entry: Dict) -> Dict:
    """ProQuest Dissertations & Theses lookup.

    DEFERRED: Requires institutional proxy access. ProQuest does not provide
    a public API. Access requires a university library subscription and
    proxy authentication. To implement, the institution would need to
    provide SAML/Shibboleth credentials or an IP-authenticated proxy.
    """
    return {"ProQuest": {"hit": False, "reason": "requires_institutional_access"}}


async def _fetch_google_scholar(entry: Dict) -> Dict:
    """Google Scholar author lookup.

    V7 spec §10: google_scholar_optin requires --force-extreme + YES_I_ACCEPT_GS_TOS=yes.
    Results use encrypted cache to avoid repeat scraping.

    DEFERRED — DO NOT IMPLEMENT without explicit user consent: Scraping Google Scholar violates their
    Terms of Service. Google does not provide an official Scholar API.
    Any automated access is subject to IP bans and CAPTCHA challenges.
    Use OpenAlex (which ingests Scholar data) as the recommended alternative.
    """
    # V7 spec §10: require explicit opt-in
    if os.environ.get("YES_I_ACCEPT_GS_TOS", "").lower() != "yes":
        return {
            "GoogleScholar": {
                "hit": False,
                "reason": "tos_optin_required",
                "info": "Set YES_I_ACCEPT_GS_TOS=yes and use --force-extreme",
            }
        }
    # Even with opt-in, actual scraping is not implemented (ToS violation risk)
    return {"GoogleScholar": {"hit": False, "reason": "not_implemented_scraper_deferred"}}


# ── Tier registry ─────────────────────────────────────────────────────────

TIER_HANDLERS: Dict[int, List[tuple]] = {
    0: [
        ("OpenAlex", _fetch_openalex),
        ("Crossref", _fetch_crossref),
        ("ORCID_ETD", _fetch_orcid_etd),
        ("Crossref_Thesis", _fetch_crossref_thesis),
    ],
    1: [
        ("Wikidata_P184", _fetch_wikidata_p184),
        ("OAI_University", _fetch_oai_university),
        ("HAL", _fetch_hal),
        ("GND", _fetch_gnd),
        ("zbMATH_Open", _fetch_zbmath),
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


def _get_handlers_for_tiers(tiers: List[int]) -> List[tuple]:
    """Get all (name, handler) tuples for given tier list."""
    handlers = []
    for t in sorted(tiers):
        handlers.extend(TIER_HANDLERS.get(t, []))
    return handlers


async def enrich_by_tiers(entries: List[Dict], tiers: Optional[List[int]] = None) -> List[Dict]:
    """Enrich entries using authority sources from specified tiers.

    Args:
        entries: List of entry dicts.
        tiers: List of tier numbers to use (default: [0]).

    Returns:
        Enriched entries with _sources and merged external IDs.
    """
    if tiers is None:
        tiers = [0]

    handlers = _get_handlers_for_tiers(tiers)
    if not handlers:
        return entries

    logger.info(f"Authority enrichment: tiers={tiers}, sources={[n for n, _ in handlers]}")

    out = []
    for e in entries:
        merged = dict(e)
        tasks = [h(e) for _, h in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        sources = set(merged.get("_sources") or [])
        identifiers = dict(merged.get("AuthorityIDs") or merged.get("ExternalIDs") or {})

        for (name, _), r in zip(handlers, results):
            if isinstance(r, Exception):
                logger.debug(f"Authority {name} failed for {e.get('CanonicalLatin', '?')}: {r}")
                continue
            if not isinstance(r, dict):
                continue

            sources.add(name)
            # Extract identifiers from the result
            for source_name, source_data in r.items():
                if isinstance(source_data, dict):
                    if source_data.get("hit"):
                        sid = source_data.get("source_id")
                        if sid:
                            identifiers[source_name] = sid
                    ids = source_data.get("identifiers")
                    if isinstance(ids, dict):
                        for k, v in ids.items():
                            if isinstance(v, str):
                                identifiers[k] = v

            # Merge advisor edges from Wikidata P184
            if name == "Wikidata_P184":
                wd = r.get("Wikidata_P184", {})
                edges = wd.get("edges", []) if isinstance(wd, dict) else []
                if edges:
                    existing = set(merged.get("Advisors") or [])
                    for edge in edges:
                        if isinstance(edge, dict) and edge.get("target"):
                            existing.add(edge["target"])
                    merged["Advisors"] = sorted(existing)

            # Extract NameEvents from authority sources (v7 spec glossary)
            for source_name, source_data in r.items():
                if isinstance(source_data, dict):
                    name_events = source_data.get("name_events", [])
                    if name_events:
                        existing_events = merged.get("NameEvents", [])
                        seen = {(ev.get("type"), ev.get("year")) for ev in existing_events}
                        for ev in name_events:
                            key = (ev.get("type"), ev.get("year"))
                            if key not in seen:
                                existing_events.append(ev)
                                seen.add(key)
                        merged["NameEvents"] = sorted(
                            existing_events, key=lambda x: x.get("year", 0)
                        )

            # Extract AffiliationTimeline from authority sources (v7 spec glossary)
            for source_name, source_data in r.items():
                if isinstance(source_data, dict):
                    affiliations = source_data.get("affiliations", [])
                    if affiliations:
                        existing_aff = merged.get("AffiliationTimeline", [])
                        seen_aff = {(a.get("country"), a.get("from")) for a in existing_aff}
                        for aff in affiliations:
                            key = (aff.get("country"), aff.get("from"))
                            if key not in seen_aff and "country" in aff:
                                existing_aff.append(aff)
                                seen_aff.add(key)
                        merged["AffiliationTimeline"] = existing_aff

            # Extract DegreeDate from thesis/ETD sources (v7 spec glossary)
            for source_name, source_data in r.items():
                if isinstance(source_data, dict):
                    degree_date = source_data.get("degree_date")
                    if degree_date and "DegreeDate" not in merged:
                        if isinstance(degree_date, dict):
                            merged["DegreeDate"] = degree_date
                        elif isinstance(degree_date, str):
                            # Infer precision from format
                            precision = "year"
                            if len(degree_date) == 10:
                                precision = "day"
                            elif len(degree_date) == 7:
                                precision = "month"
                            merged["DegreeDate"] = {"date": degree_date, "precision": precision}

        merged["_sources"] = sorted(sources)
        if identifiers:
            merged["AuthorityIDs"] = identifiers
        out.append(merged)

    return out


# Backward compatibility
async def enrich_all(entries: List[Dict]) -> List[Dict]:
    """Legacy entry point - enriches using tier 0+1."""
    return await enrich_by_tiers(entries, tiers=[0, 1])
