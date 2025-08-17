import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sensors import LightSensor, Calibration
from sampling import SampleScheduler


def test_sensor_read_and_calibration():
    sensor = LightSensor(reader=lambda: 10.0, calibration=Calibration(offset=1.0, scale=2.0))
    reading = sensor.read()
    assert reading["value"] == 22.0
    assert "ts" in reading and "quality" in reading


def test_scheduler_sampling_and_stats():
    values = iter([10.0, 20.0, -5.0, 30.0, 40.0])
    sensor = LightSensor(reader=lambda: next(values), min_value=0.0, max_value=100.0)
    sched = SampleScheduler({"light": sensor}, {"light": 1})

    now = 0.0
    for _ in range(5):
        sched.tick(now)
        now += 60.0  # advance 1 minute

    stats = sched.get_stats()["light"]
    assert stats["count"] == 4  # one invalid reading skipped
    assert stats["min"] == 10.0
    assert stats["max"] == 40.0
    assert abs(stats["avg"] - (10 + 20 + 30 + 40) / 4) < 1e-6
    assert len(sched.stats["light"].buffer) == 4

    sched.reset_stats()
    assert sched.get_stats()["light"]["count"] == 0
