"""Hierarchical network simulation for smart agriculture.

Demonstrates how constrained IoT sensors can split readings into
Chinese Remainder Theorem (CRT) residues and participate in a
hierarchical consensus. Sensors send residues to zone gateways which
forward validated values to the farm server for block creation.
"""
from dataclasses import dataclass
from typing import Dict, List, Tuple

MODULI = (101, 103, 107)  # pairwise coprime; residues fit in a byte

def crt_split(value: float) -> List[int]:
    scaled = int(value * 100)
    return [scaled % m for m in MODULI]

def crt_reconstruct(residues: List[int]) -> float:
    M = 1
    for m in MODULI:
        M *= m
    total = 0
    for r, m in zip(residues, MODULI):
        Mi = M // m
        total += r * Mi * pow(Mi, -1, m)
    return (total % M) / 100.0

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
        value = crt_reconstruct(residues)
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

if __name__ == "__main__":
    simulate()
