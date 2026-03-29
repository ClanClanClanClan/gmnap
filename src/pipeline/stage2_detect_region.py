from __future__ import annotations
from typing import Dict, Tuple
from ..regions.script_detect import primary_script

# Minimal deterministic mapping based on script – refined later by overlays/affiliations.
_SCRIPT_TO_REGION = {
    "Cyrillic": "B1",
    "Greek": "B3",
    "Han": "E1",
    "Hangul": "E4",
    "Arabic": "C3",
    "Hebrew": "C6",
    "Devanagari": "D1",
    "Thai": "E6",
    "Khmer": "E6",
    "Lao": "E6",
    "Georgian": "C8",
    "Armenian": "C7",
    "Latin": "A2",  # default Western Europe; refined by overlays later
}


def detect_region(entry: Dict) -> Tuple[str, str]:
    """
    Return (region_code, script) based on CanonicalNative or CanonicalLatin.
    This is a Stage 2 starter; later overlays (affiliations, DOI prefixes) refine the decision.
    """
    name = entry.get("CanonicalNative") or entry.get("CanonicalLatin") or ""
    script = primary_script(name)
    return _SCRIPT_TO_REGION.get(script, "R0"), script


def stage2_detect_region(*args, **kwargs):
    """Stub for stage2_detect_region"""
    pass
