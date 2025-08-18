"""Threshold and rate-of-change event detection with urgent uplink support."""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .ring_buffer import RingBuffer


class EventDetector:
    """Detect threshold and rate-of-change breaches for sensors.

    When a breach is detected for ``hysteresis`` consecutive samples the detector
    captures a batch of ``pre_samples`` preceding the breach and ``post_samples``
    following it.  The resulting payload is marked ``urgent`` and added to
    ``uplinks`` for immediate transmission.  To avoid flapping, only a limited
    number of urgent uploads are allowed in a sliding window.
    """

    def __init__(
        self,
        *,
        thresholds: Optional[Dict[str, float]] = None,
        rate_limits: Optional[Dict[str, float]] = None,
        hysteresis: int = 2,
        pre_samples: int = 2,
        post_samples: int = 2,
        limit: int = 2,
        window_sec: int = 600,
    ) -> None:
        self.thresholds = thresholds or {}
        self.rate_limits = rate_limits or {}
        self.hysteresis = hysteresis
        self.pre = pre_samples
        self.post = post_samples
        self.limit = limit
        self.window = window_sec

        self.buffers: Dict[str, RingBuffer] = {
            sid: RingBuffer(pre_samples + post_samples + 5)
            for sid in set(self.thresholds) | set(self.rate_limits)
        }
        self.prev: Dict[str, Dict[str, float]] = {}
        self.breach_counts: Dict[str, int] = {sid: 0 for sid in self.buffers}
        self.pending_posts: Dict[str, int] = {}
        self.trigger_ts: Dict[str, float] = {}
        self.urgent_times: List[float] = []
        self.uplinks: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    def _check_limit(self, now: float) -> bool:
        self.urgent_times = [t for t in self.urgent_times if now - t <= self.window]
        return len(self.urgent_times) < self.limit

    # ------------------------------------------------------------------
    def process(self, sensor_id: str, value: float, ts: Optional[float] = None) -> None:
        """Process a new sensor sample."""
        ts = ts if ts is not None else time.time()
        buf = self.buffers.setdefault(
            sensor_id, RingBuffer(self.pre + self.post + 5)
        )
        buf.append({"ts": ts, "value": value})

        # Handle collection of post-event samples first.
        if sensor_id in self.pending_posts:
            self.pending_posts[sensor_id] -= 1
            if self.pending_posts[sensor_id] <= 0:
                samples = buf.data()[-(self.pre + self.post + 1) :]
                payload = {
                    "sensor_id": sensor_id,
                    "samples": samples,
                    "urgent": True,
                    "event_ts": self.trigger_ts.pop(sensor_id),
                }
                self.uplinks.append(payload)
                del self.pending_posts[sensor_id]
            self.prev[sensor_id] = {"ts": ts, "value": value}
            return

        # Determine whether this reading breaches thresholds or rate limits.
        breach = False
        if sensor_id in self.thresholds and value >= self.thresholds[sensor_id]:
            breach = True
        if sensor_id in self.rate_limits and sensor_id in self.prev:
            dt = ts - self.prev[sensor_id]["ts"]
            if dt > 0:
                rate = abs(value - self.prev[sensor_id]["value"]) / dt
                if rate >= self.rate_limits[sensor_id]:
                    breach = True
        if breach:
            self.breach_counts[sensor_id] = self.breach_counts.get(sensor_id, 0) + 1
        else:
            self.breach_counts[sensor_id] = 0

        if (
            self.breach_counts[sensor_id] >= self.hysteresis
            and sensor_id not in self.pending_posts
            and self._check_limit(ts)
        ):
            self.pending_posts[sensor_id] = self.post
            self.trigger_ts[sensor_id] = ts
            self.urgent_times.append(ts)

        self.prev[sensor_id] = {"ts": ts, "value": value}


__all__ = ["EventDetector"]
