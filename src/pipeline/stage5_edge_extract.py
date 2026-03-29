from __future__ import annotations

from typing import Any, Dict, List


def extract_edges_from_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stage 5: Extract genealogy edges (student -> advisor).

    Returns list of edges with the schema:
      {source_id, target_name_or_id, relation_type, degree_date, institution, confidence, sources}
    The target_id may be unknown at this stage; graph loader will try to resolve by name.
    """
    edges: List[Dict[str, Any]] = []
    for e in entries:
        sid = e.get("GlobalID")
        if not sid:
            continue
        for adv in e.get("Advisors", []) or []:
            edges.append(
                {
                    "source_id": sid,
                    "target_id": adv.get("advisor_id"),  # can be None
                    "target_name": adv.get("advisor_name"),
                    "relation_type": adv.get("relation_type", "doctoralAdvisor"),
                    "degree_date": adv.get("degree_date"),
                    "institution": adv.get("institution"),
                    "confidence": float(adv.get("confidence", 0.90)),
                    "sources": adv.get("sources", []),
                    "target_birth_year": adv.get("birth_year"),
                }
            )
    return edges
