"""
collectors/openalex_client.py
OpenAlex client with polite identification and mailto param.
Docs: https://docs.openalex.org/how-to-use-the-api/rate-limits-and-authentication
"""

import time, requests
from typing import Dict, Any, Optional


class OpenAlex:
    def __init__(self, email: str, max_per_sec: float = 5.0):
        self.email = email
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": f"GMNAP/1.0 (mailto:{email})"})
        self.delay = 1.0 / max_per_sec

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        params = dict(params or {})
        # Add `mailto` per documentation
        params.setdefault("mailto", self.email)
        time.sleep(self.delay)
        r = self.session.get(f"https://api.openalex.org{path}", params=params, timeout=30)
        if r.status_code == 429:
            # Backoff on rate limit
            retry = int(r.headers.get("Retry-After", "2"))
            time.sleep(max(2, retry))
            return self.get(path, params)
        r.raise_for_status()
        return r


# Example:
# client = OpenAlex(email="you@example.org")
# resp = client.get("/authors", {"filter": "last_known_institution.country_code:US"})
# data = resp.json()
