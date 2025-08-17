import flask_app.hlf_client as hlf


def test_scheduled_and_event_blocks(monkeypatch):
    hlf.CURRENT_BLOCK = 0
    hlf.BLOCK_EVENTS.clear()
    hlf.SENSOR_DATA.clear()
    hlf.LAST_SEQ.clear()
    hlf.LAST_PH.clear()
    hlf.BLOCK_BUFFER.clear()
    hlf.LAST_BLOCK_TIME = 0.0
    monkeypatch.setattr(hlf, "BLOCK_INTERVAL_MINUTES", 1)

    times = iter([1000, 1030, 1061, 1070])
    monkeypatch.setattr(hlf.time, "time", lambda: next(times))

    hlf._record_sensor_data_direct("s1", 1, 25, 40, 50, 7.0, 200, 50, 1000, {})
    hlf._record_sensor_data_direct("s1", 2, 25, 40, 50, 7.0, 200, 50, 1030, {})
    hlf._record_sensor_data_direct("s1", 3, 25, 40, 50, 7.0, 200, 50, 1061, {})
    hlf._record_sensor_data_direct("s1", 4, 25, 40, 5, 7.0, 200, 50, 1070, {})

    messages = [e["message"] for e in hlf.BLOCK_EVENTS if e["message"].startswith("Creating")]
    assert messages[0].startswith("Creating scheduled block 1")
    assert messages[1].startswith("Creating scheduled block 2")
    assert messages[2].startswith("Creating event block 3")
