"""Hybrid polling and event-driven LoRa network with TDMA slots.

This module demonstrates how a Raspberry Pi gateway can coordinate up to
fifty ESP32 nodes over a LoRa link.  The gateway polls each node in a
fixed time division multiple access (TDMA) frame while also listening for
asynchronous event messages from the nodes.  The design mirrors the
architecture described in the user request: a hybrid of periodic polling
and immediate event transmission.

The implementation is intentionally lightweight and hardware agnostic so
that it can run in the repository's test environment.  The :class:`DummyLoRa`
class simulates the behaviour of a radio by providing ``send`` and
``receive`` hooks.

Example
-------
>>> if __name__ == "__main__":
...     network = build_demo_network(node_count=3)
...     network.run(frames=2)

The example above creates three nodes and runs two TDMA frames of polling
while concurrently checking for event messages.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Callable


class DummyLoRa:
    """Extremely small stand‑in for a real LoRa radio.

    ``send`` simply prints the payload while ``receive`` returns any queued
    responses.  The class is sufficient for unit testing and demonstration
    purposes where no actual radio hardware is available.
    """

    def __init__(self) -> None:
        self.responses: list[bytes] = []

    def send(self, payload: bytes) -> None:
        print("TX:", payload.decode())

    def queue_response(self, payload: bytes) -> None:
        self.responses.append(payload)

    def receive(self, timeout: float = 0.0) -> bytes:
        if self.responses:
            return self.responses.pop(0)
        time.sleep(timeout)
        return b""


@dataclass
class HybridNode:
    """Representation of a leaf node with optional event generation."""

    node_id: int
    lora: DummyLoRa
    check_event: Optional[Callable[[], Optional[Dict]]] = None

    def poll(self) -> Dict:
        """Return sensor readings when the gateway polls this node."""
        data = {
            "id": self.node_id,
            "temperature": 22.0 + random.random(),
            "humidity": 60.0 + random.random(),
            "timestamp": time.time(),
        }
        self.lora.send(str(data).encode())
        return data

    def maybe_send_event(self) -> None:
        """Send an event message if ``check_event`` deems it necessary."""
        if self.check_event:
            event = self.check_event()
            if event:
                event_packet = {"id": self.node_id, "event": event, "timestamp": time.time()}
                self.lora.send(str(event_packet).encode())


class HybridGateway:
    """Coordinate polling and event reception for multiple nodes."""

    def __init__(self, nodes: Dict[int, HybridNode], slot_ms: int = 20, frame_ms: int = 1000) -> None:
        self.nodes = nodes
        self.slot_ms = slot_ms
        self.frame_ms = frame_ms
        self.lora = DummyLoRa()

    def _poll_frame(self) -> None:
        start = time.time()
        for offset, node_id in enumerate(sorted(self.nodes)):
            slot_start = start + (offset * self.slot_ms) / 1000.0
            delay = slot_start - time.time()
            if delay > 0:
                time.sleep(delay)
            data = self.nodes[node_id].poll()
            self.handle_poll_response(data)
        # ensure frame duration
        frame_end = start + self.frame_ms / 1000.0
        if frame_end > time.time():
            time.sleep(frame_end - time.time())

    def handle_poll_response(self, data: Dict) -> None:  # pragma: no cover - simple print
        print("Gateway received poll:", data)

    def handle_event(self, data: Dict) -> None:  # pragma: no cover - simple print
        print("Gateway received event:", data)

    def _event_listener(self, stop: threading.Event) -> None:
        while not stop.is_set():
            for node in self.nodes.values():
                node.maybe_send_event()
            msg = self.lora.receive(timeout=self.slot_ms / 1000.0)
            if msg:
                self.handle_event(eval(msg.decode()))

    def run(self, frames: int = 1) -> None:
        """Run ``frames`` TDMA polling frames while listening for events."""
        stop = threading.Event()
        listener = threading.Thread(target=self._event_listener, args=(stop,), daemon=True)
        listener.start()
        for _ in range(frames):
            self._poll_frame()
        stop.set()
        listener.join()


# Convenience ----------------------------------------------------------------

def build_demo_network(node_count: int = 5) -> HybridGateway:
    """Create a demonstration network with random event generation.

    Each node raises an event with a small probability each time the event
    listener checks it.  This mirrors a node triggering an urgent update
    without waiting for its polling slot.
    """

    def event_factory(threshold: float = 0.99) -> Callable[[], Optional[Dict]]:
        def _maybe_event() -> Optional[Dict]:
            if random.random() > threshold:
                return {"soil_moisture": random.uniform(0, 1)}
            return None
        return _maybe_event

    lora_bus = DummyLoRa()
    nodes = {
        i: HybridNode(i, lora_bus, check_event=event_factory())
        for i in range(1, node_count + 1)
    }
    return HybridGateway(nodes)


if __name__ == "__main__":  # pragma: no cover - manual test
    gw = build_demo_network(3)
    gw.run(frames=2)
