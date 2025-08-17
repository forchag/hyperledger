"""Utilities for joining a peer to a Fabric channel and waiting for ledger sync.

This module automates the workflow described in the project documentation:

* Retrieve a channel's configuration block (if not already present).
* Join the local peer to the channel using that block.
* Poll both the local ledger height and the network's latest block height.
* Block until the peer has caught up before allowing it to service requests.

The functions rely on the Hyperledger Fabric ``peer`` CLI being available in the
execution environment.  They do not start or stop the peer process; callers
should ensure the peer is running but not registered as an endorser until
``wait_for_sync`` has completed successfully.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from channel_block_retrieval import fetch_channel_block


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Run ``cmd`` and return the completed process with text output."""
    return subprocess.run(
        cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def join_channel(channel_block: Path | str) -> None:
    """Join the peer to the channel using ``channel_block``."""
    block = Path(channel_block)
    _run(["peer", "channel", "join", "-b", str(block)])


def _local_height(channel: str) -> int:
    """Return the local ledger height for ``channel``."""
    result = _run(["peer", "channel", "getinfo", "-c", channel])
    for line in result.stdout.splitlines():
        if "height:" in line:
            # line format: 'Blockchain info: height: 4, ...'
            try:
                return int(line.split("height:")[1].split(",")[0].strip())
            except ValueError:
                continue
    raise RuntimeError("Unable to parse local ledger height")


def _network_height(channel: str, orderer: str, ca_cert: Path | str) -> int:
    """Return the current network height by fetching the newest block."""
    temp_block = Path("newest.block")
    try:
        result = _run(
            [
                "peer",
                "channel",
                "fetch",
                "newest",
                str(temp_block),
                "-o",
                orderer,
                "-c",
                channel,
                "--tls",
                "--cafile",
                str(ca_cert),
            ]
        )
        for line in result.stdout.splitlines():
            if "Received block:" in line:
                # Output example: 'Received block: 5'
                try:
                    return int(line.split(":")[1].strip()) + 1
                except ValueError:
                    continue
    finally:
        if temp_block.exists():
            temp_block.unlink()
    raise RuntimeError("Unable to determine network height")


def wait_for_sync(
    channel: str,
    orderer: str,
    ca_cert: Path | str,
    *,
    interval: float = 5.0,
    timeout: float = 300.0,
) -> None:
    """Block until the peer's ledger matches the network height.

    Parameters
    ----------
    channel:
        Name of the channel to inspect.
    orderer:
        ``host:port`` of the orderer used to query the latest block.
    ca_cert:
        Path to the TLS certificate for the orderer.
    interval:
        Seconds between height checks.
    timeout:
        Maximum time to wait before raising ``TimeoutError``.
    """

    deadline = time.time() + timeout
    while True:
        local = _local_height(channel)
        network = _network_height(channel, orderer, ca_cert)
        if local >= network:
            return
        if time.time() > deadline:
            raise TimeoutError(
                f"Peer did not catch up within {timeout} seconds (local={local}, network={network})"
            )
        time.sleep(interval)


def join_and_sync(
    channel: str,
    orderer: str,
    ca_cert: Path | str,
    block_path: Path | str,
    *,
    interval: float = 5.0,
    timeout: float = 300.0,
) -> None:
    """Fetch the channel block, join the peer, and wait for ledger sync."""
    fetch_channel_block(channel, orderer, ca_cert, block_path)
    join_channel(block_path)
    wait_for_sync(channel, orderer, ca_cert, interval=interval, timeout=timeout)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Join peer to channel and wait for ledger sync")
    parser.add_argument("channel", help="Name of the channel to join")
    parser.add_argument("orderer", help="Orderer endpoint, e.g. orderer.example.com:7050")
    parser.add_argument("ca_cert", help="Path to TLS CA certificate for the orderer")
    parser.add_argument(
        "block", help="Path where the channel configuration block should be stored"
    )
    parser.add_argument(
        "--interval", type=float, default=5.0, help="Seconds between height checks"
    )
    parser.add_argument(
        "--timeout", type=float, default=300.0, help="Maximum seconds to wait"
    )

    args = parser.parse_args()
    join_and_sync(
        args.channel,
        args.orderer,
        Path(args.ca_cert),
        Path(args.block),
        interval=args.interval,
        timeout=args.timeout,
    )
