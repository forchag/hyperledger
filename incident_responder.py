import time
from flask_app.hlf_client import get_incidents, quarantine_device, is_quarantined


def watch():
    """Watch the ledger for incidents and quarantine devices."""
    seen = set()
    while True:
        for inc in get_incidents():
            key = (inc["device_id"], inc["timestamp"])
            if key in seen:
                continue
            seen.add(key)
            if not is_quarantined(inc["device_id"]):
                quarantine_device(inc["device_id"])
        time.sleep(5)


if __name__ == "__main__":
    watch()
