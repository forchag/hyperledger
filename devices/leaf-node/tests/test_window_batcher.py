import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from telemetry.summary_store import SummaryStore
from telemetry.window import WindowBatcher


def test_window_summary_and_tail(tmp_path):
    store_path = tmp_path / "store.json"
    state_path = tmp_path / "state.json"
    store = SummaryStore(str(store_path))
    wm = WindowBatcher(60, store, tail_size=5, state_path=str(state_path))

    base = time.time()
    start = int((base + 10) // 60 * 60)
    wm.add_sample({"ts": base + 10, "value": 1})
    wm.add_sample({"ts": start + 30, "value": 3})
    wm.add_sample({"ts": start + 65, "value": 5})  # closes first window

    summary = store.peek()
    assert summary["window_id"] == [start, start + 60]
    assert summary["stats"]["min"] == 1
    assert summary["stats"]["max"] == 3
    assert summary["last_sample"]["value"] == 3
    assert summary["tail"] == [1, 3]


def test_resume_and_sequence(tmp_path):
    store_path = tmp_path / "store.json"
    state_path = tmp_path / "state.json"
    store = SummaryStore(str(store_path))
    wm = WindowBatcher(60, store, tail_size=5, state_path=str(state_path))

    base = time.time()
    start = int((base + 5) // 60 * 60)
    wm.add_sample({"ts": base + 5, "value": 2})
    # simulate reboot
    wm2 = WindowBatcher(60, store, tail_size=5, state_path=str(state_path))
    wm2.add_sample({"ts": start + 35, "value": 4})
    wm2.add_sample({"ts": start + 65, "value": 6})  # closes first window
    wm2.flush()

    first = store.dequeue()
    second = store.dequeue()
    assert first["seq"] == 1
    assert second["seq"] == 2
    assert second["stats"]["count"] == 1  # window after reboot has one sample


def test_store_and_forward_expiry(tmp_path):
    store_path = tmp_path / "store.json"
    state_path = tmp_path / "state.json"
    store = SummaryStore(str(store_path), expiry_sec=1)
    wm = WindowBatcher(60, store, tail_size=5, state_path=str(state_path))

    base = time.time()
    wm.add_sample({"ts": base, "value": 1})
    wm.add_sample({"ts": base + 60, "value": 2})  # closes window

    assert store.peek() is not None
    # mark as very old
    store.queue[0]["window_id"][1] = 0
    store._persist()

    store2 = SummaryStore(str(store_path), expiry_sec=1)
    assert store2.peek() is None
