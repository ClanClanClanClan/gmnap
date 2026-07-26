"""
GND authority source (Tier 1).

GND (Gemeinsame Normdatei) is the German National Library's authority file:
CC0, keyless, and unusually rich for HISTORICAL scholars — birth/death dates
AND places, academic degree, name variants, and sameAs links to VIAF/BnF/LoC.
That matters here because the highest-descendant root nodes of this genealogy
are overwhelmingly 19th-century German mathematicians (Kummer, Weierstraß,
Klein, Schwarz, Fuchs, Schmidt, Lindemann).

R66 — THIS FETCHER WAS STRUCTURALLY DEAD and documented as "✅ WORKING". It
delegated to ``UniversalFetcher("GND", ...)``, but "GND" is absent from
``AUTHORITY_CONFIGS``, so the lookup silently returned ``{}``, ``api_type``
fell back to ``"REST"``, and ``_fetch_rest`` hit its else-branch returning
``PARSE_ERROR: Unsupported authority: GND`` — BEFORE opening a socket. Every
call resolved to ``hit: False``.

It is now implemented natively against ``src.authorities.base`` rather than
via the template, for two reasons:
  1. ``templates/authority_engine.py`` does ``sys.path.insert`` + ``from
     authorities.base import ...``, registering a SECOND copy of the base
     module. Its ``FetchResult``/``FetchStatus`` are therefore DIFFERENT class
     objects from the ones the orchestrator builds — the orchestrator only
     survives this because it is duck-typed. Any ``isinstance`` check would
     silently fail. Going native avoids that trap entirely.
  2. The template's generic parser would discard exactly the fields that make
     GND worth having (dates, places, degree, variants).

Licence: CC0. Endpoint: lobid.org (keyless, no auth header).
"""

import logging
import re
from typing import Any, Dict, List, Optional

from src.authorities.base import (
    AuthorityData,
    AuthorityFetcher,
    AuthorityTier,
    FetchResult,
    FetchStatus,
)

logger = logging.getLogger(__name__)


def _year(value: Any) -> Optional[int]:
    """First 4-digit year from a GND date, which may be partial or a range.

    GND emits "1862-01-23", "1862-01", "1862", and occasionally ranges — so a
    bare ``int(v[:4])`` raises on real data.
    """
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, str):
        return None
    m = re.search(r"(\d{4})", value)
    return int(m.group(1)) if m else None


def _labels(entries: Any) -> List[str]:
    """GND returns [{'id':..., 'label':...}] for place/occupation fields."""
    out: List[str] = []
    for e in entries or []:
        if isinstance(e, dict) and e.get("label"):
            out.append(e["label"])
        elif isinstance(e, str):
            out.append(e)
    return out


