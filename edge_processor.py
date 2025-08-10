import numpy as np
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization

# Reuse generic CRT utilities for agricultural data
from crt_agri import (
    CRTResidues,
    compress_values,
    recover_values,
    scale_values,
)

@dataclass
class Features:
    min_val: float
    max_val: float
    mean: float
    std: float
    p10: float
    median: float
    p90: float


def extract_features(samples):
    """Return seven statistical features for a list of numbers."""
    arr = np.array(samples)
    return Features(
        float(np.min(arr)),
        float(np.max(arr)),
        float(np.mean(arr)),
        float(np.std(arr)),
        float(np.percentile(arr, 10)),
        float(np.percentile(arr, 50)),
        float(np.percentile(arr, 90)),
    )


def crt_compress(feat: Features) -> CRTResidues:
    """Compress selected features into CRT residues."""
    values = {
        "mean": feat.mean,
        "std": feat.std,
        "max": feat.max_val,
        "min": feat.min_val,
        "N": 0,
        "P": 0,
        "K": 0,
    }
    scaled = scale_values(values)
    return compress_values(scaled)

def recover_features(residues: CRTResidues) -> dict:
    """Recover original feature values from CRT residues."""
    rec = recover_values(residues)
    return {
        "min": rec["min"],
        "max": rec["max"],
        "mean": rec["mean"],
        "std": rec["std"],
    }


def generate_private_key(path: str):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(path, "wb") as f:
        f.write(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
    return key


def load_private_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def sign_payload(payload: bytes, private_key) -> bytes:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(payload)
    signature = private_key.sign(
        digest.finalize(),
        padding.PKCS1v15(),
    )
    return signature[:33]


def verify_signature(payload: bytes, signature: bytes, public_key) -> bool:
    digest = hashes.Hash(hashes.SHA256())
    digest.update(payload)
    try:
        public_key.verify(signature, digest.finalize(), padding.PKCS1v15())
        return True
    except Exception:
        return False


if __name__ == "__main__":
    # Example usage processing random samples
    samples = np.random.uniform(low=0.0, high=50.0, size=360)
    features = extract_features(samples)
    residues = crt_compress(features)
    payload = residues.to_bytes()
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    sig = sign_payload(payload, key)
    recovered = recover_features(residues)
    print("Features:", features)
    print("Recovered:", recovered)
    print(
        "Signature verified:",
        verify_signature(payload, sig, key.public_key()),
    )
