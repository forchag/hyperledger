import importlib.util
from pathlib import Path


def load_client(monkeypatch, env=None):
    if env:
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
    spec = importlib.util.spec_from_file_location("hlf_client", Path("flask_app/hlf_client.py"))
    hlf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hlf)
    return hlf


def test_time_interval_block_creation(monkeypatch):
    hlf = load_client(monkeypatch, {"BLOCK_INTERVAL_MINUTES": 30})
    now = 1000
    monkeypatch.setattr(hlf.time, "time", lambda: now)
    assert hlf._should_create_block("s1", 50, 7, 50) == "scheduled"
    now += 60
    monkeypatch.setattr(hlf.time, "time", lambda: now)
    assert hlf._should_create_block("s1", 50, 7, 50) is None
    now += 30 * 60
    monkeypatch.setattr(hlf.time, "time", lambda: now)
    assert hlf._should_create_block("s1", 50, 7, 50) == "scheduled"


def test_event_trigger_block_creation(monkeypatch):
    hlf = load_client(monkeypatch, {"BLOCK_INTERVAL_MINUTES": 120})
    start = 2000
    monkeypatch.setattr(hlf.time, "time", lambda: start)
    # initial reading creates block and sets baseline
    hlf._should_create_block("s1", 50, 7, 50)
    hlf.LAST_BLOCK_TIME = start
    # Soil moisture trigger
    monkeypatch.setattr(hlf.time, "time", lambda: start + 10)
    assert (
        hlf._should_create_block("s1", hlf.SOIL_MOISTURE_THRESHOLD - 1, 7, 50)
        == "event"
    )
    hlf.LAST_BLOCK_TIME = start + 10
    # pH change trigger
    monkeypatch.setattr(hlf.time, "time", lambda: start + 20)
    baseline = hlf.LAST_PH["s1"]
    assert (
        hlf._should_create_block(
            "s1", 50, baseline + hlf.PH_CHANGE_THRESHOLD + 0.1, 50
        )
        == "event"
    )
