import numpy as np
import math
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization

# 16-bit prime moduli for CRT encoding
MODULI = (65521, 65519, 65497)

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


def crt_compress(feat: Features) -> bytes:
    """Compress selected features into six bytes using CRT."""
    scaled_mean = int(feat.mean * 100)
    scaled_std = int(feat.std * 100)
    scaled_min = int(feat.min_val * 100)
    scaled_max = int(feat.max_val * 100)
    residues = [
        scaled_mean % MODULI[0],
        scaled_std % MODULI[1],
        (scaled_max * 10000 + scaled_min) % MODULI[2],
    ]
    return b"".join(r.to_bytes(2, "big") for r in residues)


def _chinese_remainder(residues, moduli):
    total = 0
    M = math.prod(moduli)
    for r, m in zip(residues, moduli):
        Mi = M // m
        total += r * Mi * pow(Mi, -1, m)
    return total % M


def recover_features(residues: bytes) -> dict:
    r1 = int.from_bytes(residues[0:2], "big")
    r2 = int.from_bytes(residues[2:4], "big")
    r3 = int.from_bytes(residues[4:6], "big")
    mean = _chinese_remainder([r1], [MODULI[0]]) / 100.0
    std = _chinese_remainder([r2], [MODULI[1]]) / 100.0
    combined = _chinese_remainder([r3], [MODULI[2]])
    max_val = (combined // 10000) / 100.0
    min_val = (combined % 10000) / 100.0
    return {
        "min": min_val,
        "max": max_val,
        "mean": mean,
        "std": std,
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
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    sig = sign_payload(residues, key)
    recovered = recover_features(residues)
    print("Features:", features)
    print("Recovered:", recovered)
    print("Signature verified:", verify_signature(residues, sig, key.public_key()))
