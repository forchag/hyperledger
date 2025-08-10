"""Utilities for CRT-based decomposition of blockchain blocks.

This module implements a minimal Chinese Remainder Theorem (CRT)
framework for splitting an integer transaction block into residue streams
that can be processed in parallel by IoT devices. A coordinating node can
then reconstruct the original value from the residues.

The functions are intentionally small and rely only on Python's built-in
`pow` for modular inversion. They assume the provided moduli are pairwise
coprime so that reconstruction is unique.
"""
from math import prod
from typing import Iterable, List


def crt_decompose(block: int, moduli: Iterable[int]) -> List[int]:
    """Split ``block`` into residues for each modulus.

    Args:
        block: Integer representing the transaction block.
        moduli: Iterable of pairwise coprime integers.

    Returns:
        A list of ``block % m`` for each ``m`` in ``moduli``.
    """
    return [block % m for m in moduli]


def crt_reconstruct(residues: Iterable[int], moduli: Iterable[int]) -> int:
    """Reconstruct the original block from residues.

    Args:
        residues: Residues produced by :func:`crt_decompose`.
        moduli: The same moduli used during decomposition.

    Returns:
        The smallest non-negative integer congruent to all residues.
    """
    residues = list(residues)
    moduli = list(moduli)
    M = prod(moduli)
    x = 0
    for a_i, m_i in zip(residues, moduli):
        M_i = M // m_i
        inv = pow(M_i, -1, m_i)
        x += a_i * inv * M_i
    return x % M


__all__ = ["crt_decompose", "crt_reconstruct"]
