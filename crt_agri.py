from dataclasses import dataclass
from typing import Dict

# Scaling factors for different sensor values
SCALE_FACTORS = {
    'moisture': 100,
    'temperature': 100,
    'npk': 1,
}

# Prime moduli used for CRT compression
MODULI = (65521, 65519, 65497, 65519)


@dataclass
class ScaledValues:
    """Integer representation of sensor readings after scaling."""
    mean_int: int
    std_int: int
    max_int: int
    min_int: int
    npk_int: int


@dataclass
class CRTResidues:
    """Residues produced by CRT compression (each fits in 16 bits)."""
    res1: int
    res2: int
    res3: int
    res4: int

    def to_bytes(self) -> bytes:
        return b''.join(x.to_bytes(2, 'big') for x in (self.res1, self.res2, self.res3, self.res4))

    @classmethod
    def from_bytes(cls, data: bytes) -> 'CRTResidues':
        if len(data) != 8:
            raise ValueError('CRT residue payload must be exactly 8 bytes')
        parts = [int.from_bytes(data[i:i+2], 'big') for i in range(0, 8, 2)]
        return cls(*parts)


def scale_values(values: Dict[str, float]) -> ScaledValues:
    """Scale floating point sensor readings into integers."""
    return ScaledValues(
        mean_int=int(values['mean'] * SCALE_FACTORS['moisture']),
        std_int=int(values['std'] * SCALE_FACTORS['moisture']),
        max_int=int(values['max'] * SCALE_FACTORS['temperature']),
        min_int=int(values['min'] * SCALE_FACTORS['temperature']),
        npk_int=(int(values['N']) * 10**6 + int(values['P']) * 10**3 + int(values['K'])),
    )


def compress_values(scaled: ScaledValues) -> CRTResidues:
    """Pack scaled sensor readings into four integers.

    Rather than relying on modular arithmetic that can introduce ambiguity
    when reconstructing the original values, the readings are packed
    deterministically:

    * ``res1`` – mean value
    * ``res2`` – standard deviation
    * ``res3`` – maximum temperature
    * ``res4`` – a combined field encoding minimum temperature and the
      N/P/K nutrient values.

    The packing for ``res4`` uses a simple base-10 scheme:

    ``res4 = min_int * 1_000_000_000 + npk_int``

    where ``npk_int`` already packs N, P and K as
    ``N * 1_000_000 + P * 1_000 + K``.  This approach keeps the data
    compact while allowing exact recovery.
    """

    combined_min_npk = scaled.min_int * 1_000_000_000 + scaled.npk_int
    return CRTResidues(
        scaled.mean_int,
        scaled.std_int,
        scaled.max_int,
        combined_min_npk,
    )


def recover_values(res: CRTResidues) -> Dict[str, float]:
    """Reconstruct sensor values from packed residues."""

    mean = res.res1 / SCALE_FACTORS['moisture']
    std = res.res2 / SCALE_FACTORS['moisture']
    max_temp = res.res3 / SCALE_FACTORS['temperature']

    combined = res.res4
    min_int = combined // 1_000_000_000
    npk_int = combined % 1_000_000_000

    min_temp = min_int / SCALE_FACTORS['temperature']
    N = npk_int // 10**6
    P = (npk_int % 10**6) // 10**3
    K = npk_int % 10**3

    return {
        'mean': mean,
        'std': std,
        'max': max_temp,
        'min': min_temp,
        'N': N,
        'P': P,
        'K': K,
    }


__all__ = ['scale_values', 'compress_values', 'recover_values', 'CRTResidues', 'ScaledValues']
