from __future__ import annotations

from typing import Any, Dict


def shadow_node(global_id: str) -> Dict[str, Any]:
    return {
        "GlobalID": global_id,
        "CanonicalLatin": "GDPR-ERASED",
        "Field": "Mathematics",
        "Source": "GDPR",
        "LastUpdated": "1970-01-01T00:00:00Z",
        "ValidationStatus": "verified",
        "GDPR": True,
    }
