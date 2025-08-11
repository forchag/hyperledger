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


__all__ = ["MODULI", "crt_split", "crt_value"]
