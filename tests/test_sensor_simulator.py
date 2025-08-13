import sys
import types
import subprocess
import importlib
from pathlib import Path

import pytest

# Stub out heavy dependencies imported by sensor_simulator
hlf_client_stub = types.ModuleType("hlf_client")
hlf_client_stub.record_sensor_data = lambda *args, **kwargs: None
hlf_client_stub.register_device = lambda *args, **kwargs: None
pkg = types.ModuleType("flask_app")
pkg.hlf_client = hlf_client_stub
sys.modules.setdefault("flask_app", pkg)
sys.modules["flask_app.hlf_client"] = hlf_client_stub

from sensor_simulator import build_mapping, GPIO_PINS, DEFAULT_SENSORS


def test_build_mapping_basic_multiple_nodes():
    config = {
        "nodes": [
            {"id": "node1", "sensors": ["temp", "humidity"]},
            {"id": "node2", "ip": "10.0.0.2", "sensors": ["ph"]},
        ]
    }
    mapping = build_mapping(config)
    assert mapping["node2"]["ip"] == "10.0.0.2"
    assert mapping["node1"]["sensors"] == {"temp": GPIO_PINS[0], "humidity": GPIO_PINS[1]}
    assert mapping["node2"]["sensors"] == {"ph": GPIO_PINS[0]}
    assert mapping["node1"]["ip"].startswith("192.168.0.")


def test_build_mapping_generates_unique_ips():
    config = {"nodes": [{"id": f"n{i}"} for i in range(1, 6)]}
    mapping = build_mapping(config)
    ips = [info["ip"] for info in mapping.values()]
    assert len(set(ips)) == len(ips)
    assert all(ip.startswith("192.168.0.") for ip in ips)


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
    expected_defaults = {s: GPIO_PINS[i] for i, s in enumerate(DEFAULT_SENSORS)}
    assert mapping["node1"]["sensors"] == expected_defaults
    assert mapping["node2"]["sensors"]["only"] == GPIO_PINS[0]


def test_simulation_updates_app_and_registers_devices(monkeypatch):
    """Posting to /simulate should populate NODE_MAP and register sensors."""

    # Remove the stubbed modules so the real Flask app can be imported
    sys.modules.pop("flask_app", None)
    sys.modules.pop("flask_app.hlf_client", None)
    sys.modules.pop("hlf_client", None)
    extra_path = str(Path(__file__).resolve().parents[1] / "flask_app")
    sys.path.append(extra_path)
    app_mod = importlib.import_module("flask_app.app")
    import hlf_client

    app_mod.NODE_MAP.clear()
    hlf_client.DEVICES.clear()

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: None)
    client = app_mod.app.test_client()
    resp = client.post(
        "/simulate",
        json={"nodes": [{"id": "node1"}, {"id": "node2", "ip": "10.0.0.2", "sensors": ["ph"]}]},
    )
    assert resp.status_code == 200
    mapping = resp.get_json()["mapping"]
    assert app_mod.NODE_MAP == mapping

    expected = {f"{n}_{s}" for n, info in mapping.items() for s in info["sensors"]}
    assert set(hlf_client.DEVICES) >= expected

    # Discover should now report the configured IPs
    resp = client.post(
        "/announce",
        json={
            "id": "node1",
            "ip": mapping["node1"]["ip"],
            "port": mapping["node1"].get("port", 8000),
        },
    )
    assert resp.status_code == 200
    resp = client.get("/discover")
    info = resp.get_json()
    ips = {n["ip"] for n in info["nodes"]}
    assert {m["ip"] for m in mapping.values()} <= ips

    # Clean up generated config file and globals
    cfg = Path(__file__).resolve().parents[1] / "simulator_config.json"
    if cfg.exists():
        cfg.unlink()
    hlf_client.DEVICES.clear()
    app_mod.NODE_MAP.clear()
    sys.path.remove(extra_path)


def test_announce_endpoint_updates_node_map():
    sys.modules.pop("flask_app", None)
    sys.modules.pop("flask_app.hlf_client", None)
    sys.modules.pop("hlf_client", None)
    extra_path = str(Path(__file__).resolve().parents[1] / "flask_app")
    sys.path.append(extra_path)
    app_mod = importlib.import_module("flask_app.app")

    client = app_mod.app.test_client()
    resp = client.post(
        "/announce", json={"id": "nodeA", "ip": "192.168.0.5", "port": 8123}
    )
    assert resp.status_code == 200
    assert app_mod.NODE_MAP["nodeA"]["ip"] == "192.168.0.5"
    assert app_mod.NODE_MAP["nodeA"]["port"] == 8123

    app_mod.NODE_MAP.clear()
    sys.path.remove(extra_path)
