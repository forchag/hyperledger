"""Example LoRa node communicating with the gateway.

This demo uses pySX127x to send and receive JSON encoded sensor readings.
Configure GPIO pins according to your Raspberry Pi wiring.
"""

import json
from datetime import datetime

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


if __name__ == "__main__":
    send_reading("device-1")
