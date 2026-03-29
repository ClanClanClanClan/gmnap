from __future__ import annotations
import os
from typing import List, Dict, Any


async def infer_from_openalex(student: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Optional inference via co-authorship.
    OFF by default. Returns [] unless OPENALEX_INFER=1.
    """
    if os.getenv("OPENALEX_INFER") != "1":
        return []
    # Implement your OpenAlex calls here (omitted in this offline kit).
    return []
