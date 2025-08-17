"""Persistent monotonic sequence store for ESP32 leaf nodes.

The store is backed by a small file representing NVS/flash to survive
reboots. Sequence values strictly increase across initialisations so
that receivers can deduplicate packets.
"""

from __future__ import annotations

import os
import threading
from typing import Optional


class SeqStore:
    """A simple persistent counter."""

    def __init__(self, path: str = "seq_store.dat") -> None:
        self.path = path
        self._lock = threading.Lock()
        self.seq = self._load()

    def _load(self) -> int:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def _persist(self) -> None:
        tmp_path = f"{self.path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(str(self.seq))
        os.replace(tmp_path, self.path)

    def next(self) -> int:
        """Increment and return the next sequence value."""
        with self._lock:
            self.seq += 1
            self._persist()
            return self.seq
