from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional
import yaml

Strategy = Literal["source_priority", "set_union", "weighted"]


@dataclass(frozen=True)
class FieldStrategy:
    field: str
    strategy: Strategy
    source_priority: Optional[List[str]] = None


@dataclass
class ConflictPolicy:
    weights: Dict[str, float]
    strategies: Dict[str, FieldStrategy]

    @staticmethod
    def load(
        path: str = "config/conflict_policy.yaml",
        weights_path: str = "config/weights.yaml",
    ) -> "ConflictPolicy":
        with open(path, "r", encoding="utf-8") as f:
            conf = yaml.safe_load(f) or {}
        try:
            with open(weights_path, "r", encoding="utf-8") as f:
                weights = yaml.safe_load(f) or {}
        except FileNotFoundError:
            weights = {}
        # normalise weights
        s = sum(float(v) for v in weights.values()) or 1.0
        weights = {k: float(v) / s for k, v in weights.items()}
        strategies = {}
        for field, spec in (conf.get("fields") or {}).items():
            strategies[field] = FieldStrategy(
                field=field,
                strategy=spec.get("strategy", "source_priority"),
                source_priority=spec.get("source_priority"),
            )
        return ConflictPolicy(weights=weights, strategies=strategies)

    def pick_source(self, field: str, sources: Dict[str, object]) -> str:
        s = self.strategies.get(field)
        if s and s.strategy == "source_priority" and s.source_priority:
            for name in s.source_priority:
                if name in sources:
                    return name
        # fallback: highest weight
        return max(sources.keys(), key=lambda k: self.weights.get(k, 0.0))
