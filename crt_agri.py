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
    """Compress scaled sensor readings into four 16-bit residues."""
    res1 = scaled.mean_int % MODULI[0]
    res2 = scaled.std_int % MODULI[1]
    res3 = (scaled.max_int * 10000 + scaled.min_int) % MODULI[2]
    res4 = scaled.npk_int % MODULI[3]
    return CRTResidues(res1, res2, res3, res4)


def recover_values(res: CRTResidues) -> Dict[str, float]:
    """Reconstruct sensor values from residues using brute-force search for NPK."""
    mean = res.res1 / SCALE_FACTORS['moisture']
    std = res.res2 / SCALE_FACTORS['moisture']
    # Recover max/min temperatures
    max_temp = min_temp = 0.0
    for k in range(0, 1_000_000):
        candidate = res.res3 + k * MODULI[2]
        max_int = candidate // 10000
        min_int = candidate % 10000
        if max_int < 10000 and min_int < 10000 and max_int >= min_int:
            max_temp = max_int / SCALE_FACTORS['temperature']
            min_temp = min_int / SCALE_FACTORS['temperature']
            break

    # Recover N, P, K by enumerating possible solutions within 0-999 ppm
    modulus = MODULI[3]
    N = P = K = 0
    for k in range(0, 1_000_000):
        candidate = res.res4 + k * modulus
        N = candidate // 10**6
        P = (candidate % 10**6) // 10**3
        K = candidate % 10**3
        if N < 1000 and P < 1000 and K < 1000:
            break
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
