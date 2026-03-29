#!/usr/bin/env python3
import importlib, json
from src.core.pipeline_v7_hotfix import apply_pipeline_hotfix

V7 = importlib.import_module("src.core.pipeline_v7").V7Pipeline
V7 = apply_pipeline_hotfix(V7)
p = V7()
print(
    json.dumps(
        {
            "has_attr": hasattr(p, "_force_immediate_processing"),
            "value": getattr(p, "_force_immediate_processing"),
        },
        indent=2,
    )
)
