import json
from pathlib import Path

import node_bootstrap


def test_write_status_ready(tmp_path, monkeypatch):
    dest = tmp_path / "status.json"
    monkeypatch.setattr(node_bootstrap, "STATUS_FILE", dest)
    status = {
        "HAVE_IDENTITY": True,
        "JOINED_CHANNEL": True,
        "LEDGER_SYNCED": True,
        "CC_READY": True,
    }
    node_bootstrap._write_status(status)
    data = json.loads(dest.read_text())
    assert data["ready"] is True
