"""Sampling scheduler and rolling statistics for ESP32 sensors."""
from __future__ import annotations

import time
from typing import Dict, Any
from statistics import mean, pstdev

from telemetry.ring_buffer import RingBuffer


class RollingStats:
    """Maintain a rolling window of numeric samples and compute statistics."""

    def __init__(self, capacity: int = 180) -> None:
        self.buffer = RingBuffer(capacity)

    def add(self, value: float) -> None:
        self.buffer.append(value)

    def compute(self) -> Dict[str, Any]:
        data = self.buffer.data()
        if not data:
            return {"min": None, "avg": None, "max": None, "std": None, "count": 0}
        return {
            "min": min(data),
            "avg": mean(data),
            "max": max(data),
            "std": pstdev(data) if len(data) > 1 else 0.0,
            "count": len(data),
        }

    def reset(self) -> None:
        self.buffer = RingBuffer(self.buffer.capacity)


class SampleScheduler:
    """Schedule periodic sampling of sensors.

    ``sensors`` maps sensor IDs to sensor instances.  ``periods`` is the sampling
    period for each sensor in minutes (clamped to 1–5).  Readings are validated
    via the sensor adapters and pushed into per-sensor rolling statistics.
    """

    def __init__(self, sensors: Dict[str, Any], periods: Dict[str, int]) -> None:
        self.sensors = sensors
        self.periods = {sid: max(1, min(5, p)) * 60 for sid, p in periods.items()}
        # ``next_times`` defaults to ``0`` so the first ``tick`` call always
        # performs a reading regardless of the wall-clock time passed in tests.
        self.next_times = {sid: 0.0 for sid in sensors}
        self.stats = {sid: RollingStats() for sid in sensors}

    def tick(self, now: float | None = None) -> None:
        now = now if now is not None else time.time()
        for sid, sensor in self.sensors.items():
            if now >= self.next_times[sid]:
                try:
                    reading = sensor.read()
                except ValueError:
                    # Invalid reading; schedule next attempt but do not record.
                    self.next_times[sid] = now + self.periods[sid]
                    continue
                self.stats[sid].add(reading["value"])
                self.next_times[sid] = now + self.periods[sid]

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        return {sid: rs.compute() for sid, rs in self.stats.items()}

    def reset_stats(self) -> None:
        for rs in self.stats.values():
            rs.reset()

