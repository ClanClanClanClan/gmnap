from __future__ import annotations
from typing import Any, List, Tuple


def _as_list(x: Any) -> List[dict]:
    if isinstance(x, list):
        out: List[dict] = []
        for itm in x:
            if isinstance(itm, dict):
                out.append(itm)
            else:
                out.append({"status": "processing_error", "error": str(itm)})
        return out
    return [
        {
            "status": "processing_error",
            "error": f"Unexpected result type: {type(x).__name__}",
        }
    ]


def normalize_result(res: Any) -> Tuple[List[dict], dict]:
    if isinstance(res, tuple) and len(res) == 2 and isinstance(res[1], dict):
        return _as_list(res[0]), res[1]
    if isinstance(res, dict):
        metrics = res.get("metrics") or {}
        for key in ("entries", "results", "data"):
            if key in res and isinstance(res[key], list):
                return _as_list(res[key]), metrics
        if any(k in res for k in ("GlobalID", "status", "CanonicalNative")):
            return [res], metrics
        return [
            {"status": "processing_error", "error": "Malformed result dict"}
        ], metrics
    if isinstance(res, list):
        return _as_list(res), {}
    return [{"status": "processing_error", "error": str(res)}], {}
