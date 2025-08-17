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
import os
import subprocess
import time
from contextlib import contextmanager
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


def _peer_version() -> str:
    """Return the local peer binary version if available."""
    try:
        result = subprocess.run(
            ["peer", "version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split("Version:", 1)[1].strip()
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


@contextmanager
def log_step(name: str):
    """Context manager that logs start/end/duration of a bootstrap step."""
    logger = logging.getLogger("bootstrap")
    logger.info("start %s", name)
    start = time.time()
    try:
        yield
    except Exception:
        duration = time.time() - start
        logger.exception("error %s (%.2fs)", name, duration)
        raise
    else:
        duration = time.time() - start
        logger.info("end %s (%.2fs)", name, duration)


def _write_status(status: Dict[str, Any], info: Dict[str, Any] | None = None) -> None:
    """Persist ``status`` and optional ``info`` to ``STATUS_FILE``."""
    status = dict(status)
    if info:
        status.update(info)
    status["timestamp"] = datetime.utcnow().isoformat() + "Z"
    status["ready"] = all(
        status.get(k)
        for k in ["HAVE_IDENTITY", "JOINED_CHANNEL", "LEDGER_SYNCED", "CC_READY"]
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

    os.environ.update(
        {
            "FABRIC_CHANNEL": args.channel,
            "FABRIC_ORDERER": args.orderer,
            "FABRIC_CA_URL": args.ca_url,
            "FABRIC_PEER": args.peer_endpoint,
        }
    )

    info = {
        "endpoints": {"peer": args.peer_endpoint, "orderer": args.orderer},
        "fabric_version": _peer_version(),
    }

    status: Dict[str, Any] = {
        "HAVE_IDENTITY": False,
        "JOINED_CHANNEL": False,
        "LEDGER_SYNCED": False,
        "CC_READY": False,
    }

    previous = _load_status()
    full_run = not previous.get("ready")

    if not full_run:
        logger.info("Prior successful state detected; performing verification")
        msp_cert = Path(args.msp_dir) / "signcerts" / "cert.pem"
        tls_cert = Path(args.tls_dir) / "server.crt"
        status["HAVE_IDENTITY"] = _certificate_valid(msp_cert) and _certificate_valid(tls_cert)
        try:
            with log_step("ledger sync check"):
                wait_for_sync(args.channel, args.orderer, args.ca_cert, timeout=args.timeout)
            status["LEDGER_SYNCED"] = True
            status["JOINED_CHANNEL"] = True
        except Exception as exc:  # noqa: BLE001
            logger.error("Ledger sync verification failed: %s", exc)
        try:
            with log_step("chaincode health check"):
                activate_committed_chaincodes(args.channel, READY_FLAG)
            status["CC_READY"] = True
        except Exception as exc:  # noqa: BLE001
            logger.error("Chaincode health check failed: %s", exc)
        _write_status(status, info)
        return status

    # ---- Full bootstrap ----
    try:
        with log_step("enroll identity"):
            enroll_identity(
                args.node_name,
                args.ca_url,
                args.msp_dir,
                args.tls_dir,
                args.peer_endpoint,
                args.orderer,
                csr_hosts=args.csr_hosts,
            )
        status["HAVE_IDENTITY"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("CA enrollment failed: %s", exc)
        _write_status(status, info)
        return status

    try:
        with log_step("join channel"):
            fetch_channel_block(args.channel, args.orderer, args.ca_cert, args.block_path)
            join_channel(args.block_path)
        status["JOINED_CHANNEL"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Channel join failed: %s", exc)
        _write_status(status, info)
        return status

    try:
        with log_step("ledger sync"):
            wait_for_sync(
                args.channel,
                args.orderer,
                args.ca_cert,
                interval=args.interval,
                timeout=args.timeout,
            )
        status["LEDGER_SYNCED"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ledger synchronization failed: %s", exc)
        _write_status(status, info)
        return status

    try:
        with log_step("activate chaincodes"):
            activate_committed_chaincodes(args.channel, READY_FLAG)
        status["CC_READY"] = True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chaincode activation failed: %s", exc)

    _write_status(status, info)
    return status


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a Fabric peer node")
    parser.add_argument("--config", help="Path to JSON configuration", default=None)
    parser.add_argument("--channel", help="Channel name to join")
    parser.add_argument("--orderer", help="Orderer endpoint (host:port)")
    parser.add_argument("--ca_cert", help="Path to orderer TLS CA cert")
    parser.add_argument("--ca_url", help="URL of certificate authority")
    parser.add_argument("--node_name", help="Identity to enroll with the CA")
    parser.add_argument("--peer_endpoint", help="Host:port of the local peer")
    parser.add_argument("--msp_dir", help="Directory for MSP materials")
    parser.add_argument("--tls_dir", help="Directory for TLS materials")
    parser.add_argument("--block_path", help="Where to store the channel block")
    parser.add_argument("--csr-hosts", nargs="*", default=None, help="Hosts for TLS CSR")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between height checks")
    parser.add_argument("--timeout", type=float, default=300.0, help="Max seconds to wait for sync")
    args = parser.parse_args()

    if args.config:
        data = json.loads(Path(args.config).read_text())
        for key, value in data.items():
            if getattr(args, key, None) is None:
                setattr(args, key, value)

    required = [
        "channel",
        "orderer",
        "ca_cert",
        "ca_url",
        "node_name",
        "peer_endpoint",
        "msp_dir",
        "tls_dir",
        "block_path",
    ]
    missing = [k for k in required if getattr(args, k, None) is None]
    if missing:
        parser.error("Missing required parameters: " + ", ".join(missing))

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
