from __future__ import annotations
import os
from typing import Dict, Any
from urllib.parse import urlencode
from .common import AuthorityContext, canonical_query_key


class ORCIDETDAdapter:
    """ORCID public API — expanded search for mathematician profiles.

    Free, no auth required. 100K/day quota.
    Endpoint: pub.orcid.org/v3.0/expanded-search/
    Returns: ORCID iD, affiliations, works count.
    """

    name = "ORCID_ETD"

    def __init__(self, cfg: Dict[str, Any] = None):
        base = (cfg or {}).get("base_url", "https://pub.orcid.org/v3.0")
        self.ctx = AuthorityContext(self.name, base, rps=6, burst=6, cache_ttl=86400)

    async def enrich(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        name = entry.get("CanonicalLatin", "")
        if not name:
            return {"_source": {"service": self.name, "hit": False}}
        if os.getenv("GMNAP_NO_NETWORK", "") == "1":
            return {"_source": {"service": self.name, "hit": False}}
        # Build ORCID expanded-search query
        if "," in name:
            parts = name.split(",", 1)
            family = parts[0].strip()
            given = parts[1].strip()
            q = {"q": f"family-name:{family} AND given-names:{given}"}
        else:
            q = {"q": name}
        key = canonical_query_key({"svc": self.name, "q": q})
        c = await self.ctx.cache.get_json(key)
        if c is not None:
            return c
        await self.ctx.limiter.acquire()
        url = f"{self.ctx.base_url}/expanded-search/?{urlencode(q)}"
        out = {"_source": {"service": self.name, "url": url}}
        try:
            if self.ctx.http:
                r = await self.ctx.http.get(
                    url,
                    timeout=15.0,
                    headers={"Accept": "application/json"},
                )
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("expanded-result") or []
                    if results:
                        rec = results[0]
                        orcid_id = rec.get("orcid-id", "")
                        if orcid_id:
                            out["ORCID"] = orcid_id
                        # Extract institution from affiliations
                        institutions = rec.get("institution-name") or []
                        if institutions:
                            out["Institution"] = institutions[0]
                            out["_InstitutionAll"] = institutions[:5]
                        out["_source"]["hit"] = True
                        # Optional: fetch education details for DegreeDate
                        if orcid_id and os.getenv("ORCID_FETCH_EDUCATIONS", "") == "1":
                            try:
                                edu_url = f"https://pub.orcid.org/v3.0/{orcid_id}/educations"
                                edu_r = await self.ctx.http.get(
                                    edu_url,
                                    timeout=10.0,
                                    headers={"Accept": "application/json"},
                                )
                                if edu_r.status_code == 200:
                                    groups = edu_r.json().get("affiliation-group", [])
                                    for g in groups:
                                        for s in g.get("summaries", []):
                                            ed = s.get("education-summary", {})
                                            end_date = ed.get("end-date")
                                            if end_date and end_date.get("year"):
                                                out["DegreeDate"] = {
                                                    "date": end_date["year"]["value"],
                                                    "precision": "year",
                                                }
                                                break
                                        if "DegreeDate" in out:
                                            break
                            except Exception:
                                pass  # Education fetch is optional
        except Exception:
            pass
        await self.ctx.cache.set_json(key, out)
        return out
