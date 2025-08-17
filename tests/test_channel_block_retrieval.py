import subprocess
from pathlib import Path
from unittest.mock import patch

from channel_block_retrieval import fetch_channel_block


def test_fetch_skips_if_block_exists(tmp_path):
    block = tmp_path / "mychannel.block"
    block.write_bytes(b"existing")
    ca_cert = tmp_path / "ca.crt"
    ca_cert.write_text("cert")

    with patch("channel_block_retrieval.subprocess.run") as run_mock:
        result = fetch_channel_block("mychannel", "orderer.example.com:7050", ca_cert, block)
    assert result is False
    run_mock.assert_not_called()


def test_fetch_retries_and_saves(tmp_path):
    block = tmp_path / "mychannel.block"
    ca_cert = tmp_path / "ca.crt"
    ca_cert.write_text("cert")

    attempts = {"count": 0}

    def run_side_effect(cmd, check, stdout, stderr):
        if attempts["count"] < 2:
            attempts["count"] += 1
            raise subprocess.CalledProcessError(1, cmd)
        block.write_bytes(b"blockdata")
        return subprocess.CompletedProcess(cmd, 0)

    sleeps = []

    with patch("channel_block_retrieval.subprocess.run", side_effect=run_side_effect) as run_mock, patch(
        "channel_block_retrieval.time.sleep", side_effect=lambda s: sleeps.append(s)
    ):
        result = fetch_channel_block(
            "mychannel",
            "orderer.example.com:7050",
            ca_cert,
            block,
            max_retries=5,
            backoff=1,
        )
    assert result is True
    assert block.read_bytes() == b"blockdata"
    assert run_mock.call_count == 3
    assert sleeps == [1, 2]
