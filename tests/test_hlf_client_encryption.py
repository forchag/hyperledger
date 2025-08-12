import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from flask_app.hlf_client import encrypt_payload, decrypt_payload


def test_encrypt_decrypt_large_payload():
    # Build a payload that would exceed RSA limits without compression
    payload = {
        "id": "sensor",
        "data": "x" * 300,  # repeated data to push size over RSA block limit
    }
    enc = encrypt_payload(payload)
    dec = decrypt_payload(enc)
    assert dec == payload
