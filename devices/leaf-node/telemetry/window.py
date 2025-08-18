"""Windowed batching and summarisation for sensor readings."""
from __future__ import annotations

import json
import math
import os
import statistics
from typing import Any, Dict, List

from .summary_store import SummaryStore
from .ring_buffer import RingBuffer


class WindowBatcher:
    """Aggregate sensor samples into fixed windows.

    ``period_sec`` defines the duration of each window.  Samples added via
    :meth:`add_sample` are buffered until their timestamp crosses the window
    boundary, at which point a summary record is created and persisted to the
    provided :class:`SummaryStore`.
    """

    def __init__(
        self,
        period_sec: int,
        store: SummaryStore,
        *,
        tail_size: int = 5,
        state_path: str = "window_state.json",
    ) -> None:
        self.period = period_sec
        self.store = store
        self.tail_size = tail_size
        self.state_path = state_path

        self.samples: List[Dict[str, Any]] = []
        self.tail = RingBuffer(tail_size)
        self.start_ts: int | None = None
        self.end_ts: int | None = None
        self.last_sample: Dict[str, Any] | None = None
        self._load_state()

    # ------------------------------------------------------------------
    def _align_start(self, ts: float) -> int:
        return int(math.floor(ts / self.period) * self.period)

    # ------------------------------------------------------------------
    def _load_state(self) -> None:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.samples = data.get("samples", [])
            self.start_ts = data.get("start_ts")
            self.end_ts = data.get("end_ts")
            self.last_sample = data.get("last_sample")
            self.tail = RingBuffer(self.tail_size)
            for s in data.get("tail", []):
                self.tail.append(s)
        except Exception:
            # Fresh state
            self.samples = []
            self.start_ts = None
            self.end_ts = None
            self.last_sample = None
            self.tail = RingBuffer(self.tail_size)

    # ------------------------------------------------------------------
    def _persist_state(self) -> None:
        tmp = f"{self.state_path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "samples": self.samples,
                    "start_ts": self.start_ts,
                    "end_ts": self.end_ts,
                    "last_sample": self.last_sample,
                    "tail": list(self.tail),
                },
                f,
            )
        os.replace(tmp, self.state_path)

    # ------------------------------------------------------------------
    def add_sample(self, reading: Dict[str, Any]) -> None:
        ts = reading["ts"]
        if self.start_ts is None:
            self.start_ts = self._align_start(ts)
            self.end_ts = self.start_ts + self.period
        if ts >= self.end_ts:
            if self.samples:
                self._finalise_window(self.last_sample)
            self.start_ts = self._align_start(ts)
            self.end_ts = self.start_ts + self.period
            self.samples = []
            self.tail = RingBuffer(self.tail_size)
        self.samples.append(reading)
        self.tail.append(reading)
        self.last_sample = reading
        self._persist_state()

    # ------------------------------------------------------------------
    def _finalise_window(self, last_sample: Dict[str, Any] | None) -> None:
        if not self.samples or last_sample is None:
            return
        values = [s["value"] for s in self.samples]
        stats = {
            "min": min(values),
            "avg": statistics.mean(values),
            "max": max(values),
            "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "count": len(values),
        }
        summary = {
            "window_id": [self.start_ts, self.end_ts],
            "stats": stats,
            "last_sample": last_sample,
            "last_ts": last_sample["ts"],
            "tail": [s["value"] for s in self.tail],
        }
        self.store.enqueue(summary)

    # ------------------------------------------------------------------
    def flush(self) -> None:
        """Force emission of the current window summary."""
        if self.samples:
            self._finalise_window(self.last_sample)
            self.samples = []
            self.tail = RingBuffer(self.tail_size)
            self.start_ts = None
            self.end_ts = None
            self.last_sample = None
            if os.path.exists(self.state_path):
                os.remove(self.state_path)

