#!/usr/bin/env python3
"""Replicate sensor data for a new node joining the network."""

import argparse
from flask_app import hlf_client


def bootstrap() -> None:
    """Fetch all stored sensor payloads and display them."""
    for dev in hlf_client.list_devices():
        for record in hlf_client.get_sensor_history(dev):
            payload = record.get("payload")
            if payload:
                print(f"Payload for {dev} at {record['timestamp']}: {payload[:30]}...")


def main():
    p = argparse.ArgumentParser(description="Display stored payloads")
    p.parse_args()
    bootstrap()


if __name__ == "__main__":
    main()
