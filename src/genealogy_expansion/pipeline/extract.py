from __future__ import annotations

import re
from typing import Any, Dict, List

import yaml


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


LEX = None
COMMITTEE = None


def init(config_dir: str = "config"):
    global LEX, COMMITTEE
    lex = load_yaml(f"{config_dir}/locales/advisor_lexicons.yml")
    LEX = lex.get("advisor", {})
    COMMITTEE = lex.get("committee", {})


def extract_from_metadata(th: Dict[str, Any], advisor_locale: str) -> Dict[str, Any]:
    return th


def extract_from_text_blob(text: str, advisor_locale: str) -> List[Dict[str, str]]:
    if not text:
        return []
    tokens = LEX.get(advisor_locale, [])
    pattern = "|".join(map(re.escape, tokens)) if tokens else None
    hits = []
    if pattern:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            window = text[max(0, m.start() - 80) : m.end() + 80]
            names = re.findall(r"[A-Z][A-Za-z\-']+(?:\s+[A-Z][A-Za-z\-']+)*", window)
            for n in names[:3]:
                hits.append({"name": n.strip(), "role": "advisor"})
    return hits
