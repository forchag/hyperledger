import json
from pathlib import Path

import sys
base = Path(__file__).resolve()
sys.path.append(str(base.parents[1]))  # leaf-node
sys.path.append(str(base.parents[3]))  # repo root

from telemetry.payload import build_payload, crt_encoder  # noqa: E402

MODULI = [401, 409, 419, 421, 431]


def test_payload_without_crt():
    summary = {
        "window_id": [0, 60],
        "stats": {"min": 1.0, "avg": 2.0, "max": 3.0, "std": 0.5, "count": 5},
        "last_ts": 1,
        "tail": [1, 2],
    }
    payload = build_payload(summary, size_limit=100)
    assert "stats" in payload
    assert "crt" not in payload
    body = json.dumps(payload, separators=(",", ":")).encode()
    assert len(body) <= 100


def test_payload_with_crt_and_tail_drop():
    summary = {
        "window_id": [0, 60],
        "stats": {"min": 1.0, "avg": 2.0, "max": 3.0, "std": 0.5, "count": 5},
        "last_ts": 1,
        "tail": list(range(20)),
    }
    payload = build_payload(summary, moduli=MODULI, size_limit=100)
    assert "crt" in payload
    assert "stats" not in payload
    assert "tail" not in payload
    body = json.dumps(payload, separators=(",", ":")).encode()
    assert len(body) <= 100
