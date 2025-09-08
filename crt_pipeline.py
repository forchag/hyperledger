"""Sensor node and gateway pipeline using CRT compaction.

This module demonstrates how sensor readings can be summarised, optionally
compressed into Chinese Remainder Theorem (CRT) residues and forwarded to a
gateway.  The gateway reconstructs the values, aggregates them into a bundle and
computes a Merkle root suitable for anchoring on a blockchain.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import statistics
from typing import Dict, List

from crt_utils import crt_split, crt_value

# Sensor fields included in the demo payloads
SENSOR_FIELDS = ["temperature", "humidity", "soil_moisture"]


@dataclass
class SensorNode:
    """Simulated sensor node that produces window summaries."""

    device_id: str

    def summarise(self, readings: List[Dict[str, float]]) -> Dict[str, Dict[str, float]]:
        """Return per-field statistics for ``readings``.

        ``readings`` is a list of dictionaries with keys from ``SENSOR_FIELDS``.
        For each field the mean, min, max, standard deviation and count are
        computed.
        """

        stats: Dict[str, Dict[str, float]] = {}
        count = len(readings)
        for field in SENSOR_FIELDS:
            values = [r[field] for r in readings]
            mean = statistics.mean(values)
            min_v = min(values)
            max_v = max(values)
            std = statistics.stdev(values) if count > 1 else 0.0
            stats[field] = {
                "mean": mean,
                "min": min_v,
                "max": max_v,
                "std": std,
                "count": count,
            }
        return stats

    def create_payload(self, readings: List[Dict[str, float]], use_crt: bool = True) -> Dict:
        """Create a payload from ``readings`` with optional CRT compaction."""

        stats = self.summarise(readings)
        sensors: Dict[str, Dict[str, object]] = {}
        for field, data in stats.items():
            if use_crt:
                sensors[field] = {
                    "mean": crt_split(data["mean"]),
                    "min": crt_split(data["min"]),
                    "max": crt_split(data["max"]),
                    "std": crt_split(data["std"]),
                    "count": data["count"],
                }
            else:
                sensors[field] = data
        return {"device_id": self.device_id, "sensors": sensors}


class Gateway:
    """Gateway that reconstructs readings and computes Merkle roots."""

    def __init__(self, use_crt: bool = True) -> None:
        self.use_crt = use_crt
        self.buffer: List[Dict] = []

    def ingest(self, payload: Dict) -> None:
        """Recombine a sensor payload into floating point values."""

        sensors: Dict[str, Dict[str, float]] = {}
        for field, data in payload["sensors"].items():
            if self.use_crt:
                sensors[field] = {
                    "mean": crt_value(data["mean"]),
                    "min": crt_value(data["min"]),
                    "max": crt_value(data["max"]),
                    "std": crt_value(data["std"]),
                    "count": data["count"],
                }
            else:
                sensors[field] = data
        self.buffer.append({"device_id": payload["device_id"], "sensors": sensors})

    @staticmethod
    def _hash_record(record: Dict) -> str:
        blob = json.dumps(record, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()

    def compute_window(self) -> Dict:
        """Return bundled readings and their Merkle root."""

        hashes = [self._hash_record(r) for r in self.buffer]
        root = compute_merkle_root(hashes)
        bundle = {"readings": self.buffer, "merkle_root": root}
        self.buffer = []
        return bundle


def compute_merkle_root(hashes: List[str]) -> str:
    """Compute the Merkle root of a list of hexadecimal hashes."""

    if not hashes:
        return ""
    level = hashes[:]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        next_level = []
        for i in range(0, len(level), 2):
            joined = level[i] + level[i + 1]
            next_level.append(hashlib.sha256(joined.encode()).hexdigest())
        level = next_level
    return level[0]


__all__ = ["SensorNode", "Gateway", "compute_merkle_root", "SENSOR_FIELDS"]
