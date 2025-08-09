"""Example LoRa node communicating with the gateway.

This demo uses pySX127x to send and receive JSON encoded sensor readings.
Configure GPIO pins according to your Raspberry Pi wiring.
"""

import json
from datetime import datetime
import argparse
import time
from typing import List, Optional

# Importing the sx127x driver requires hardware and is commented out
# from SX127x.LoRa import LoRa
# from SX127x.board_config import BOARD


def read_sensor():
    """Dummy sensor reader returning temperature/humidity."""
    return 22.0, 60.0


class DummyLoRa:
    """Very small stand‑in for a SX127x driver.

    It allows the example to run without hardware while simulating the rapid
    switching between transmit (TX) and receive (RX) modes that real LoRa radios
    support. Any bytes present in ``responses`` will be returned by ``receive``.
    """

    def __init__(self, responses: Optional[List[bytes]] = None):
        self.responses = responses or []

    def send(self, payload: bytes):
        print("Sending:", payload)

    def receive(self, timeout: float = 0.1) -> bytes:
        if self.responses:
            return self.responses.pop(0)
        time.sleep(timeout)
        return b""


# lora = LoRa()
lora = DummyLoRa()


def send_reading(device_id: str, target: Optional[str] = None):
    """Send a sensor reading to ``target`` and immediately transmit it."""

    temp, hum = read_sensor()
    data = {
        "id": device_id,
        "temperature": temp,
        "humidity": hum,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if target:
        data["to"] = target
    payload = json.dumps(data).encode("utf-8")
    lora.send(payload)


def send_heartbeat(device_id: str, target: Optional[str] = None):
    """Send a heartbeat packet to ``target``."""

    msg = {
        "id": device_id,
        "type": "heartbeat",
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if target:
        msg["to"] = target
    payload = json.dumps(msg).encode("utf-8")
    lora.send(payload)


def listen_for_reply(timeout: float):
    """Listen for a reply for ``timeout`` seconds and print it if present."""

    start = time.time()
    while time.time() - start < timeout:
        data = lora.receive(timeout)
        if data:
            print("Received:", data)
            return data
    return b""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoRa sensor node")
    parser.add_argument("device_id")
    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="send heartbeats instead of a single reading",
    )
    parser.add_argument(
        "--interval", type=int, default=60, help="seconds between heartbeats"
    )
    parser.add_argument(
        "--targets",
        nargs="*",
        default=[],
        help="IDs of peer devices to contact",
    )
    parser.add_argument(
        "--switch-delay",
        type=float,
        default=2.0,
        help="delay in milliseconds before switching to RX",
    )
    parser.add_argument(
        "--rx-timeout",
        type=float,
        default=0.2,
        help="seconds to listen for a reply",
    )
    args = parser.parse_args()

    def tx_rx_cycle(target: str):
        if args.heartbeat:
            send_heartbeat(args.device_id, target)
        else:
            send_reading(args.device_id, target)
        time.sleep(args.switch_delay / 1000.0)
        listen_for_reply(args.rx_timeout)

    if args.targets:
        if args.heartbeat:
            while True:
                for target in args.targets:
                    tx_rx_cycle(target)
                time.sleep(args.interval)
        else:
            for target in args.targets:
                tx_rx_cycle(target)
    else:
        if args.heartbeat:
            while True:
                tx_rx_cycle(None)
                time.sleep(args.interval)
        else:
            tx_rx_cycle(None)
