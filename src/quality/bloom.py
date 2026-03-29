from __future__ import annotations
import math, mmh3  # type: ignore


class BloomFilter:
    """Simple Bloom filter for fast negative membership tests.

    Not a replacement for set() in Python for small N, but useful to reduce hash table probes on huge streams.
    """

    def __init__(self, n_items: int, fp_rate: float = 0.01):
        m = -(n_items * math.log(fp_rate)) / (math.log(2) ** 2)
        k = (m / n_items) * math.log(2)
        self.m = int(m)
        self.k = max(1, int(k))
        self.bits = bytearray((self.m + 7) // 8)

    def _setbit(self, idx: int):
        self.bits[idx // 8] |= 1 << (idx % 8)

    def _getbit(self, idx: int) -> bool:
        return bool(self.bits[idx // 8] & (1 << (idx % 8)))

    def add(self, s: str):
        for i in range(self.k):
            h = mmh3.hash(s, i) % self.m
            self._setbit(h)

    def __contains__(self, s: str) -> bool:
        for i in range(self.k):
            h = mmh3.hash(s, i) % self.m
            if not self._getbit(h):
                return False
        return True
