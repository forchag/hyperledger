import subprocess
from pathlib import Path
from unittest.mock import patch

import peer_join_sync


def test_activate_committed_chaincodes_starts_and_marks(tmp_path):
    ready = tmp_path / "ready.flag"
    side_effects = [
        subprocess.CompletedProcess(
            ["peer", "lifecycle", "chaincode", "querycommitted"],
            0,
            stdout="Name: sensor, Version: 1, Sequence: 1\n",
            stderr="",
        ),
        subprocess.CompletedProcess(
            ["peer", "chaincode", "query"], 0, stdout="OK", stderr=""
        ),
    ]
    with patch("peer_join_sync._run", side_effect=side_effects) as run_mock:
        names = peer_join_sync.activate_committed_chaincodes("mychannel", ready)
    assert names == ["sensor"]
    assert ready.exists()
    assert run_mock.call_count == 2


def test_activate_committed_chaincodes_none(tmp_path):
    ready = tmp_path / "ready.flag"
    with patch(
        "peer_join_sync._run",
        return_value=subprocess.CompletedProcess(
            ["peer", "lifecycle", "chaincode", "querycommitted"],
            0,
            stdout="",
            stderr="",
        ),
    ) as run_mock:
        names = peer_join_sync.activate_committed_chaincodes("mychannel", ready)
    assert names == []
    assert ready.exists()
    run_mock.assert_called_once()
