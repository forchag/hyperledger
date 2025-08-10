from crt_parallel import crt_decompose, crt_reconstruct


def test_crt_roundtrip():
    moduli = [17, 19, 23]
    block = 3210  # less than product of moduli (7429)
    residues = crt_decompose(block, moduli)
    assert residues == [block % m for m in moduli]
    reconstructed = crt_reconstruct(residues, moduli)
    assert reconstructed == block
