from __future__ import annotations
import os

try:
    import requests
except Exception:
    requests = None

OFFLINE = os.getenv("OFFLINE", "1") == "1"


def http_json(url: str, **params):
    if requests is None:
        raise RuntimeError("requests not available")
    r = requests.get(
        url, params=params, headers={"User-Agent": "gmnap-omega-bayes"}, timeout=20
    )
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
                headers={"User-Agent": "gmnap-omega-bayes"},
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
