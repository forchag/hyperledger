import importlib.util
import json
import sys
import time
import types
from pathlib import Path

import pytest

# Stub out the heavy hlf_client dependency so flask_app.app can be imported
fake_client = types.ModuleType("hlf_client")
for name in [
    "record_sensor_data",
    "register_device",
    "log_event",
    "get_sensor_data",
    "get_sensor_history",
    "get_all_sensor_data",
    "get_state_on",
    "get_latest_readings",
    "list_devices",
    "get_block",
    "get_incidents",
    "get_quarantined",
    "get_attestations",
    "get_block_events",
    "log_security_incident",
    "attest_device",
]:
    setattr(fake_client, name, lambda *a, **k: None)
sys.modules.setdefault("hlf_client", fake_client)

# Load orchestrator from flask_app.app
spec = importlib.util.spec_from_file_location("flask_app.app", Path("flask_app/app.py"))
apps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apps)  # type: ignore[misc]
sys.modules.pop("gateway_orchestrator", None)

Settings = apps.Settings
StoreAndForward = apps.StoreAndForward
FabricClient = apps.FabricClient
Bundler = apps.Bundler
IngressService = apps.IngressService
MeshMonitor = apps.MeshMonitor
HealthServer = apps.HealthServer
hmac_sha256 = apps.hmac_sha256


def setup_services(tmp_path, connected=True):
    cfg = Settings(
        uplink_period_min=1,
        event_coalesce_sec=1,
        event_rate_limit_per_pi=100,
        store_dir=str(tmp_path),
    )
    client = FabricClient(cfg)
    client.connected = connected
    store = StoreAndForward(cfg)
    bundler = Bundler(cfg, store, client)
    registry = {"leaf01": "secret"}
    ingress = IngressService(bundler, registry)
    return cfg, client, bundler, ingress, store


def make_packet(seq, urgent=False, window_id="0-1"):
    body = {
        "device_id": "leaf01",
        "seq": seq,
        "stats": {"temp": 1.0},
        "sensor_set": ["temp"],
        "urgent": urgent,
        "window_id": window_id,
    }
    payload = json.dumps(body, sort_keys=True).encode()
    body["sig"] = hmac_sha256("secret", payload)
    return body


def test_duplicate_rejection(tmp_path):
    cfg, client, bundler, ingress, store = setup_services(tmp_path)
    for i in range(5):
        ingress.ingest(make_packet(i))
    ingress.ingest(make_packet(4))  # duplicate
    assert sum(len(v) for v in bundler.readings.values()) == 5


def test_event_and_interval_submission(tmp_path):
    cfg, client, bundler, ingress, store = setup_services(tmp_path)
    ingress.ingest(make_packet(0, urgent=True))
    time.sleep(cfg.event_coalesce_sec + 0.1)
    ev = bundler.close_event_window()
    assert ev is not None
    bundler.submit_bundle(ev)
    assert client.submits and client.submits[0]["type"] == "event"

    for i in range(3):
        ingress.ingest(make_packet(i + 1))
    for b in bundler.pop_closed_windows():
        bundler.submit_bundle(b)
    assert any(s["type"] == "interval" for s in client.submits)


def test_store_and_forward(tmp_path):
    cfg, client, bundler, ingress, store = setup_services(tmp_path, connected=False)
    ingress.ingest(make_packet(1))
    for b in bundler.pop_closed_windows():
        bundler.submit_bundle(b)
    assert store.queue  # stored due to outage
    client.connected = True
    bundler.flush_store()
    assert not store.queue


def test_health_endpoints(tmp_path):
    cfg, client, bundler, ingress, store = setup_services(tmp_path)
    mesh = MeshMonitor(cfg)
    mesh.neighbors = ["peer"]
    hs = HealthServer(cfg, mesh, client)
    tc = hs.app.test_client()
    assert tc.get("/healthz").status_code == 200
    assert tc.get("/readyz").status_code == 503
    client.last_commit_time = time.time()
    assert tc.get("/readyz").status_code == 200
    assert tc.get("/metrics").status_code == 200
