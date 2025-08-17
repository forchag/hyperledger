"""Utility functions for Hyperledger Fabric identity enrollment.

This module provides a helper to ensure a peer node has valid MSP and TLS
certificates by registering and enrolling with a Fabric Certificate
Authority.  The process is designed to be idempotent: if existing
certificates are present and not close to expiry, no network operations are
performed.
"""

from __future__ import annotations

import datetime as _dt
import os
import socket
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend


def _endpoint_up(endpoint: str, timeout: float = 5.0) -> bool:
    """Return True if ``host:port`` is reachable via TCP."""
    host, port = endpoint.split(":", 1)
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _certificate_valid(cert_path: Path, min_validity: int = 3600) -> bool:
    """Check that ``cert_path`` exists and is not expiring soon.

    ``min_validity`` is the minimum number of seconds the certificate must
    remain valid.  If the certificate is missing or invalid, ``False`` is
    returned.
    """
    cert_file = Path(cert_path)
    if not cert_file.exists():
        return False
    try:
        cert = x509.load_pem_x509_certificate(cert_file.read_bytes(), default_backend())
    except Exception:
        return False
    remaining = cert.not_valid_after - _dt.datetime.utcnow()
    return remaining.total_seconds() > min_validity


def enroll_identity(
    node_name: str,
    ca_url: str,
    msp_dir: Path | str,
    tls_dir: Path | str,
    peer_endpoint: str,
    orderer_endpoint: str,
    *,
    csr_hosts: Optional[Iterable[str]] = None,
    secret: str = "pw",
    min_validity: int = 3600,
) -> bool:
    """Ensure certificates for ``node_name`` exist and are valid.

    Returns ``True`` if a (re-)enrollment was performed, ``False`` if the
    existing certificates were deemed valid and no action was taken.
    """

    if not (_endpoint_up(peer_endpoint) and _endpoint_up(orderer_endpoint)):
        raise RuntimeError("Network baseline is not alive")

    msp_dir = Path(msp_dir)
    tls_dir = Path(tls_dir)
    msp_cert = msp_dir / "signcerts" / "cert.pem"
    tls_cert = tls_dir / "server.crt"

    if _certificate_valid(msp_cert, min_validity) and _certificate_valid(tls_cert, min_validity):
        return False

    msp_dir.mkdir(parents=True, exist_ok=True)
    tls_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("FABRIC_CA_CLIENT_HOME", str(msp_dir.parent))

    # Register identity (idempotent; errors are ignored if already registered)
    try:
        subprocess.run(
            [
                "fabric-ca-client",
                "register",
                f"--id.name={node_name}",
                f"--id.secret={secret}",
                "--id.type=peer",
                "-u",
                ca_url,
            ],
            check=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError:
        pass

    # Enroll for MSP
    subprocess.run(
        [
            "fabric-ca-client",
            "enroll",
            "-u",
            f"http://{node_name}:{secret}@{ca_url}",
            "-M",
            str(msp_dir),
        ],
        check=True,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Enroll for TLS
    tls_args = [
        "fabric-ca-client",
        "enroll",
        "-u",
        f"http://{node_name}:{secret}@{ca_url}",
        "--enrollment.profile",
        "tls",
        "-M",
        str(tls_dir),
    ]
    if csr_hosts:
        tls_args.extend(["--csr.hosts", ",".join(csr_hosts)])
    subprocess.run(tls_args, check=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    return True
