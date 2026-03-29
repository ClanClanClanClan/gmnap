from __future__ import annotations
from typing import Dict, Any, Tuple, List


class V7SchemaValidator:
    REQUIRED = ["GlobalID", "CanonicalLatin", "Field", "Source", "LastUpdated", "ValidationStatus"]
    ENUMS = {
        "Gender": {"M", "F", "X", "U"},
        "ValidationStatus": {"verified", "pending", "disputed"},
    }
    INT_BOUNDS = {"BirthYear": (-2000, 2100), "DeathYear": (-2000, 2100)}
    TYPES = {
        "GlobalID": str,
        "CanonicalLatin": str,
        "CanonicalNative": str,
        "AlternativeLatin": list,
        "AlternativeNative": list,
        "BirthYear": int,
        "DeathYear": int,
        "Gender": str,
        "Nationality": str,
        "Field": str,
        "Subfield": list,
        "Institution": list,
        "Advisors": list,
        "Students": list,
        "Collaborators": list,
        "Awards": list,
        "Publications": list,
        "Source": str,
        "SourceID": (str, int, type(None)),
        "LastUpdated": str,
        "ValidationStatus": str,
    }

    def validate(self, entry: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errs: List[str] = []
        if not isinstance(entry, dict):
            return False, ["Entry must be an object"]
        for f in self.REQUIRED:
            if f not in entry:
                errs.append(f"Missing required field: {f}")
        for k, v in entry.items():
            T = self.TYPES.get(k)
            if T and not isinstance(v, T if isinstance(T, type) else T):
                errs.append(f"{k} must be {T if isinstance(T, type) else [t.__name__ for t in T]}")
        for k, (lo, hi) in self.INT_BOUNDS.items():
            if k in entry:
                val = entry[k]
                # Check if it's an integer first
                if not isinstance(val, int):
                    if not isinstance(val, (int, float)) or val != int(val):
                        continue  # Type error will be caught above
                    val = int(val)
                if not (lo <= val <= hi):
                    errs.append(f"{k} out of bounds [{lo},{hi}]")
        for k, allowed in self.ENUMS.items():
            if k in entry and entry[k] not in allowed:
                errs.append(f"{k} not in {sorted(allowed)}")
        return (len(errs) == 0), errs
