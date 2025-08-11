import pytest
from advanced_consensus import build_demo_network, SensorNode, RELIABILITY_TARGET


def test_end_to_end_consensus():
    root, gateways, sensors = build_demo_network()
    for sensor in sensors:
        sensor.submit(23.75)
    for gw in gateways:
        gw.reach_consensus()
    # both sector heads reached PBFT consensus; root performs FBA
    assert root.finalized["S1"] == pytest.approx(23.75)


def test_poa_rejects_unauthorized_sensor():
    root, gateways, sensors = build_demo_network()
    unauthorized = SensorNode("S2", gateways[0])  # gateway A1 not authorized for S2
    for sensor in sensors:
        sensor.submit(18.5)
    unauthorized.submit(50.0)
    for gw in gateways:
        gw.reach_consensus()
    assert "S2" not in root.finalized
    assert root.finalized["S1"] == pytest.approx(18.5)


def test_queue_meets_reliability():
    root, _, _ = build_demo_network()
    assert root.queue.reliability >= RELIABILITY_TARGET
