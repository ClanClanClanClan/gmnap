from __future__ import annotations
from typing import Any, Dict


def map_oai_dc_xml(xml_txt: str, country: str, source_name: str) -> Dict[str, Any]:
    # Placeholder mapper: keep raw; extraction will handle roles if needed later.
    return {
        "title": None,
        "degree_type": None,
        "discipline": "Mathematics",
        "author_name": None,
        "author_birth_year": None,
        "defense_date": None,
        "institution": None,
        "country": country,
        "advisors": [],
        "committee": [],
        "pdf_url": None,
        "source_id": None,
        "source_name": source_name,
        "raw": {"_raw_xml": xml_txt},
    }
