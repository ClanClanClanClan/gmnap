from __future__ import annotations

import re
from typing import Any, Dict

import yaml


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


ALIASES = None
DEGREES = None


def init(config_dir: str = "config"):
    global ALIASES, DEGREES
    ALIASES = load_yaml(f"{config_dir}/locales/institution_aliases.yml")["aliases"]
    DEGREES = load_yaml(f"{config_dir}/locales/degree_lexicons.yml")


def canon_institution(name: str) -> str:
    if not name:
        return None
    for canon, variants in ALIASES.items():
        if name == canon or name in variants:
            return canon
    return name


def norm_degree(raw: str) -> str:
    if not raw:
        return None
    raw_l = raw.lower()
    for k, vals in DEGREES.items():
        if isinstance(vals, list):
            for v in vals:
                if v.lower() in raw_l:
                    return "PhD" if k == "PhD" else v
    return raw


def canon_person(name: str) -> str:
    if not name:
        return None
    parts = re.split(r"\s+", name.strip())
    if len(parts) == 1:
        return parts[0]
    return f"{parts[-1]}, {' '.join(parts[:-1])}"


def normalize_thesis(th: Dict[str, Any]) -> Dict[str, Any]:
    th = dict(th)
    th["institution"] = canon_institution(th.get("institution"))
    th["degree_type"] = norm_degree(th.get("degree_type") or "")
    th["author_name"] = canon_person(th.get("author_name"))
    for a in th.get("advisors", []):
        a["name"] = canon_person(a.get("name"))
    for c in th.get("committee", []):
        c["name"] = canon_person(c.get("name"))
    return th
