from __future__ import annotations
from typing import Dict, List, Tuple

REQUIRED = ["GlobalID","CanonicalLatin","Field","Source","LastUpdated","ValidationStatus"]

def validate_entry(entry: Dict) -> Tuple[bool, List[str]]:
    errors = []
    for k in REQUIRED:
        if k not in entry:
            errors.append(f"Missing required field: {k}")
    # Simple type checks
    if "BirthYear" in entry and not isinstance(entry["BirthYear"], int):
        errors.append("BirthYear must be int")
    if "ValidationStatus" in entry and entry["ValidationStatus"] not in {"verified","pending","disputed"}:
        errors.append("ValidationStatus must be one of verified|pending|disputed")
    return (len(errors)==0), errors
