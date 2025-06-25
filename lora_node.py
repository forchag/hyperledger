"""Example LoRa node communicating with the gateway.

This demo uses pySX127x to send and receive JSON encoded sensor readings.
Configure GPIO pins according to your Raspberry Pi wiring.
"""

import json
from datetime import datetime
import argparse
import time

# Importing the sx127x driver requires hardware and is commented out
# from SX127x.LoRa import LoRa
# from SX127x.board_config import BOARD


def read_sensor():
    """Dummy sensor reader returning temperature/humidity."""
    return 22.0, 60.0


class DummyLoRa:
    def send(self, payload: bytes):
        print("Sending:", payload)

    def receive(self) -> bytes:
        return b''


# lora = LoRa()
lora = DummyLoRa()


def send_reading(device_id: str):
    temp, hum = read_sensor()
    data = {
        "id": device_id,
        "temperature": temp,
        "humidity": hum,
        "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    payload = json.dumps(data).encode('utf-8')
    lora.send(payload)


def send_heartbeat(device_id: str):
    msg = {
        "id": device_id,
        "type": "heartbeat",
        "timestamp": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
    }
    payload = json.dumps(msg).encode('utf-8')
    lora.send(payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LoRa sensor node")
    parser.add_argument("device_id")
    parser.add_argument("--heartbeat", action="store_true",
                        help="send heartbeats instead of a single reading")
    parser.add_argument("--interval", type=int, default=60,
                        help="seconds between heartbeats")
    args = parser.parse_args()

    if args.heartbeat:
        while True:
            send_heartbeat(args.device_id)
            time.sleep(args.interval)
    else:
        send_reading(args.device_id)
