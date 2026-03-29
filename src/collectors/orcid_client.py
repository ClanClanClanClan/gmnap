"""
collectors/orcid_client.py
Guard against None and implement respectful backoff.
"""

import time, requests
from typing import Optional, Dict, Any

BASE = "https://pub.orcid.org/v3.0"


class Orcid:
    def __init__(self, max_per_sec: float = 3.0):
        self.s = requests.Session()
        self.s.headers.update({"Accept": "application/json"})
        self.delay = 1.0 / max_per_sec

    def get_person(self, orcid_id: str) -> Optional[Dict[str, Any]]:
        time.sleep(self.delay)
        r = self.s.get(f"{BASE}/{orcid_id}/person", timeout=30)
        if r.status_code == 429:
            retry = int(r.headers.get("Retry-After", "2"))
            time.sleep(max(2, retry))
            return self.get_person(orcid_id)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        name = data.get("name") or {}
        given = (name.get("given-names") or {}).get("value") or ""
        family = (name.get("family-name") or {}).get("value") or ""
        return {"given": given, "family": family, "raw": data}
