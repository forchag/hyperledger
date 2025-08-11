"""Advanced consensus mechanisms for AgriParallel-Chain simulation.

This module extends the simple CRT-based hierarchy with additional
features described in the AgriParallel-Chain specification:

* Proof-of-Authority (PoA) at gateways
* Practical Byzantine Fault Tolerance (PBFT) at sector heads
* Federated Byzantine Agreement (FBA) at the root node
* M/D/1 queue with dynamic buffering to meet explicit reliability targets
* Modulus-weighted prioritization when the buffer is congested
* Placeholder ZK-SNARK proof generation for transmitted residues
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import heapq
import hashlib
from math import factorial

from crt_parallel import crt_decompose, crt_reconstruct

# pairwise coprime moduli for CRT residue handling
MODULI = (101, 103, 107)

# explicit reliability target (e.g., 99.999%)
RELIABILITY_TARGET = 0.99999


def crt_split(value: float) -> List[int]:
    """Split ``value`` into CRT residues scaled to two decimal places."""
    scaled = int(value * 100)
    return crt_decompose(scaled, MODULI)


def crt_value(residues: List[int]) -> float:
    """Reconstruct the original value from CRT residues."""
    scaled = crt_reconstruct(residues, MODULI)
    return scaled / 100.0


def generate_snark_proof(residues: List[int]) -> str:
    """Return a placeholder SNARK proof for ``residues``.

    Real deployments would generate a cryptographic ZK-SNARK proof. For this
    simulation we simply hash the residues to provide a lightweight stand-in."""
    return hashlib.sha256(bytes(residues)).hexdigest()


def erlang_b(traffic_intensity: float, capacity: int) -> float:
    """Compute loss probability for an M/D/1/``capacity`` queue via Erlang B."""
    numerator = (traffic_intensity ** capacity) / factorial(capacity)
    denom = sum((traffic_intensity ** k) / factorial(k) for k in range(capacity + 1))
    return numerator / denom


class MD1Queue:
    """M/D/1 queue with dynamic buffering and modulus-weighted prioritization."""

    def __init__(self, arrival_rate: float, service_rate: float) -> None:
        self.arrival_rate = arrival_rate
        self.service_rate = service_rate
        self.buffer: List[Tuple[float, Tuple[str, str, List[int], str]]] = []
        self.capacity = 1
        self.reliability = 0.0
        self.adjust_buffer(RELIABILITY_TARGET)

    def adjust_buffer(self, target: float) -> None:
        traffic = self.arrival_rate / self.service_rate
        size = 1
        while True:
            loss = erlang_b(traffic, size)
            reliability = 1 - loss
            if reliability >= target:
                self.capacity = size
                self.reliability = reliability
                break
            size += 1

    def _priority(self, residues: List[int]) -> float:
        weights = [1 / m for m in MODULI]
        return -sum(r * w for r, w in zip(residues, weights))

    def enqueue(self, sector_id: str, sensor_id: str, residues: List[int], proof: str) -> None:
        priority = self._priority(residues)
        item = (priority, (sector_id, sensor_id, residues, proof))
        if len(self.buffer) >= self.capacity:
            heapq.heappushpop(self.buffer, item)
        else:
            heapq.heappush(self.buffer, item)

    def dequeue(self) -> Optional[Tuple[str, str, List[int], str]]:
        if self.buffer:
            return heapq.heappop(self.buffer)[1]
        return None


@dataclass
class SensorNode:
    sensor_id: str
    gateway: "Gateway"

    def submit(self, reading: float) -> None:
        residues = crt_split(reading)
        proof = generate_snark_proof(residues)
        self.gateway.collect(self.sensor_id, residues, proof)


class Gateway:
    """Gateway performing Proof-of-Authority validation."""

    def __init__(self, gateway_id: str, sector_head: "SectorHead", authorized: List[str]):
        self.gateway_id = gateway_id
        self.sector_head = sector_head
        self.authorized = set(authorized)
        self.pending: Dict[str, Tuple[List[int], str]] = {}

    def collect(self, sensor_id: str, residues: List[int], proof: str) -> None:
        if sensor_id in self.authorized:
            self.pending[sensor_id] = (residues, proof)

    def reach_consensus(self) -> None:
        # PoA: gateways vouch for authorized sensor readings
        for sensor_id, (residues, proof) in self.pending.items():
            self.sector_head.receive(self.gateway_id, sensor_id, residues, proof)
        self.pending.clear()


class SectorHead:
    """Sector head executing a minimal PBFT round among gateways."""

    def __init__(self, sector_id: str, root: "RootNode") -> None:
        self.sector_id = sector_id
        self.root = root
        self.messages: Dict[Tuple[str, str], Dict[str, Tuple[List[int], str]]] = {}

    def receive(self, gateway_id: str, sensor_id: str, residues: List[int], proof: str) -> None:
        key = (sensor_id, proof)
        self.messages.setdefault(key, {})[gateway_id] = (residues, proof)
        # PBFT: require at least 2 matching gateway messages
        if len(self.messages[key]) >= 2:
            residues, proof = list(self.messages[key].values())[0]
            self.root.receive(self.sector_id, sensor_id, residues, proof)
            del self.messages[key]


class RootNode:
    """Root node combining sector outputs via Federated Byzantine Agreement."""

    def __init__(self, arrival_rate: float, service_rate: float) -> None:
        self.queue = MD1Queue(arrival_rate, service_rate)
        self.fba_messages: Dict[str, Dict[str, Tuple[List[int], str]]] = {}
        self.finalized: Dict[str, float] = {}

    def receive(self, sector_id: str, sensor_id: str, residues: List[int], proof: str) -> None:
        key = proof
        self.fba_messages.setdefault(key, {})[sector_id] = (residues, proof)
        # FBA quorum: need two sector heads agreeing on the proof
        if len(self.fba_messages[key]) >= 2:
            residues, proof = list(self.fba_messages[key].values())[0]
            self.queue.enqueue(sector_id, sensor_id, residues, proof)
            del self.fba_messages[key]
            self.process_queue()

    def process_queue(self) -> None:
        item = self.queue.dequeue()
        if item:
            sector_id, sensor_id, residues, proof = item
            value = crt_value(residues)
            self.finalized[sensor_id] = value


def build_demo_network() -> Tuple[RootNode, List[Gateway], List[SensorNode]]:
    """Return a small network of components wired for simulation.

    The layout mirrors the one used in the unit tests and provides two
    sector heads with a pair of gateways each. All gateways authorize the
    same sensor identifier (``S1``) so a single reading can traverse PoA,
    PBFT and FBA stages.
    """

    root = RootNode(arrival_rate=20, service_rate=25)
    sector_a = SectorHead("A", root)
    sector_b = SectorHead("B", root)

    g_a1 = Gateway("A1", sector_a, ["S1"])
    g_a2 = Gateway("A2", sector_a, ["S1"])
    g_b1 = Gateway("B1", sector_b, ["S1"])
    g_b2 = Gateway("B2", sector_b, ["S1"])

    sensors = [
        SensorNode("S1", g_a1),
        SensorNode("S1", g_a2),
        SensorNode("S1", g_b1),
        SensorNode("S1", g_b2),
    ]

    gateways = [g_a1, g_a2, g_b1, g_b2]
    return root, gateways, sensors


def run_demo(reading: float = 23.75) -> Dict[str, float]:
    """Run an end-to-end demo and return finalized sensor values."""

    root, gateways, sensors = build_demo_network()
    for sensor in sensors:
        sensor.submit(reading)
    for gw in gateways:
        gw.reach_consensus()
    return root.finalized

