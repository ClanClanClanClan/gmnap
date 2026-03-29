from __future__ import annotations

import os

try:
    import requests  # type: ignore
except Exception:
    requests = None

OFFLINE = os.getenv("OFFLINE", "1") == "1"
FORCE_EXTREME = os.getenv("FORCE_EXTREME", "0") == "1"


def _require_extreme_and(env_key: str | None = None, expected: str | None = None):
    if not FORCE_EXTREME:
        return False, "FORCE_EXTREME=0"
    if env_key and expected is not None and os.getenv(env_key) != expected:
        return False, f"{env_key} must be '{expected}'"
    return True, ""


class BaseExtreme:
    name = "ExtremeBase"

    def _offline(self):
        return {"ok": True, "source": self.name, "offline": True}


class MathSciNet_HTML(BaseExtreme):
    name = "MathSciNet_HTML"

    def query(self, q: str = "einstein"):
        ok, why = _require_extreme_and()
        if not ok:
            return {"ok": False, "reason": why}
        if OFFLINE:
            return self._offline()
        return {"ok": True, "source": self.name, "data": "<html>MathSciNet</html>"}


class Scopus(BaseExtreme):
    name = "Scopus"

    def query(self, api_key_env="SCOPUS_API_KEY", q: str = "einstein"):
        ok, why = _require_extreme_and()
        if not ok:
            return {"ok": False, "reason": why}
        if OFFLINE:
            return self._offline()
        api_key = os.getenv(api_key_env)
        if not api_key:
            return {"ok": False, "reason": "no_api_key"}
        return {
            "ok": True,
            "source": self.name,
            "data": {"search-results": {"entry": []}},
        }


class Dimensions(BaseExtreme):
    name = "Dimensions"

    def query(self, token_env="DIMENSIONS_TOKEN", q="einstein"):
        ok, why = _require_extreme_and()
        if not ok:
            return {"ok": False, "reason": why}
        if OFFLINE:
            return self._offline()
        tok = os.getenv(token_env)
        if not tok:
            return {"ok": False, "reason": "no_token"}
        return {"ok": True, "source": self.name, "data": {"docs": []}}


class ProQuest_ETD(BaseExtreme):
    name = "ProQuest_ETD"

    def query(self, accept_env="PROQUEST_ACCEPT", q="thesis"):
        ok, why = _require_extreme_and(accept_env, "yes")
        if not ok:
            return {"ok": False, "reason": why}
        if OFFLINE:
            return self._offline()
        return {"ok": True, "source": self.name, "data": {"status": "ok"}}


class Google_Scholar(BaseExtreme):
    name = "Google_Scholar"

    def query(self, accept_env="YES_I_ACCEPT_GS_TOS"):
        ok, why = _require_extreme_and(accept_env, "yes")
        if not ok:
            return {"ok": False, "reason": why}
        if OFFLINE:
            return self._offline()
        return {"ok": True, "source": self.name, "data": {"gs_cache_hit": True}}
