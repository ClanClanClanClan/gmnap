from __future__ import annotations

import json
import os
import unicodedata
from typing import Dict, List, Tuple

from jsonschema import Draft202012Validator

from ..ops.metrics import PROCESSED_TOTAL, ROUNDTRIP_FAILURES, SCHEMA_VALIDATION_ERRORS
from ..pipeline.stage6_graph_consistency import enforce_graph_coherence_gate


def _load_entry_schema(
    path: str = "schemas/v7_entry.schema.json",
) -> Draft202012Validator:
    with open(path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


def _bigrams(s: str) -> set[tuple[str, str]]:
    s = "".join(
        ch
        for ch in unicodedata.normalize("NFC", s.lower())
        if not unicodedata.category(ch).startswith("C")
    )
    s = s.replace(" ", "").replace("-", "")
    return set(zip(s, s[1:])) if len(s) >= 2 else {(s,)} if s else set()


def _dice(a: str, b: str) -> float:
    A = _bigrams(a)
    B = _bigrams(b)
    if not A and not B:
        return 1.0
    return 2 * len(A & B) / (len(A) + len(B))


def _latinise_basic(native: str) -> str:
    import unicodedata

    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", native)
        if not unicodedata.combining(ch)
    )


def _roundtrip_score(entry: Dict[str, any]) -> float:
    canon = entry.get("CanonicalLatin") or ""
    native = entry.get("CanonicalNative") or ""
    if not native:
        return 1.0
    latinised = _latinise_basic(native)
    return _dice(canon, latinised)


def global_validate(
    batch: List[Dict], mode: str | None = None
) -> Tuple[List[Dict], Dict[str, float]]:
    validator = _load_entry_schema()
    mode = (mode or os.getenv("GMNAP_RUNTIME_MODE", "Quick")).strip()
    rt_min = 0.97

    errors_total = 0
    rt_fail = 0
    for e in batch:
        errs = sorted(validator.iter_errors(e), key=lambda x: x.path)
        if errs:
            errors_total += 1
            for err in errs:
                field = str(list(err.path)[0]) if err.path else "root"
                SCHEMA_VALIDATION_ERRORS.labels(field=field).inc()
            raise ValueError(
                f"Schema validation failed for GlobalID={e.get('GlobalID')}: {errs[0].message}"
            )
        score = _roundtrip_score(e)
        if score < rt_min:
            rt_fail += 1
            ROUNDTRIP_FAILURES.labels(region=e.get("DetectedRegion", "UNK")).inc()
            raise ValueError(
                f"Round-trip score {score:.3f} below {rt_min:.2f} for GlobalID={e.get('GlobalID')}"
            )

    _, m6 = enforce_graph_coherence_gate(batch, mode=mode)
    if PROCESSED_TOTAL:
        PROCESSED_TOTAL.labels(stage="8").inc()
    return batch, {
        "schema_errors": float(errors_total),
        "roundtrip_failures": float(rt_fail),
        **m6,
    }
