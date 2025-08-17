import time

from sensor_node import should_transmit, SOIL_MOISTURE_THRESHOLD, PH_LOW, PH_HIGH, WATER_LEVEL_THRESHOLD


def test_event_triggered():
    now = time.time()
    assert should_transmit(now, now, 60, SOIL_MOISTURE_THRESHOLD - 1, 6.0, 50.0)


def test_periodic_report():
    last = 0
    now = 60 * 31  # 31 minutes
    assert should_transmit(last, now, 30, 100.0, 6.5, 50.0)


def test_no_trigger():
    last = 0
    now = 60 * 10  # 10 minutes
    assert not should_transmit(last, now, 30, 100.0, 6.5, 50.0)
