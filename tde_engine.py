import math
import json
import time
from collections import deque
from datetime import datetime

from flask_app.hlf_client import list_devices, get_sensor_data, log_security_incident


class DeviceProfile:
    """Maintain rolling stats for a device."""

    def __init__(self, window=20):
        self.window = window
        self.intervals = deque(maxlen=window)
        self.last_ts = None
        self.temperature = deque(maxlen=window)
        self.humidity = deque(maxlen=window)

    def update(self, timestamp, temperature=None, humidity=None):
        ts = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        if self.last_ts is not None:
            self.intervals.append((ts - self.last_ts).total_seconds())
        self.last_ts = ts
        if temperature is not None:
            self.temperature.append(float(temperature))
        if humidity is not None:
            self.humidity.append(float(humidity))

    @staticmethod
    def _stats(values):
        if not values:
            return 0.0, 0.0
        avg = sum(values) / len(values)
        var = sum((v - avg) ** 2 for v in values) / len(values)
        return avg, math.sqrt(var)

    def score(self, interval, temperature=None, humidity=None):
        """Return a Suspicion Score between 0 and 1."""
        score = 0.0
        if interval is not None and len(self.intervals) >= 5:
            avg, std = self._stats(self.intervals)
            if std > 0 and abs(interval - avg) > 3 * std:
                score = max(score, 0.5)
        if temperature is not None and len(self.temperature) >= 5:
            avg, std = self._stats(self.temperature)
            if std > 0 and abs(temperature - avg) > 3 * std:
                score = max(score, 0.7)
        if humidity is not None and len(self.humidity) >= 5:
            avg, std = self._stats(self.humidity)
            if std > 0 and abs(humidity - avg) > 3 * std:
                score = max(score, 0.7)
        return min(score, 1.0)


class ThreatDetectionEngine:
    """Continuously monitor devices and report anomalies."""

    def __init__(self, threshold=0.8):
        self.threshold = threshold
        self.profiles = {}

    def process_reading(self, device_id, reading):
        profile = self.profiles.setdefault(device_id, DeviceProfile())
        ts = reading.get("timestamp")
        temp = reading.get("temperature")
        hum = reading.get("humidity")
        interval = None
        if profile.last_ts is not None:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
            interval = (dt - profile.last_ts).total_seconds()
        suspicion = profile.score(interval, temp, hum)
        profile.update(ts, temp, hum)
        if suspicion >= self.threshold:
            sir = {
                "device_id": device_id,
                "type": "behavior_anomaly",
                "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "score": round(suspicion, 3),
                "payload": reading,
            }
            log_security_incident(device_id, "behavior_anomaly", sir["time"], score=sir["score"], payload=reading)
            print(json.dumps(sir))
            return sir
        return None

    def run(self):
        while True:
            for dev in list_devices():
                data = get_sensor_data(dev)
                if not data:
                    continue
                self.process_reading(dev, data)
            time.sleep(5)


if __name__ == "__main__":
    ThreatDetectionEngine().run()
