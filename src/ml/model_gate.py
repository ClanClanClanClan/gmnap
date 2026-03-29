"""
src/ml/model_gate.py
Hard safety gates for candidate regional models.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class EvalReport:
    overall: float
    per_class: Dict[str, float]


def _acc(truths: List[str], preds: List[str]) -> float:
    correct = sum(1 for t, p in zip(truths, preds) if t == p)
    return correct / max(1, len(truths))


def load_labels(path: str) -> List[Tuple[str, str]]:
    # CSV: name,region
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.lower().startswith("name,"):
                continue
            name, region = line.rstrip().split(",", 1)
            out.append((name, region))
    return out


def evaluate(model_fn, labelled_csv: str) -> EvalReport:
    items = load_labels(labelled_csv)
    preds = [model_fn(name) for name, _ in items]
    truths = [region for _, region in items]
    overall = _acc(truths, preds)
    per: Dict[str, List[int]] = {}
    for (_, t), p in zip(items, preds):
        per.setdefault(t, []).append(1 if t == p else 0)
    per_acc = {k: sum(v) / len(v) for k, v in per.items()}
    return EvalReport(overall, per_acc)


def gate(candidate_eval: EvalReport, baseline_eval: EvalReport, min_gain=0.015) -> bool:
    # Must beat baseline by min_gain and not regress more than 2 pp on any class.
    if candidate_eval.overall < baseline_eval.overall + min_gain:
        return False
    for cls, base_acc in baseline_eval.per_class.items():
        cand = candidate_eval.per_class.get(cls, 0.0)
        if cand + 0.02 < base_acc:
            return False
    return True
