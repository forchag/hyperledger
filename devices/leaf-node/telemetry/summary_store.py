"""Persistent summary queue with monotonic sequence numbers."""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional


class SummaryStore:
    """File-backed FIFO store for window summaries.

    The store keeps pending summaries along with a monotonically increasing
    sequence number.  Both the queue and the sequence counter are persisted in
    the same file so that they survive reboots without introducing duplicate
    sequence values.
    """

    def __init__(self, path: str = "summaries.json", *, expiry_sec: int = 24 * 3600) -> None:
        self.path = path
        self.expiry_sec = expiry_sec
        self.last_seq = 0
        self.queue: List[Dict[str, Any]] = []
        self._load()

    # ------------------------------------------------------------------
    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.last_seq = int(data.get("last_seq", 0))
            self.queue = list(data.get("queue", []))
        except Exception:
            self.last_seq = 0
            self.queue = []
        self._purge_expired(persist=False)

    # ------------------------------------------------------------------
    def _persist(self) -> None:
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"last_seq": self.last_seq, "queue": self.queue}, f)
        os.replace(tmp, self.path)

    # ------------------------------------------------------------------
    def _purge_expired(self, *, persist: bool = True) -> None:
        now = time.time()
        new_queue = [
            item
            for item in self.queue
            if now - item.get("window_id", [0, 0])[1] <= self.expiry_sec
        ]
        if len(new_queue) != len(self.queue):
            self.queue = new_queue
            if persist:
                self._persist()

    # ------------------------------------------------------------------
    def enqueue(self, summary: Dict[str, Any]) -> int:
        """Append ``summary`` assigning the next sequence value."""
        self.last_seq += 1
        item = dict(summary)
        item["seq"] = self.last_seq
        self.queue.append(item)
        self._persist()
        return self.last_seq

    # ------------------------------------------------------------------
    def peek(self) -> Optional[Dict[str, Any]]:
        """Return the next summary without removing it."""
        self._purge_expired()
        return self.queue[0] if self.queue else None

    # ------------------------------------------------------------------
    def dequeue(self) -> Optional[Dict[str, Any]]:
        """Remove and return the next summary."""
        self._purge_expired()
        if not self.queue:
            return None
        item = self.queue.pop(0)
        self._persist()
        return item

    # ------------------------------------------------------------------
    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.queue)

