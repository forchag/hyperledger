import sys
import types

import pytest

# Stub out heavy dependencies imported by sensor_simulator
hlf_client_stub = types.ModuleType("hlf_client")
hlf_client_stub.record_sensor_data = lambda *args, **kwargs: None
hlf_client_stub.register_device = lambda *args, **kwargs: None
pkg = types.ModuleType("flask_app")
pkg.hlf_client = hlf_client_stub
sys.modules.setdefault("flask_app", pkg)
sys.modules["flask_app.hlf_client"] = hlf_client_stub

from sensor_simulator import build_mapping, GPIO_PINS


def test_build_mapping_basic_multiple_nodes():
    config = {
        "nodes": [
            {"id": "node1", "sensors": ["temp", "humidity"]},
            {"id": "node2", "sensors": ["ph"]},
        ]
    }
    mapping = build_mapping(config)
    assert mapping == {
        "node1": {"ip": "node1", "sensors": {"temp": GPIO_PINS[0], "humidity": GPIO_PINS[1]}},
        "node2": {"ip": "node2", "sensors": {"ph": GPIO_PINS[0]}},
    }


def test_build_mapping_pin_wraps_when_exhausted():
    sensor_count = len(GPIO_PINS) + 3
    sensors = [f"s{i}" for i in range(sensor_count)]
    config = {"nodes": [{"id": "node1", "sensors": sensors}]}
    mapping = build_mapping(config)
    sensors_map = mapping["node1"]["sensors"]
    assert sensors_map[f"s{len(GPIO_PINS)}"] == GPIO_PINS[0]
    assert sensors_map[f"s{len(GPIO_PINS)+1}"] == GPIO_PINS[1]
    assert sensors_map[f"s{len(GPIO_PINS)+2}"] == GPIO_PINS[2]


def test_build_mapping_resets_for_each_node():
    config = {
        "nodes": [
            {"id": "node1", "sensors": ["s1", "s2"]},
            {"id": "node2", "sensors": ["s3", "s4"]},
        ]
    }
    mapping = build_mapping(config)
    assert mapping["node1"]["sensors"]["s1"] == GPIO_PINS[0]
    assert mapping["node1"]["sensors"]["s2"] == GPIO_PINS[1]
    assert mapping["node2"]["sensors"]["s3"] == GPIO_PINS[0]
    assert mapping["node2"]["sensors"]["s4"] == GPIO_PINS[1]


def test_build_mapping_handles_empty_sensor_lists():
    config = {
        "nodes": [
            {"id": "node1", "sensors": []},
            {"id": "node2", "sensors": ["only"]},
        ]
    }
    mapping = build_mapping(config)
    assert mapping["node1"]["sensors"] == {}
    assert mapping["node2"]["sensors"]["only"] == GPIO_PINS[0]
