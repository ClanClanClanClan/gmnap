from __future__ import annotations
import tracemalloc
from typing import List


class MemDiff:
    """Scoped memory diff using tracemalloc to find top allocators between points."""

    def __init__(self, top=20):
        self.top = top
        tracemalloc.start()

    def snapshot(self):
        return tracemalloc.take_snapshot()

    def compare(self, before, after) -> List[str]:
        stats = after.compare_to(before, "lineno")[: self.top]
        lines = []
        for st in stats:
            tb = st.traceback[0] if st.traceback else None
            loc = f"{tb.filename}:{tb.lineno}" if tb else "unknown"
            lines.append(
                f"{loc} +{st.size_diff/1024:.1f} KiB in {st.count_diff} allocs"
            )
        return lines
