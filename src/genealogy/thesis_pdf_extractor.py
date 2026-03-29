from __future__ import annotations
from typing import Dict, Any


def extract_from_pdf(path: str) -> Dict[str, Any]:
    """Placeholder PDF extractor (LLM or regex). Returns empty structure in this kit."""
    return {
        "title": None,
        "authors": [],
        "advisors": [],
        "committee": [],
        "degree_date": None,
        "institution": None,
        "department": None,
    }
