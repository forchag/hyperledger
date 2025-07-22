"""Sensor node that periodically records environmental data on chain."""

import argparse
import json
import random
import time
from datetime import datetime

import requests

from flask_app.hlf_client import record_sensor_data

# Importing the sx127x driver would require hardware. We keep a stub.
class DummyLoRa:
    def send(self, payload: bytes):
        print("Sending:", payload)


def read_dht22():
    """Return dummy temperature and humidity readings."""
    temp = random.uniform(20.0, 30.0)
    hum = random.uniform(40.0, 70.0)
    return temp, hum


def read_soil_moisture():
    return random.uniform(0.0, 100.0)


def read_ph():
    return random.uniform(5.5, 7.5)


def read_light():
    return random.uniform(0.0, 1023.0)


def read_water_level():
    return random.uniform(0.0, 100.0)


def main():
    parser = argparse.ArgumentParser(description="Sensor node")
    parser.add_argument("device_id")
    parser.add_argument("--interval", type=int, default=60,
                        help="seconds between measurements")
    parser.add_argument("--mode", choices=["http", "lora", "both"],
                        default="http",
                        help="transmission method")
    parser.add_argument("--endpoint", default="http://localhost:8443/sensor",
                        help="HTTP endpoint for sensor data")
    args = parser.parse_args()

    lora = DummyLoRa() if args.mode in ("lora", "both") else None
    session = requests.Session() if args.mode in ("http", "both") else None

    while True:
        temp, hum = read_dht22()
        soil = read_soil_moisture()
        ph = read_ph()
        light = read_light()
        water = read_water_level()
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

        payload = {
            'id': args.device_id,
            'temperature': temp,
            'humidity': hum,
            'soil_moisture': soil,
            'ph': ph,
            'light': light,
            'water_level': water,
            'timestamp': timestamp,
        }

        if args.mode == 'http':
            try:
                session.post(args.endpoint, json=payload, timeout=5)
            except Exception as e:
                print('HTTP send failed:', e)
        else:
            record_sensor_data(
                args.device_id,
                temp,
                hum,
                soil,
                ph,
                light,
                water,
                timestamp,
                payload,
            )
            data = json.dumps(payload).encode('utf-8')

            if lora:
                try:
                    lora.send(data)
                except Exception as e:
                    print('LoRa send failed:', e)

            if args.mode == 'both' and session:
                try:
                    session.post(args.endpoint, json=payload, timeout=5)
                except Exception as e:
                    print('HTTP send failed:', e)

        time.sleep(args.interval)


if __name__ == '__main__':
    main()
