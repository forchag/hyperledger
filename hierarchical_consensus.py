"""Hierarchical network simulation for smart agriculture.

Demonstrates how constrained IoT sensors can split readings into
Chinese Remainder Theorem (CRT) residues and participate in a
hierarchical consensus. Sensors send residues to zone gateways which
forward validated values to the farm server for block creation.

The core CRT arithmetic is delegated to :mod:`crt_parallel` so that all
components share the same implementation for decomposing and
reconstructing values.

The module also exposes :func:`run_advanced_consensus` which wires in the
more elaborate consensus pipeline from :mod:`advanced_consensus`. This
allows external callers to exercise Proof-of-Authority, PBFT and
Federated Byzantine Agreement flows without rewriting the simple
hierarchical demo.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple

from crt_parallel import crt_decompose, crt_reconstruct

# Pairwise coprime moduli; residues fit in a byte
MODULI = (101, 103, 107)


def crt_split(value: float) -> List[int]:
    """Return residues representing ``value`` to two decimal places."""
    scaled = int(value * 100)
    return crt_decompose(scaled, MODULI)


def crt_value(residues: List[int]) -> float:
    """Recover original value from residues produced by :func:`crt_split`."""
    scaled = crt_reconstruct(residues, MODULI)
    return scaled / 100.0

@dataclass
class SensorNode:
    sensor_id: str
    gateway: "Gateway"

    def submit(self, reading: float) -> None:
        residues = crt_split(reading)
        self.gateway.collect(self.sensor_id, residues)

class Gateway:
    def __init__(self, zone_id: str, server: "FarmServer") -> None:
        self.zone_id = zone_id
        self.server = server
        self.pending: Dict[str, List[int]] = {}

    def collect(self, sensor_id: str, residues: List[int]) -> None:
        self.pending[sensor_id] = residues

    def reach_consensus(self) -> None:
        # Gateways could validate or average readings here.
        for sensor_id, residues in self.pending.items():
            self.server.receive(self.zone_id, sensor_id, residues)
        self.pending.clear()

class FarmServer:
    def __init__(self) -> None:
        self.received: Dict[Tuple[str, str], float] = {}

    def receive(self, zone_id: str, sensor_id: str, residues: List[int]) -> None:
        value = crt_value(residues)
        self.received[(zone_id, sensor_id)] = value


def build_farm() -> Tuple[List[SensorNode], List[Gateway], FarmServer]:
    server = FarmServer()
    zones = ["North", "South", "East", "West"]
    gateways = [Gateway(zone, server) for zone in zones]
    sensors: List[SensorNode] = []
    for gw in gateways:
        for idx in range(1, 6):  # five sensors per zone for demo
            sensors.append(SensorNode(f"{gw.zone_id[0]}{idx}", gw))
    return sensors, gateways, server

def simulate() -> None:
    sensors, gateways, server = build_farm()
    # Sensors generate a sample reading and send residues
    for sensor in sensors:
        sensor.submit(23.75)
    # Gateways validate/aggregate and forward to the farm server
    for gw in gateways:
        gw.reach_consensus()
    # Farm server reconstructs original values
    for (zone, sensor_id), value in server.received.items():
        print(f"{zone}:{sensor_id} -> {value:.2f}")


def run_advanced_consensus(reading: float) -> Dict[str, float]:
    """Run the advanced consensus pipeline for a single reading."""

    from advanced_consensus import build_demo_network

    root, gateways, sensors = build_demo_network()
    for sensor in sensors:
        sensor.submit(reading)
    for gw in gateways:
        gw.reach_consensus()
    return root.finalized

if __name__ == "__main__":
    simulate()
