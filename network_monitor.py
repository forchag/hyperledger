"""Network monitor that logs device heartbeats to the blockchain."""

import time
import json
from datetime import datetime
from flask_app.hlf_client import log_event


class DummyLoRa:
    def receive(self) -> bytes:
        return b""


lora = DummyLoRa()


def monitor():
    """Listen for LoRa heartbeats and record them on chain."""
    known_nodes = set()
    last_report = time.time()
    while True:
        payload = lora.receive()
        if payload:
            try:
                data = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError:
                data = None
            if data and data.get("type") == "heartbeat":
                node_id = data["id"]
                known_nodes.add(node_id)
                log_event(node_id, "heartbeat", data["timestamp"])
        if time.time() - last_report >= 60:
            if known_nodes:
                print("Connected nodes:", ", ".join(sorted(known_nodes)))
            last_report = time.time()
        time.sleep(1)


if __name__ == "__main__":
    monitor()
