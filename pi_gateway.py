"""Raspberry Pi gateway that validates and routes sensor packets.

This module provides a small reference implementation for the redesigned
Pi gateways.  Incoming packets from ESP32 nodes are validated using a
checksum that covers the source identifier, timestamp and payload.  Normal
readings are buffered locally until ``flush_buffer`` is invoked, while
anomalies bypass the buffer and are submitted immediately to the blockchain
client.  The gateway can also share its buffer with a peer to implement
store‑and‑forward over the Wi‑Fi mesh.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Dict, List, Protocol


class BlockchainClient(Protocol):
    """Minimal protocol a blockchain client must satisfy."""

    def submit(self, packet: Dict) -> None:
        """Submit a packet to the blockchain ledger."""


# Helper --------------------------------------------------------------------


def compute_checksum(source_id: str, timestamp: float, payload: Dict) -> str:
    """Return a short checksum for the packet fields."""
    m = hashlib.sha256()
    m.update(source_id.encode())
    m.update(str(timestamp).encode())
    # We rely on ``repr`` to produce deterministic order for Dict input
    m.update(repr(sorted(payload.items())).encode())
    return m.hexdigest()[:8]


# Gateway -------------------------------------------------------------------


@dataclass
class PiGateway:
    """Validate sensor packets and forward them to the blockchain."""

    client: BlockchainClient
    buffer: List[Dict] = field(default_factory=list)

    def validate(self, packet: Dict) -> bool:
        """Verify checksum, source ID and timestamp are present."""
        required = {"source_id", "timestamp", "payload", "checksum"}
        if not required.issubset(packet):
            return False
        calc = compute_checksum(
            packet["source_id"], packet["timestamp"], packet["payload"]
        )
        return packet["checksum"] == calc

    def handle_packet(self, packet: Dict) -> None:
        """Buffer normal data and escalate anomalies immediately."""
        if not self.validate(packet):
            raise ValueError("invalid packet")
        if packet.get("anomaly"):
            self.client.submit(packet)
        else:
            self.buffer.append(packet)

    def flush_buffer(self) -> None:
        """Submit all buffered packets to the blockchain and clear buffer."""
        for pkt in self.buffer:
            self.client.submit(pkt)
        self.buffer.clear()

    def sync_to_peer(self, peer: "PiGateway") -> None:
        """Share buffered packets with another gateway."""
        peer.buffer.extend(self.buffer)
