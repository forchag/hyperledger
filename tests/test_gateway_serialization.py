import threading
import time
import importlib.util
from pathlib import Path


spec = importlib.util.spec_from_file_location("hlf_client", Path("flask_app/hlf_client.py"))
hlf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hlf)


def test_per_device_serialization(monkeypatch, tmp_path):
    # use temporary backlog directory and disable retry timers for determinism
    monkeypatch.setattr(hlf, "BACKLOG_DIR", tmp_path)
    monkeypatch.setattr(hlf, "_schedule_retry", lambda device_id: None)

    processed = []

    def fake_send(*args):
        # append sequence to verify ordering
        processed.append(args[1])

    monkeypatch.setattr(hlf, "_record_sensor_data_direct", fake_send)

    threads = []
    for seq in range(5):
        t = threading.Thread(
            target=hlf.record_sensor_data,
            args=("dev", seq, 0, 0, 0, 0, 0, 0, "t", {}),
        )
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    # wait for worker to finish
    hlf.DEVICE_QUEUES["dev"].join()

    assert processed == list(range(5))


def test_parallel_across_devices(monkeypatch, tmp_path):
    monkeypatch.setattr(hlf, "BACKLOG_DIR", tmp_path)
    monkeypatch.setattr(hlf, "_schedule_retry", lambda device_id: None)

    def fake_send(*args):
        time.sleep(0.1)

    monkeypatch.setattr(hlf, "_record_sensor_data_direct", fake_send)

    start = time.time()
    t1 = threading.Thread(
        target=hlf.record_sensor_data, args=("a", 1, 0, 0, 0, 0, 0, 0, "t", {})
    )
    t2 = threading.Thread(
        target=hlf.record_sensor_data, args=("b", 1, 0, 0, 0, 0, 0, 0, "t", {})
    )
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    hlf.DEVICE_QUEUES["a"].join()
    hlf.DEVICE_QUEUES["b"].join()
    duration = time.time() - start

    assert duration < 0.2
