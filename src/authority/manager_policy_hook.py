
from __future__ import annotations
from typing import Dict, Any
from .merge_authority_data import merge_authority_fragments
from .policy import ConflictPolicy

def merge_all(fragments: list[Dict[str, Any]]) -> Dict[str, Any]:
    return merge_authority_fragments(fragments, ConflictPolicy.load())
