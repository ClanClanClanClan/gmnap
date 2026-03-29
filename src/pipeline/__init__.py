"""
GMNAP v7.0 Processing Pipeline
Stages 0-11 as defined in specs v7.0.yaml

Individual stage modules can be imported as needed.
"""

# Stage functions are available in their respective modules
# Import them directly when needed:
# from src.pipeline.stage7_tag_short_forms import tag_short_forms
# from src.pipeline.stage8_global_validate import global_validate
# from src.pipeline.stage11_idempotency_check import enforce_idempotency_gate

__all__ = [
    # List modules available but don't import them automatically
    "stage2_detect_region",
    "stage3_region_hooks",
    "stage5_collision_analytics",
    "stage6_graph_consistency",
    "stage7_tag_short_forms",
    "stage8_global_validate",
    "stage9_write_and_diff",
    "stage10_report",
    "stage11_idempotency_check",
]
