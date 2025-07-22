import time
from datetime import datetime
from flask_app.hlf_client import list_devices, get_sensor_data, log_security_incident

THRESHOLDS = {
    "temperature": (-10.0, 60.0),
    "humidity": (0.0, 100.0),
}


def detect():
    """Monitor devices and log security incidents."""
    while True:
        for dev in list_devices():
            data = get_sensor_data(dev)
            if not data:
                continue
            anomalies = []
            t = data.get("temperature")
            if t is not None:
                lo, hi = THRESHOLDS["temperature"]
                if t < lo or t > hi:
                    anomalies.append(f"temperature={t}")
            h = data.get("humidity")
            if h is not None:
                lo, hi = THRESHOLDS["humidity"]
                if h < lo or h > hi:
                    anomalies.append(f"humidity={h}")
            if anomalies:
                desc = "anomaly: " + ", ".join(anomalies)
                ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                log_security_incident(dev, desc, ts)
        time.sleep(5)


if __name__ == "__main__":
    detect()
