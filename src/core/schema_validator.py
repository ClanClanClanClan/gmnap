from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from jsonschema import Draft202012Validator  # type: ignore
except Exception:  # pragma: no cover
    Draft202012Validator = None  # lazy optional

# V7 specification (required keys and a pragmatic, strict-enough validator).
V7_REQUIRED = [
    "GlobalID",
    "CanonicalLatin",
    "Field",
    "Source",
    "LastUpdated",
    "ValidationStatus",
]

# Types accepted for known fields (conservative where spec is open-ended).
V7_FIELD_TYPES: Dict[str, Union[type, tuple]] = {
    "GlobalID": str,
    "CanonicalLatin": str,
    "CanonicalNative": str,
    "AlternativeLatin": list,
    "AlternativeNative": list,
    "BirthYear": int,
    "DeathYear": int,
    "Gender": str,
    "Nationality": str,
    "Field": str,  # MSC label string per spec; schema checks structure elsewhere
    "Subfield": list,  # List of MSC codes/objects
    "Institution": list,
    "Advisors": list,
    "Students": list,
    "Collaborators": list,
    "Awards": list,
    "Publications": list,
    "Source": str,
    "SourceID": (str, int),
    "LastUpdated": str,
    "ValidationStatus": str,
}


# Predicate constraints (range/enumerations/patterns).
def _is_iso8601(ts: str) -> bool:
    try:
        # Accept 'Z' suffix as UTC
        datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return True
    except Exception:
        return False


V7_CONSTRAINTS = {
    "BirthYear": lambda x: isinstance(x, int) and -2000 <= x <= 2100,
    "DeathYear": lambda x: isinstance(x, int) and -2000 <= x <= 2100,
    "Nationality": lambda x: isinstance(x, str) and bool(re.fullmatch(r"[A-Z]{2}", x)),
    "Gender": lambda x: x
    in {"M", "F", "X", "U", "male", "female", "nonbinary", "unspecified"},
    "ValidationStatus": lambda x: x in {"verified", "pending", "disputed"},
    "LastUpdated": _is_iso8601,
}

VOLATILE_KEYS = {"ProcessedAt", "ProcessingLatencyMs", "_debug", "_trace_id", "_meta"}


class CoreV7SchemaValidator:
    """
    Strict, defensive validator matching the V7 spec expectations.
    Optionally augments validation using a JSON‑Schema if provided.
    """

    def __init__(self, json_schema: Optional[Dict[str, Any]] = None) -> None:
        self.json_schema = json_schema
        if json_schema and Draft202012Validator is not None:
            self._json_validator = Draft202012Validator(json_schema)
        else:
            self._json_validator = None

    def validate(self, entry: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        # Required fields
        for f in V7_REQUIRED:
            if f not in entry:
                errors.append(f"Missing required field: {f}")

        # Types
        for k, v in entry.items():
            if k in V7_FIELD_TYPES:
                typ = V7_FIELD_TYPES[k]
                if isinstance(typ, tuple):
                    if not isinstance(v, typ):
                        errors.append(f"{k} must be one of {[t.__name__ for t in typ]}")
                else:
                    if not isinstance(v, typ):
                        errors.append(f"{k} must be {typ.__name__}")

        # Constraints
        for k, pred in V7_CONSTRAINTS.items():
            if k in entry and entry[k] is not None:
                try:
                    if not pred(entry[k]):
                        errors.append(f"{k} fails constraint check")
                except Exception:
                    errors.append(f"{k} fails constraint check")

        # Optional JSON‑Schema deep validation
        if self._json_validator is not None:
            for e in self._json_validator.iter_errors(entry):  # type: ignore[attr-defined]
                errors.append(f"JSONSchema: {e.message}")

        return (len(errors) == 0, errors)

    @classmethod
    def load_default_schema(
        cls, path: str = "schemas/v7_entry.schema.json"
    ) -> "V7SchemaValidator":
        try:
            with open(path, "r", encoding="utf-8") as f:
                schema = json.load(f)
        except FileNotFoundError:
            schema = None
        return cls(schema)
