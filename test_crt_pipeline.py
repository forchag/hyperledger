import hashlib
import json

from crt_pipeline import SensorNode, Gateway


def _truncate(val: float) -> float:
    return int(val * 100) / 100.0


def test_roundtrip_and_merkle():
    readings = [
        {"temperature": 20.0, "humidity": 55.0, "soil_moisture": 40.0},
        {"temperature": 22.0, "humidity": 50.0, "soil_moisture": 42.0},
        {"temperature": 24.0, "humidity": 53.0, "soil_moisture": 41.0},
    ]
    node = SensorNode("node1")
    stats = node.summarise(readings)
    payload = node.create_payload(readings, use_crt=True)
    gw = Gateway(use_crt=True)
    gw.ingest(payload)
    bundle = gw.compute_window()

    # Expected record after truncation to two decimals
    expected = {"device_id": "node1", "sensors": {}}
    for field, data in stats.items():
        expected["sensors"][field] = {
            "mean": _truncate(data["mean"]),
            "min": _truncate(data["min"]),
            "max": _truncate(data["max"]),
            "std": _truncate(data["std"]),
            "count": data["count"],
        }

    blob = json.dumps(expected, sort_keys=True).encode()
    expected_root = hashlib.sha256(blob).hexdigest()

    assert bundle["readings"][0] == expected
    assert bundle["merkle_root"] == expected_root
