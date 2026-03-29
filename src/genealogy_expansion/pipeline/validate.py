from __future__ import annotations
from typing import Dict, Any


def temporal_validate(edge: Dict[str, Any]) -> Dict[str, Any]:
    issues = []
    dd = edge.get("degree_date")
    if dd and len(str(dd)) < 4:
        issues.append("bad_degree_date")
    edge["_issues"] = issues
    return edge
