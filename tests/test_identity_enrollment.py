import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from identity_enrollment import enroll_identity


def _write_cert(path: Path, expire_after: int) -> None:
    """Create a self-signed certificate at ``path`` valid for ``expire_after`` seconds."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    now = datetime.utcnow()
    
    if expire_after >= 0:
        not_before = now
        not_after = now + timedelta(seconds=expire_after)
    else:
        not_after = now + timedelta(seconds=expire_after)
        not_before = not_after - timedelta(days=1)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .sign(key, hashes.SHA256())
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def test_enroll_skips_if_certificates_valid(tmp_path):
    msp_dir = tmp_path / "msp"
    tls_dir = tmp_path / "tls"
    _write_cert(msp_dir / "signcerts" / "cert.pem", 86400)
    _write_cert(tls_dir / "server.crt", 86400)

    with patch("identity_enrollment._endpoint_up", return_value=True), patch("subprocess.run") as run_mock:
        result = enroll_identity(
            "peer0",
            "http://ca:7054",
            msp_dir,
            tls_dir,
            "peer.example.com:7051",
            "orderer.example.com:7050",
        )
    assert result is False
    run_mock.assert_not_called()


def test_enroll_runs_when_certificate_missing(tmp_path):
    msp_dir = tmp_path / "msp"
    tls_dir = tmp_path / "tls"
    _write_cert(msp_dir / "signcerts" / "cert.pem", -3600)  # expired

    with patch("identity_enrollment._endpoint_up", return_value=True), patch("subprocess.run") as run_mock:
        run_mock.return_value = subprocess.CompletedProcess(args=[], returncode=0)
        result = enroll_identity(
            "peer0",
            "http://ca:7054",
            msp_dir,
            tls_dir,
            "peer.example.com:7051",
            "orderer.example.com:7050",
        )
    assert result is True
    assert run_mock.called
