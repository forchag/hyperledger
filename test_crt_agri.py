import math
import pytest
from crt_agri import scale_values, compress_values, recover_values, CRTResidues


def nearly_equal(a, b, tol=0.01):
    return abs(a - b) <= tol


def test_roundtrip_known_values():
    values = {
        'mean': 45.23,
        'std': 3.18,
        'max': 29.8,
        'min': 22.1,
        'N': 120,
        'P': 45,
        'K': 210,
    }
    scaled = scale_values(values)
    residues = compress_values(scaled)
    recovered = recover_values(residues)

    assert nearly_equal(recovered['mean'], values['mean'])
    assert nearly_equal(recovered['std'], values['std'])
    assert nearly_equal(recovered['max'], values['max'])
    assert nearly_equal(recovered['min'], values['min'])
    assert recovered['N'] == values['N']
    assert recovered['P'] == values['P']
    assert recovered['K'] == values['K']


def test_crt_residues_serialization():
    residues = CRTResidues(1, 2, 3, 4)
    blob = residues.to_bytes()
    assert isinstance(blob, bytes)
    restored = CRTResidues.from_bytes(blob)
    assert restored == residues

    with pytest.raises(ValueError):
        CRTResidues.from_bytes(b'123')


def test_edge_case_bounds():
    values = {
        'mean': 100.0,
        'std': 0.0,
        'max': 60.0,
        'min': 60.0,
        'N': 999,
        'P': 999,
        'K': 999,
    }
    scaled = scale_values(values)
    residues = compress_values(scaled)
    recovered = recover_values(residues)

    assert nearly_equal(recovered['mean'], values['mean'])
    assert nearly_equal(recovered['std'], values['std'])
    assert nearly_equal(recovered['max'], values['max'])
    assert nearly_equal(recovered['min'], values['min'])
    assert recovered['N'] == values['N']
    assert recovered['P'] == values['P']
    assert recovered['K'] == values['K']
