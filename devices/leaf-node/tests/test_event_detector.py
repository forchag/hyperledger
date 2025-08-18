import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from telemetry.event_detector import EventDetector


def test_urgent_uplink_threshold_and_limit():
    det = EventDetector(
        thresholds={"soil": 50.0},
        hysteresis=2,
        pre_samples=2,
        post_samples=2,
        limit=2,
        window_sec=600,
    )
    ts = 0.0
    # First event
    det.process("soil", 40.0, ts); ts += 1
    det.process("soil", 45.0, ts); ts += 1
    det.process("soil", 55.0, ts); ts += 1
    det.process("soil", 60.0, ts); ts += 1
    det.process("soil", 65.0, ts); ts += 1
    det.process("soil", 70.0, ts); ts += 1

    assert len(det.uplinks) == 1
    payload = det.uplinks[0]
    assert payload["urgent"] is True
    assert len(payload["samples"]) == 5  # 2 pre, event sample, 2 post

    # Second event within window
    det.process("soil", 40.0, ts); ts += 1
    det.process("soil", 45.0, ts); ts += 1
    det.process("soil", 55.0, ts); ts += 1
    det.process("soil", 60.0, ts); ts += 1
    det.process("soil", 65.0, ts); ts += 1
    det.process("soil", 70.0, ts); ts += 1
    assert len(det.uplinks) == 2

    # Third event should be suppressed by rate limit
    det.process("soil", 40.0, ts); ts += 1
    det.process("soil", 45.0, ts); ts += 1
    det.process("soil", 55.0, ts); ts += 1
    det.process("soil", 60.0, ts); ts += 1
    det.process("soil", 65.0, ts); ts += 1
    det.process("soil", 70.0, ts); ts += 1
    assert len(det.uplinks) == 2


def test_rate_of_change_detection():
    det = EventDetector(rate_limits={"temp": 5.0}, hysteresis=2, pre_samples=1, post_samples=1)
    ts = 0.0
    det.process("temp", 10.0, ts); ts += 1
    det.process("temp", 12.0, ts); ts += 1
    det.process("temp", 25.0, ts); ts += 1  # first ROC breach
    det.process("temp", 40.0, ts); ts += 1  # second ROC breach triggers event
    det.process("temp", 42.0, ts); ts += 1  # post sample

    assert len(det.uplinks) == 1
    payload = det.uplinks[0]
    assert payload["sensor_id"] == "temp"
    assert payload["urgent"] is True
    assert len(payload["samples"]) == 3  # 1 pre, event, 1 post
