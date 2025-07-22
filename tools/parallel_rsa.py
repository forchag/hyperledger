# Parallel RSA validation using CRT

import concurrent.futures
import os
from dataclasses import dataclass
from typing import List, Tuple
from hashlib import sha256

from cryptography.hazmat.primitives.asymmetric import rsa


def modinv(a: int, m: int) -> int:
    """Compute modular inverse using extended Euclidean algorithm."""
    if m == 0:
        raise ValueError("Modulus must be non-zero")
    lm, hm = 1, 0
    low, high = a % m, m
    while low > 1:
        r = high // low
        nm, new = hm - lm * r, high - low * r
        lm, low, hm, high = nm, new, lm, low
    return lm % m


@dataclass
class RSAKey:
    """Simple RSA key structure with CRT parameters."""

    p: int
    q: int
    d: int
    e: int

    dp: int
    dq: int
    q_inv: int

    @property
    def n(self) -> int:
        return self.p * self.q


def generate_key(bits: int = 2048) -> RSAKey:
    """Generate RSA key and pre-compute CRT parameters."""
    private = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    numbers = private.private_numbers()
    p = numbers.p
    q = numbers.q
    d = numbers.d
    e = numbers.public_numbers.e
    dp = d % (p - 1)
    dq = d % (q - 1)
    q_inv = modinv(q, p)
    return RSAKey(p=p, q=q, d=d, e=e, dp=dp, dq=dq, q_inv=q_inv)


def sign_crt(m: int, key: RSAKey) -> int:
    """Sign message digest using RSA CRT optimization."""
    m1 = pow(m, key.dp, key.p)
    m2 = pow(m, key.dq, key.q)
    h = (key.q_inv * (m1 - m2)) % key.p
    return (m2 + h * key.q) % key.n


def verify(m: int, sig: int, key: RSAKey) -> bool:
    """Verify RSA signature."""
    return pow(sig, key.e, key.n) == m % key.n


def hash_message(msg: bytes) -> int:
    return int.from_bytes(sha256(msg).digest(), "big")


def verify_single(tx: Tuple[bytes, int], key: RSAKey) -> bool:
    data, sig = tx
    m = hash_message(data)
    return verify(m, sig, key)


def verify_transactions_parallel(
    txs: List[Tuple[bytes, int]], key: RSAKey, workers: int = None
) -> List[bool]:
    """Verify multiple transactions in parallel."""
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(verify_single, tx, key) for tx in txs]
        return [f.result() for f in futures]


if __name__ == "__main__":
    key = generate_key()

    # create dummy transactions
    txs: List[Tuple[bytes, int]] = []
    for i in range(10):
        payload = os.urandom(32)
        digest = hash_message(payload)
        sig = sign_crt(digest, key)
        txs.append((payload, sig))

    results = verify_transactions_parallel(txs, key)
    print("Verification results:", results)
