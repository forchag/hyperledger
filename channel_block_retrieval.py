"""Helpers for retrieving and validating channel configuration blocks.

This module provides a utility to fetch a channel's genesis or configuration
block from a Fabric orderer or seed peer.  The block is only fetched when not
already present locally and is retrieved using TLS verification against
specified certificate authority roots.  To handle transient network
conditions, the operation is retried with exponential backoff.
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path


def _block_valid(block_path: Path) -> bool:
    """Return ``True`` if ``block_path`` exists and is non-empty."""
    try:
        return block_path.exists() and block_path.stat().st_size > 0
    except OSError:
        return False


def fetch_channel_block(
    channel_name: str,
    orderer_endpoint: str,
    ca_cert: Path | str,
    dest: Path | str,
    *,
    max_retries: int = 5,
    backoff: float = 1.0,
) -> bool:
    """Ensure the channel configuration block is present locally.

    Parameters
    ----------
    channel_name:
        The name of the channel to fetch.
    orderer_endpoint:
        ``host:port`` of the orderer or seed peer.
    ca_cert:
        Path to the trusted CA certificate used for TLS validation.
    dest:
        Destination file for the fetched block.
    max_retries:
        Maximum number of fetch attempts.  ``0`` means no retries.
    backoff:
        Initial delay in seconds between retries; doubled after each failure.

    Returns
    -------
    bool
        ``True`` if a fetch was performed, ``False`` if the existing block was
        deemed valid and no action was taken.
    """

    dest_path = Path(dest)
    if _block_valid(dest_path):
        return False

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    ca_cert = Path(ca_cert)

    attempt = 0
    while True:
        try:
            subprocess.run(
                [
                    "peer",
                    "channel",
                    "fetch",
                    "config",
                    str(dest_path),
                    "-o",
                    orderer_endpoint,
                    "-c",
                    channel_name,
                    "--tls",
                    "--cafile",
                    str(ca_cert),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if _block_valid(dest_path):
                return True
        except subprocess.CalledProcessError:
            attempt += 1
            if attempt > max_retries:
                raise
            time.sleep(backoff)
            backoff *= 2
            continue
        break
    return True
