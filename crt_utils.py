"""Shared utilities for handling sensor readings as CRT residues."""
from typing import List
from crt_parallel import crt_decompose, crt_reconstruct

# Pairwise coprime moduli used across the project
MODULI = (101, 103, 107)


def crt_split(value: float) -> List[int]:
    """Split ``value`` into CRT residues scaled to two decimal places."""
    scaled = int(value * 100)
    return crt_decompose(scaled, MODULI)


def crt_value(residues: List[int]) -> float:
    """Reconstruct the original value from CRT residues."""
    scaled = crt_reconstruct(residues, MODULI)
    return scaled / 100.0


def select_moduli(node_count: int, memory_bytes: int) -> List[int]:
    """Recommend a CRT moduli set based on node population and memory budget.

    Each additional modulus yields another residue per reading.  Secondary
    nodes that must relay many readings therefore pay a memory penalty for
    wider numeric ranges.  To keep payloads small, this function divides the
    available RAM across the expected number of nodes and chooses a threshold
    band:

    * ``<32 KiB`` per node – two primes ``[97, 101]``
    * ``32–64 KiB`` – three primes ``[97, 101, 103]``
    * ``>64 KiB`` – four primes ``[97, 101, 103, 107]``

    These primes are just above 100 so each residue fits in one byte, keeping
    per-reading memory roughly proportional to the number of moduli.  Staying
    within the recommended bands lets secondary nodes forward traffic with
    low latency and minimal queuing.
    """

    per_node = memory_bytes // max(1, node_count)
    if per_node < 32_768:
        return [97, 101]
    if per_node < 65_536:
        return [97, 101, 103]
    return [97, 101, 103, 107]


__all__ = ["MODULI", "crt_split", "crt_value", "select_moduli"]
