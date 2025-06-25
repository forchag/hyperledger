"""Network monitor that logs device heartbeats to the blockchain."""

import time
from datetime import datetime
from flask_app.hlf_client import log_event


def monitor(device_id: str):
    while True:
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        log_event(device_id, "heartbeat", timestamp)
        time.sleep(60)


if __name__ == "__main__":
    monitor("device-1")
