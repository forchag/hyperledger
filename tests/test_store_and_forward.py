import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location("hlf_client", Path("flask_app/hlf_client.py"))
hlf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hlf)


def test_store_and_forward(monkeypatch, tmp_path):
    monkeypatch.setattr(hlf, "BACKLOG_DIR", tmp_path)
    monkeypatch.setattr(hlf, "_schedule_retry", lambda device_id: None)

    def failing(*args):
        raise RuntimeError("down")

    monkeypatch.setattr(hlf, "_record_sensor_data_direct", failing)

    hlf.record_sensor_data("dev1", 1, 0, 0, 0, 0, 0, 0, "t", {})
    hlf.DEVICE_QUEUES["dev1"].join()

    stats = hlf.get_backlog_stats()
    assert stats == {"dev1": 1}

    sent = []

    def succeed(*args):
        sent.append(args[1])

    monkeypatch.setattr(hlf, "_record_sensor_data_direct", succeed)
    hlf._flush_backlog("dev1")

    assert sent == [1]
    assert hlf.get_backlog_stats() == {}
