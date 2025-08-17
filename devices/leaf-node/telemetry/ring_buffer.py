"""Fixed-size ring buffer for raw sensor samples.

Defaults to 180 entries, giving ~15 minutes of retention at 5s sampling
or ~2 hours at 40s sampling.
"""
from __future__ import annotations

from typing import Any, Iterable, List


class RingBuffer:
    def __init__(self, capacity: int = 180) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._buf = [None] * capacity
        self._start = 0
        self._size = 0

    def append(self, item: Any) -> None:
        idx = (self._start + self._size) % self.capacity
        self._buf[idx] = item
        if self._size < self.capacity:
            self._size += 1
        else:
            self._start = (self._start + 1) % self.capacity

    def __len__(self) -> int:
        return self._size

    def __iter__(self) -> Iterable[Any]:
        for i in range(self._size):
            yield self._buf[(self._start + i) % self.capacity]

    def data(self) -> List[Any]:
        """Return a list of buffer contents in chronological order."""
        return list(self)
