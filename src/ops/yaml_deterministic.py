from __future__ import annotations

import json
from typing import Any, Dict, List

from ruamel.yaml import YAML

_VOLATILE_KEYS = {
    "ProcessedAt",
    "ProcessingLatencyMs",
    "_trace_id",
    "_debug",
    "_meta",
    "_runtime",
    "ETDText",  # raw text not part of canonical output
}

# Arrays whose order is not semantically meaningful → sort deterministically
_SET_ARRAY_FIELDS = {
    "AlternativeLatin",
    "AlternativeNative",
    "Institution",
    "Advisors",
    "Students",
    "Collaborators",
    "Publications",
    "Subfield",
    "Awards",
}


def scrub_volatiles(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in entry.items() if k not in _VOLATILE_KEYS}


def _sort_key_for_value(v: Any) -> str:
    try:
        if isinstance(v, (int, float)):
            return f"#{v}"
        if isinstance(v, str):
            return v
        return json.dumps(v, sort_keys=True, ensure_ascii=False)
    except Exception:
        return str(v)


def canonicalise_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Return a deep‑copy with sorted keys and set‑arrays deterministically ordered."""
    e = scrub_volatiles(dict(entry))

    def canon(o, parent_key: str | None = None):
        if isinstance(o, dict):
            # Sort keys lexicographically to enforce byte‑stable ordering
            return {k: canon(o[k], k) for k in sorted(o.keys())}
        if isinstance(o, list):
            items = [canon(x, parent_key) for x in o]
            if parent_key in _SET_ARRAY_FIELDS:
                try:
                    return sorted(items, key=_sort_key_for_value)
                except Exception:
                    return items
            return items
        if isinstance(o, str):
            # Normalise line endings and escape hard tabs (YAML ambiguity)
            s = o.replace("\r\n", "\n").replace("\r", "\n")
            return s
        return o

    return canon(e)


def to_canonical_bytes(batch: List[Dict[str, Any]]) -> bytes:
    """Stable bytes for idempotency / diff, with per‑entry canonicalisation and batch sort."""
    canon = [canonicalise_entry(e) for e in batch]
    canon_sorted = sorted(
        canon, key=lambda e: (e.get("GlobalID", ""), e.get("Source", ""))
    )
    return json.dumps(
        canon_sorted, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def dump_yaml_deterministic(data: Any) -> str:
    """Dump YAML with stable formatting (no anchors, fixed indentation, sorted keys assumed)."""
    y = YAML()
    y.indent(mapping=2, sequence=2, offset=0)
    y.explicit_start = False
    y.default_flow_style = False
    y.allow_unicode = True
    y.width = 1000000  # avoid line wrapping to keep diffs simple
    from io import StringIO

    buf = StringIO()
    y.dump(data, buf)
    text = buf.getvalue()
    # Ensure trailing newline
    if not text.endswith("\n"):
        text += "\n"
    return text
