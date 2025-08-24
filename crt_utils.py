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
    """Recommend a CRT moduli set based on network size and device memory.

    The heuristic balances the number of secondary nodes against available
    memory per device.  Smaller memories use fewer, smaller moduli to reduce
    residue size, while larger memories can afford a wider numeric range.
    """

    per_node = memory_bytes // max(1, node_count)
    if per_node < 32_768:
        return [97, 101]
    if per_node < 65_536:
        return [97, 101, 103]
    return [97, 101, 103, 107]


__all__ = ["MODULI", "crt_split", "crt_value", "select_moduli"]
