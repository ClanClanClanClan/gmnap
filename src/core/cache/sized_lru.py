
from __future__ import annotations

import sys
from collections import OrderedDict
from typing import Any, Dict, Tuple


class SizedLRU:
    def __init__(self, max_bytes: int = 256 * 1024 * 1024):
        self.max_bytes = max_bytes
        self._data: "OrderedDict[Any, Tuple[Any,int]]" = OrderedDict()
        self._size = 0
    def _est(self, k: Any, v: Any) -> int:
        try: return sys.getsizeof(k)+sys.getsizeof(v)
        except Exception: return 64
    def get(self, k: Any, default=None):
        it = self._data.get(k)
        if it is None: return default
        v, _ = it; self._data.move_to_end(k); return v
    def put(self, k: Any, v: Any):
        sz = self._est(k, v)
        if k in self._data:
            _, old = self._data.pop(k); self._size -= old
        self._data[k] = (v, sz); self._size += sz
        while self._size > self.max_bytes and self._data:
            _, (_, s) = self._data.popitem(last=False); self._size -= s
    def __contains__(self, k: Any)->bool: return k in self._data
    def __len__(self)->int: return len(self._data)
    @property
    def size_bytes(self)->int: return self._size
