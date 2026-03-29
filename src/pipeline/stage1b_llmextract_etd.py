from __future__ import annotations

import json
import os
import pathlib
import re
from typing import Any, Dict, Tuple

import yaml
from jsonschema import Draft202012Validator

CACHE_DIR = os.getenv("GMNAP_ETD_CACHE_DIR", "cache/etd")


def _load_etd_schema(spec_paths=("specs_v7.yaml", "v7.0.yaml")) -> Dict[str, Any]:
    for p in spec_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data.get("llm_extract", {}).get("json_schema_inline", {})
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ETD‑LLM‑Output",
        "type": "object",
        "required": ["title", "authors", "advisors", "degree_date", "institution"],
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string", "minLength": 2},
            "authors": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "advisors": {"type": "array", "items": {"type": "string"}, "minItems": 1},
            "degree_date": {"type": "string", "pattern": "^[0-9]{4}(-[0-9]{2}){0,2}$"},
            "degree": {"type": "string"},
            "institution": {"type": "string"},
            "language": {"type": "string", "maxLength": 16},
        },
    }


def _cache_key(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _ensure_cache() -> pathlib.Path:
    p = pathlib.Path(CACHE_DIR)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _validate(payload: Dict[str, Any]) -> Tuple[bool, str]:
    schema = _load_etd_schema()
    v = Draft202012Validator(schema)
    errs = list(v.iter_errors(payload))
    if errs:
        return False, errs[0].message
    return True, ""


def extract_from_text(text: str) -> Dict[str, Any]:
    key = _cache_key(text)
    cache = _ensure_cache() / f"{key}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))

    def find(pattern, default=""):
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else default

    title = find(r"^title:\s*(.+)$") or find(r"^thesis title[:\-]\s*(.+)$") or ""
    a_line = find(r"^author[s]?:\s*(.+)$")
    authors = [a.strip() for a in a_line.split(",")] if a_line else []
    adv_line = find(r"^advisor[s]?:\s*(.+)$")
    advisors = [x.strip() for x in adv_line.split(",")] if adv_line else []
    degree_date = find(r"^degree date[:\-]\s*([0-9]{4}(?:-[0-9]{2}){0,2})$") or find(
        r"^year[:\-]\s*([0-9]{4})$"
    )
    institution = find(r"^institution[:\-]\s*(.+)$") or find(
        r"^university[:\-]\s*(.+)$"
    )

    payload = {
        "title": title,
        "authors": authors,
        "advisors": advisors,
        "degree_date": degree_date or "",
        "institution": institution or "",
    }
    ok, err = _validate(payload)
    if not ok:
        raise ValueError(f"ETD extract invalid: {err}")
    cache.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload
