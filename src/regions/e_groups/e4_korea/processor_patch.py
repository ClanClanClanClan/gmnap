from __future__ import annotations
from .korean_v7_profile import KoreanV7Profile


def process_v7_korean_name(native: str, base_processor) -> str:
    prof = KoreanV7Profile()
    r = base_processor.romanizer
    std_prev, hyp_prev, alias_prev, ov_prev = (
        r.standard,
        r.hyphenate_given,
        r.apply_given_aliases,
        getattr(r, "name_overrides", {}),
    )
    try:
        r.standard = "rr_strict"
        r.hyphenate_given = True
        r.apply_given_aliases = True
        r.name_overrides = {}
        st = base_processor.parser.parse(native)
        return r.romanise_name(native, st).replace("Jeong", "Jung")
    finally:
        r.standard, r.hyphenate_given, r.apply_given_aliases, r.name_overrides = (
            std_prev,
            hyp_prev,
            alias_prev,
            ov_prev,
        )