class GNDFetcher(AuthorityFetcher):
    """GND authority source fetcher (native lobid implementation)."""

    SEARCH_URL = "https://lobid.org/gnd/search"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config or {})
        self.service = "GND"
        self.tier = AuthorityTier.TIER_1
        self.daily_quota = 100000  # CC0, no published cap; be polite anyway
        self.base_url = "https://lobid.org/gnd/"
        self.requires_auth = False
        self._min_request_interval = 0.2

    async def fetch_by_gnd_id(self, gnd_id: str) -> FetchResult:
        """Look a person up by GND IDENTIFIER — the only high-precision path.

        Prefer this over ``fetch()``. Wikidata's **P227** carries the GND ID,
        so for any person we already hold a QID for we can resolve GND exactly
        instead of guessing from a name. See the precision warning on
        ``fetch()``.
        """
        if not gnd_id or not gnd_id.strip():
            return FetchResult(
                status=FetchStatus.NOT_FOUND, error_message="empty gnd_id"
            )
        try:
            session = await self.get_session()
            url = f"https://lobid.org/gnd/{gnd_id.strip()}.json"
            async with session.get(url) as response:
                if response.status == 404:
                    return FetchResult(status=FetchStatus.NOT_FOUND)
                if response.status == 429:
                    return FetchResult(status=FetchStatus.RATE_LIMITED)
                if response.status != 200:
                    return FetchResult(
                        status=FetchStatus.NETWORK_ERROR,
                        error_message=f"HTTP {response.status}",
                    )
                payload = await response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("GND id fetch failed for %r: %s", gnd_id, exc)
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(exc))
        if not payload or not payload.get("gndIdentifier"):
            return FetchResult(status=FetchStatus.NOT_FOUND)
        return FetchResult(
            status=FetchStatus.SUCCESS, data=self.parse_response(payload)
        )

    async def fetch(self, query: str) -> FetchResult:
        """Search GND by NAME. LOW PRECISION — do not enrich silently from it.

        MEASURED (R66, live lobid): on three of this graph's highest-descendant
        root nodes, the top hit was the WRONG PERSON twice:
            "Kummer, Ernst Eduard" -> b.1847 d.1923   (真 Kummer: 1810-1893)
            "Klein, Felix"         -> b.1887, no death (真 Klein: 1849-1925)
            "Weierstrass, Karl"    -> b.1815 d.1897    correct
        A name is not an identity: GND holds many people per common German
        surname, and the search ranks by relevance, not by "is this the
        mathematician". Writing these dates into the graph would corrupt
        precisely the roots that anchor thousands of descendants.

        So this method is for DISCOVERY and manual adjudication only. For
        enrichment use ``fetch_by_gnd_id`` with the GND ID from Wikidata P227.
        A caller that must use a name should corroborate the returned dates
        against something it already knows before accepting them.
        """
        if not query or not query.strip():
            return FetchResult(
                status=FetchStatus.NOT_FOUND, error_message="empty query"
            )
        params = {
            "q": query.strip(),
            # DifferentiatedPerson = an identified individual (as opposed to an
            # undifferentiated name shared by several people) — the only kind
            # that can safely carry dates onto ONE person.
            "filter": "type:DifferentiatedPerson",
            "format": "json",
            "size": "1",
        }
        try:
            session = await self.get_session()
            async with session.get(self.SEARCH_URL, params=params) as response:
                if response.status == 404:
                    return FetchResult(status=FetchStatus.NOT_FOUND)
                if response.status == 429:
                    return FetchResult(status=FetchStatus.RATE_LIMITED)
                if response.status != 200:
                    return FetchResult(
                        status=FetchStatus.NETWORK_ERROR,
                        error_message=f"HTTP {response.status}",
                    )
                payload = await response.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("GND fetch failed for %r: %s", query, exc)
            return FetchResult(status=FetchStatus.NETWORK_ERROR, error_message=str(exc))

        members = payload.get("member") or []
        if not payload.get("totalItems") or not members:
            return FetchResult(status=FetchStatus.NOT_FOUND)
        return FetchResult(
            status=FetchStatus.SUCCESS, data=self.parse_response(members[0])
        )

    def parse_response(self, response: Dict[str, Any]) -> AuthorityData:
        """Map one lobid GND member record to AuthorityData."""
        gnd_id = response.get("gndIdentifier") or ""
        identifiers: Dict[str, str] = {}
        if gnd_id:
            identifiers["GND"] = gnd_id
        # sameAs carries VIAF / BnF / LoC — free cross-authority identity, and
        # the reason we can take VIAF ids without touching VIAF (which blocks
        # automated clients and whose dumps are frozen).
        for same in response.get("sameAs") or []:
            if not isinstance(same, dict):
                continue
            coll = (same.get("collection") or {}).get("abbr") or (
                same.get("collection") or {}
            ).get("name")
            if coll and same.get("id"):
                identifiers.setdefault(str(coll), str(same["id"]))

        metadata: Dict[str, Any] = {}
        for key, src in (
            ("academic_degree", response.get("academicDegree")),
            ("place_of_birth", _labels(response.get("placeOfBirth"))),
            ("place_of_death", _labels(response.get("placeOfDeath"))),
            ("occupation", _labels(response.get("professionOrOccupation"))),
        ):
            if src:
                metadata[key] = src

        return AuthorityData(
            source="GND",
            source_id=gnd_id,
            canonical_name=response.get("preferredName"),
            name_variants=[
                v for v in (response.get("variantName") or []) if isinstance(v, str)
            ],
            identifiers=identifiers,
            birth_year=_year(response.get("dateOfBirth")),
            death_year=_year(response.get("dateOfDeath")),
            metadata=metadata,
        )

    def calculate_confidence(self, data: AuthorityData) -> float:
        """GND is a curated national authority file — high floor, and each
        corroborating field nudges it up."""
        score = 0.7
        if data.birth_year:
            score += 0.1
        if data.death_year:
            score += 0.05
        if data.identifiers.get("GND"):
            score += 0.1
        return min(score, 1.0)
