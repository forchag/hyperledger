#!/usr/bin/env python3
"""Automated node bootstrapping for Hyperledger Fabric peers.

This script consolidates enrollment, channel joining and ledger synchronization
into a single idempotent workflow.  It is intended to run automatically on node
start-up and may be invoked repeatedly without side effects.  Progress is logged
and a machine-readable status file is produced that summarises readiness.

On a clean run the following steps are executed in order:

* Enroll the peer's identity with the Certificate Authority (CA).
* Fetch the channel configuration block and join the peer to the channel.
* Wait for the peer's ledger to catch up with the network height.
* Activate committed chaincodes to verify their responsiveness.

A ``bootstrap_status.json`` file tracks completion of each step so that later
runs can fast-path to verification rather than performing the full workflow
again.  The status file is also exposed through the Flask application for
inspection via the web UI.
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from identity_enrollment import enroll_identity, _certificate_valid
from peer_join_sync import (
    activate_committed_chaincodes,
    fetch_channel_block,
    join_channel,
    wait_for_sync,
)


LOG_FILE = Path("bootstrap.log")
STATUS_FILE = Path("bootstrap_status.json")
READY_FLAG = Path("peer.ready")


def _write_status(status: Dict[str, Any]) -> None:
    """Persist ``status`` to ``STATUS_FILE`` with an updated timestamp."""
    status = dict(status)
    status["timestamp"] = datetime.utcnow().isoformat() + "Z"
    status["ready"] = all(
        status.get(k)
        for k in ["ca_enrolled", "channel_joined", "ledger_synced", "chaincodes_healthy"]
    )
    STATUS_FILE.write_text(json.dumps(status, indent=2))


def _load_status() -> Dict[str, Any]:
    if STATUS_FILE.exists():
        try:
            return json.loads(STATUS_FILE.read_text())
        except Exception:  # noqa: BLE001
            return {}
    return {}


def bootstrap(args: argparse.Namespace) -> Dict[str, Any]:
    """Run the full bootstrap or a verification pass if previously completed."""
    logger = logging.getLogger("bootstrap")
    logger.info("Starting node bootstrap")

    status: Dict[str, Any] = {
        "ca_enrolled": False,
        "channel_joined": False,
        "ledger_synced": False,
        "chaincodes_healthy": False,
    }

    previous = _load_status()
    full_run = not previous.get("ready")

    if not full_run:
        logger.info("Prior successful state detected; performing verification")
        msp_cert = Path(args.msp_dir) / "signcerts" / "cert.pem"
        tls_cert = Path(args.tls_dir) / "server.crt"
        status["ca_enrolled"] = _certificate_valid(msp_cert) and _certificate_valid(tls_cert)
        try:
            wait_for_sync(args.channel, args.orderer, args.ca_cert, timeout=args.timeout)
            status["ledger_synced"] = True
            status["channel_joined"] = True  # implied by successful query
        except Exception as exc:  # noqa: BLE001
            logger.error("Ledger sync verification failed: %s", exc)
        try:
            activate_committed_chaincodes(args.channel, READY_FLAG)
            status["chaincodes_healthy"] = True
        except Exception as exc:  # noqa: BLE001
            logger.error("Chaincode health check failed: %s", exc)
        _write_status(status)
        return status

    # ---- Full bootstrap ----
    try:
        logger.info("Enrolling identity via CA")
        enroll_identity(
            args.node_name,
            args.ca_url,
            args.msp_dir,
            args.tls_dir,
            args.peer_endpoint,
            args.orderer,
            csr_hosts=args.csr_hosts,
        )
        status["ca_enrolled"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("CA enrollment failed: %s", exc)
        _write_status(status)
        return status

    try:
        logger.info("Fetching channel block and joining peer")
        fetch_channel_block(args.channel, args.orderer, args.ca_cert, args.block_path)
        join_channel(args.block_path)
        status["channel_joined"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Channel join failed: %s", exc)
        _write_status(status)
        return status

    try:
        logger.info("Waiting for ledger to synchronize")
        wait_for_sync(
            args.channel,
            args.orderer,
            args.ca_cert,
            interval=args.interval,
            timeout=args.timeout,
        )
        status["ledger_synced"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ledger synchronization failed: %s", exc)
        _write_status(status)
        return status

    try:
        logger.info("Activating committed chaincodes")
        activate_committed_chaincodes(args.channel, READY_FLAG)
        status["chaincodes_healthy"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chaincode activation failed: %s", exc)

    _write_status(status)
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a Fabric peer node")
    parser.add_argument("channel", help="Channel name to join")
    parser.add_argument("orderer", help="Orderer endpoint (host:port)")
    parser.add_argument("ca_cert", help="Path to orderer TLS CA cert")
    parser.add_argument("ca_url", help="URL of certificate authority")
    parser.add_argument("node_name", help="Identity to enroll with the CA")
    parser.add_argument("peer_endpoint", help="Host:port of the local peer")
    parser.add_argument("msp_dir", help="Directory for MSP materials")
    parser.add_argument("tls_dir", help="Directory for TLS materials")
    parser.add_argument("block_path", help="Where to store the channel block")
    parser.add_argument("--csr-hosts", nargs="*", default=None, help="Hosts for TLS CSR")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between height checks")
    parser.add_argument("--timeout", type=float, default=300.0, help="Max seconds to wait for sync")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(),
        ],
    )
    bootstrap(args)


if __name__ == "__main__":
    main()
