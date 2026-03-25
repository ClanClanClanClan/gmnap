from __future__ import annotations
from .metrics import Counter, Gauge

WRITE_DIFF_ADDED = Counter("gmnap_write_diff_added_total", "New entries in snapshot")
WRITE_DIFF_REMOVED = Counter("gmnap_write_diff_removed_total", "Removed entries in snapshot")
WRITE_DIFF_MODIFIED = Counter("gmnap_write_diff_modified_total", "Modified entries in snapshot")
WRITE_DIFF_LATEST = Gauge(
    "gmnap_write_diff_latest_total", "Changed entries in latest diff (added+removed+modified)"
)
