"""Stage 3: RegionHooks - clean->augment->validate->order_key per detected region."""

from __future__ import annotations
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


def stage3_region_hooks(batch: List[Dict], region_manager) -> List[Dict]:
    """Apply region-specific hooks: clean -> augment -> validate -> order_key.

    Args:
        batch: List of entries with DetectedRegion already set (from Stage 2).
        region_manager: RegionManager instance with get_region() method.

    Returns:
        Processed entries with region-specific transformations applied.
    """
    out = []
    for e in batch:
        code = e.get("DetectedRegion", "R0")
        region = region_manager.get_region(code)

        if region is None:
            logger.warning(f"No processor for region {code}, using pass-through")
            out.append(e)
            continue

        try:
            e2 = dict(e)  # shallow copy to avoid mutating input

            # Ensure YAML config overrides are applied (lazy, runs once per processor)
            if hasattr(region, "ensure_yaml_loaded"):
                region.ensure_yaml_loaded()

            # V7 spec: clean -> augment -> validate -> order_key
            # Processor methods modify entry in-place (return None), except order_key which returns str
            if hasattr(region, "clean"):
                region.clean(e2)
            if hasattr(region, "augment"):
                region.augment(e2)
            if hasattr(region, "validate"):
                region.validate(e2)
            if hasattr(region, "order_key"):
                order_key = region.order_key(e2)
                if order_key:
                    e2["OrderKey"] = order_key

            out.append(e2)
        except Exception as ex:
            logger.error(
                f"Region hooks failed for {code} on entry {e.get('CanonicalLatin', '?')}: {ex}"
            )
            e["_region_hook_error"] = str(ex)
            out.append(e)

    return out
