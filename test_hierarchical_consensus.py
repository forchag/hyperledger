import pytest
from hierarchical_consensus import SensorNode, Gateway, FarmServer


def test_sensor_roundtrip():
    server = FarmServer()
    gateway = Gateway("Z1", server)
    sensor = SensorNode("S1", gateway)
    sensor.submit(23.75)
    gateway.reach_consensus()
    assert server.received[("Z1", "S1")] == pytest.approx(23.75)
