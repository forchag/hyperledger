from crt_utils import select_moduli


def test_select_moduli_scales_with_memory():
    assert select_moduli(10, 100_000) == [97, 101]
    assert select_moduli(10, 500_000) == [97, 101, 103]
    assert select_moduli(10, 1_000_000) == [97, 101, 103, 107]
