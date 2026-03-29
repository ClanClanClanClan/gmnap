from __future__ import annotations

import logging
import os
from typing import Any, Dict

try:
    import requests  # type: ignore
except Exception:
    requests = None

OFFLINE = os.getenv("OFFLINE", "1") == "1"
logger = logging.getLogger(__name__)


def http_json(url: str, **params):
    if requests is None:
        raise RuntimeError("requests not available")
    r = requests.get(url, params=params, headers={"User-Agent": "gmnap-v7"}, timeout=20)
    r.raise_for_status()
    if "application/json" in r.headers.get("Content-Type", ""):
        return r.json()
    return {"raw": r.text}


class Crossref_Thesis:
    name = "Crossref_Thesis"

    def query(self, author="Gauss"):
        if OFFLINE:
            return {"ok": True, "source": self.name, "offline": True}
        return {
            "ok": True,
            "source": self.name,
            "data": http_json(
                "https://api.crossref.org/works",
                **{"filter": "type:dissertation", "query.author": author, "rows": 1},
            ),
        }


class Wikidata_P184:
    name = "Wikidata_P184"

    def query(self, limit=1):
        if OFFLINE:
            return {"ok": True, "source": self.name, "offline": True}
        import requests

        return {
            "ok": True,
            "source": self.name,
            "data": requests.get(
                "https://query.wikidata.org/sparql",
                params={
                    "query": "SELECT ?p WHERE { ?p wdt:P106 wd:Q170790 . } LIMIT %d"
                    % limit,
                    "format": "json",
                },
                headers={"User-Agent": "gmnap-v7"},
                timeout=30,
            ).json(),
        }


class OAI_University:
    name = "OAI_University"

    def query(self, base=None):
        base = base or os.getenv("OAI_BASE_URL")
        if not base:
            return {"ok": False, "reason": "no_base_url"}
        if OFFLINE:
            return {"ok": True, "source": self.name, "offline": True}
        import requests

        return {
            "ok": True,
            "source": self.name,
            "data": requests.get(base, params={"verb": "Identify"}, timeout=20).text,
        }


class LiveAuthorityAdapters:
    """Collection of live authority adapters."""

    def __init__(self):
        """Initialize live authority adapters."""
        self.crossref_thesis = Crossref_Thesis()
        self.wikidata = Wikidata_P184()
        self.oai_university = OAI_University()

        # Import the new V7 Crossref fetcher if available
        try:
            from .crossref_v7 import CrossrefV7Fetcher

            self.crossref_v7 = CrossrefV7Fetcher()
            logger.info("CrossrefV7Fetcher loaded successfully")
        except ImportError as e:
            self.crossref_v7 = None
            logger.warning(f"Could not load CrossrefV7Fetcher: {e}")

        # Import OpenAlex API if available
        try:
            from .openalex import OpenAlexAPI

            self.openalex = OpenAlexAPI()
            logger.info("OpenAlexAPI loaded successfully")
        except ImportError as e:
            self.openalex = None
            logger.warning(f"Could not load OpenAlexAPI: {e}")

        self.adapters = {
            "Crossref_Thesis": self.crossref_thesis,
            "Wikidata_P184": self.wikidata,
            "OAI_University": self.oai_university,
        }

        if self.crossref_v7:
            self.adapters["Crossref_V7"] = self.crossref_v7

        if self.openalex:
            self.adapters["OpenAlex"] = self.openalex

    def get_adapter(self, name: str):
        """Get adapter by name."""
        return self.adapters.get(name)

    def list_adapters(self):
        """List available adapters."""
        return list(self.adapters.keys())

    def fetch_live_authorities(self, entries: list) -> list:
        """
        Fetch authority data for multiple entries.

        Args:
            entries: List of entries to enrich

        Returns:
            List of enriched entries
        """
        current_offline = os.getenv("OFFLINE", "1") == "1"

        for entry in entries:
            if "AuthoritySources" not in entry:
                entry["AuthoritySources"] = []

            if current_offline:
                # In offline mode, just mark that we tried
                entry["AuthoritySources"].append("Offline")
            else:
                # Try to fetch from Crossref
                try:
                    if self.crossref_thesis:
                        name = entry.get(
                            "CanonicalLatin", entry.get("CanonicalNative", "")
                        )
                        if name:
                            result = self.crossref_thesis.query(author=name)
                            if result.get("ok"):
                                entry["AuthoritySources"].append("Crossref_Thesis")
                                entry["CrossrefData"] = result.get("data", {})
                except Exception as e:
                    logger.warning(f"Failed to fetch from Crossref: {e}")

        return entries

    async def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich an entry using available authority sources.

        Args:
            entry: Entry to enrich with CanonicalLatin name

        Returns:
            Enriched entry with authority data
        """
        # Track which sources were attempted
        if "AuthoritySources" not in entry:
            entry["AuthoritySources"] = []

        # Check OFFLINE status at runtime (not just module load time)
        current_offline = os.getenv("OFFLINE", "1") == "1"

        # Try Crossref V7 if available and not offline
        if self.crossref_v7 and not current_offline:
            try:
                await self.crossref_v7.enrich_entry(entry)
                if "Crossref" not in entry["AuthoritySources"]:
                    entry["AuthoritySources"].append("Crossref")
            except Exception as e:
                logger.warning(f"Crossref V7 enrichment failed: {e}")

        # Try OpenAlex if available and not offline
        if self.openalex and not current_offline:
            try:
                # OpenAlex needs to be used with async context manager
                async with self.openalex as api:
                    entry = await api.enrich_entry(entry)
                    if "OpenAlex" not in entry["AuthoritySources"]:
                        entry["AuthoritySources"].append("OpenAlex")
            except Exception as e:
                logger.warning(f"OpenAlex enrichment failed: {e}")

        # Could add other authority sources here
        return entry


class HAL:
    name = "HAL"

    def query(self, q="thesis"):
        if OFFLINE:
            return {"ok": True, "source": self.name, "offline": True}
        return {
            "ok": True,
            "source": self.name,
            "data": http_json(
                "https://api.archives-ouvertes.fr/search/", q=q, rows=1, fl="docid"
            ),
        }


class GND:
    name = "GND"

    def query(self, base=None, q="Albert Einstein"):
        base = base or os.getenv("GND_SRU_URL")
        if not base:
            return {"ok": False, "reason": "no_base_url"}
        if OFFLINE:
            return {"ok": True, "source": self.name, "offline": True}
        import requests

        return {
            "ok": True,
            "source": self.name,
            "data": requests.get(
                base,
                params={
                    "version": "1.1",
                    "operation": "searchRetrieve",
                    "recordSchema": "PicaPlus-xml",
                    "query": f'any="{q}"',
                    "maximumRecords": 1,
                },
                timeout=20,
            ).text,
        }


class zbMATH_Open:
    name = "zbMATH_Open"

    def query(self, base=None, q="einstein"):
        base = base or os.getenv("ZBMATH_API_URL")
        if not base:
            return {"ok": False, "reason": "no_base_url"}
        if OFFLINE:
            return {"ok": True, "source": self.name, "offline": True}
        import requests

        return {
            "ok": True,
            "source": self.name,
            "data": requests.get(base, params={"q": q}, timeout=20).json(),
        }
