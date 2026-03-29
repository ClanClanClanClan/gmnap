from __future__ import annotations
from typing import Dict, Any, Tuple, List
import datetime


def build_draft_doi(
    run_hash: str,
    specs: Dict[str, Any],
    metrics: Dict[str, Any] | None = None,
    subjects: List[str] | None = None,
    snapshot_url: str | None = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Construct a DataCite JSON-API payload for a **draft** DOI registration.
    Returns (doi_string, payload_as_dict). Does not perform any network call.
    """
    doi_conf = (specs or {}).get("doi_minting", {}) if isinstance(specs, dict) else {}
    shoulder = doi_conf.get("shoulder", "10.3929/ethz-lineage")
    doi = f"{shoulder}/{run_hash}"
    publication_year = int(datetime.datetime.utcnow().strftime("%Y"))
    publisher = "ETH Zürich"
    title = f"MathLineage Snapshot {run_hash}"
    creators = [{"name": "MathLineage Project"}]

    # Convert subjects into DataCite 'subjects' list if present
    subjects_attr = [{"subject": s} for s in (subjects or [])]

    description_lines = [f"MathLineage snapshot {run_hash}."]
    if metrics:
        for k, v in metrics.items():
            try:
                description_lines.append(f"{k}: {v}")
            except Exception:
                pass
    description = "\n".join(description_lines)

    attributes = {
        "doi": doi,
        "event": "draft",
        "titles": [{"title": title}],
        "creators": creators,
        "publisher": publisher,
        "publicationYear": publication_year,
        "types": {
            "resourceTypeGeneral": "Dataset",
            "resourceType": "Genealogy Snapshot",
        },
        "subjects": subjects_attr,
        "descriptions": [{"description": description, "descriptionType": "Abstract"}],
        "url": snapshot_url or f"https://example.invalid/lineage/snapshots/{run_hash}",
        "schemaVersion": "http://datacite.org/schema/kernel-4",
    }
    payload = {"data": {"type": "dois", "attributes": attributes}}
    return doi, payload
